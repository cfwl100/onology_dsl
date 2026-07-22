#!/usr/bin/env python3
"""Semantic Subgraph Search: 语义子图搜索

Usage:
    python semantic_subgraph_search.py --ontology-id <id> --query <query>

Examples:
    python semantic_subgraph_search.py --ontology-id test --query "设备故障诊断"
    python semantic_subgraph_search.py --ontology-id test --query-json '{"query": "设备故障", "similarityThreshold": 0.8}'
    python semantic_subgraph_search.py --plan-json '{"ontology_id": "test", "oag_payload": {...}}'
"""
from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from pathlib import Path

import requests

# 禁用不安全的 HTTPS 请求警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

MAX_RETRIES = 3
RETRY_DELAY = 1


def search_subgraph(
    ontology_id: str,
    query: str,
    similarity_threshold: float = 0.6,
    include_functions: int = 1,
    include_actions: int = 0,
    seed_retrieval_mode: str = "vector",
    top_k: int = 3,
    graph_expansion_strategy: str = "minimal",
    adaptive_retrieval: int = 1,
    hop_limit: int = 3,
) -> dict:
    namespace = os.environ.get("SERVICE_NAMESPACE")
    tenant_id = os.environ.get("TENANT_ID")

    if not namespace:
        return {
            "success": False,
            "error": {
                "exception_type": "EnvironmentError",
                "message": "环境变量 SERVICE_NAMESPACE 未设置，请检查集群配置",
            },
        }

    if not tenant_id:
        return {
            "success": False,
            "error": {
                "exception_type": "EnvironmentError",
                "message": "环境变量 TENANT_ID 未设置，请检查租户配置",
            },
        }

    url = (
        f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/ontoretrieval/rest/onto-retrieval-api/v1/onto"
        f"-retrieval/{ontology_id}/subgraph/semantic-search"
    )
    headers = {
        "Content-Type": "application/json",
        "accept": "*/*",
        "x-gde-tenant-id": tenant_id,
    }
    payload = {
        "query": query,
        "similarityThreshold": similarity_threshold,
        "includeFunctions": include_functions,
        "includeActions": include_actions,
        "seedRetrievalMode": seed_retrieval_mode,
        "topK": top_k,
        "graphExpansionStrategy": graph_expansion_strategy,
        "adaptiveRetrieval": adaptive_retrieval,
        "hopLimit": hop_limit,
    }

    session = requests.Session()
    session.trust_env = False
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.post(url, headers=headers, json=payload, verify=False, timeout=30)
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
                    "message": str(e),
                },
            }


def _load_json(raw: str, label: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} JSON parse failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _resolve_plan_payload(args: argparse.Namespace) -> tuple[str, float, int, int, str, int, str, int, int]:
    if args.plan_json:
        plan = _load_json(args.plan_json, "plan")
        oag_payload = plan.get("oag_payload") if isinstance(plan.get("oag_payload"), dict) else {}
        if not oag_payload:
            oag_payload = plan
        ontology_id = plan.get("ontology_id") or plan.get("ontology-id") or os.environ.get("ONTOLOGY_ID")
        query = oag_payload.get("query") or plan.get("query") or args.query
        similarity_threshold = oag_payload.get("similarity-threshold", args.similarity_threshold)
        include_functions = oag_payload.get("include-functions", args.include_functions)
        include_actions = oag_payload.get("include-actions", args.include_actions)
        seed_retrieval_mode = oag_payload.get("seed-retrieval-mode", args.seed_retrieval_mode)
        top_k = oag_payload.get("topK", args.topK)
        graph_expansion_strategy = oag_payload.get("graph-expansion-strategy", args.graph_expansion_strategy)
        adaptive_retrieval = oag_payload.get("adaptive-retrieval", args.adaptive_retrieval)
        hop_limit = oag_payload.get("hopLimit", args.hopLimit)
        return (
            ontology_id,
            query,
            similarity_threshold,
            include_functions,
            include_actions,
            seed_retrieval_mode,
            top_k,
            graph_expansion_strategy,
            adaptive_retrieval,
            hop_limit,
        )

    if args.query_json:
        payload = _load_json(args.query_json, "query")
        ontology_id = payload.get("ontology-id") or os.environ.get("ONTOLOGY_ID")
        query = payload.get("query")
        similarity_threshold = payload.get("similarity-threshold", args.similarity_threshold)
        include_functions = payload.get("include-functions", args.include_functions)
        include_actions = payload.get("include-actions", args.include_actions)
        seed_retrieval_mode = payload.get("seed-retrieval-mode", args.seed_retrieval_mode)
        top_k = payload.get("topK", args.topK)
        graph_expansion_strategy = payload.get("graph-expansion-strategy", args.graph_expansion_strategy)
        adaptive_retrieval = payload.get("adaptive-retrieval", args.adaptive_retrieval)
        hop_limit = payload.get("hopLimit", args.hopLimit)
        return (
            ontology_id,
            query,
            similarity_threshold,
            include_functions,
            include_actions,
            seed_retrieval_mode,
            top_k,
            graph_expansion_strategy,
            adaptive_retrieval,
            hop_limit,
        )

    ontology_id = args.ontology_id or os.environ.get("ONTOLOGY_ID")
    query = args.query
    return (
        ontology_id,
        query,
        args.similarity_threshold,
        args.include_functions,
        args.include_actions,
        args.seed_retrieval_mode,
        args.topK,
        args.graph_expansion_strategy,
        args.adaptive_retrieval,
        args.hopLimit,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic Subgraph Search: 语义子图搜索")
    parser.add_argument("--ontology-id", help="Ontology ID")
    parser.add_argument("--query", help="查询语句")
    parser.add_argument("--query-json", help="完整查询 JSON 字符串")
    parser.add_argument("--plan-json", help="由 deterministic planner 输出的完整计划 JSON 字符串")
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

    if not args.plan_json and not args.query_json and not args.query:
        result = {"success": False, "error": {"code": "INVALID_INPUT", "message": "query 是必填参数"}}
        output = json.dumps(result, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 1

    ontology_id, query, similarity_threshold, include_functions, include_actions, seed_retrieval_mode, top_k, graph_expansion_strategy, adaptive_retrieval, hop_limit = _resolve_plan_payload(args)

    if not query:
        result = {"success": False, "error": {"code": "INVALID_INPUT", "message": "query 不能为空"}}
        output = json.dumps(result, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 1

    result = search_subgraph(
        ontology_id,
        query,
        similarity_threshold,
        include_functions,
        include_actions,
        seed_retrieval_mode,
        top_k,
        graph_expansion_strategy,
        adaptive_retrieval,
        hop_limit,
    )

    output = json.dumps({"message_type": "message_ontololgy_subgraph", "title": "本体子图", "content": result["data"]["result"]}, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
