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
import os

import requests
import sys
import warnings
from pathlib import Path

# 禁用不安全的 HTTPS 请求警告
warnings.filterwarnings("ignore")

# 操作符白名单
VALID_OPERATORS = {
    "EQ", "NE", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN", "CONTAINS",
    "BETWEEN", "LIKE", "STARTS_WITH", "ENDS_WITH",
    "IS_NULL", "IS_NOT_NULL", "IS_EMPTY", "IS_NOT_EMPTY",
    "EXISTS", "NOT_EXISTS"
}

# operation 白名单
VALID_OPERATIONS = {"QUERY", "AGGREGATE", "ASSOCIATION_QUERY", "CREATE", "UPDATE", "DELETE", "UPSERT", "BATCH"}

# returns.kind 白名单
VALID_RETURN_KINDS = {"FIELDS", "EXPR", "GROUP_BY", "METRIC"}

# 聚合函数白名单
VALID_AGGREGATE_FUNCTIONS = {"COUNT", "SUM", "AVG", "MIN", "MAX"}

# aggregateFilter 操作符
VALID_AGGREGATE_OPERATORS = {"EQ", "NE", "GT", "GTE", "LT", "LTE", "BETWEEN", "IN", "NOT_IN", "IS_NULL", "IS_NOT_NULL"}

# 核心内置函数白名单
CORE_FUNCTIONS = {
    "ABS", "ROUND", "CEIL", "FLOOR",
    "LENGTH", "LOWER", "UPPER", "TRIM", "SUBSTRING", "CONCAT",
    "NOW", "DATE_TRUNC", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND", "DATE_ADD", "DATE_SUB", "DATEDIFF",
    "COALESCE", "IFNULL"
}


def validate_oac_json(oac_json: dict) -> tuple[bool, str | None]:
    """校验 OAC JSON 参数

    Returns:
        (is_valid, error_message): 如果校验通过返回 (True, None)，否则返回 (False, error_message)
    """
    # 1. version 校验（可选，为空时默认插入 "1.0"）
    if not oac_json.get("version"):
        oac_json["version"] = "1.0"

    # 2. schemaRef（可从环境变量获取）
    if not oac_json.get("schemaRef"):
        schema_ref_from_env = os.environ.get("ONTOLOGY_SCHEMA_REF")
        if schema_ref_from_env:
            oac_json["schemaRef"] = schema_ref_from_env
        else:
            return False, "schemaRef 为必填字段（可设置环境变量 ONTOLOGY_SCHEMA_REF）"

    # 3. operation 必填且合法
    operation = oac_json.get("operation", "").upper()
    if not operation:
        return False, "operation 为必填字段"
    if operation not in VALID_OPERATIONS:
        return False, f"operation 必须是 {VALID_OPERATIONS} 之一，当前值为: {operation}"

    # 4. strict 字段校验（不存在时默认插入 true）
    if "strict" not in oac_json or oac_json["strict"] is None:
        oac_json["strict"] = True

    # 5. operation 与字段兼容性校验
    error = validate_operation_compatibility(oac_json)
    if error:
        return False, error

    # 6. objects 校验
    objects = oac_json.get("objects", [])
    if operation in ("CREATE", "UPDATE", "DELETE", "UPSERT"):
        if not objects or len(objects) != 1:
            return False, f"operation={operation} 时 objects 必须恰好有一个对象"
    elif operation == "BATCH":
        if objects:
            return False, "operation=BATCH 时顶层不得出现 objects"
    else:
        if not objects:
            return False, "objects 为必填字段"

    object_aliases = set()
    for i, obj in enumerate(objects):
        alias = obj.get("alias", "")
        object_type = obj.get("objectType", "")
        if not alias:
            return False, f"objects[{i}].alias 不能为空"
        if not object_type:
            return False, f"objects[{i}].objectType 不能为空"
        if alias in object_aliases:
            return False, f"objects alias 必须唯一，当前重复: {alias}"
        object_aliases.add(alias)

    # 7. relationships 校验（仅当 operation 为 ASSOCIATION_QUERY 时）
    rel_aliases = set()
    if operation == "ASSOCIATION_QUERY":
        relationships = oac_json.get("relationships", [])
        if not relationships:
            return False, "operation=ASSOCIATION_QUERY 时 relationships 为必填字段"
        for i, rel in enumerate(relationships):
            required_fields = {"relationshipType", "alias", "from", "to"}
            if not required_fields.issubset(set(rel.keys())):
                return False, f"relationships[{i}] 必须包含 {required_fields} 四个字段"
            alias = rel.get("alias", "")
            if alias and not alias.startswith("r"):
                return False, f"relationships 的 alias 必须以 r 开头，当前值为: {alias}"
            if alias in rel_aliases:
                return False, f"relationships alias 必须唯一，当前重复: {alias}"
            rel_aliases.add(alias)
            if alias in object_aliases:
                return False, f"relationships alias '{alias}' 不能与对象 alias 冲突"
            from_alias = rel.get("from", "")
            to_alias = rel.get("to", "")
            if from_alias not in object_aliases:
                return False, f"relationships[{i}].from '{from_alias}' 必须引用已声明的对象 alias"
            if to_alias not in object_aliases:
                return False, f"relationships[{i}].to '{to_alias}' 必须引用已声明的对象 alias"

    # 8. returns 校验
    if operation in ("QUERY", "ASSOCIATION_QUERY", "AGGREGATE"):
        if "returns" not in oac_json or not oac_json.get("returns"):
            return False, f"operation={operation} 时 returns 为必填字段"
        all_aliases = object_aliases | rel_aliases
        result = validate_returns(oac_json.get("returns", []), operation, all_aliases)
        if isinstance(result, tuple):
            error, metric_aliases = result
        else:
            error = result
            metric_aliases = set()
        if error:
            return False, error
    else:
        metric_aliases = set()

    # 9. conditions 校验
    conditions = oac_json.get("conditions")
    if conditions:
        all_aliases = object_aliases | rel_aliases
        error = validate_conditions(conditions, all_aliases, 0)
        if error:
            return False, error

    # 10. aggregateFilter 校验
    if "aggregateFilter" in oac_json and oac_json["aggregateFilter"]:
        if operation != "AGGREGATE":
            return False, "aggregateFilter 仅允许在 AGGREGATE 中使用"
        error = validate_aggregate_filter(oac_json["aggregateFilter"], metric_aliases)
        if error:
            return False, error

    # 11. orders 校验
    if "orders" in oac_json and oac_json["orders"]:
        error = validate_orders(oac_json["orders"])
        if error:
            return False, error

    # 12. maxResults 校验
    if "maxResults" in oac_json and oac_json["maxResults"]:
        error = validate_max_results(oac_json["maxResults"])
        if error:
            return False, error

    # 13. mutation 校验
    if "mutation" in oac_json and oac_json["mutation"]:
        if operation not in ("CREATE", "UPDATE", "DELETE", "UPSERT"):
            return False, f"operation={operation} 时不允许出现 mutation"
        error = validate_mutation(oac_json["mutation"], operation)
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
        if relation not in ("AND", "OR", "NOT"):
            return f"conditions.relation 必须是 AND、OR 或 NOT，当前值为: {relation}"
        children = conditions.get("children", [])
        if not children:
            return "conditions.children 不能为空"
        if relation == "NOT" and len(children) != 1:
            return "conditions.relation=NOT 时，children 必须恰好有一个子条件"
        for i, child in enumerate(children):
            error = validate_conditions(child, valid_aliases, depth + 1)
            if error:
                return f"conditions.children[{i}] {error}"

    elif kind == "PREDICATE":
        ref = conditions.get("ref", "")
        left = conditions.get("left", {})
        if not ref and not left:
            return "conditions 必须包含 ref 或 left 字段"

        if ref and ref not in valid_aliases:
            return f"conditions.ref '{ref}' 必须来自于 objects 或 relationships 中的 alias"

        operator = conditions.get("operator", "")
        if operator not in VALID_OPERATORS:
            return f"conditions.operator 必须是 {VALID_OPERATORS} 之一，当前值为: {operator}"

        # 操作符与 values 个数校验
        values = conditions.get("values", [])
        if operator == "BETWEEN":
            if len(values) != 2:
                return f"BETWEEN 操作符需要 exactly 两个 values，当前: {len(values)}"
        elif operator in ("IN", "NOT_IN"):
            if not values:
                return f"IN/NOT_IN 操作符需要 non-empty values"
        else:
            if not values:
                return "conditions.values 不能为空"
    return None


def validate_returns(returns: list, operation: str, valid_aliases: set) -> tuple[str | None, set]:
    """校验 returns 定义"""
    if not returns:
        return "returns 不能为空"

    metric_aliases = set()
    group_by_aliases = set()

    for i, ret in enumerate(returns):
        kind = ret.get("kind", "")
        if kind not in VALID_RETURN_KINDS:
            return f"returns[{i}].kind 必须是 {VALID_RETURN_KINDS} 之一，当前值为: {kind}"

        if kind == "FIELDS":
            if operation not in ("QUERY", "ASSOCIATION_QUERY"):
                return f"returns.kind=FIELDS 仅允许在 QUERY/ASSOCIATION_QUERY 中使用，当前 operation: {operation}"
            ref = ret.get("ref", "")
            if ref not in valid_aliases:
                return f"returns[{i}].ref '{ref}' 必须引用已声明的 alias"
            fields = ret.get("fields", [])
            if not fields or not isinstance(fields, list):
                return f"returns[{i}].fields 必须是非空数组"

        elif kind == "GROUP_BY":
            if operation != "AGGREGATE":
                return f"returns.kind=GROUP_BY 仅允许在 AGGREGATE 中使用，当前 operation: {operation}"
            alias = ret.get("alias", "")
            if not alias:
                return f"returns[{i}].alias 不能为空"
            ref = ret.get("ref", "")
            field = ret.get("field", "")
            expr = ret.get("expr", {})
            if expr:
                error = validate_expr(expr, valid_aliases, f"returns[{i}].expr")
                if error:
                    return error
            elif ref and field:
                if ref not in valid_aliases:
                    return f"returns[{i}].ref '{ref}' 必须引用已声明的 alias"
            else:
                return f"returns[{i}].GROUP_BY 必须包含 ref+field 或 expr"
            group_by_aliases.add(alias)

        elif kind == "METRIC":
            if operation != "AGGREGATE":
                return f"returns.kind=METRIC 仅允许在 AGGREGATE 中使用，当前 operation: {operation}"
            function = ret.get("function", "")
            alias = ret.get("alias", "")
            ref = ret.get("ref", "")
            field = ret.get("field", "")
            if function not in VALID_AGGREGATE_FUNCTIONS:
                return f"returns[{i}].function 必须是 {VALID_AGGREGATE_FUNCTIONS} 之一，当前值为: {function}"
            if not alias:
                return f"returns[{i}].alias 不能为空"
            if ref not in valid_aliases:
                return f"returns[{i}].ref '{ref}' 必须引用已声明的 alias"
            if not field:
                return f"returns[{i}].field 不能为空"
            if function != "COUNT" and field == "*":
                return f"returns[{i}].function={function} 时不允许 field=*"
            metric_aliases.add(alias)

    return None, metric_aliases


def validate_expr(expr: dict, valid_aliases: set, path: str) -> str | None:
    """校验表达式结构"""
    kind = expr.get("kind", "")
    if kind == "FIELD":
        ref = expr.get("ref", "")
        if ref not in valid_aliases:
            return f"{path}.ref '{ref}' 必须引用已声明的 alias"
        if not expr.get("field", ""):
            return f"{path}.field 不能为空"
    elif kind == "VALUE":
        pass
    elif kind == "FUNCTION":
        name = expr.get("name", "")
        if name not in CORE_FUNCTIONS:
            return f"{path}.name '{name}' 必须是核心内置函数或已注册扩展函数"
        args = expr.get("args", [])
        if not isinstance(args, list):
            return f"{path}.args 必须是数组"
        for j, arg in enumerate(args):
            error = validate_expr(arg, valid_aliases, f"{path}.args[{j}]")
            if error:
                return error
    return None


def validate_aggregate_filter(af: dict, metric_aliases: set) -> str | None:
    """校验 aggregateFilter"""
    kind = af.get("kind", "")
    if kind == "METRIC_PREDICATE":
        metric_alias = af.get("metricAlias", "")
        if metric_alias not in metric_aliases:
            return f"aggregateFilter.metricAlias '{metric_alias}' 必须引用 returns 中的 METRIC alias"
        operator = af.get("operator", "")
        if operator not in VALID_AGGREGATE_OPERATORS:
            return f"aggregateFilter.operator 必须是 {VALID_AGGREGATE_OPERATORS} 之一，当前值为: {operator}"
        values = af.get("values", [])
        if operator in ("IS_NULL", "IS_NOT_NULL"):
            if values:
                return "aggregateFilter.operator=IS_NULL/IS_NOT_NULL 时不得包含 values"
        elif operator == "BETWEEN":
            if len(values) != 2:
                return f"aggregateFilter.operator=BETWEEN 需要 exactly 两个 values，当前: {len(values)}"
        elif operator in ("IN", "NOT_IN"):
            if not values:
                return "aggregateFilter.operator=IN/NOT_IN 需要 non-empty values"
        else:
            if not values or len(values) != 1:
                return f"aggregateFilter.operator={operator} 需要 exactly 一个 value"
    elif kind == "GROUP":
        relation = af.get("relation", "")
        if relation not in ("AND", "OR", "NOT"):
            return f"aggregateFilter.relation 必须是 AND、OR 或 NOT，当前值为: {relation}"
        children = af.get("children", [])
        if not children:
            return "aggregateFilter.children 不能为空"
        if relation == "NOT" and len(children) != 1:
            return "aggregateFilter.relation=NOT 时，children 必须恰好有一个子条件"
        for i, child in enumerate(children):
            error = validate_aggregate_filter(child, metric_aliases)
            if error:
                return f"aggregateFilter.children[{i}] {error}"
    else:
        return f"aggregateFilter.kind 必须是 METRIC_PREDICATE 或 GROUP，当前值为: {kind}"
    return None


def validate_orders(orders: list) -> str | None:
    """校验 orders 定义"""
    for i, order in enumerate(orders):
        direction = order.get("direction", "")
        if direction not in ("ASC", "DESC"):
            return f"orders[{i}].direction 必须是 ASC 或 DESC，当前值为: {direction}"
        field = order.get("field", "")
        if not field:
            return f"orders[{i}].field 不能为空"
    return None


def validate_max_results(mr: dict) -> str | None:
    """校验 maxResults 定义"""
    if not mr:
        return None
    limit = mr.get("limit")
    offset = mr.get("offset", 0)
    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            return "maxResults.limit 必须为大于 0 的整数"
    if offset is not None:
        if not isinstance(offset, int) or offset < 0:
            return "maxResults.offset 必须为大于等于 0 的整数"
    return None


def validate_mutation(mutation: dict, operation: str, properties: dict | None = None) -> str | None:
    """校验 mutation 定义"""
    if operation == "CREATE":
        data = mutation.get("data", {})
        props = data.get("properties", {})
        if not props:
            return "mutation.data.properties 不能为空"
    elif operation == "UPDATE":
        if not mutation.get("scope"):
            return "mutation.scope 不能为空"
        set_data = mutation.get("set", {})
        if not set_data:
            return "mutation.set 不能为空"
    elif operation == "DELETE":
        if not mutation.get("scope"):
            return "mutation.scope 不能为空"
    elif operation == "UPSERT":
        match_by = mutation.get("matchBy", [])
        if not match_by:
            return "mutation.matchBy 不能为空"
        data = mutation.get("data", {})
        props = data.get("properties", {})
        if not props:
            return "mutation.data.properties 不能为空"
        for field in match_by:
            if field not in props:
                return f"mutation.matchBy 中字段 '{field}' 必须出现在 mutation.data.properties 中"
    return None


def validate_operation_compatibility(oac_json: dict) -> str | None:
    """校验 operation 与字段的兼容性"""
    operation = oac_json.get("operation", "").upper()

    forbidden_for_query = {"relationships", "aggregateFilter", "mutation"}
    forbidden_for_aggregate = {"relationships", "mutation"}
    forbidden_for_assoc = {"mutation"}
    forbidden_for_mutation = {"returns", "orders", "relationships", "aggregateFilter", "sourceQuery"}

    if operation == "QUERY":
        for field in forbidden_for_query:
            if field in oac_json and oac_json[field]:
                return f"operation=QUERY 时不允许出现 {field}"
    elif operation == "AGGREGATE":
        for field in forbidden_for_aggregate:
            if field in oac_json and oac_json[field]:
                return f"operation=AGGREGATE 时不允许出现 {field}"
    elif operation == "ASSOCIATION_QUERY":
        for field in forbidden_for_assoc:
            if field in oac_json and oac_json[field]:
                return f"operation=ASSOCIATION_QUERY 时不允许出现 {field}"
    elif operation in ("CREATE", "UPDATE", "DELETE", "UPSERT"):
        for field in forbidden_for_mutation:
            if field in oac_json and oac_json[field]:
                return f"operation={operation} 时不允许出现 {field}"

    return None


def execute_operation(oac_json: dict) -> dict:

    namespace = os.environ.get("SERVICE_NAMESPACE")
    tenant_id = os.environ.get("TENANT_ID")

    if not namespace:
        return {
            "success": False,
            "error": {
                "exception_type": "EnvironmentError",
                "message": "环境变量 NAMESPACE 未设置，请检查集群配置"
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

    url = f"http://api-gateway-mesh.{namespace}.svc.cluster.local:39071/ontoaccess/rest/v1/objects/query"

    """执行 OAC 操作"""
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": "multiDatasource",
        "X-Tenant-Id": tenant_id,
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=oac_json,
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