#!/usr/bin/env python3
"""Validate OAC natural-language data-access template.

This script performs front-end friendly soft validation for the generic
OAC natural-language delegation template. It validates whether the template
contains enough information for an agent to route to OAC and generate OQL.
It does not validate business-specific semantics.

Usage:
  python scripts/validate_oac_nl_template.py --template-json '{"operationType":"查询明细",...}'
  cat template.json | python scripts/validate_oac_nl_template.py --input -

Output:
  {"valid": true|false, "errors": [], "warnings": [], "normalized": {...}}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

FIELD_ALIASES = {
    "schemaRef": ["schemaRef", "schema_ref", "schema", "本体schema", "模型范围"],
    "operationType": ["operationType", "operation_type", "操作类型", "查询动作", "数据访问动作"],
    "operationReason": ["operationReason", "operation_reason", "操作选择依据", "选择依据"],
    "queryObjects": ["queryObjects", "query_objects", "查询对象", "对象", "objects"],
    "relationPath": ["relationPath", "relation_path", "关系路径", "路径", "relationships"],
    "filters": ["filters", "过滤条件", "conditions", "条件"],
    "returnFields": ["returnFields", "return_fields", "返回字段", "returns"],
    "aggregateRequirement": ["aggregateRequirement", "aggregate_requirement", "聚合要求", "统计要求"],
    "orderLimit": ["orderLimit", "order_limit", "排序限制", "排序/限制", "排序", "限制"],
    "timeRequirement": ["timeRequirement", "time_requirement", "时间要求", "时间口径", "时间范围"],
    "extensions": ["extensions", "扩展说明", "扩展参数"],
    "resultHandling": ["resultHandling", "result_handling", "结果处理"],
}

QUERY_HINTS = ("查询", "明细", "属性", "列表", "对象", "指标明细")
ASSOCIATION_HINTS = ("关系", "路径", "遍历", "连接", "经过", "一跳", "多跳", "归属", "对应")
AGGREGATE_HINTS = ("统计", "聚合", "分组", "计数", "求和", "平均", "最大", "最小", "总数", "总和")


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip() in {"无", "不涉及", "无需", "N/A", "null"}
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def normalize_template(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in payload:
                normalized[canonical] = payload[alias]
                break
        else:
            normalized[canonical] = None
    return normalized


def infer_operation_kind(operation_text: str) -> str | None:
    text = operation_text or ""
    if any(token in text for token in AGGREGATE_HINTS):
        return "AGGREGATE"
    if any(token in text for token in ASSOCIATION_HINTS):
        return "ASSOCIATION_QUERY"
    if any(token in text for token in QUERY_HINTS):
        return "QUERY"
    return None


def validate_extensions(extensions: Any, errors: list[str], warnings: list[str]) -> None:
    if _is_empty(extensions):
        return
    if isinstance(extensions, str):
        text = extensions.strip()
        if "localtime" in text and "true" not in text and "false" not in text:
            warnings.append("extensions 提到了 localtime，但没有明确 true 或 false。")
        return
    if not isinstance(extensions, dict):
        errors.append("extensions/扩展说明 应为对象或自然语言说明。")
        return
    if "localtime" in extensions:
        value = extensions.get("localtime")
        if str(value).lower() not in {"true", "false"}:
            errors.append("extensions.localtime 仅允许为 true 或 false。")


def validate_time_requirement(time_requirement: Any, extensions: Any, warnings: list[str]) -> None:
    text = _to_text(time_requirement)
    ext_text = _to_text(extensions)
    if "本地时间" in text and "localtime" not in ext_text:
        warnings.append("时间要求包含本地时间，建议在扩展说明中写明 extensions.localtime=true。")
    if "UTC" in text.upper() and "localtime" not in ext_text:
        warnings.append("时间要求包含 UTC，建议在扩展说明中写明 extensions.localtime=false。")
    if ("本地时间" in text or "UTC" in text.upper()) and not any(token in text for token in ("从", "到", "最近", "今天", "昨天", "时间范围", "起止")):
        warnings.append("时间口径不能替代时间范围；如需要按时间过滤，请补充起止范围或相对时间窗口。")


def validate_template(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_template(payload)
    errors: list[str] = []
    warnings: list[str] = []

    schema_ref = normalized["schemaRef"]
    if _is_empty(schema_ref) and not os.environ.get("ONTOLOGY_SCHEMA_REF"):
        warnings.append("schemaRef 未填写，且当前环境变量 ONTOLOGY_SCHEMA_REF 未设置；执行前需要补齐其一。")

    operation_type = normalized["operationType"]
    if _is_empty(operation_type):
        errors.append("操作类型/查询动作 为必填字段，可用中文自然语言描述。")
        operation_kind = None
    else:
        operation_kind = infer_operation_kind(_to_text(operation_type))
        if operation_kind is None:
            warnings.append("操作类型未能明确匹配 QUERY、ASSOCIATION_QUERY 或 AGGREGATE，建议补充操作选择依据。")

    if _is_empty(normalized["queryObjects"]):
        errors.append("查询对象 为必填字段，应说明对象类型、别名或业务对象范围。")

    if _is_empty(normalized["returnFields"]):
        errors.append("返回字段 为必填字段，应说明返回哪个对象或关系的哪些字段。")

    if operation_kind == "ASSOCIATION_QUERY" and _is_empty(normalized["relationPath"]):
        errors.append("关联/路径查询必须填写关系路径。")

    if operation_kind == "AGGREGATE" and _is_empty(normalized["aggregateRequirement"]):
        errors.append("聚合查询必须填写聚合要求，例如分组字段、统计函数和指标别名。")

    validate_extensions(normalized["extensions"], errors, warnings)
    validate_time_requirement(normalized["timeRequirement"], normalized["extensions"], warnings)

    normalized["operationKindHint"] = operation_kind
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "normalized": normalized,
    }


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.template_json:
        raw = args.template_json
    elif args.input == "-":
        raw = sys.stdin.read()
    else:
        raise SystemExit("必须通过 --template-json 或 --input - 传入模板 JSON。")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"模板 JSON 解析失败: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("模板 JSON 顶层必须是对象。")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OAC natural-language template fields.")
    parser.add_argument("--template-json", help="Template JSON string.")
    parser.add_argument("--input", help="Use '-' to read template JSON from stdin.")
    args = parser.parse_args()

    payload = load_payload(args)
    result = validate_template(payload)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
