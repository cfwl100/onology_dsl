#!/usr/bin/env python3
"""Get Function Params Spec: 获取函数参数规格

Usage:
    python get_function_params_spec.py --function-id <dtmi_string>

Examples:
    python get_function_params_spec.py --function-id "dtmi:test:test:8888"
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

FUNC_TYPE_URL = "https://7.220.122.186:31842"
OAC_CERT = str(TOOLS_DIR / "client.crt.pem")
OAC_KEY = str(TOOLS_DIR / "client.key.pem")

# Retry config
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def _simplify_inputs(inputs: list) -> list:
    """Simplify input params, only keep key info"""
    simplified = []
    for inp in inputs:
        simplified.append({
            "name": inp.get("name", ""),
            "description": inp.get("description", {}),
            "type": inp.get("type", ""),
            "required": inp.get("required", False),
            "position": inp.get("position", 0)
        })
    return simplified


def _simplify_outputs(outputs: dict) -> dict:
    """Simplify output description"""
    return {
        "name": outputs.get("name", ""),
        "description": outputs.get("description", {}),
        "type": outputs.get("type", "")
    }


def get_params_spec(function_id: str) -> dict:
    """获取函数参数规格"""
    url = f"{FUNC_TYPE_URL}/ontologymanagement/rest/api/v1/ontologies/test/function-types/{function_id}/query"
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json"
    }
    cert = (OAC_CERT, OAC_KEY)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, cert=cert, verify=False)
            response.raise_for_status()
            raw_data = response.json()['result']

            # Simplify metadata, only keep key info
            simplified = {
                "id": raw_data.get("id", ""),
                "name": raw_data.get("name", ""),
                "display": raw_data.get("display", {}),
                "description": raw_data.get("description", {}),
                "status": raw_data.get("status", ""),
                "inputs": _simplify_inputs(raw_data.get("inputs", [])),
                "outputs": _simplify_outputs(raw_data.get("outputs", {}))
            }
            return {"success": True, "data": simplified}
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
        description="Get Function Params Spec: 获取函数参数规格"
    )
    parser.add_argument("--function-id", required=True, help="Function ID (dtmi string)")
    parser.add_argument("--output", help="输出文件路径 (可选)")
    args = parser.parse_args()

    # 执行获取
    result = get_params_spec(args.function_id)

    # 输出结果
    output = json.dumps(result, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())