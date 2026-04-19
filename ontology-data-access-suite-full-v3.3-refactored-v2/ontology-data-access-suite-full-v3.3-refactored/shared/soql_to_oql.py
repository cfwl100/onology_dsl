
#!/usr/bin/env python3
"""S-OQL -> canonical OQL converter with expression support."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List
NULL_OPS = {"IS_NULL", "IS_NOT_NULL"}
ARRAY_OPS = {"IN", "NOT_IN"}
def _is_canonical_expr(v: Any) -> bool:
    return isinstance(v, dict) and v.get("kind") in {"FUNCTION", "FIELD_REF"}
def _is_fn(v: Any) -> bool:
    return isinstance(v, dict) and isinstance(v.get("$fn"), str) and v["$fn"].strip()
def _is_ref_field(v: Any) -> bool:
    return isinstance(v, str) and "." in v and all(part for part in v.split(".", 1))
def _split(v: str):
    ref, field = v.split(".", 1)
    if not ref or not field:
        raise ValueError(f"invalid ref.field expression: {v!r}")
    return ref, field
def convert_expr(v: Any) -> Any:
    if _is_canonical_expr(v):
        return v
    if _is_fn(v):
        args = v.get("args", [])
        if not isinstance(args, list):
            raise ValueError("function args must be an array")
        return {"kind": "FUNCTION", "name": v["$fn"].strip(), "args": [convert_expr_or_literal(a) for a in args]}
    if _is_ref_field(v):
        ref, field = _split(v)
        return {"kind": "FIELD_REF", "ref": ref, "field": field}
    raise ValueError(f"unsupported expression shape: {v!r}")
def convert_expr_or_literal(v: Any) -> Any:
    if _is_fn(v) or _is_canonical_expr(v) or _is_ref_field(v):
        return convert_expr(v)
    if isinstance(v, list):
        return [convert_expr_or_literal(x) for x in v]
    return v
def _values(op: str, raw: Any = None) -> List[Any]:
    if op in NULL_OPS:
        return []
    if op == "BETWEEN":
        if not isinstance(raw, list) or len(raw) != 2:
            raise ValueError("BETWEEN requires a 2-item array")
        return [convert_expr_or_literal(x) for x in raw]
    if op in ARRAY_OPS:
        if not isinstance(raw, list):
            raise ValueError(f"{op} requires an array value")
        return [convert_expr_or_literal(x) for x in raw]
    return [convert_expr_or_literal(raw)]
def convert_condition(node: Any) -> Dict[str, Any]:
    if isinstance(node, dict) and node.get("kind") in {"PREDICATE", "GROUP"}:
        return node
    if isinstance(node, list):
        if len(node) not in {2, 3}:
            raise ValueError("condition tuple must have length 2 or 3")
        left, op = node[0], node[1]
        pred = {"kind": "PREDICATE", "operator": op}
        if _is_ref_field(left) and not _is_fn(left):
            ref, field = _split(left)
            pred["ref"] = ref; pred["field"] = field
        else:
            pred["leftExpr"] = convert_expr(left)
        if len(node) == 3 and op not in NULL_OPS:
            pred["values"] = _values(op, node[2])
        return pred
    if isinstance(node, dict):
        if "all" in node:
            return {"kind": "GROUP", "relation": "AND", "children": [convert_condition(c) for c in node["all"]]}
        if "any" in node:
            return {"kind": "GROUP", "relation": "OR", "children": [convert_condition(c) for c in node["any"]]}
        if "not" in node:
            return {"kind": "GROUP", "relation": "NOT", "children": [convert_condition(node["not"])]}
    raise ValueError(f"unsupported condition shape: {node!r}")
def convert_return_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict) and isinstance(item.get("kind"), str):
        return item
    if not isinstance(item, list) or not item:
        raise ValueError(f"unsupported returns item: {item!r}")
    kind = item[0]
    if kind == "FIELDS":
        if len(item) != 3: raise ValueError("FIELDS tuple must have length 3")
        return {"kind": "FIELDS", "ref": item[1], "fields": item[2]}
    if kind == "EXPR":
        if len(item) != 3: raise ValueError("EXPR tuple must have length 3")
        return {"kind": "EXPR", "expr": convert_expr(item[1]), "alias": item[2]}
    if kind == "GROUP_BY":
        if len(item) != 3: raise ValueError("GROUP_BY tuple must have length 3")
        target = item[1]
        if _is_ref_field(target):
            ref, field = _split(target)
            return {"kind": "GROUP_BY", "ref": ref, "field": field, "alias": item[2]}
        return {"kind": "GROUP_BY", "expr": convert_expr(target), "alias": item[2]}
    if kind == "METRIC":
        if len(item) != 4: raise ValueError("METRIC tuple must have length 4")
        ref, field = _split(item[2])
        return {"kind": "METRIC", "function": item[1], "ref": ref, "field": field, "alias": item[3]}
    raise ValueError(f"unsupported returns tuple kind: {kind!r}")
def convert_order_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict) and {"ref","field","direction"}.issubset(item.keys()):
        return item
    if not isinstance(item, list) or len(item) != 4 or item[0] != "ORDER_BY":
        raise ValueError(f"unsupported orders item: {item!r}")
    return {"ref": item[1], "field": item[2], "direction": item[3]}
def convert_mutation(block: Any) -> Any:
    if not isinstance(block, dict):
        return block
    out = dict(block)
    data = out.get("data")
    if isinstance(data, dict) and "properties" not in data:
        out["data"] = {"properties": data}
    return out
def convert_document(doc: Any) -> Any:
    if isinstance(doc, list):
        return [convert_document(x) for x in doc]
    if not isinstance(doc, dict):
        return doc
    out = {k: convert_document(v) for k, v in doc.items()}
    if "conditions" in out:
        out["conditions"] = convert_condition(out["conditions"])
    if "returns" in out and isinstance(out["returns"], list):
        out["returns"] = [convert_return_item(x) for x in out["returns"]]
    if "orders" in out and isinstance(out["orders"], list):
        out["orders"] = [convert_order_item(x) for x in out["orders"]]
    if "mutation" in out:
        out["mutation"] = convert_mutation(out["mutation"])
    if "sourceQuery" in out:
        source = out["sourceQuery"]
        if isinstance(source, list):
            out["sourceQuery"] = [convert_document(x) for x in source]
        elif isinstance(source, dict):
            out["sourceQuery"] = convert_document(source)
    if isinstance(out.get("mutation"), dict) and isinstance(out["mutation"].get("items"), list):
        out["mutation"]["items"] = [convert_document(x) for x in out["mutation"]["items"]]
    return out
def main() -> int:
    parser = argparse.ArgumentParser(description="Convert S-OQL JSON into canonical OQL JSON")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    converted = convert_document(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(converted, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
