
#!/usr/bin/env python3
"""Deterministic OQL assembler."""
from __future__ import annotations
import argparse, json
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict
READ_OPS = {"QUERY", "AGGREGATE", "ASSOCIATION_QUERY", "LINK_QUERY"}
WRITE_OPS = {"CREATE", "UPDATE", "DELETE", "UPSERT", "BATCH"}
ALL_OPS = READ_OPS | WRITE_OPS
TOP_ORDER = ["version","schemaRef","strict","operation","objects","relationships","conditions","returns","orders","maxResults","sourceQuery","linkQuery","mutation","options","extensions"]
def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
def _dump(obj: Any, path: Path | None) -> str:
    payload = json.dumps(obj, ensure_ascii=False, indent=2)
    if path:
        path.write_text(payload + "\n", encoding="utf-8")
    return payload
def _ordered(data: Dict[str, Any]) -> OrderedDict:
    out = OrderedDict()
    for key in TOP_ORDER:
        if key in data:
            out[key] = data[key]
    for key in data:
        if key not in out:
            out[key] = data[key]
    return out
def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        out = OrderedDict()
        for k, v in value.items():
            vv = _strip(v)
            if vv is None or vv == {} or vv == []:
                continue
            out[k] = vv
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            vv = _strip(item)
            if vv is None or vv == {} or vv == []:
                continue
            out.append(vv)
        return out
    return value
def assemble(data: Dict[str, Any], is_batch_item: bool = False):
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
    if "sourceQuery" in normalized and isinstance(normalized["sourceQuery"], list):
        normalized["sourceQuery"] = [assemble(item, False) for item in normalized["sourceQuery"]]
    if op == "BATCH":
        mutation = dict(normalized.get("mutation", {}))
        items = mutation.get("items", [])
        out_items = []
        for item in items:
            if item.get("operation") == "BATCH":
                raise ValueError("nested BATCH is not allowed")
            out_items.append(assemble(item, True))
        mutation["items"] = out_items
        normalized["mutation"] = mutation
    return _strip(_ordered(normalized))
def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical OQL with stable ordering")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = assemble(_load(Path(args.input)))
    payload = _dump(result, Path(args.output) if args.output else None)
    if not args.output:
        print(payload)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
