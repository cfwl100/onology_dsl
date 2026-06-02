#!/usr/bin/env python3
"""Get Function Result: 获取函数执行结果

Usage:
    python get_function_result.py --function-id <dtmi_string> --params '<json_string>'

Examples:
    python get_function_result.py --function-id "dtmi:test:test:8888" --params '{"param1": "value1"}'
"""
from __future__ import annotations
import argparse
import json
import requests
import time
import warnings
from pathlib import Path

# 禁用不安全的 HTTPS 请求警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Configuration
SCRIPTS_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPTS_ROOT / "tools"

FUNC_RESULT_URL = "http://7.220.122.186:18088"
OAC_CERT = str(TOOLS_DIR / "client.crt.pem")
OAC_KEY = str(TOOLS_DIR / "client.key.pem")

# Retry config
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def call_function(function_id: str, params: dict) -> dict:
    """调用函数并获取结果"""
    url = f"{FUNC_RESULT_URL}/function/call"
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    cert = (OAC_CERT, OAC_KEY)
    body = {"function_id": function_id, "args": params}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, cert=cert, json=body, verify=False)
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
    parser.add_argument("--function-id", required=True, help="Function ID (dtmi string)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--params", help="参数字符串 (JSON)")
    group.add_argument("--params-json", help="完整参数 JSON 字符串")
    parser.add_argument("--output", help="输出文件路径 (可选)")
    args = parser.parse_args()

    # 解析参数
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
            # 同时支持两种格式：{"args": {...}} 或 {"alarm_names": [...]}
            params = payload.get("args") or payload
        except json.JSONDecodeError as e:
            result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
            output = json.dumps(result, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)
            return 1

    # 执行调用
    result = call_function(args.function_id, params)

    # 输出结果
    if result["success"]:
        # 尝试解析返回的 JSON 字符串
        try:
            data = json.loads(result["data"])
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效 JSON，保持原字符串
            data = result["data"]
        # 成功时在外层包 FUNCTION_RESULT
        # message_type为FUNCTION_RESULT是，自己去data里解析真正的message_type
        output = json.dumps({"message_type": "FUNCTION_RESULT", "title": "故障传播子图", "content": data["result"]["result"]}, ensure_ascii=False)
    else:
        # 失败时返回 JSON 格式
        output = json.dumps(result, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())