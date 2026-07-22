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
import time
import os
from pathlib import Path

# 禁用不安全的 HTTPS 请求警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

MAX_RETRIES = 3
RETRY_DELAY = 1


def search_subgraph(ontologyId: str, query: str, similarityThreshold: float = 0.6, includeFunctions: int = 1,
                    includeActions: int = 0, seedRetrievalMode: str = "vector",
                    topK: int = 3, graphExpansionStrategy: str = "minimal", adaptive_retrieval: int = 1,hopLimit: int = 3) -> dict:
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
    """执行语义子图搜索"""
    url = (f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/ontoretrieval/rest/onto-retrieval-api/v1/onto"
           f"-retrieval/{ontologyId}/subgraph/semantic-search")
    headers = {
        "Content-Type": "application/json",
        "accept": "*/*",
        "x-gde-tenant-id": tenant_id,
    }
    payload = {
        "query": query,
        "similarityThreshold": similarityThreshold,
        "includeFunctions": includeFunctions,
        "includeActions": includeActions,
        "seedRetrievalMode": seedRetrievalMode,
        "topK": topK,
        "graphExpansionStrategy": graphExpansionStrategy,
        "adaptiveRetrieval": adaptive_retrieval,
        "hopLimit": hopLimit
    }

    session = requests.Session()
    session.trust_env = False
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.post(
                url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=30,
            )
            return {"success": True, "data": resp.json()}
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Semantic Subgraph Search: 语义子图搜索"
    )

    parser.add_argument("--ontology-id", help="Ontology ID")
    parser.add_argument("--query", help="查询语句")
    parser.add_argument("--query-json", help="完整查询 JSON 字符串")
    parser.add_argument("--similarity-threshold", type=float, default=0.6, help="相似度阈值 (默认 0.6)")
    parser.add_argument("--include-functions", type=int, default=0, help="是否包含函数 (默认 0)")
    parser.add_argument("--include-actions", type=int, default=0, help="是否包含操作 (默认 0)")
    parser.add_argument("--seed-retrieval-mode", type=str, default="vector", help="检索模式")
    parser.add_argument("--topK", type=int, default=3, help="topK (默认 3)")
    parser.add_argument("--graph-expansion-strategy", type=str, default="minimal", help="图检索策略")
    parser.add_argument("--adaptive-retrieval", type=int, default=1, help="自适应检索图检索策略")
    parser.add_argument("--hopLimit", type=int, default=3, help="种子节点向外扩散的深度，仅使用多源BFS时，该参数生效")
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
            ontology_id = payload.get("ontology-id") or os.environ.get("ONTOLOGY_ID")
            query = payload.get("query")
            similarity_threshold = payload.get("similarity-threshold") or args.similarity_threshold
            include_functions = payload.get("include-functions") or args.include_functions
            include_actions = payload.get("include-actions") or args.include_actions
            seed_retrieval_mode = payload.get("seed-retrieval-mode") or args.seed_retrieval_mode
            top_k = payload.get("topK") or args.topK
            graph_expansion_strategy = payload.get("graph-expansion-strategy") or args.graph_expansion_strategy
            adaptive_retrieval = payload.get("adaptive-retrieval") or args.adaptive_retrieval
            hop_limit = payload.get("hopLimit") or args.hopLimit
        except json.JSONDecodeError as e:
            result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
            output = json.dumps(result, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)
            return 1
    else:
        ontology_id = args.ontology_id or os.environ.get("ONTOLOGY_ID")
        query = args.query
        similarity_threshold = args.similarity_threshold
        include_functions = args.include_functions
        include_actions = args.include_actions
        seed_retrieval_mode = args.seed_retrieval_mode
        top_k = args.topK
        graph_expansion_strategy = args.graph_expansion_strategy
        adaptive_retrieval = args.adaptive_retrieval
        hop_limit = args.hopLimit

    # 执行搜索
    result = search_subgraph(ontology_id, query, similarity_threshold, include_functions, include_actions,
                             seed_retrieval_mode, top_k, graph_expansion_strategy, adaptive_retrieval ,hop_limit)

    # 输出结果
    output = json.dumps(
        {"message_type": "message_ontololgy_subgraph", "title": "本体子图", "content": result["data"]["result"]},
        ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
