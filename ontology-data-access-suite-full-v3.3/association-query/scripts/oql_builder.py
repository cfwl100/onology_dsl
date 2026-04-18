#!/usr/bin/env python3
"""Deterministic OQL assembler with optional profile overrides."""

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


def _get_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    ext = data.get("extensions")
    if isinstance(ext, dict):
        prof = ext.get("profile")
        if isinstance(prof, dict):
            return prof
    return {}


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
            if vv is None or vv == {} or vv == []:
                continue
            cleaned[k] = vv
        return cleaned
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            vv = _strip_empty(item)
            if vv is None or vv == {} or vv == []:
                continue
            cleaned_list.append(vv)
        return cleaned_list
    return value




def _lowercase_alias_refs(node: Any) -> Any:
    if isinstance(node, dict):
        out = OrderedDict()
        for k, v in node.items():
            if k in {"ref", "from", "to", "sourceRef", "targetRef"} and isinstance(v, str):
                out[k] = v.lower()
            else:
                out[k] = _lowercase_alias_refs(v)
        return out
    if isinstance(node, list):
        return [_lowercase_alias_refs(x) for x in node]
    return node

def _stringify_condition_values(node: Any) -> Any:
    if isinstance(node, dict):
        out = OrderedDict()
        for k, v in node.items():
            if k == "values" and isinstance(v, list):
                out[k] = [str(x) for x in v]
            else:
                out[k] = _stringify_condition_values(v)
        return out
    if isinstance(node, list):
        return [_stringify_condition_values(x) for x in node]
    return node


def _canonicalize_source_query(items: List[Dict[str, Any]]) -> List[OrderedDict]:
    return [assemble(item, is_batch_item=False) for item in items]


def assemble(data: Dict[str, Any], is_batch_item: bool = False) -> OrderedDict:
    if not isinstance(data, dict):
        raise ValueError("input plan must be a JSON object")

    op = data.get("operation")
    if op not in ALL_OPS:
        raise ValueError(f"unsupported operation: {op!r}")

    normalized = dict(data)
    profile = _get_profile(normalized)

    if not is_batch_item:
        normalized.setdefault("version", "1.0")
        normalized.setdefault("strict", True)
    if op in READ_OPS and "maxResults" not in normalized:
        normalized["maxResults"] = int(profile.get("defaultMaxResults", 1000))

    if profile.get("requireLowerCaseTypes"):
        for obj in normalized.get("objects", []):
            if isinstance(obj.get("objectType"), str):
                obj["objectType"] = obj["objectType"].lower()
            if isinstance(obj.get("alias"), str):
                obj["alias"] = obj["alias"].lower()
        for rel in normalized.get("relationships", []):
            for key in ("relationshipType", "alias", "from", "to"):
                if isinstance(rel.get(key), str):
                    rel[key] = rel[key].lower()
        for block in ("conditions", "returns", "orders", "linkQuery"):
            if block in normalized:
                normalized[block] = _lowercase_alias_refs(normalized[block])

    if profile.get("stringifyConditionValues") and "conditions" in normalized:
        normalized["conditions"] = _stringify_condition_values(normalized["conditions"])

    if "sourceQuery" in normalized:
        normalized["sourceQuery"] = _canonicalize_source_query(normalized["sourceQuery"])

    if op == "BATCH":
        mutation = dict(normalized.get("mutation", {}))
        items = mutation.get("items", [])
        normalized_items = []
        for item in items:
            if item.get("operation") == "BATCH":
                raise ValueError("nested BATCH is not allowed")
            normalized_items.append(assemble(item, is_batch_item=True))
        mutation["items"] = normalized_items
        normalized["mutation"] = mutation

    cleaned = _strip_empty(_ordered_top(normalized))
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    data = _load_json(Path(args.input))
    result = assemble(data)
    payload = _dump_json(result, Path(args.output) if args.output else None)
    if not args.output:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
