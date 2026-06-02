#!/usr/bin/env python3
"""Execute OAC Operation: 执行 OAC 操作

Usage:
    python execute_oac_operation.py --oac-json '<json_string>'
    python execute_oac_operation.py --oac-json '<json_string>' --message-type '<message_type>'
    echo '<json_string>' | python execute_oac_operation.py --input -

Examples:
    python execute_oac_operation.py --oac-json '{"version": "1.0", "operation": "query", ...}'
    python execute_oac_operation.py --oac-json '{"version": "1.0", "operation": "query", ...}' --message-type "same_site_active_alarms"
    cat request.json | python execute_oac_operation.py --input -

Output format: {"message_type": "<message_type>", "content": <data>}
Default message_type: "OAC_RETURN"
"""
from __future__ import annotations
import argparse
import json
import requests
import sys
import warnings
from pathlib import Path

# 禁用不安全的 HTTPS 请求警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Configuration
SCRIPTS_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPTS_ROOT / "tools"

OAC_URL = "https://7.220.122.186:28810/ontologyobjectservice/rest/v1/objects/query"
OAC_CERT = str(TOOLS_DIR / "client.crt.pem")
OAC_KEY = str(TOOLS_DIR / "client.key.pem")
OAC_TOKEN = "test-token"
OAC_TENANT_ID = "2001"

# 操作符白名单
VALID_OPERATORS = {"EQ", "NE", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN", "CONTAINS"}


def validate_oac_json(oac_json: dict) -> tuple[bool, str | None]:
    """校验 OAC JSON 参数

    Returns:
        (is_valid, error_message): 如果校验通过返回 (True, None)，否则返回 (False, error_message)
    """
    # 1. schemaRef 默认值
    if "schemaRef" not in oac_json or not oac_json.get("schemaRef"):
        oac_json["schemaRef"] = "network@1.0"

    # 3. objects、relationships、returns 必填
    if "objects" not in oac_json or not oac_json.get("objects"):
        return False, "objects 为必填字段"
    if "returns" not in oac_json or not oac_json.get("returns"):
        return False, "returns 为必填字段"

    # 4. objects 中的 objectType 转为小写
    objects = oac_json.get("objects", [])
    object_aliases = set()
    for obj in objects:
        if "objectType" in obj and obj["objectType"]:
            obj["objectType"] = obj["objectType"].lower()
        if "alias" in obj and obj["alias"]:
            object_aliases.add(obj["alias"])

    # 4.1 获取 operation
    operation = oac_json.get("operation", "").upper()

    # 5. relationships 校验（仅当 operation 为 ASSOCIATION_QUERY 时）
    rel_aliases = set()
    if operation == "ASSOCIATION_QUERY":
        if "relationships" not in oac_json or not oac_json.get("relationships"):
            return False, "relationships 为必填字段"
        relationships = oac_json.get("relationships", [])
        for i, rel in enumerate(relationships):
            # 每项必须有 4 个字段
            required_fields = {"relationshipType", "alias", "from", "to"}
            if not required_fields.issubset(set(rel.keys())):
                return False, f"relationships[{i}] 必须包含 {required_fields} 四个字段"

            # alias 必须以 r 开头
            alias = rel.get("alias", "")
            if alias and not alias.startswith("r"):
                return False, f"relationships 的 alias 必须以 r 开头，当前值为: {alias}"

            # alias 唯一
            if alias in rel_aliases:
                return False, f"relationships alias 必须唯一，当前重复: {alias}"
            rel_aliases.add(alias)

            # alias 不能与对象 alias 冲突
            if alias in object_aliases:
                return False, f"relationships alias '{alias}' 不能与对象 alias 冲突"

            # from/to 必须引用已声明对象 alias
            from_alias = rel.get("from", "")
            to_alias = rel.get("to", "")
            if from_alias not in object_aliases:
                return False, f"relationships[{i}].from '{from_alias}' 必须引用已声明的对象 alias"
            if to_alias not in object_aliases:
                return False, f"relationships[{i}].to '{to_alias}' 必须引用已声明的对象 alias"

    # 6. returns 只允许 FIELDS kind，不允许 EXPR、GROUP_BY、METRIC
    returns = oac_json.get("returns", [])
    for i, ret in enumerate(returns):
        kind = ret.get("kind", "")
        if kind != "FIELDS":
            return False, f"returns[{i}].kind 必须是 FIELDS，不允许 EXPR、GROUP_BY、METRIC，当前值为: {kind}"

    # 7. conditions 校验
    conditions = oac_json.get("conditions")
    if conditions:
        all_aliases = object_aliases | rel_aliases
        error = validate_conditions(conditions, all_aliases, 0)
        if error:
            return False, error

    return True, None

def validate_conditions(conditions: dict, valid_aliases: set, depth: int) -> str | None:
    """校验 conditions 递归逻辑树"""
    if depth > 10:
        return "conditions 嵌套层数超过限制 (10层)"

    kind = conditions.get("kind", "")
    if kind not in ("GROUP", "PREDICATE"):
        return f"conditions.kind 必须是 GROUP 或 PREDICATE，当前值为: {kind}"

    if kind == "GROUP":
        relation = conditions.get("relation", "")
        if relation not in ("AND", "OR"):
            return f"conditions.relation 必须是 AND 或 OR，当前值为: {relation}"
        children = conditions.get("children", [])
        if not children:
            return "conditions.children 不能为空"
        for i, child in enumerate(children):
            error = validate_conditions(child, valid_aliases, depth + 1)
            if error:
                return f"conditions.children[{i}] {error}"

    elif kind == "PREDICATE":
        ref = conditions.get("ref", "")
        if ref not in valid_aliases:
            return f"conditions.ref '{ref}' 必须来自于 objects 或 relationships 中的 alias"

        operator = conditions.get("operator", "")
        if operator not in VALID_OPERATORS:
            return f"conditions.operator 必须是 {VALID_OPERATORS} 之一，当前值为: {operator}"

        values = conditions.get("values", [])
        if not values:
            return "conditions.values 不能为空"
        # values 必须是字符串数组
        if not all(isinstance(v, str) for v in values):
            return "conditions.values 数组中的值必须是字符串"

    return None


def execute_operation(oac_json: dict) -> dict:
    """执行 OAC 操作"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OAC_TOKEN}",
        "X-Request-Id": "demo-001",
        "X-Tenant-Id": OAC_TENANT_ID,
    }

    try:
        resp = requests.post(
            OAC_URL,
            headers=headers,
            json=oac_json,
            cert=(OAC_CERT, OAC_KEY),
            verify=False,
            timeout=60,
        )
        return {"success": True, "data": resp.text}
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
        description="Execute OAC Operation: 执行 OAC 操作"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--oac-json", help="OAC JSON 字符串")
    group.add_argument("--input", help="从文件或 stdin 读取 JSON (使用 - 表示 stdin)")
    parser.add_argument("--output", help="输出文件路径 (可选)")
    parser.add_argument("--message-type", "--msg-type", dest="message_type", default="OAC_RETURN", help="返回消息类型 (默认: OAC_RETURN)")
    args = parser.parse_args()

    # 解析输入
    if args.oac_json:
        try:
            oac_json = json.loads(args.oac_json)
        except json.JSONDecodeError as e:
            result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
            output = json.dumps(result, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)
            return 1
    elif args.input:
        if args.input == "-":
            # 从 stdin 读取
            try:
                oac_json = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
                output = json.dumps(result, ensure_ascii=False)
                if args.output:
                    Path(args.output).write_text(output + "\n", encoding="utf-8")
                else:
                    print(output)
                return 1
        else:
            # 从文件读取
            input_path = Path(args.input)
            if not input_path.exists():
                result = {"success": False, "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {args.input}"}}
                output = json.dumps(result, ensure_ascii=False)
                if args.output:
                    Path(args.output).write_text(output + "\n", encoding="utf-8")
                else:
                    print(output)
                return 1
            try:
                oac_json = json.loads(input_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                result = {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": str(e)}}
                output = json.dumps(result, ensure_ascii=False)
                if args.output:
                    Path(args.output).write_text(output + "\n", encoding="utf-8")
                else:
                    print(output)
                return 1

    # 校验参数
    is_valid, error_msg = validate_oac_json(oac_json)
    if not is_valid:
        result = {"success": False, "error": {"code": "VALIDATION_ERROR", "message": error_msg}}
        output = json.dumps(result, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 1

    # 执行操作
    result = execute_operation(oac_json)

    # 输出结果
    if result["success"]:
        # 尝试解析返回的 JSON 字符串
        try:
            data = json.loads(result["data"])
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效 JSON，保持原字符串
            data = result["data"]
        # 成功时使用 message_type 和 content 格式
        if "data" in data:
            output = json.dumps({"message_type": args.message_type, "content": data["data"]}, ensure_ascii=False)
        else:
            output = json.dumps({"message_type": args.message_type, "content": []}, ensure_ascii=False)
    else:
        # 失败时返回 JSON 格式错误
        output = json.dumps(result, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())