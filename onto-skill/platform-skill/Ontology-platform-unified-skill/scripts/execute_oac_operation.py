#!/usr/bin/env python3
"""Execute OAC Operation.

The execution script reuses scripts/oql_validator.py as the single OQL validation gate.

Input guidance:
- Use --input for complex or long OQL JSON, especially on Windows shells.
- Use --oac-json only for short compact JSON when the current shell quoting is known to be safe.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import requests

from oql_validator import validate_oql_dict

warnings.filterwarnings("ignore")


def compact(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def write_or_print(output: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


def load_input(args: argparse.Namespace) -> dict[str, Any]:
    if args.oac_json:
        data = json.loads(args.oac_json)
    elif args.input == "-":
        data = json.load(sys.stdin)
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {args.input}")
        data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be object")
    return data


def apply_runtime_defaults(oql: dict[str, Any]) -> None:
    if not oql.get("version"):
        oql["version"] = os.environ.get("OQL_VERSION", "2.0")
    if not oql.get("schemaRef"):
        schema_ref = os.environ.get("ONTOLOGY_SCHEMA_REF")
        if schema_ref:
            oql["schemaRef"] = schema_ref
    if "operation" in oql and isinstance(oql["operation"], str):
        oql["operation"] = oql["operation"].upper()
    if "strict" not in oql or oql["strict"] is None:
        oql["strict"] = True


def validate_for_execution(oql: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    apply_runtime_defaults(oql)
    errors = validate_oql_dict(oql)
    return not errors, errors


def missing_runtime_env() -> list[str]:
    required = ["SERVICE_NAMESPACE", "TENANT_ID"]
    return [name for name in required if not os.environ.get(name)]


def execute_operation(oql: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("DEBUG_OAC", "false").lower() == "true":
        debug_dir = os.environ.get("DEBUG_OAC_DIR", "/tmp")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        debug_file = os.path.join(debug_dir, f"oac_debug_{timestamp}.json")
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(oql, f, ensure_ascii=False, indent=2)
        return {"success": True, "data": json.dumps({"data": [f"DEBUG_MODE: OQL 已写入 {debug_file}"]}, ensure_ascii=False)}

    missing = missing_runtime_env()
    if missing:
        return {
            "success": False,
            "error": {
                "code": "ENV_MISSING",
                "exception_type": "EnvironmentError",
                "missing": missing,
                "message": "真实 OAC 执行环境变量未设置，请检查集群与租户配置: " + ", ".join(missing),
            },
        }

    namespace = os.environ.get("SERVICE_NAMESPACE")
    tenant_id = os.environ.get("TENANT_ID")

    url = f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/ontoaccess/rest/v1/objects/query"
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": "multiDatasource",
        "X-Tenant-Id": tenant_id,
    }
    try:
        response = requests.post(url, headers=headers, json=oql, verify=False, timeout=60)
        return {"success": True, "data": response.text}
    except Exception as exc:
        return {"success": False, "error": {"exception_type": type(exc).__name__, "message": str(exc)}}


def format_success(result: dict[str, Any], message_type: str) -> str:
    try:
        data = json.loads(result.get("data", ""))
    except (json.JSONDecodeError, TypeError):
        data = result.get("data", "")
    if isinstance(data, dict) and "data" in data:
        content = data["data"]
    else:
        content = []
    return compact({"message_type": message_type, "content": content})


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute OAC Operation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--oac-json", help="OAC JSON 字符串；仅建议用于短小 compact JSON，复杂 JSON 优先使用 --input")
    group.add_argument("--input", help="从 UTF-8 文件或 stdin 读取 JSON，使用 - 表示 stdin；复杂/长 OQL 推荐使用该方式")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--message-type", "--msg-type", dest="message_type", default="OAC_RETURN", help="返回消息类型")
    args = parser.parse_args()

    try:
        oql = load_input(args)
    except json.JSONDecodeError as exc:
        write_or_print(compact({"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(exc)}}), args.output)
        return 1
    except Exception as exc:
        write_or_print(compact({"success": False, "error": {"code": type(exc).__name__, "message": str(exc)}}), args.output)
        return 1

    valid, errors = validate_for_execution(oql)
    if not valid:
        write_or_print(compact({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "OQL validation failed", "details": errors}}), args.output)
        return 1

    result = execute_operation(oql)
    output = format_success(result, args.message_type) if result.get("success") else compact(result)
    write_or_print(output, args.output)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
