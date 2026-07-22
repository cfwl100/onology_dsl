#!/usr/bin/env python3
"""Shared OQL validator.

This module is the single validation source used by execute_oac_operation.py as pre-execution validation gate.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "QUERY": ROOT / "schemas" / "oql-query.schema.json",
    "ASSOCIATION_QUERY": ROOT / "schemas" / "oql-association-query.schema.json",
    "AGGREGATE": ROOT / "schemas" / "oql-aggregate.schema.json",
}

ID_NAME_RE = re.compile(r"^(ID|NAME)\(([A-Za-z_][A-Za-z0-9_]*)\)$")
LOWER_ID_NAME_RE = re.compile(r"^(id|name)\(")


def make_error(code: str, message: str, path: str = "$") -> dict[str, Any]:
    return {"code": code, "message": message, "path": path}


def json_path(parts: Any) -> str:
    return "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in parts)


def is_id_name(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_NAME_RE.match(value))


def is_lower_id_name(value: Any) -> bool:
    return isinstance(value, str) and bool(LOWER_ID_NAME_RE.match(value))


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
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() can only be used in returns.kind=FUNCTION.field", f"{path}.field"))
    if kind == "FUNCTION":
        if node.get("name") in ("ID", "NAME", "id", "name"):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID/NAME must use returns.kind=FUNCTION with field=ID(...)/NAME(...)", f"{path}.name"))
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
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in conditions", f"{path}.field"))
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

    if "maxResults" in oql:
        value = oql.get("maxResults")
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(make_error("OQL_MAX_RESULTS_ERROR", "maxResults must be an integer, for example: \"maxResults\": 1000", "$.maxResults"))
        elif value < 1:
            errors.append(make_error("OQL_MAX_RESULTS_ERROR", "maxResults must be greater than or equal to 1", "$.maxResults"))

    objects = oql.get("objects", []) if isinstance(oql.get("objects", []), list) else []
    obj_aliases: set[str] = set()
    rel_aliases: set[str] = set()
    metric_aliases: set[str] = set()

    for i, obj in enumerate(objects):
        alias = obj.get("alias") if isinstance(obj, dict) else None
        if isinstance(alias, str):
            if alias in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"duplicate object alias: {alias}", f"$.objects[{i}].alias"))
            obj_aliases.add(alias)

    relationships = oql.get("relationships", []) if isinstance(oql.get("relationships", []), list) else []
    for i, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            continue
        alias = rel.get("alias")
        if isinstance(alias, str):
            if alias in rel_aliases or alias in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"invalid relationship alias: {alias}", f"$.relationships[{i}].alias"))
            rel_aliases.add(alias)
        for key in ("from", "to"):
            if rel.get(key) not in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"relationships[{i}].{key} must reference object alias", f"$.relationships[{i}].{key}"))

    all_aliases = obj_aliases | rel_aliases
    refs: list[str] = []
    walk_condition(oql.get("conditions"), refs, errors, "$.conditions")

    returns = oql.get("returns", []) if isinstance(oql.get("returns", []), list) else []
    for i, ret in enumerate(returns):
        if not isinstance(ret, dict):
            continue
        path = f"$.returns[{i}]"
        kind = ret.get("kind")
        if isinstance(ret.get("ref"), str):
            refs.append(ret["ref"])
        if kind == "EXPR":
            walk_expr(ret.get("expr"), refs, errors, f"{path}.expr")
        if kind == "FIELDS":
            fields = ret.get("fields", []) if isinstance(ret.get("fields", []), list) else []
            for j, field in enumerate(fields):
                if is_id_name(field) or is_lower_id_name(field):
                    errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must use returns.kind=FUNCTION, not FIELDS.fields[]", f"{path}.fields[{j}]"))
        if kind == "FUNCTION":
            field = ret.get("field")
            if not is_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "returns.kind=FUNCTION.field must be ID(fieldName) or NAME(fieldName) with uppercase function name", f"{path}.field"))
            if is_lower_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "id()/name() must be normalized to uppercase ID()/NAME()", f"{path}.field"))
            if op == "AGGREGATE":
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() does not express aggregate metric; use GROUP_BY or METRIC in AGGREGATE", path))
        if kind in ("GROUP_BY", "METRIC"):
            field = ret.get("field")
            if is_id_name(field) or is_lower_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in AGGREGATE returns", f"{path}.field"))
        if kind == "METRIC" and isinstance(ret.get("alias"), str):
            metric_aliases.add(ret["alias"])
        if kind == "METRIC" and ret.get("function") != "COUNT" and ret.get("field") == "*":
            errors.append(make_error("OQL_SEMANTIC_ERROR", "only COUNT can use field '*'", f"{path}.field"))

    orders = oql.get("orders", []) if isinstance(oql.get("orders", []), list) else []
    for i, order in enumerate(orders):
        if isinstance(order, dict) and (is_id_name(order.get("field")) or is_lower_id_name(order.get("field"))):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in orders", f"$.orders[{i}].field"))

    for ref in refs:
        if ref not in all_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"unknown alias reference: {ref}"))

    aggregate_aliases: list[str] = []
    walk_aggregate_filter(oql.get("aggregateFilter"), aggregate_aliases)
    for alias in aggregate_aliases:
        if alias not in metric_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"unknown metricAlias: {alias}", "$.aggregateFilter"))
    return errors


def schema_errors(oql: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    op = str(oql.get("operation", "")).upper()
    schema = load_schema(op, root)
    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema)
    return [make_error("OQL_SCHEMA_ERROR", item.message, json_path(item.path)) for item in validator.iter_errors(oql)]


def validate_oql_dict(oql: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    if not isinstance(oql, dict):
        return [make_error("OQL_VALIDATION_ERROR", "top-level JSON must be object")]
    try:
        return schema_errors(oql, root) + semantic_errors(oql)
    except Exception as exc:
        return [make_error("OQL_VALIDATION_ERROR", str(exc))]


def is_valid_oql(oql: dict[str, Any], root: Path | None = None) -> bool:
    return not validate_oql_dict(oql, root)
