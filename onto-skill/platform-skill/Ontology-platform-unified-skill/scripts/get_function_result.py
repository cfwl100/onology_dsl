#!/usr/bin/env python3
"""Get Function Result: 获取函数执行结果

Usage:
    python get_function_result.py --physicalName <physicalName> --function-id <dtmi_string> --params '<json_string>'

Examples:
    python get_function_result.py --physical-name "ars-5877acb8cc" --function-id "dtmi:test:test:8888" --params '{"param1": "value1"}'
"""
from __future__ import annotations
import argparse
import json
import os
import requests
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

SCRIPTS_ROOT = Path(__file__).resolve().parent

MAX_RETRIES = 3
RETRY_DELAY = 1


def call_function(physicalName: str, function_id: str, params: dict) -> dict:
    """调用函数并获取结果"""
    namespace = os.environ.get("SERVICE_NAMESPACE")
    tenant_id = os.environ.get("TENANT_ID")

    if not namespace:
        return {
            "success": False,
            "error": {
                "exception_type": "EnvironmentError",
                "message": "环境变量 SERVICE_NAMESPACE 未设置，请检查集群配置"
            }
        }

    if not tenant_id:
        return {
            "success": False,
            "error": {
                "exception_type": "EnvironmentError",
                "message": "环境变量 TENANT_ID 未设置，请检查租户配置"
            }
        }

    url = f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/{physicalName}/ontology/function/call"
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json",
        "x-gde-tenant-id": tenant_id
    }
    body = {"function_id": function_id, "args": params}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=body, verify=False)
            response.raise_for_status()
            return {"success": True, "data": response.text}
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"\033[33m[Retry] Attempt {attempt + 1} failed: {e}\033[0m")
                time.sleep(RETRY_DELAY)
                continue
            return {
                "success": False,
                "error": {
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
            }

    return {"success": False, "error": {"message": "All retries failed"}}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get Function Result: 获取函数执行结果"
    )
    parser.add_argument("--physicalName", required=True, help="Function physical name")
    parser.add_argument("--function-id", required=True, help="Function ID (dtmi string)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--params", help="参数字符串 (JSON)")
    group.add_argument("--params-json", help="完整参数 JSON 字符串")
    parser.add_argument("--output", help="输出文件路径 (可选)")
    args = parser.parse_args()

    params = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
            output = json.dumps(result, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)
            return 1
    elif args.params_json:
        try:
            payload = json.loads(args.params_json)
            params = payload.get("args") or payload
        except json.JSONDecodeError as e:
            result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
            output = json.dumps(result, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)
            return 1

    if params is None:
        result = {"success": False, "error": {"code": "MISSING_PARAMS", "message": "必须提供 --params 或 --params-json 参数"}}
        output = json.dumps(result, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 1

    result = call_function(args.physicalName, args.function_id, params)

    if result["success"]:
        try:
            data = json.loads(result["data"])
        except (json.JSONDecodeError, TypeError):
            data = result["data"]
        output = json.dumps({"message_type": "FUNCTION_RESULT", "title": "故障传播子图", "content": data["result"]["result"]}, ensure_ascii=False)
    else:
        output = json.dumps(result, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())