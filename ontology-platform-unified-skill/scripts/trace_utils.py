#!/usr/bin/env python3
import json
import os
import random
import sys
import io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CONTEXT_BASE_DIR = "/var/log/contexts"
LOG_BASE_DIR = "/var/log/trace_logs"

TENANT_ID = os.getenv("tenant_id", "1002")

def build_headers(context_json=None, tenant_id=None):

    return {
        "X-Request-Id": "multiDatasource",
        "X-Tenant-Id": tenant_id,
        "x-gde-tenant-id": tenant_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-B3-TraceId": _get(context_json, "X-B3-TraceId"),
        "X-B3-SpanId": _get(context_json, "X-B3-SpanId"),
        "X-B3-ParentSpanId": _get(context_json, "X-B3-ParentSpanId"),
    }

def get_context_by_session(session_id: str) -> dict:
    """根据 session_id 读取 bash context 文件，返回更新 SpanId 后的请求头字典。

    Args:
        session_id: 会话标识，用于拼接 context 文件路径。

    Returns:
        更新 X-B3-ParentSpanId 和 X-B3-SpanId 后的 context 字典（不写回文件）。

    Raises:
        FileNotFoundError: context 文件不存在时抛出。
    """

    context_path = os.path.join(CONTEXT_BASE_DIR, f"context_bash_{session_id}")

    if not os.path.exists(context_path):
        error_msg = f"bash context file not found: {context_path}"
        print(error_msg, file=sys.stderr)
        raise FileNotFoundError(error_msg)

    with open(context_path, "r", encoding="utf-8") as f:
        context_json = json.loads(f.read())

    return context_json


def _get(d: dict, key: str, default: str = "") -> str:
    """安全获取字典值，字典为 None 时返回默认值。"""
    return d.get(key, default) if d else default


def _get_number(d: dict, key: str, default: int = 0) -> int:
    """安全获取字典中的数值，字典为 None 时返回默认值。"""
    return d.get(key, default) if d else default


def escape_for_json_lines(value: str) -> str:
    """将真实换行符和回车符转义为字面量 \r / \n，防止 JSON Lines 被截断。"""
    return value.replace("\r", "\\r").replace("\n", "\\n")


def _build_base_entry(context_json: dict, ext_content_json: dict) -> dict:
    """构建 trace log 的基准条目（公共字段）。"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "start_time": _get_number(ext_content_json, "start_time"),
        "end_time": 0,
        "trace_id": _get(context_json, "X-B3-TraceId"),
        "parent_id": _get(context_json, "X-B3-ParentSpanId"),
        "span_id": _get(context_json, "X-B3-SpanId"),
        "span_name": "",
        "gen_ai.conversation.id": _get(context_json, "x-gde-agent-conversation-id"),
        "attributes": {
            "gen_ai.session.id": _get(context_json, "x-gde-agent-session-id"),
            "gen_ai.agent.name": _get(context_json, "x-gde-agent-name"),
            "gen_ai.span.kind": "API",
            "span.display_name": "{\"zh_CN\":\"\",\"en_US\":\"\"}",
            "input.value": escape_for_json_lines(_get(ext_content_json, "input.value")),
            "output.value": "",
            "tool.type": "",
            "api.url": "",
            "api.method": "",
            "skill.name": "",
            "remote.cse.uri": _get(ext_content_json, "remote.cse.uri"),
            "error": "",
        },
    }


def _apply_type_fields(base_entry: dict, type: str, ext_content_json: dict) -> None:
    """根据 type 填充 end_time、span_name、span.display_name 及 type 专属字段。"""
    type_mapping = {
        "CSE Invoke Failed": {
            "span_name": "CSE Invoke Failed",
            "display_name": "{\"zh_CN\":\"CSE 调用失败\",\"en_US\":\"CSE Invoke Failed\"}",
        },
        "CSE Invoke Completed": {
            "span_name": "CSE Invoke Completed",
            "display_name": "{\"zh_CN\":\"CSE 调用完成\",\"en_US\":\"CSE Invoke Completed\"}",
        },
    }
    info = type_mapping.get(type)
    if not info:
        return

    base_entry["end_time"] = _get_number(ext_content_json, "end_time")
    base_entry["span_name"] = info["span_name"]
    base_entry["attributes"]["span.display_name"] = info["display_name"]

    if type == "CSE Invoke Failed":
        base_entry["attributes"]["error"] = escape_for_json_lines(_get(ext_content_json, "error"))
    elif type == "CSE Invoke Completed":
        base_entry["attributes"]["output.value"] = escape_for_json_lines(_get(ext_content_json, "output.value"))


def write_cse_trace_log(session_id: str, type: str, ext_content_json: dict, context_json: dict) -> None:
    """将 CSE 接口调用日志追加写入日志文件。

    Args:
        session_id: 会话标识，用于拼接日志文件路径。
        type: 日志类型，可选 "CSE Invoke Failed" 或 "CSE Invoke Completed"。
        ext_content_json: 扩展内容字典，包含业务字段（start_time, end_time, input.value, output.value, remote.cse.uri 等）。
        context_json: 请求头字典（由 get_context_by_session 获得），包含链路追踪字段。
    """
    log_path = os.path.join(LOG_BASE_DIR, f"trace_{session_id}.log")
    os.makedirs(LOG_BASE_DIR, exist_ok=True)

    base_entry = _build_base_entry(context_json, ext_content_json)
    _apply_type_fields(base_entry, type, ext_content_json)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(base_entry, ensure_ascii=False) + "\n")