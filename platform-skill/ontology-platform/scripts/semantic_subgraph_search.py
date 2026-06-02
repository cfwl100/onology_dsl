#!/usr/bin/env python3
"""Semantic Subgraph Search: 语义子图搜索

Usage:
    python semantic_subgraph_search.py --ontology-id <id> --query <query>

Examples:
    python semantic_subgraph_search.py --ontology-id test --query "设备故障诊断"
    python semantic_subgraph_search.py --ontology-id test --query-json '{"query": "设备故障", "similarityThreshold": 0.8}'
"""
from __future__ import annotations
import argparse
import json
import requests
import warnings
from pathlib import Path

# 禁用不安全的 HTTPS 请求警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Configuration
SCRIPTS_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPTS_ROOT / "tools"

OAG_URL = "https://7.220.122.186:30281/data-pilot/cse/ontology-knowledge-api"
OAG_CERT = str(TOOLS_DIR / "client.crt.pem")
OAG_KEY = str(TOOLS_DIR / "client.key.pem")
OAG_TOKEN = "test-token"
OAG_TENANT_ID = "2001"


def search_subgraph(ontology_id: str, query: str, similarity_threshold: float = 0.8, include_functions: int = 1) -> dict:
    """执行语义子图搜索"""
    url = f"{OAG_URL}/v1/okb/{ontology_id}/subgraph/semanticsearch"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OAG_TOKEN}",
        "x-cse-context": json.dumps({"x-gde-tenant-id": OAG_TENANT_ID}, ensure_ascii=False),
    }
    payload = {
        "query": query,
        "similarityThreshold": similarity_threshold,
        "includeFunctions": include_functions
    }

    session = requests.Session()
    session.trust_env = False

    try:
        resp = session.post(
            url,
            headers=headers,
            json=payload,
            cert=(OAG_CERT, OAG_KEY),
            verify=False,
            timeout=30,
        )
        return {"success": True, "data": resp.json()}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "exception_type": type(e).__name__,
                "message": str(e)
            }
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Semantic Subgraph Search: 语义子图搜索"
    )
    parser.add_argument("--ontology-id", help="Ontology ID")
    parser.add_argument("--query", help="查询语句")
    parser.add_argument("--query-json", help="完整查询 JSON 字符串")
    parser.add_argument("--similarity-threshold", type=float, default=0.8, help="相似度阈值 (默认 0.8)")
    parser.add_argument("--include-functions", type=int, default=1, help="是否包含函数 (默认 1)")
    parser.add_argument("--output", help="输出文件路径 (可选)")
    args = parser.parse_args()

    # 校验：query 是必填参数，ontology_id 默认使用 network@1.0
    if not args.query_json and not args.query:
        result = {"success": False, "error": {"code": "INVALID_INPUT", "message": "query 是必填参数"}}
        output = json.dumps(result, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 1

    # 解析输入
    if args.query_json:
        try:
            payload = json.loads(args.query_json)
            # 同时支持下划线和连字符格式
            ontology_id = payload.get("ontology_id") or payload.get("ontology-id") or ""
            query = payload.get("query", "")
            similarity_threshold = payload.get("similarityThreshold") or payload.get("similarity-threshold") or args.similarity_threshold
            include_functions = payload.get("includeFunctions") or payload.get("include-functions") or args.include_functions
        except json.JSONDecodeError as e:
            result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
            output = json.dumps(result, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)
            return 1
    else:
        ontology_id = args.ontology_id or "network@1.0"
        query = args.query
        similarity_threshold = args.similarity_threshold
        include_functions = args.include_functions

    # 执行搜索
    result = search_subgraph(ontology_id, query, similarity_threshold, include_functions)

    # 输出结果
    output = json.dumps({"message_type": "message_ontololgy_subgraph", "title": "本体子图", "content": result["data"]["result"]}, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())