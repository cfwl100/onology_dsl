#!/usr/bin/env python3
"""Deterministic OQL assembler.

Input: a normalized JSON plan with canonical keys.
Output: canonicalized OQL JSON with stable field order and defaults.

Example:
  python scripts/oql_builder.py --input plan.json --output oql.json
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List

READ_OPS = {"QUERY", "AGGREGATE", "ASSOCIATION_QUERY", "LINK_QUERY"}
WRITE_OPS = {"CREATE", "UPDATE", "DELETE", "UPSERT", "BATCH"}
ALL_OPS = READ_OPS | WRITE_OPS

TOP_ORDER = [
    "version",
    "schemaRef",
    "strict",
    "operation",
    "objects",
    "relationships",
    "conditions",
    "returns",
    "orders",
    "maxResults",
    "sourceQuery",
    "linkQuery",
    "mutation",
    "options",
    "extensions",
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(obj: Any, path: Path | None) -> str:
    payload = json.dumps(obj, ensure_ascii=False, indent=2)
    if path:
        path.write_text(payload + "\n", encoding="utf-8")
    return payload


def _ordered_top(data: Dict[str, Any]) -> OrderedDict:
    out: OrderedDict[str, Any] = OrderedDict()
    for key in TOP_ORDER:
        if key in data:
            out[key] = data[key]
    for key in data:
        if key not in out:
            out[key] = data[key]
    return out


def _strip_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = OrderedDict()
        for k, v in value.items():
            vv = _strip_empty(v)
            if vv is None:
                continue
            if vv == {} or vv == []:
                continue
            cleaned[k] = vv
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            vv = _strip_empty(item)
            if vv is None:
                continue
            if vv == {} or vv == []:
                continue
            cleaned_list.append(vv)
        return cleaned_list
    return value


def _canonicalize_source_query(items: List[Dict[str, Any]]) -> List[OrderedDict]:
    out = []
    for item in items:
        normalized = assemble(item, is_batch_item=False, is_source_query=True)
        out.append(normalized)
    return out


def assemble(data: Dict[str, Any], is_batch_item: bool = False, is_source_query: bool = False) -> OrderedDict:
    if not isinstance(data, dict):
        raise ValueError("input plan must be a JSON object")

    op = data.get("operation")
    if op not in ALL_OPS:
        raise ValueError(f"unsupported operation: {op!r}")

    normalized = dict(data)
    if not is_batch_item:
        normalized.setdefault("version", "1.0")
        normalized.setdefault("strict", True)
    if op in READ_OPS and "maxResults" not in normalized:
        normalized["maxResults"] = 1000

    if "sourceQuery" in normalized:
        normalized["sourceQuery"] = _canonicalize_source_query(normalized["sourceQuery"])

    if op == "BATCH":
        mutation = dict(normalized.get("mutation", {}))
        items = mutation.get("items", [])
        normalized_items = []
        for item in items:
            if item.get("operation") == "BATCH":
                raise ValueError("nested BATCH is not allowed")
            normalized_items.append(assemble(item, is_batch_item=True, is_source_query=False))
        mutation["items"] = normalized_items
        normalized["mutation"] = mutation

    cleaned = _strip_empty(_ordered_top(normalized))
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="normalized input JSON path")
    parser.add_argument("--output", help="output JSON path")
    args = parser.parse_args()

    data = _load_json(Path(args.input))
    result = assemble(data)
    payload = _dump_json(result, Path(args.output) if args.output else None)
    if not args.output:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
