#!/usr/bin/env python3
"""Deterministic helpers for the 0713 ontology skill stack.

This module centralizes the parts that should not rely on repeated LLM calls:
- intent / operation routing
- OAG payload preparation
- lightweight plan caching
- OQL normalization / construction

The module is intentionally stdlib-only so every script in this skill stack can
import it without adding a new dependency.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ONTOLOGY_ID = "dtmi.ontology.07a3e859.1"
DEFAULT_VERSION = "1.0"
DEFAULT_MAX_RESULTS = 1000
DEFAULT_TOP_K = 3
DEFAULT_SIMILARITY_THRESHOLD = 0.6
DEFAULT_HOP_LIMIT = 3
DEFAULT_SEED_RETRIEVAL_MODE = "vector"
DEFAULT_GRAPH_EXPANSION_STRATEGY = "minimal"

AGGREGATE_HINTS: tuple[str, ...] = (
    "统计",
    "数量",
    "条数",
    "总数",
    "合计",
    "求和",
    "平均",
    "最大",
    "最小",
    "分布",
    "占比",
    "比例",
    "排名",
    "top",
    "topk",
    "group by",
    "聚合",
)

ASSOCIATION_HINTS: tuple[str, ...] = (
    "关系",
    "关联",
    "路径",
    "一跳",
    "多跳",
    "归属",
    "连接",
    "经过",
    "包含",
    "承载",
    "上游",
    "下游",
    "周边",
    "附近",
    "周围",
    "半径",
    "范围",
    "route",
)

FUNCTION_HINTS: tuple[str, ...] = (
    "自动创建工单",
    "创建工单",
    "派单",
    "函数",
    "function",
    "调用函数",
)

COORDINATE_HINTS: tuple[str, ...] = (
    "周边",
    "附近",
    "周围",
    "半径",
    "多少米",
    "范围内",
    "附近站点",
)

INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("TICKET_CREATE", ("自动创建工单", "创建工单", "派单", "工单自动创建")),
    ("ALARM_ANALYSIS", ("告警", "alarm", "有没有告警", "查询告警")),
    ("KPI_ANALYSIS", ("kpi", "mtte", "mttr", "性能指标", "指标")),
    ("OUTAGE_ANALYSIS", ("断站", "sitedownfault", "site down", "离线", "掉站")),
    ("DEVICE_QUERY", ("站点", "网元", "小区", "设备", "详情", "列表", "query serving site")),
)


def normalize_text(value: str) -> str:
    """Collapse whitespace and normalize for keyword matching."""
    return re.sub(r"\s+", "", value or "").lower()


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def detect_intent(question: str) -> str:
    text = normalize_text(question)
    for intent, keywords in INTENT_RULES:
        if _contains_any(text, keywords):
            return intent
    return "GENERAL_QUERY"


def detect_operation(question: str) -> str:
    text = normalize_text(question)
    if _contains_any(text, AGGREGATE_HINTS):
        return "AGGREGATE"
    if _contains_any(text, ASSOCIATION_HINTS):
        return "ASSOCIATION_QUERY"
    return "QUERY"


def needs_function_call(question: str) -> bool:
    text = normalize_text(question)
    return _contains_any(text, FUNCTION_HINTS)


def needs_coordinate_lookup(question: str, entity_has_coordinate: bool = False) -> bool:
    if entity_has_coordinate:
        return False
    text = normalize_text(question)
    return _contains_any(text, COORDINATE_HINTS)


def context_fingerprint(*parts: Any) -> str:
    """Return a stable fingerprint for cache keys and deduplication."""
    payload = "\u241f".join(json.dumps(part, ensure_ascii=False, sort_keys=True, default=str) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def load_cache(cache_dir: str | Path | None, cache_key: str) -> dict[str, Any] | None:
    if not cache_dir:
        return None
    cache_path = Path(cache_dir) / f"{cache_key}.json"
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def store_cache(cache_dir: str | Path | None, cache_key: str, payload: dict[str, Any]) -> None:
    if not cache_dir:
        return
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    target = cache_path / f"{cache_key}.json"
    target.write_text(compact_json(payload) + "\n", encoding="utf-8")


def build_oag_query(question: str, operation: str, entity_hints: dict[str, Any] | None = None) -> str:
    """Create a compact OAG query hint with deterministic phrasing.

    The query text still preserves the original user meaning, but the router can
    use a stable canonical string when the upstream planner no longer wants to
    spend a model call on this step.
    """
    raw = (question or "").strip()
    if not raw:
        return raw

    if operation != "ASSOCIATION_QUERY":
        return raw

    hints = entity_hints or {}
    source = hints.get("source") or hints.get("site") or hints.get("anchor") or hints.get("name") or "起点对象"
    target = hints.get("target") or hints.get("destination") or "终点对象"
    return f"从【{source}】到【{target}】之间的路径，其中对象携带【属性】"


def build_oag_payload(
    question: str,
    ontology_id: str | None = None,
    *,
    entity_hints: dict[str, Any] | None = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    include_functions: int = 0,
    include_actions: int = 0,
    seed_retrieval_mode: str = DEFAULT_SEED_RETRIEVAL_MODE,
    top_k: int = DEFAULT_TOP_K,
    graph_expansion_strategy: str = DEFAULT_GRAPH_EXPANSION_STRATEGY,
    adaptive_retrieval: int = 1,
    hop_limit: int = DEFAULT_HOP_LIMIT,
) -> dict[str, Any]:
    operation = detect_operation(question)
    query = build_oag_query(question, operation, entity_hints)
    return {
        "ontology-id": ontology_id or os.environ.get("ONTOLOGY_ID") or DEFAULT_ONTOLOGY_ID,
        "query": query,
        "similarity-threshold": similarity_threshold,
        "include-functions": include_functions,
        "include-actions": include_actions,
        "seed-retrieval-mode": seed_retrieval_mode,
        "topK": top_k,
        "graph-expansion-strategy": graph_expansion_strategy,
        "adaptive-retrieval": adaptive_retrieval,
        "hopLimit": hop_limit,
    }


def plan_service_request(
    question: str,
    ontology_id: str | None = None,
    *,
    entity_hints: dict[str, Any] | None = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    include_functions: int = 0,
    include_actions: int = 0,
    top_k: int = DEFAULT_TOP_K,
    graph_expansion_strategy: str = DEFAULT_GRAPH_EXPANSION_STRATEGY,
    adaptive_retrieval: int = 1,
    hop_limit: int = DEFAULT_HOP_LIMIT,
) -> dict[str, Any]:
    """Create a single deterministic planning result for the business skill.

    The returned plan is intentionally compact so the orchestration layer can
    stop repeatedly re-planning and instead execute the fixed tool chain.
    """
    normalized_question = normalize_text(question)
    intent = detect_intent(question)
    operation = detect_operation(question)
    need_function = needs_function_call(question)
    entity_hints = entity_hints or {}
    need_coordinate = needs_coordinate_lookup(question, bool(entity_hints.get("has_coordinate")))

    blocking_gaps: list[str] = []
    if need_coordinate and not any(entity_hints.get(key) for key in ("source", "site", "anchor", "name")):
        blocking_gaps.append("缺少周边查询锚点对象")
    if need_function and not entity_hints.get("function_id"):
        blocking_gaps.append("缺少函数标识或函数名")

    cache_key = context_fingerprint(
        ontology_id or os.environ.get("ONTOLOGY_ID") or DEFAULT_ONTOLOGY_ID,
        question,
        entity_hints,
        similarity_threshold,
        include_functions,
        include_actions,
        top_k,
        graph_expansion_strategy,
        adaptive_retrieval,
        hop_limit,
    )
    oag_payload = build_oag_payload(
        question,
        ontology_id,
        entity_hints=entity_hints,
        similarity_threshold=similarity_threshold,
        include_functions=include_functions or (1 if need_function else 0),
        include_actions=include_actions,
        top_k=top_k,
        graph_expansion_strategy=graph_expansion_strategy,
        adaptive_retrieval=adaptive_retrieval,
        hop_limit=hop_limit,
    )

    return {
        "message_type": "SERVICE_QUALITY_PLAN",
        "ontology_id": ontology_id or os.environ.get("ONTOLOGY_ID") or DEFAULT_ONTOLOGY_ID,
        "question": question,
        "normalized_question": normalized_question,
        "intent": intent,
        "operation": operation,
        "route": {
            "needs_oag": True,
            "needs_oac": True,
            "needs_function": need_function,
            "needs_coordinate": need_coordinate,
        },
        "blocking_gaps": blocking_gaps,
        "entity_hints": entity_hints,
        "oag_payload": oag_payload,
        "cache_key": cache_key,
        "recommended_steps": [
            {
                "step": 1,
                "script": "semantic_subgraph_search.py",
                "input_mode": "--plan-json",
            },
            {
                "step": 2,
                "script": "execute_oac_operation.py",
                "input_mode": "--oac-json",
            },
        ],
    }


def normalize_oql(oql: dict[str, Any], ontology_id: str | None = None) -> dict[str, Any]:
    """Apply harmless deterministic normalization before validation."""
    payload = copy.deepcopy(oql)
    payload["version"] = payload.get("version") or os.environ.get("OQL_VERSION") or DEFAULT_VERSION

    operation = payload.get("operation")
    if isinstance(operation, str):
        payload["operation"] = operation.upper()

    if not payload.get("schemaRef"):
        payload["schemaRef"] = ontology_id or os.environ.get("ONTOLOGY_ID") or DEFAULT_ONTOLOGY_ID

    if "strict" not in payload or payload["strict"] is None:
        payload["strict"] = True

    if "maxResults" not in payload or payload["maxResults"] in (None, ""):
        payload["maxResults"] = DEFAULT_MAX_RESULTS
    elif isinstance(payload["maxResults"], str) and payload["maxResults"].isdigit():
        payload["maxResults"] = int(payload["maxResults"])

    return payload


def build_oql_request(
    operation: str,
    schema_ref: str,
    *,
    objects: list[dict[str, Any]],
    returns: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    conditions: dict[str, Any] | None = None,
    aggregate_filter: dict[str, Any] | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    strict: bool = True,
    version: str = DEFAULT_VERSION,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": version,
        "schemaRef": schema_ref,
        "strict": strict,
        "operation": operation,
        "objects": objects,
        "returns": returns,
        "maxResults": max_results,
    }
    if relationships:
        payload["relationships"] = relationships
    if conditions:
        payload["conditions"] = conditions
    if aggregate_filter:
        payload["aggregateFilter"] = aggregate_filter
    return normalize_oql(payload, ontology_id=schema_ref)
