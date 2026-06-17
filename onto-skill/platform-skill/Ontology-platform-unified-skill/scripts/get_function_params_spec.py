#!/usr/bin/env python3
"""Get Function Params Spec: 获取函数参数规格

Usage:
    python get_function_params_spec.py --ontology-id <ontology_id> --function-id <dtmi_string>

Examples:
    python get_function_params_spec.py --ontology-id "dtmi:com:huawei:ict:IP" --function-id "dtmi:test:test:8888"
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


def get_params_spec(ontology_id: str, function_id: str) -> dict:
    """获取函数参数规格"""
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

    url = f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/oms/rest/api/v1/ontologies/{ontology_id}/function-types/{function_id}/query"
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json",
        "x-gde-tenant-id": tenant_id
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            raw_data = response.json()['result']

            simplified = {
                "id": raw_data.get("id", ""),
                "name": raw_data.get("name", ""),
                "physicalName": raw_data.get("physicalName", ""),
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
    parser.add_argument("--ontology-id", required=True, help="Ontology ID (如 network@1.0)")
    parser.add_argument("--function-id", required=True, help="Function ID (dtmi string)")
    parser.add_argument("--output", help="输出文件路径 (可选)")
    args = parser.parse_args()

    result = get_params_spec(args.ontology_id, args.function_id)

    output = json.dumps(result, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())