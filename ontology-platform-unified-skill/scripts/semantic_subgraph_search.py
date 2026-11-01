#!/usr/bin/env python3
"""OAG V2 semantic subgraph search.

HTTP entities is a JSON string containing {"entities": {...}}.
Preserves existing Skill defaults: hybrid search and includeFunctions=1.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from trace_utils import build_headers, get_context_by_session

MAX_RETRIES = 3
RETRY_DELAY = 1
RETRY_HTTP = {429, 502, 503, 504}
MESSAGE_TYPE = "message_ontololgy_subgraph"  # Legacy consumer compatibility.


class InputError(ValueError):
    """Invalid local request."""


def _read_json(source: Any) -> Any:
    if not isinstance(source, str):
        return source
    if source.startswith("@"):
        source = Path(source[1:]).read_text(encoding="utf-8")
    return json.loads(source)


def normalize_entities(raw: Any) -> str | None:
    """Accept an inner object, a wrapped object or JSON text; send V2 JSON string."""
    if raw is None or raw == "":
        return None
    data = _read_json(raw)
    if not isinstance(data, dict):
        raise InputError("entities 必须是 JSON 对象")
    if "entities" in data:
        data = data["entities"]
    if not isinstance(data, dict):
        raise InputError("entities 根字段必须为对象")
    anchors = data.get("extractedEntities")
    if not isinstance(anchors, list) or not anchors:
        raise InputError("entities.extractedEntities 至少包含一个对象")
    for i, item in enumerate(anchors):
        if not isinstance(item, dict) or not isinstance(item.get("objectType"), str) or not item["objectType"].strip():
            raise InputError(f"extractedEntities[{i}].objectType 必须为非空字符串")
        props = item.get("properties", [])
        if not isinstance(props, list) or any(not isinstance(x, str) or not x for x in props):
            raise InputError(f"extractedEntities[{i}].properties 必须为字符串数组")
    groups = data.get("propertyValues", [])
    if not isinstance(groups, list):
        raise InputError("entities.propertyValues 必须是数组")
    for i, group in enumerate(groups):
        if not isinstance(group, dict) or not isinstance(group.get("objectType"), str) or not group["objectType"].strip():
            raise InputError(f"propertyValues[{i}].objectType 必须为非空字符串")
        pairs = group.get("propertyValues")
        if not isinstance(pairs, list):
            raise InputError(f"propertyValues[{i}].propertyValues 必须为数组")
        for j, pair in enumerate(pairs):
            if not isinstance(pair, dict) or not isinstance(pair.get("value"), str) or not pair["value"]:
                raise InputError(f"propertyValues[{i}].propertyValues[{j}].value 必须为非空字符串")
            if "property" in pair and not isinstance(pair["property"], str):
                raise InputError(f"propertyValues[{i}].propertyValues[{j}].property 必须为字符串或省略")
    encoded = json.dumps({"entities": data}, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > 102400:
        raise InputError("entities 超过 102400 字符")
    return encoded


def build_payload(*, ontology_id: str, query: str | None = None, entities: Any = None,
                  similarity_threshold: float = 0.6, include_functions: int = 1,
                  include_actions: int = 0, seed_retrieval_mode: str = "hybrid",
                  topk: int = 3, graph_expansion_strategy: str = "minimal",
                  adaptive_retrieval: int | None = None, hop_limit: int = 3) -> dict:
    if not isinstance(ontology_id, str) or not 1 <= len(ontology_id.strip()) <= 256:
        raise InputError("ontologyId 必须为 1~256 字符")
    if query is not None and not isinstance(query, str):
        raise InputError("query 必须为字符串")
    query = query.strip() if query is not None else None
    entities_text = normalize_entities(entities)
    if not query and not entities_text:
        raise InputError("query 与 entities 至少一个非空")
    if query and len(query) > 1024:
        raise InputError("query 超过 1024 字符")
    if seed_retrieval_mode not in ("vector", "keyword", "hybrid"):
        raise InputError("seedRetrievalMode 必须为 vector/keyword/hybrid")
    if graph_expansion_strategy not in ("minimal", "khop", "component"):
        raise InputError("graphExpansionStrategy 必须为 minimal/khop/component")
    if type(topk) is not int or topk < 1:
        raise InputError("topk 必须是正整数")
    if type(hop_limit) is not int or hop_limit < 0:
        raise InputError("hopLimit 必须是非负整数")
    if type(include_functions) is not int or include_functions not in (0, 1):
        raise InputError("includeFunctions 必须为 0/1")
    if type(include_actions) is not int or include_actions not in (0, 1):
        raise InputError("includeActions 必须为 0/1")
    if adaptive_retrieval is None:
        adaptive_retrieval = 0 if entities_text else 1
    if type(adaptive_retrieval) is not int or adaptive_retrieval not in (0, 1):
        raise InputError("adaptiveRetrieval 必须为 0/1")
    if type(similarity_threshold) not in (int, float) or not 0 <= similarity_threshold <= 1:
        raise InputError("similarityThreshold 必须在 0 到 1 之间")
    payload = {"ontologyId": ontology_id.strip(), "seedRetrievalMode": seed_retrieval_mode,
               "similarityThreshold": similarity_threshold, "topk": topk,
               "graphExpansionStrategy": graph_expansion_strategy, "adaptiveRetrieval": adaptive_retrieval,
               "hopLimit": hop_limit, "includeFunctions": include_functions, "includeActions": include_actions}
    if query:
        payload["query"] = query
    if entities_text:
        payload["entities"] = entities_text
    return payload


def _get(data: dict, key: str, alias: str, fallback: Any) -> Any:
    if key in data:
        return data[key]
    if alias in data:
        return data[alias]
    return fallback


def payload_from_args(args: argparse.Namespace) -> dict:
    data = _read_json(args.query_json) if args.query_json is not None else {}
    if not isinstance(data, dict):
        raise InputError("--query-json 必须是 JSON 对象")
    entities = data.get("entities", args.entities)
    if args.entities_file:
        if entities is not None:
            raise InputError("--entities-file 不可与 --entities/JSON entities 同时使用")
        entities = "@" + args.entities_file
    return build_payload(
        ontology_id=_get(data, "ontologyId", "ontology-id", args.ontology_id or os.getenv("ONTOLOGY_ID")),
        query=data.get("query", args.query), entities=entities,
        similarity_threshold=_get(data, "similarityThreshold", "similarity-threshold", args.similarity_threshold),
        include_functions=_get(data, "includeFunctions", "include-functions", args.include_functions),
        include_actions=_get(data, "includeActions", "include-actions", args.include_actions),
        seed_retrieval_mode=_get(data, "seedRetrievalMode", "seed-retrieval-mode", args.seed_retrieval_mode),
        topk=_get(data, "topk", "topK", args.topk),
        graph_expansion_strategy=_get(data, "graphExpansionStrategy", "graph-expansion-strategy", args.graph_expansion_strategy),
        adaptive_retrieval=_get(data, "adaptiveRetrieval", "adaptive-retrieval", args.adaptive_retrieval),
        hop_limit=_get(data, "hopLimit", "hop-limit", args.hop_limit),
    )


def _error(code: str, message: str, **extra: Any) -> dict:
    return {"success": False, "error": {"code": code, "message": message, **extra}}


def post_subgraph(payload: dict, *, session: Any = None) -> dict:
    namespace = os.getenv("SERVICE_NAMESPACE")
    tenant_id = os.getenv("TENANT_ID")
    if not namespace or not tenant_id:
        return _error("ENVIRONMENT_ERROR", "SERVICE_NAMESPACE 和 TENANT_ID 必须设置")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", namespace):
        return _error("ENVIRONMENT_ERROR", "SERVICE_NAMESPACE 非法")
    url = (f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/ontoretrieval/rest/"
           "onto-retrieval-api/v2/onto-retrieval/subgraph/semantic-search")
    try:
        session_id = os.getenv("_AGENT_SESSION_ID", "")
        ctx = get_context_by_session(session_id) if session_id else {}
        headers = build_headers(ctx, tenant_id)
        headers["Content-Type"] = "application/json"
    except Exception as exc:
        return _error("TRACE_CONTEXT_ERROR", f"会话上下文不可用: {type(exc).__name__}")
    owned = session is None
    session = session or requests.Session()
    if owned:
        session.trust_env = False
    try:
        for attempt in range(MAX_RETRIES):
            try:
                resp = session.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code in RETRY_HTTP and attempt + 1 < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                if not 200 <= resp.status_code < 300:
                    return _error("HTTP_ERROR", f"HTTP {resp.status_code}", status_code=resp.status_code)
                try:
                    data = resp.json()
                except ValueError:
                    return _error("INVALID_RESPONSE", "服务端未返回合法 JSON")
                if not isinstance(data, dict):
                    return _error("INVALID_RESPONSE", "服务端响应必须为 JSON 对象")
                if str(data.get("resultCode")) != "200" or data.get("result") is None:
                    return _error("OAG_BUSINESS_ERROR", str(data.get("resultMessage") or "子图检索失败"),
                                  result_code=data.get("resultCode"))
                return {"success": True, "data": data}
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt + 1 >= MAX_RETRIES:
                    return _error("NETWORK_ERROR", f"请求失败: {type(exc).__name__}")
                time.sleep(RETRY_DELAY * (attempt + 1))
            except requests.RequestException as exc:
                return _error("HTTP_CLIENT_ERROR", f"请求异常: {type(exc).__name__}")
        return _error("RETRY_EXHAUSTED", "重试次数已用尽")
    finally:
        if owned:
            session.close()


def search_subgraph(ontologyId: str, query: str | None = None, similarityThreshold: float = 0.6,
                    includeFunctions: int = 1, includeActions: int = 0, seedRetrievalMode: str = "hybrid",
                    topK: int = 3, graphExpansionStrategy: str = "minimal",
                    adaptive_retrieval: int | None = None, hopLimit: int = 3,
                    entities: Any = None) -> dict:
    """Backward-compatible Python call signature; always uses V2 over HTTP."""
    try:
        payload = build_payload(ontology_id=ontologyId, query=query, entities=entities,
                                similarity_threshold=similarityThreshold, include_functions=includeFunctions,
                                include_actions=includeActions, seed_retrieval_mode=seedRetrievalMode,
                                topk=topK, graph_expansion_strategy=graphExpansionStrategy,
                                adaptive_retrieval=adaptive_retrieval, hop_limit=hopLimit)
    except (ValueError, OSError) as exc:
        return _error("INVALID_INPUT", str(exc))
    return post_subgraph(payload)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OAG V2 子图检索 (query 或 entities)")
    parser.add_argument("--ontology-id", help="本体 ID（可通过 ONTOLOGY_ID 环境变量指定）")
    parser.add_argument("--query", help="自然语言问题")
    parser.add_argument("--entities", help="entities JSON 对象或完整包装 {entities:{...}}")
    parser.add_argument("--entities-file", help="entities JSON 文件路径")
    parser.add_argument("--query-json", help="完整 V2 Body JSON（也支持 @文件路径）")
    parser.add_argument("--similarity-threshold", type=float, default=0.6)
    parser.add_argument("--include-functions", type=int, default=1)
    parser.add_argument("--include-actions", type=int, default=0)
    parser.add_argument("--seed-retrieval-mode", default="hybrid")
    parser.add_argument("--topk", "--topK", dest="topk", type=int, default=3)
    parser.add_argument("--graph-expansion-strategy", default="minimal")
    parser.add_argument("--adaptive-retrieval", type=int, default=None)
    parser.add_argument("--hop-limit", "--hopLimit", dest="hop_limit", type=int, default=3)
    parser.add_argument("--output", help="保存输出 JSON 到文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        payload = payload_from_args(args)
        result = post_subgraph(payload)
    except (ValueError, OSError) as exc:
        result = _error("INVALID_INPUT", str(exc))
    output = {"message_type": MESSAGE_TYPE, "title": "本体子图",
              "content": result["data"]["result"] if result.get("success") else result}
    content = json.dumps(output, ensure_ascii=False)
    try:
        if args.output:
            Path(args.output).write_text(content + "\n", encoding="utf-8")
        else:
            print(content)
    except OSError as exc:
        print(f"输出失败: {exc}", file=sys.stderr)
        return 1
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
