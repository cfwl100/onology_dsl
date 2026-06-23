#!/usr/bin/env python3
"""Validate generated OQL JSON."""
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
    group.add_argument("--oac-json", "--oql-json", dest="oac_json", help="OAC/OQL JSON 字符串；默认推荐使用，避免临时文件")
    group.add_argument("--input", "--oql-file", "--oql_file", dest="input", help="从文件或 stdin 读取 JSON，使用 - 表示 stdin；--oql-file/--oql_file 为兼容旧用法")
    args = parser.parse_args()
    try:
        errors = validate_oql_dict(load_oql(args))
        return emit(not errors, errors)
    except Exception as exc:
        return emit(False, [make_error("OQL_VALIDATION_ERROR", str(exc))])


if __name__ == "__main__":
    raise SystemExit(main())
