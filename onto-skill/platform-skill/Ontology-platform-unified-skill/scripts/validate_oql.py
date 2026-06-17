#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
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


def out(ok: bool, errors: list[dict[str, Any]] | None = None) -> int:
    print(json.dumps({"success": ok, "errors": errors or []}, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


def error(code: str, message: str, path: str = "$") -> dict[str, Any]:
    return {"code": code, "message": message, "path": path}


def load_json(args: argparse.Namespace) -> dict[str, Any]:
    if args.oac_json:
        raw = args.oac_json
    elif args.input == "-":
        raw = sys.stdin.read()
    elif args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raise ValueError("missing --oac-json or --input")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be object")
    return data


def is_id_name_field(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_NAME_RE.match(value))


def is_lower_id_name_field(value: Any) -> bool:
    return isinstance(value, str) and bool(LOWER_ID_NAME_RE.match(value))


def inner_id_name_field(value: str) -> str:
    match = ID_NAME_RE.match(value)
    return match.group(2) if match else ""


def walk_expr(node: Any, refs: list[str], errors: list[dict[str, Any]], path: str) -> None:
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    if kind == "FIELD":
        ref = node.get("ref")
        if isinstance(ref, str):
            refs.append(ref)
        field = node.get("field")
        if is_id_name_field(field) or is_lower_id_name_field(field):
            errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() can only be used in returns.kind=FUNCTION.field", path + ".field"))
    if kind == "FUNCTION":
        name = node.get("name")
        if name in ("ID", "NAME", "id", "name"):
            errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID/NAME must not be expressed as expr.kind=FUNCTION; use returns.kind=FUNCTION with field=ID(...)/NAME(...)", path + ".name"))
        for i, arg in enumerate(node.get("args", []) if isinstance(node.get("args", []), list) else []):
            walk_expr(arg, refs, errors, f"{path}.args[{i}]")


def walk_condition(node: Any, refs: list[str], errors: list[dict[str, Any]], path: str) -> None:
    if not isinstance(node, dict):
        return
    if node.get("kind") == "PREDICATE":
        if isinstance(node.get("ref"), str):
            refs.append(node["ref"])
        if is_id_name_field(node.get("field")) or is_lower_id_name_field(node.get("field")):
            errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in conditions", path + ".field"))
        walk_expr(node.get("left"), refs, errors, path + ".left")
    if node.get("kind") == "GROUP":
        children = node.get("children", []) if isinstance(node.get("children", []), list) else []
        for i, child in enumerate(children):
            walk_condition(child, refs, errors, f"{path}.children[{i}]")


def walk_af(node: Any, aliases: list[str]) -> None:
    if not isinstance(node, dict):
        return
    if node.get("kind") == "METRIC_PREDICATE" and isinstance(node.get("metricAlias"), str):
        aliases.append(node["metricAlias"])
    if node.get("kind") == "GROUP":
        for child in node.get("children", []) if isinstance(node.get("children", []), list) else []:
            walk_af(child, aliases)


def semantic(oql: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    op = str(oql.get("operation", "")).upper()
    objects = oql.get("objects", []) if isinstance(oql.get("objects", []), list) else []
    obj_aliases: set[str] = set()
    rel_aliases: set[str] = set()
    metric_aliases: set[str] = set()

    for i, obj in enumerate(objects):
        alias = obj.get("alias") if isinstance(obj, dict) else None
        if isinstance(alias, str):
            if alias in obj_aliases:
                errors.append(error("OQL_SEMANTIC_ERROR", f"duplicate object alias: {alias}", f"$.objects[{i}].alias"))
            obj_aliases.add(alias)

    relationships = oql.get("relationships", []) if isinstance(oql.get("relationships", []), list) else []
    for i, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            continue
        alias = rel.get("alias")
        if isinstance(alias, str):
            if alias in rel_aliases or alias in obj_aliases:
                errors.append(error("OQL_SEMANTIC_ERROR", f"invalid relationship alias: {alias}", f"$.relationships[{i}].alias"))
            rel_aliases.add(alias)
        for key in ("from", "to"):
            if rel.get(key) not in obj_aliases:
                errors.append(error("OQL_SEMANTIC_ERROR", f"relationships[{i}].{key} must reference object alias", f"$.relationships[{i}].{key}"))

    all_aliases = obj_aliases | rel_aliases
    refs: list[str] = []
    walk_condition(oql.get("conditions"), refs, errors, "$.conditions")

    returns = oql.get("returns", []) if isinstance(oql.get("returns", []), list) else []
    for i, ret in enumerate(returns):
        if not isinstance(ret, dict):
            continue
        path = f"$.returns[{i}]"
        kind = ret.get("kind")
        ref = ret.get("ref")
        if isinstance(ref, str):
            refs.append(ref)
        if kind == "EXPR":
            walk_expr(ret.get("expr"), refs, errors, path + ".expr")
        if kind == "FIELDS":
            for j, field in enumerate(ret.get("fields", []) if isinstance(ret.get("fields", []), list) else []):
                if is_id_name_field(field) or is_lower_id_name_field(field):
                    errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must use returns.kind=FUNCTION, not FIELDS.fields[]", f"{path}.fields[{j}]"))
        if kind == "FUNCTION":
            field = ret.get("field")
            if not is_id_name_field(field):
                errors.append(error("OQL_ID_NAME_USAGE_ERROR", "returns.kind=FUNCTION.field must be ID(fieldName) or NAME(fieldName) with uppercase function name", path + ".field"))
            if is_lower_id_name_field(field):
                errors.append(error("OQL_ID_NAME_USAGE_ERROR", "id()/name() must be normalized to uppercase ID()/NAME()", path + ".field"))
            if op == "AGGREGATE":
                errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() does not express aggregate metric; use GROUP_BY or METRIC in AGGREGATE", path))
            if is_id_name_field(field) and inner_id_name_field(field) == "*":
                errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() fieldName must be a concrete object field", path + ".field"))
        if kind in ("GROUP_BY", "METRIC"):
            field = ret.get("field")
            if is_id_name_field(field) or is_lower_id_name_field(field):
                errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in AGGREGATE returns", path + ".field"))
        if kind == "METRIC" and isinstance(ret.get("alias"), str):
            metric_aliases.add(ret["alias"])
        if kind == "METRIC" and ret.get("function") != "COUNT" and ret.get("field") == "*":
            errors.append(error("OQL_SEMANTIC_ERROR", "only COUNT can use field '*'", path + ".field"))

    orders = oql.get("orders", []) if isinstance(oql.get("orders", []), list) else []
    for i, order in enumerate(orders):
        if isinstance(order, dict) and (is_id_name_field(order.get("field")) or is_lower_id_name_field(order.get("field"))):
            errors.append(error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in orders", f"$.orders[{i}].field"))

    for ref in refs:
        if ref not in all_aliases:
            errors.append(error("OQL_SEMANTIC_ERROR", f"unknown alias reference: {ref}"))

    af_aliases: list[str] = []
    walk_af(oql.get("aggregateFilter"), af_aliases)
    for alias in af_aliases:
        if alias not in metric_aliases:
            errors.append(error("OQL_SEMANTIC_ERROR", f"unknown metricAlias: {alias}", "$.aggregateFilter"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oac-json")
    parser.add_argument("--input")
    args = parser.parse_args()
    try:
        oql = load_json(args)
        op = str(oql.get("operation", "")).upper()
        schema_path = SCHEMAS.get(op)
        if not schema_path:
            raise ValueError(f"unsupported operation: {op}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)
        validator = Draft7Validator(schema)
        errors = [error("OQL_SCHEMA_ERROR", item.message, "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in item.path)) for item in validator.iter_errors(oql)]
        if not errors:
            errors = semantic(oql)
        return out(not errors, errors)
    except Exception as exc:
        return out(False, [error("OQL_VALIDATION_ERROR", str(exc))])


if __name__ == "__main__":
    raise SystemExit(main())
