#!/usr/bin/env python3
"""Validate generated OQL JSON.

Input guidance:
- Use --input for complex or long OQL JSON, especially on Windows shells.
- Use --oac-json only for short compact JSON when the current shell quoting is known to be safe.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from oql_validator import make_error, validate_oql_dict


def emit(success, errors=None):
    print(json.dumps({"success": success, "errors": errors or []}, ensure_ascii=False, separators=(",", ":")))
    return 0 if success else 1


def load_oql(args):
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


def main():
    parser = argparse.ArgumentParser(description="Validate OQL JSON")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--oac-json",
        "--oql-json",
        dest="oac_json",
        help="OAC/OQL JSON 字符串；仅建议用于短小 compact JSON，复杂 JSON 优先使用 --input",
    )
    group.add_argument(
        "--input",
        "--oql-file",
        "--oql_file",
        dest="input",
        help="从 UTF-8 文件或 stdin 读取 JSON，使用 - 表示 stdin；复杂/长 OQL 推荐使用该方式",
    )
    args = parser.parse_args()
    try:
        errors = validate_oql_dict(load_oql(args))
        return emit(not errors, errors)
    except Exception as exc:
        return emit(False, [make_error("OQL_VALIDATION_ERROR", str(exc))])


if __name__ == "__main__":
    raise SystemExit(main())
