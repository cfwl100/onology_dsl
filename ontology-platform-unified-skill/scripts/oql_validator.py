#!/usr/bin/env python3
"""Shared OQL validator.

This module is the single validation source used by both:
- validate_oql.py: standalone CLI validation
- execute_oac_operation.py: pre-execution validation gate

No external dependencies - embeds minimal JSON Schema Draft7 validation.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "QUERY": ROOT / "schemas" / "oql-query.schema.json",
    "ASSOCIATION_QUERY": ROOT / "schemas" / "oql-association-query.schema.json",
    "AGGREGATE": ROOT / "schemas" / "oql-aggregate.schema.json",
}

ID_NAME_RE = re.compile(r"^[A-Z][A-Z0-9]*\(([A-Za-z_][A-Za-z0-9_]*)\)$")
LOWER_ID_NAME_RE = re.compile(r"^(id|name)\(")
ALIAS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def make_error(code: str, message: str, path: str = "$") -> dict[str, Any]:
    return {"code": code, "message": message, "path": path}


def json_path(parts: Any) -> str:
    return "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in parts)


def is_id_name(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_NAME_RE.match(value))


def is_lower_id_name(value: Any) -> bool:
    return isinstance(value, str) and bool(LOWER_ID_NAME_RE.match(value))


def is_valid_alias(value: Any) -> bool:
    return isinstance(value, str) and bool(ALIAS_RE.match(value))


def load_schema(operation: str, root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    schemas = {
        "QUERY": base / "schemas" / "oql-query.schema.json",
        "ASSOCIATION_QUERY": base / "schemas" / "oql-association-query.schema.json",
        "AGGREGATE": base / "schemas" / "oql-aggregate.schema.json",
    }
    schema_path = schemas.get(operation.upper())
    if not schema_path:
        raise ValueError(f"unsupported operation: {operation}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def walk_expr(node: Any, refs: list[str], errors: list[dict[str, Any]], path: str) -> None:
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    if kind == "FIELD":
        if isinstance(node.get("ref"), str):
            refs.append(node["ref"])
        if is_id_name(node.get("field")) or is_lower_id_name(node.get("field")):
            errors.append(
                make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() can only be used in returns.kind=FUNCTION.field",
                           f"{path}.field"))
    if kind == "FUNCTION":
        if node.get("name") in ("ID", "NAME", "id", "name"):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR",
                                     "ID/NAME must use returns.kind=FUNCTION with field=ID(...)/NAME(...)",
                                     f"{path}.name"))
        args = node.get("args", []) if isinstance(node.get("args", []), list) else []
        for i, arg in enumerate(args):
            walk_expr(arg, refs, errors, f"{path}.args[{i}]")


def walk_condition(node: Any, refs: list[str], errors: list[dict[str, Any]], path: str) -> None:
    if not isinstance(node, dict):
        return
    if node.get("kind") == "PREDICATE":
        if isinstance(node.get("ref"), str):
            refs.append(node["ref"])
        if is_id_name(node.get("field")) or is_lower_id_name(node.get("field")):
            errors.append(
                make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in conditions", f"{path}.field"))
        walk_expr(node.get("left"), refs, errors, f"{path}.left")
    if node.get("kind") == "GROUP":
        children = node.get("children", []) if isinstance(node.get("children", []), list) else []
        for i, child in enumerate(children):
            walk_condition(child, refs, errors, f"{path}.children[{i}]")


def walk_aggregate_filter(node: Any, aliases: list[str]) -> None:
    if not isinstance(node, dict):
        return
    if node.get("kind") == "METRIC_PREDICATE" and isinstance(node.get("metricAlias"), str):
        aliases.append(node["metricAlias"])
    if node.get("kind") == "GROUP":
        children = node.get("children", []) if isinstance(node.get("children", []), list) else []
        for child in children:
            walk_aggregate_filter(child, aliases)


def semantic_errors(oql: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    op = str(oql.get("operation", "")).upper()

    validate_maxResults(errors, oql)

    objects = oql.get("objects", []) if isinstance(oql.get("objects", []), list) else []
    obj_aliases: set[str] = set()
    rel_aliases: set[str] = set()
    metric_aliases: set[str] = set()

    validate_objects_oql(errors, obj_aliases, objects)

    relationships = oql.get("relationships", []) if isinstance(oql.get("relationships", []), list) else []
    validate_relationships_oql(errors, obj_aliases, rel_aliases, relationships)

    all_aliases = obj_aliases | rel_aliases

    source_query_aliases: set[str] = set()
    source_queries = oql.get("sourceQuery", []) if isinstance(oql.get("sourceQuery", []), list) else []
    validate_sourceQuery_oql(errors, source_queries, source_query_aliases)

    returns_aliases: set[str] = set()
    refs: list[str] = []
    walk_condition(oql.get("conditions"), refs, errors, "$.conditions")

    returns = oql.get("returns", []) if isinstance(oql.get("returns", []), list) else []
    validate_returns(errors, metric_aliases, obj_aliases, op, refs, rel_aliases, returns, returns_aliases)

    orders = oql.get("orders", []) if isinstance(oql.get("orders", []), list) else []
    for i, order in enumerate(orders):
        if isinstance(order, dict) and (is_id_name(order.get("field")) or is_lower_id_name(order.get("field"))):
            errors.append(
                make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in orders", f"$.orders[{i}].field"))

    all_aliases = obj_aliases | rel_aliases | returns_aliases
    for ref in refs:
        if ref not in all_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"unknown alias reference: {ref}"))

    aggregate_aliases: list[str] = []
    walk_aggregate_filter(oql.get("aggregateFilter"), aggregate_aliases)
    for alias in aggregate_aliases:
        if alias not in metric_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"unknown metricAlias: {alias}", "$.aggregateFilter"))
    return errors


def validate_maxResults(errors, oql):
    if "maxResults" in oql:
        value = oql.get("maxResults")
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(
                make_error("OQL_MAX_RESULTS_ERROR", "maxResults must be an integer, for example: \"maxResults\": 1000",
                           "$.maxResults"))
        elif value < 1:
            errors.append(
                make_error("OQL_MAX_RESULTS_ERROR", "maxResults must be greater than or equal to 1", "$.maxResults"))


def validate_returns(errors, metric_aliases, obj_aliases, op, refs, rel_aliases, returns, returns_aliases):
    for i, ret in enumerate(returns):
        if not isinstance(ret, dict):
            continue
        path = f"$.returns[{i}]"
        kind = ret.get("kind")
        ret_alias = ret.get("alias")
        # returns[G/M/E/FIELDS] alias 格式与去重校验
        validate_return_kind(errors, kind, obj_aliases, path, rel_aliases, ret_alias, returns_aliases)
        if isinstance(ret.get("ref"), str):
            refs.append(ret["ref"])
        if kind == "EXPR":
            walk_expr(ret.get("expr"), refs, errors, f"{path}.expr")
        if kind == "FIELDS":
            fields = ret.get("fields", []) if isinstance(ret.get("fields", []), list) else []
            for j, field in enumerate(fields):
                if is_id_name(field) or is_lower_id_name(field):
                    errors.append(make_error("OQL_ID_NAME_USAGE_ERROR",
                                             "ID()/NAME() must use returns.kind=FUNCTION, not FIELDS.fields[]",
                                             f"{path}.fields[{j}]"))
        validate_return_function(errors, kind, op, path, refs, ret)
        if kind in ("GROUP_BY", "METRIC"):
            field = ret.get("field")
            if is_id_name(field) or is_lower_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in AGGREGATE returns",
                                         f"{path}.field"))
        if kind == "METRIC" and isinstance(ret.get("alias"), str):
            metric_aliases.add(ret["alias"])
        if kind == "METRIC" and ret.get("function") != "COUNT" and ret.get("field") == "*":
            errors.append(make_error("OQL_SEMANTIC_ERROR", "only COUNT can use field '*'", f"{path}.field"))


def validate_return_function(errors, kind, op, path, refs, ret):
    if kind == "FUNCTION":
        if ret.get("name") is not None:
            # functionReturn 风格：name + args + alias
            if ret.get("name", "").lower() in ("id", "name"):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR",
                                         "ID/NAME must use returns.kind=FUNCTION with field=ID(...)/NAME(...)",
                                         f"{path}.name"))
            args = ret.get("args", [])
            if isinstance(args, list):
                for ai, arg in enumerate(args):
                    walk_expr(arg, refs, errors, f"{path}.args[{ai}]")
        else:
            # idNameReturn 风格：field = ID(xxx)/NAME(xxx)
            field = ret.get("field")
            if not is_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR",
                                         "returns.kind=FUNCTION.field must be ID(fieldName) or NAME(fieldName) with uppercase function name",
                                         f"{path}.field"))
            if is_lower_id_name(field):
                errors.append(
                    make_error("OQL_ID_NAME_USAGE_ERROR", "id()/name() must be normalized to uppercase ID()/NAME()",
                               f"{path}.field"))
        if op == "AGGREGATE":
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR",
                                     "ID()/NAME() does not express aggregate metric; use GROUP_BY or METRIC in AGGREGATE",
                                     path))


def validate_return_kind(errors, kind, obj_aliases, path, rel_aliases, ret_alias, returns_aliases):
    if kind in ("GROUP_BY", "METRIC", "EXPR", "FIELDS") and ret_alias is not None:
        if not is_valid_alias(ret_alias):
            errors.append(make_error("OQL_SEMANTIC_ERROR",
                                     f"alias must start with a letter or underscore, and contain only letters/digits/underscores; got: {ret_alias!r}",
                                     f"{path}.alias"))
        elif ret_alias in returns_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"duplicate return alias: {ret_alias}", f"{path}.alias"))
        elif ret_alias in obj_aliases or ret_alias in rel_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR",
                                     f"return alias '{ret_alias}' conflicts with object or relationship alias",
                                     f"{path}.alias"))
        if isinstance(ret_alias, str):
            returns_aliases.add(ret_alias)


def validate_sourceQuery_oql(errors, source_queries, source_query_aliases):
    for i, sq in enumerate(source_queries):
        if not isinstance(sq, dict):
            continue
        out_alias = sq.get("outputAs")
        if not is_valid_alias(out_alias):
            errors.append(make_error("OQL_SEMANTIC_ERROR",
                                     f"sourceQuery[{i}].outputAs must be a valid alias; got: {out_alias!r}",
                                     f"$.sourceQuery[{i}].outputAs"))
        elif out_alias in source_query_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"duplicate sourceQuery outputAs alias: {out_alias}",
                                     f"$.sourceQuery[{i}].outputAs"))
        if isinstance(out_alias, str):
            source_query_aliases.add(out_alias)


def validate_relationships_oql(errors, obj_aliases, rel_aliases, relationships):
    for i, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            continue
        alias = rel.get("alias")
        if not is_valid_alias(alias):
            errors.append(make_error("OQL_SEMANTIC_ERROR",
                                     f"alias must start with a letter or underscore, and contain only letters/digits/underscores; got: {alias!r}",
                                     f"$.relationships[{i}].alias"))
        elif alias in rel_aliases or alias in obj_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"invalid relationship alias: {alias}",
                                     f"$.relationships[{i}].alias"))
        if isinstance(alias, str):
            rel_aliases.add(alias)
        for key in ("from", "to"):
            if rel.get(key) not in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"relationships[{i}].{key} must reference object alias",
                                         f"$.relationships[{i}].{key}"))


def validate_objects_oql(errors, obj_aliases, objects):
    for i, obj in enumerate(objects):
        alias = obj.get("alias") if isinstance(obj, dict) else None
        if not is_valid_alias(alias):
            errors.append(make_error("OQL_SEMANTIC_ERROR",
                                     f"alias must start with a letter or underscore, and contain only letters/digits/underscores; got: {alias!r}",
                                     f"$.objects[{i}].alias"))
        elif alias in obj_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"duplicate object alias: {alias}", f"$.objects[{i}].alias"))
        if isinstance(alias, str):
            obj_aliases.add(alias)


TYPE_TO_BUILTIN = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}


def _validate_type(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                   path: list[str]) -> None:
    if instance is None:
        if schema.get("type") == "null":
            return
        if schema.get("type") == "string" and instance == "" and schema.get("minLength", 1) > 0:
            validator_fn(schema, instance, errors, path)
        return

    type_name = schema.get("type")
    if type_name is None:
        return

    expected_types = TYPE_TO_BUILTIN.get(type_name, ())
    if not isinstance(expected_types, tuple):
        expected_types = (expected_types,)

    if not isinstance(instance, expected_types):
        validator_fn(schema, instance, errors, path)


def _validate_const(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                    path: list[str]) -> None:
    const_value = schema.get("const")
    if const_value is not None and instance != const_value:
        validator_fn(schema, instance, errors, path)


def _validate_min_length(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                         path: list[str]) -> None:
    min_length = schema.get("minLength")
    if min_length is not None and isinstance(instance, str) and len(instance) < min_length:
        validator_fn(schema, instance, errors, path)


def _validate_pattern(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                      path: list[str]) -> None:
    pattern = schema.get("pattern")
    if pattern is not None and isinstance(instance, str):
        if not re.match(pattern, instance):
            validator_fn(schema, instance, errors, path)


def _validate_min_items(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                        path: list[str]) -> None:
    min_items = schema.get("minItems")
    if min_items is not None and isinstance(instance, list) and len(instance) < min_items:
        validator_fn(schema, instance, errors, path)


def _validate_unique_items(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                           path: list[str]) -> None:
    unique_items = schema.get("uniqueItems")
    if unique_items and isinstance(instance, list):
        seen = set()
        for i, item in enumerate(instance):
            item_key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
            if item_key in seen:
                validator_fn(schema, instance, errors, path)
                break
            seen.add(item_key)


def _validate_enum(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                   path: list[str]) -> None:
    enum_values = schema.get("enum")
    if enum_values is not None and instance not in enum_values:
        validator_fn(schema, instance, errors, path)


def _validate_minimum(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                      path: list[str]) -> None:
    minimum = schema.get("minimum")
    if minimum is not None and isinstance(instance, (int, float)) and instance < minimum:
        validator_fn(schema, instance, errors, path)


def _validate_additional_properties(validator_fn: Any, schema: dict[str, Any], instance: Any,
                                    errors: list[dict[str, Any]], path: list[str]) -> None:
    additional_props = schema.get("additionalProperties")
    if additional_props is False and isinstance(instance, dict):
        allowed_props = set(schema.get("properties", {}).keys())
        extra_props = set(instance.keys()) - allowed_props
        if extra_props:
            for prop in extra_props:
                if prop not in allowed_props:
                    validator_fn(schema, instance, errors, path + [prop])
                    break


def _validate_required(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                       path: list[str]) -> None:
    required_props = schema.get("required")
    if required_props is not None and isinstance(instance, dict):
        for prop in required_props:
            if prop not in instance:
                validator_fn(schema, instance, errors, path + [prop])


def _validate_one_of(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                     path: list[str]) -> None:
    one_of_list = schema.get("oneOf")
    if one_of_list is not None:
        matched_count = 0
        for idx, sub_schema in enumerate(one_of_list):
            sub_errors = []
            _validate_object(sub_schema, instance, sub_errors, path + ["oneOf", idx])
            if not sub_errors:
                matched_count += 1

        if matched_count != 1:
            validator_fn(schema, instance, errors, path)


def _validate_any_of(validator_fn: Any, schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]],
                     path: list[str]) -> None:
    any_of_list = schema.get("anyOf")
    if any_of_list is not None:
        for idx, sub_schema in enumerate(any_of_list):
            sub_errors = []
            _validate_object(sub_schema, instance, sub_errors, path + ["anyOf", idx])
            if not sub_errors:
                return

        validator_fn(schema, instance, errors, path)


def _validate_array_items(validator_fn: Any, schema: dict[str, Any], instance: list, errors: list[dict[str, Any]],
                          path: list[str]) -> None:
    items_schema = schema.get("items")
    if items_schema is not None and isinstance(instance, list):
        for idx, item in enumerate(instance):
            item_errors = []
            _validate_object(items_schema, item, item_errors, path + [idx])
            for err in item_errors:
                errors.append(err)


def _validate_object(schema: dict[str, Any], instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
    if schema.get("type") == "object" and not isinstance(instance, dict):
        return

    if schema.get("type") == "array" and not isinstance(instance, list):
        return

    if isinstance(instance, dict):
        _validate_required(
            lambda s, i, e, p: e.append(make_error("OQL_SCHEMA_ERROR", f"required property missing", json_path(p))),
            schema, instance, errors, path)
        _validate_additional_properties(lambda s, i, e, p: e.append(
            make_error("OQL_SCHEMA_ERROR", f"additional property not allowed", json_path(p))), schema, instance, errors,
                                        path)

    if isinstance(instance, list):
        _validate_min_items(lambda s, i, e, p: e.append(
            make_error("OQL_SCHEMA_ERROR", f"array must have at least {s.get('minItems')} items", json_path(p))),
                            schema, instance, errors, path)
        _validate_unique_items(
            lambda s, i, e, p: e.append(make_error("OQL_SCHEMA_ERROR", f"array items must be unique", json_path(p))),
            schema, instance, errors, path)
        _validate_array_items(lambda s, i, e, p: None, schema, instance, errors, path)

    if schema.get("$ref"):
        return

    if schema.get("oneOf"):
        _validate_one_of(lambda s, i, e, p: None, schema, instance, errors, path)

    if schema.get("anyOf"):
        _validate_any_of(lambda s, i, e, p: None, schema, instance, errors, path)


class MiniValidator:
    def __init__(self, schema: dict[str, Any], root_schema: dict[str, Any] | None = None):
        self.root_schema = root_schema if root_schema else schema
        self.schema = resolve_all_refs(schema, self.root_schema)

    def _make_error(self, message: str, path: list[str]) -> dict[str, Any]:
        return make_error("OQL_SCHEMA_ERROR", message, json_path(path))

    def _validate_type(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        type_name = self.schema.get("type")
        if type_name is None:
            return

        if isinstance(type_name, list):
            type_names = type_name
        else:
            type_names = [type_name]

        expected_types = []
        for tn in type_names:
            mapped = TYPE_TO_BUILTIN.get(tn, ())
            if isinstance(mapped, tuple):
                expected_types.extend(mapped)
            else:
                expected_types.append(mapped)
        expected_types = tuple(expected_types) if expected_types else (type(None),)

        if instance is not None and not isinstance(instance, expected_types):
            errors.append(self._make_error(f"expected {type_name}, got {type(instance).__name__}", path))

    def _validate_const(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        const_value = self.schema.get("const")
        if const_value is not None and instance != const_value:
            errors.append(self._make_error(f"expected {const_value}", path))

    def _validate_enum(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        enum_values = self.schema.get("enum")
        if enum_values is not None and instance not in enum_values:
            errors.append(self._make_error(f"value must be one of {enum_values}", path))

    def _validate_min_length(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        min_length = self.schema.get("minLength")
        if min_length is not None and isinstance(instance, str) and len(instance) < min_length:
            errors.append(self._make_error(f"string length must be at least {min_length}", path))

    def _validate_minimum(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        minimum = self.schema.get("minimum")
        if minimum is not None and isinstance(instance, (int, float)) and instance < minimum:
            errors.append(self._make_error(f"value must be >= {minimum}", path))

    def _validate_pattern(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        pattern = self.schema.get("pattern")
        if pattern is not None and isinstance(instance, str):
            if not re.match(pattern, instance):
                errors.append(self._make_error(f"string does not match pattern {pattern}", path))

    def _validate_required(self, instance: dict, errors: list[dict[str, Any]], path: list[str]) -> None:
        required_props = self.schema.get("required")
        if required_props is not None and isinstance(instance, dict):
            for prop in required_props:
                if prop not in instance:
                    errors.append(self._make_error(f"required property '{prop}' is missing", path + [prop]))

    def _validate_additional_properties(self, instance: dict, errors: list[dict[str, Any]], path: list[str]) -> None:
        additional_props = self.schema.get("additionalProperties")
        if additional_props is False and isinstance(instance, dict):
            allowed_props = set(self.schema.get("properties", {}).keys())
            extra_props = set(instance.keys()) - allowed_props
            for prop in extra_props:
                errors.append(self._make_error(f"additional property '{prop}' not allowed", path + [prop]))

    def _validate_array(self, instance: list, errors: list[dict[str, Any]], path: list[str]) -> None:
        min_items = self.schema.get("minItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(self._make_error(f"array must have at least {min_items} items", path))

        unique_items = self.schema.get("uniqueItems")
        if unique_items and len(instance) != len(
                set(json.dumps(i, sort_keys=True) if isinstance(i, (dict, list)) else i for i in instance)):
            errors.append(self._make_error("array items must be unique", path))

        items_schema = self.schema.get("items")
        if items_schema:
            for idx, item in enumerate(instance):
                item_validator = MiniValidator(items_schema)
                item_validator.validate(item, errors, path + [idx])

    def _validate_one_of(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        one_of_list = self.schema.get("oneOf")
        if one_of_list is not None:
            matched_count = 0
            for idx, sub_schema in enumerate(one_of_list):
                sub_errors = []
                sub_validator = MiniValidator(sub_schema)
                sub_validator.validate(instance, sub_errors, path + ["oneOf", idx])
                if not sub_errors:
                    matched_count += 1

            if matched_count != 1:
                errors.append(self._make_error(f"instance must match exactly one schema in oneOf", path))

    def _validate_any_of(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        any_of_list = self.schema.get("anyOf")
        if any_of_list is not None:
            for idx, sub_schema in enumerate(any_of_list):
                sub_errors = []
                sub_validator = MiniValidator(sub_schema)
                sub_validator.validate(instance, sub_errors, path + ["anyOf", idx])
                if not sub_errors:
                    return

            errors.append(self._make_error(f"instance must match at least one schema in anyOf", path))

    def _validate_not(self, instance: Any, errors: list[dict[str, Any]], path: list[str]) -> None:
        not_schema = self.schema.get("not")
        if not_schema is not None:
            sub_errors = []
            sub_validator = MiniValidator(not_schema)
            sub_validator.validate(instance, sub_errors, path + ["not"])
            if not sub_errors:
                errors.append(self._make_error("instance must not match schema in 'not'", path))

    def _validate_object_properties(self, instance: dict, errors: list[dict[str, Any]], path: list[str]) -> None:
        properties = self.schema.get("properties")
        if properties:
            for prop, prop_schema in properties.items():
                if prop in instance:
                    prop_validator = MiniValidator(prop_schema)
                    prop_validator.validate(instance[prop], errors, path + [prop])

    def validate(self, instance: Any, errors: list[dict[str, Any]], path: list[str] | None = None) -> None:
        if path is None:
            path = []

        self._validate_type(instance, errors, path)
        self._validate_const(instance, errors, path)
        self._validate_enum(instance, errors, path)

        if isinstance(instance, str):
            self._validate_min_length(instance, errors, path)
            self._validate_pattern(instance, errors, path)

        if isinstance(instance, (int, float)):
            self._validate_minimum(instance, errors, path)

        if isinstance(instance, dict):
            self._validate_required(instance, errors, path)
            self._validate_additional_properties(instance, errors, path)
            self._validate_object_properties(instance, errors, path)

        if isinstance(instance, list):
            self._validate_array(instance, errors, path)

        self._validate_one_of(instance, errors, path)
        self._validate_any_of(instance, errors, path)
        self._validate_not(instance, errors, path)

    def iter_errors(self, instance: Any) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        self.validate(instance, errors)
        return errors


def resolve_refs(schema: dict[str, Any], root_schema: dict[str, Any], seen: list[str] | None = None, depth: int = 0, max_depth: int = 50) -> dict[str, Any]:
    if depth > max_depth:
        return schema
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref_path = schema["$ref"]
        if ref_path.startswith("#/definitions/"):
            def_name = ref_path[len("#/definitions/"):]
            if seen is None:
                seen = []
            if def_name in seen:
                return schema
            def_schema = root_schema.get("definitions", {}).get(def_name, {})
            return resolve_refs(def_schema, root_schema, seen + [def_name], depth + 1, max_depth)
        return schema
    result = {}
    for key, value in schema.items():
        if key == "$ref":
            continue
        if isinstance(value, list):
            result[key] = [resolve_refs(item, root_schema, seen, depth + 1, max_depth) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = resolve_refs(value, root_schema, seen, depth + 1, max_depth)
    return result


def resolve_all_refs(schema: dict[str, Any], root_schema: dict[str, Any] | None = None, depth: int = 0, max_depth: int = 50) -> dict[str, Any]:
    if depth > max_depth:
        return schema
    if root_schema is None:
        root_schema = schema

    result = {}
    for key, value in schema.items():
        if key == "$ref":
            continue
        elif isinstance(value, dict):
            result[key] = resolve_all_refs(value, root_schema, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                resolve_all_refs(item, root_schema, depth + 1, max_depth) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    if "$ref" in schema:
        resolved = resolve_refs(schema, root_schema, depth=0, max_depth=max_depth)
        result.update(resolved)

    return result


def schema_errors(oql: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    op = str(oql.get("operation", "")).upper()
    schema = load_schema(op, root)
    schema = resolve_all_refs(schema)
    validator = MiniValidator(schema, schema)
    return validator.iter_errors(oql)


def validate_oql_dict(oql: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    if not isinstance(oql, dict):
        return [make_error("OQL_VALIDATION_ERROR", "top-level JSON must be object")]
    try:
        return schema_errors(oql, root) + semantic_errors(oql)
    except Exception as exc:
        return [make_error("OQL_VALIDATION_ERROR", str(exc))]


def is_valid_oql(oql: dict[str, Any], root: Path | None = None) -> bool:
    return not validate_oql_dict(oql, root)