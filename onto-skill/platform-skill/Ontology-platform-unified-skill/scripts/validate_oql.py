#!/usr/bin/env python3
"""Validate OQL JSON with JSON Schema draft-07 and OQL semantic rules."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from oql_validator import ROOT, make_error, validate_oql_dict

EXAMPLES = {
    "QUERY": ROOT / "examples" / "query.example.json",
    "ASSOCIATION_QUERY": ROOT / "examples" / "association-query.example.json",
    "AGGREGATE": ROOT / "examples" / "agg.example.json",
}


def emit(success: bool, errors: list[dict[str, Any]] | None = None) -> int:
    print(json.dumps({"success": success, "errors": errors or []}, ensure_ascii=False, separators=(",", ":")))
    return 0 if success else 1


def load_oql(args: argparse.Namespace) -> dict[str, Any]:
    if args.example:
        path = EXAMPLES.get(args.example.upper())
        if not path:
            raise ValueError(f"unsupported example operation: {args.example}")
        raw = path.read_text(encoding="utf-8")
    elif args.oac_json:
        raw = args.oac_json
    elif args.input == "-":
        raw = sys.stdin.read()
    elif args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raise ValueError("missing --oac-json, --input or --example")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OQL JSON")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--oac-json")
    group.add_argument("--input")
    group.add_argument("--example", choices=sorted(EXAMPLES.keys()))
    args = parser.parse_args()
    try:
        errors = validate_oql_dict(load_oql(args))
        return emit(not errors, errors)
    except Exception as exc:
        return emit(False, [make_error("OQL_VALIDATION_ERROR", str(exc))])


if __name__ == "__main__":
    raise SystemExit(main())
