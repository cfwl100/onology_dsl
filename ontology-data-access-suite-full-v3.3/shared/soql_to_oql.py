#!/usr/bin/env python3
"""S-OQL -> canonical OQL converter.

支持的 S-OQL 简化点：`conditions`、`returns`、`mutation`
不可简化模块保持 canonical 写法
递归处理 `sourceQuery`、`BATCH.items`
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _split_ref_field(value: str) -> tuple[str, str]:
    """Split '<alias>.<field>' into ('alias', 'field')."""
    if not isinstance(value, str) or "." not in value:
        raise ValueError(f"invalid ref.field expression: {value!r}")
    ref, field = value.split(".", 1)
    if not ref or not field:
        raise ValueError(f"invalid ref.field expression: {value!r}")
    return ref, field


def _to_values(operator: str, raw_value: Any) -> List[Any]:
    """Normalize values for canonical PREDICATE.values."""
    if operator in {"IS_NULL", "IS_NOT_NULL"}:
        return []
    if operator == "BETWEEN":
        if not isinstance(raw_value, list) or len(raw_value) != 2:
            raise ValueError("BETWEEN requires a 2-item array")
        return raw_value
    if operator in {"IN", "NOT_IN"}:
        if not isinstance(raw_value, list):
            raise ValueError(f"{operator} requires an array value")
        return raw_value
    return [raw_value]


def convert_condition(node: Any) -> Dict[str, Any]:
    """Convert S-OQL condition node to canonical condition tree.

    映射规则：
    - 条件三元组 `[ref.field, op, value]` -> `PREDICATE`
    - 条件二元组 `[ref.field, IS_NULL|IS_NOT_NULL]` -> `PREDICATE`
    - 逻辑组 `{all:[...]}` / `{any:[...]}` / `{not:...}` -> `GROUP(AND|OR|NOT)`
    """
    if isinstance(node, dict) and node.get("kind") in {"PREDICATE", "GROUP"}:
        # Already canonical.
        return node

    if isinstance(node, list):
        if len(node) not in {2, 3}:
            raise ValueError("condition tuple must have length 2 or 3")
        ref, field = _split_ref_field(node[0])
        operator = node[1]
        pred: Dict[str, Any] = {
            "kind": "PREDICATE",
            "ref": ref,
            "field": field,
            "operator": operator,
        }
        if len(node) == 3 and operator not in {"IS_NULL", "IS_NOT_NULL"}:
            pred["values"] = _to_values(operator, node[2])
        return pred

    if isinstance(node, dict):
        if "all" in node:
            children = node["all"]
            if not isinstance(children, list):
                raise ValueError("all must be an array")
            return {"kind": "GROUP", "relation": "AND", "children": [convert_condition(c) for c in children]}
        if "any" in node:
            children = node["any"]
            if not isinstance(children, list):
                raise ValueError("any must be an array")
            return {"kind": "GROUP", "relation": "OR", "children": [convert_condition(c) for c in children]}
        if "not" in node:
            return {"kind": "GROUP", "relation": "NOT", "children": [convert_condition(node["not"])]}

    raise ValueError(f"unsupported condition shape: {node!r}")


def convert_return_item(item: Any) -> Dict[str, Any]:
    """Convert one S-OQL returns tuple to canonical returns item.

    映射规则：
    - `["FIELDS", ref, [fields...]]` -> `{"kind":"FIELDS","ref":...,"fields":[...]}`
    - `["GROUP_BY", "ref.field", alias]` -> `{"kind":"GROUP_BY",...}`
    - `["METRIC", fn, "ref.field|ref.*", alias]` -> `{"kind":"METRIC",...}`
    """
    if isinstance(item, dict) and isinstance(item.get("kind"), str):
        # Already canonical.
        return item

    if not isinstance(item, list) or not item:
        raise ValueError(f"unsupported returns item: {item!r}")

    kind = item[0]
    if kind == "FIELDS":
        if len(item) != 3:
            raise ValueError("FIELDS tuple must have length 3")
        return {"kind": "FIELDS", "ref": item[1], "fields": item[2]}

    if kind == "GROUP_BY":
        if len(item) != 3:
            raise ValueError("GROUP_BY tuple must have length 3")
        ref, field = _split_ref_field(item[1])
        return {"kind": "GROUP_BY", "ref": ref, "field": field, "alias": item[2]}

    if kind == "METRIC":
        if len(item) != 4:
            raise ValueError("METRIC tuple must have length 4")
        ref, field = _split_ref_field(item[2])
        return {
            "kind": "METRIC",
            "ref": ref,
            "field": field,
            "function": item[1],
            "alias": item[3],
        }

    raise ValueError(f"unsupported returns tuple kind: {kind!r}")


def convert_mutation(block: Any) -> Any:
    """Convert `mutation.data` simplified shape to canonical `data.properties`.

    规则：仅当 `mutation.data` 是直接属性对象（且不含 `properties`）时，
    才转换为 `{"data": {"properties": ...}}`；其余 mutation 结构透传。
    """
    if not isinstance(block, dict):
        return block

    mutation = dict(block)
    data = mutation.get("data")
    if isinstance(data, dict) and "properties" not in data:
        mutation["data"] = {"properties": data}
    return mutation


def convert_document(doc: Any) -> Any:
    """Recursively convert one OQL/S-OQL document."""
    if isinstance(doc, list):
        return [convert_document(item) for item in doc]

    if not isinstance(doc, dict):
        return doc

    out = {k: convert_document(v) for k, v in doc.items()}

    # Only these three modules are simplified in S-OQL.
    if "conditions" in out:
        out["conditions"] = convert_condition(out["conditions"])

    if "returns" in out and isinstance(out["returns"], list):
        out["returns"] = [convert_return_item(item) for item in out["returns"]]

    if "mutation" in out:
        out["mutation"] = convert_mutation(out["mutation"])

    # Explicit recursive handling points requested by spec.
    if "sourceQuery" in out:
        source = out["sourceQuery"]
        if isinstance(source, list):
            out["sourceQuery"] = [convert_document(item) for item in source]
        elif isinstance(source, dict):
            out["sourceQuery"] = convert_document(source)

    if isinstance(out.get("mutation"), dict):
        items = out["mutation"].get("items")
        if isinstance(items, list):
            out["mutation"]["items"] = [convert_document(item) for item in items]

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert S-OQL JSON into canonical OQL JSON")
    parser.add_argument("--input", required=True, help="Input JSON path")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    converted = convert_document(data)
    text = json.dumps(converted, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
