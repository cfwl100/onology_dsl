#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "QUERY": ROOT / "schemas" / "oql-query.schema.json",
    "ASSOCIATION_QUERY": ROOT / "schemas" / "oql-association-query.schema.json",
    "AGGREGATE": ROOT / "schemas" / "oql-aggregate.schema.json",
}

def out(ok, errors=None):
    print(json.dumps({"success": ok, "errors": errors or []}, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1

def error(code, message, path="$"):
    return {"code": code, "message": message, "path": path}

def load_json(args):
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

def walk_condition(node, refs):
    if not isinstance(node, dict):
        return
    if node.get("kind") == "PREDICATE":
        if isinstance(node.get("ref"), str):
            refs.append(node["ref"])
        left = node.get("left")
        if isinstance(left, dict) and left.get("kind") == "FIELD" and isinstance(left.get("ref"), str):
            refs.append(left["ref"])
        if isinstance(left, dict) and left.get("kind") == "FUNCTION":
            for arg in left.get("args", []):
                walk_expr(arg, refs)
    if node.get("kind") == "GROUP":
        for child in node.get("children", []):
            walk_condition(child, refs)

def walk_expr(node, refs):
    if not isinstance(node, dict):
        return
    if node.get("kind") == "FIELD" and isinstance(node.get("ref"), str):
        refs.append(node["ref"])
    if node.get("kind") == "FUNCTION":
        for arg in node.get("args", []):
            walk_expr(arg, refs)

def walk_af(node, aliases):
    if not isinstance(node, dict):
        return
    if node.get("kind") == "METRIC_PREDICATE" and isinstance(node.get("metricAlias"), str):
        aliases.append(node["metricAlias"])
    if node.get("kind") == "GROUP":
        for child in node.get("children", []):
            walk_af(child, aliases)

def semantic(oql):
    errors = []
    objects = oql.get("objects", []) if isinstance(oql.get("objects", []), list) else []
    obj_aliases, rel_aliases, metric_aliases = set(), set(), set()
    for i, obj in enumerate(objects):
        alias = obj.get("alias") if isinstance(obj, dict) else None
        if isinstance(alias, str):
            if alias in obj_aliases:
                errors.append(error("OQL_SEMANTIC_ERROR", f"duplicate object alias: {alias}", f"$.objects[{i}].alias"))
            obj_aliases.add(alias)
    for i, rel in enumerate(oql.get("relationships", []) if isinstance(oql.get("relationships", []), list) else []):
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
    refs = []
    walk_condition(oql.get("conditions"), refs)
    for i, ret in enumerate(oql.get("returns", []) if isinstance(oql.get("returns", []), list) else []):
        if not isinstance(ret, dict):
            continue
        if isinstance(ret.get("ref"), str):
            refs.append(ret["ref"])
        if ret.get("kind") == "EXPR":
            walk_expr(ret.get("expr"), refs)
        if ret.get("kind") == "METRIC" and isinstance(ret.get("alias"), str):
            metric_aliases.add(ret["alias"])
        if ret.get("kind") == "METRIC" and ret.get("function") != "COUNT" and ret.get("field") == "*":
            errors.append(error("OQL_SEMANTIC_ERROR", "only COUNT can use field '*'", f"$.returns[{i}].field"))
    for ref in refs:
        if ref not in all_aliases:
            errors.append(error("OQL_SEMANTIC_ERROR", f"unknown alias reference: {ref}"))
    af_aliases = []
    walk_af(oql.get("aggregateFilter"), af_aliases)
    for alias in af_aliases:
        if alias not in metric_aliases:
            errors.append(error("OQL_SEMANTIC_ERROR", f"unknown metricAlias: {alias}", "$.aggregateFilter"))
    return errors

def main():
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
        errors = [error("OQL_SCHEMA_ERROR", item.message, "$" + ''.join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in item.path)) for item in validator.iter_errors(oql)]
        if not errors:
            errors = semantic(oql)
        return out(not errors, errors)
    except Exception as exc:
        return out(False, [error("OQL_VALIDATION_ERROR", str(exc))])

if __name__ == "__main__":
    raise SystemExit(main())
