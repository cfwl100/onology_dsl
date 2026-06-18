#!/usr/bin/env python3
"""OQL校验脚本，用于验证OQL查询语句的schema有效性和语义正确性

Usage:
    python validate_oql.py --oac-json '<json_string>'
    cat request.json | python validate_oql.py --input -
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "QUERY": ROOT / "schemas" / "oql-query.schema.json",
    "ASSOCIATION_QUERY": ROOT / "schemas" / "oql-association-query.schema.json",
    "AGGREGATE": ROOT / "schemas" / "oql-aggregate.schema.json",
}
ID_NAME_RE = re.compile(r"^(ID|NAME)\(([A-Za-z_][A-Za-z0-9_]*)\)$")
LOWER_ID_NAME_RE = re.compile(r"^(id|name)\(")


def make_error(code: str, message: str, path: str = "$") -> dict[str, Any]:
    """构建标准化错误对象

    Args:
        code: 错误码，用于标识错误类型
        message: 错误描述信息
        path: 错误发生位置的JSON路径，默认为根节点"$"

    Returns:
        包含code、message、path三个字段的字典
    """
    return {"code": code, "message": message, "path": path}


def emit(success: bool, errors: list[dict[str, Any]] | None = None) -> int:
    """输出校验结果并返回退出码

    将校验结果以JSON格式输出到stdout，其中success表示整体校验是否通过，
    errors数组包含所有错误详情。

    Args:
        success: 校验是否通过，True表示通过，False表示未通过
        errors: 错误列表，如果为None则使用空列表

    Returns:
        success为True时返回0，否则返回1，用于作为进程退出码
    """
    print(json.dumps({"success": success, "errors": errors or []}, ensure_ascii=False, separators=(",", ":")))
    return 0 if success else 1


def load_oql(args: argparse.Namespace) -> dict[str, Any]:
    """从参数中加载OQL查询语句

    支持三种输入方式：通过--oac-json参数直接传递JSON字符串、
    通过--input参数指定文件路径、从标准输入读取。

    Args:
        args: 包含命令行参数的命名空间对象，需包含oac_json或input属性

    Returns:
        解析后的OQL查询字典对象

    Raises:
        ValueError: 当既未提供oac_json也未提供input参数，或JSON顶层不是对象时抛出
    """
    if args.oac_json:
        raw = args.oac_json
    elif args.input == "-":
        raw = sys.stdin.read()
    elif args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raise ValueError("missing --oac-json or --input")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be object")
    return data


def is_id_name(value: Any) -> bool:
    """判断值是否为标准的ID/NAME函数调用格式

    检查值是否符合ID(fieldName)或NAME(fieldName)的大写格式，
    即以ID(或NAME(开头，后跟有效的标识符。

    Args:
        value: 待检查的值

    Returns:
        如果值是符合ID()/NAME()大写格式的字符串则返回True，否则返回False
    """
    return isinstance(value, str) and bool(ID_NAME_RE.match(value))


def is_lower_id_name(value: Any) -> bool:
    """判断值是否为小写的id/name函数调用格式

    检查值是否符合id(fieldName)或name(fieldName)的小写格式，
    用于检测需要规范化为大写的用法。

    Args:
        value: 待检查的值

    Returns:
        如果值是符合id()/name()小写格式的字符串则返回True，否则返回False
    """
    return isinstance(value, str) and bool(LOWER_ID_NAME_RE.match(value))


def walk_expr(node: Any, refs: list[str], errors: list[dict[str, Any]], path: str) -> None:
    """递归遍历OQL表达式节点，检查语义正确性

    该函数深度遍历表达式抽象语法树，收集引用的别名并检测不合法的ID()/NAME()用法。
    主要检查FIELD类型的节点引用以及FUNCTION类型的函数名称。

    Args:
        node: 当前遍历到的表达式节点，可以是字典对象或其他类型
        refs: 用于收集所有引用的别名列表，会直接修改该列表
        errors: 用于收集错误信息的列表，会直接修改该列表
        path: 当前节点在JSON中的路径，用于标注错误位置
    """
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    if kind == "FIELD":
        if isinstance(node.get("ref"), str):
            refs.append(node["ref"])
        if is_id_name(node.get("field")) or is_lower_id_name(node.get("field")):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() can only be used in returns.kind=FUNCTION.field", f"{path}.field"))
    if kind == "FUNCTION":
        if node.get("name") in ("ID", "NAME", "id", "name"):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID/NAME must use returns.kind=FUNCTION with field=ID(...)/NAME(...)", f"{path}.name"))
        args = node.get("args", []) if isinstance(node.get("args", []), list) else []
        for i, arg in enumerate(args):
            walk_expr(arg, refs, errors, f"{path}.args[{i}]")


def walk_condition(node: Any, refs: list[str], errors: list[dict[str, Any]], path: str) -> None:
    """递归遍历OQL条件节点，检查语义正确性

    该函数遍历条件表达式树，检查谓词中的别名引用以及ID()/NAME()的不当使用。
    条件节点可以是PREDICATE（谓词）或GROUP（分组）。

    Args:
        node: 当前遍历到的条件节点，可以是字典对象或其他类型
        refs: 用于收集所有引用的别名列表，会直接修改该列表
        errors: 用于收集错误信息的列表，会直接修改该列表
        path: 当前节点在JSON中的路径，用于标注错误位置
    """
    if not isinstance(node, dict):
        return
    if node.get("kind") == "PREDICATE":
        if isinstance(node.get("ref"), str):
            refs.append(node["ref"])
        if is_id_name(node.get("field")) or is_lower_id_name(node.get("field")):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in conditions", f"{path}.field"))
        walk_expr(node.get("left"), refs, errors, f"{path}.left")
    if node.get("kind") == "GROUP":
        children = node.get("children", []) if isinstance(node.get("children", []), list) else []
        for i, child in enumerate(children):
            walk_condition(child, refs, errors, f"{path}.children[{i}]")


def walk_aggregate_filter(node: Any, aliases: list[str]) -> None:
    """递归遍历聚合过滤器节点，收集度量别名

    该函数遍历聚合过滤器抽象语法树，收集所有metricAlias用于后续验证。
    主要关注METRIC_PREDICATE类型的节点。

    Args:
        node: 当前遍历到的节点，可以是字典对象或其他类型
        aliases: 用于收集度量别名的列表，会直接修改该列表
    """
    if not isinstance(node, dict):
        return
    if node.get("kind") == "METRIC_PREDICATE" and isinstance(node.get("metricAlias"), str):
        aliases.append(node["metricAlias"])
    if node.get("kind") == "GROUP":
        children = node.get("children", []) if isinstance(node.get("children", []), list) else []
        for child in children:
            walk_aggregate_filter(child, aliases)


def semantic(oql: dict[str, Any]) -> list[dict[str, Any]]:
    """执行OQL语义校验

    该函数对OQL查询语句进行全面的语义校验，包括：
    - maxResults字段的类型和取值范围检查
    - 对象别名唯一性检查
    - 关系别名唯一性及其引用的对象别名有效性检查
    - returns子句中ID()/NAME()的合法使用检查
    - 未知别名引用检查
    - 聚合过滤器中度量别名的有效性检查

    Args:
        oql: OQL查询语句字典对象，应包含operation字段标识操作类型

    Returns:
        错误信息列表，每个错误包含code、message、path三个字段；
        如果所有校验通过则返回空列表
    """
    errors: list[dict[str, Any]] = []
    op = str(oql.get("operation", "")).upper()

    if "maxResults" in oql:
        value = oql.get("maxResults")
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(make_error("OQL_MAX_RESULTS_ERROR", "maxResults must be an integer, for example: \"maxResults\": 1000", "$.maxResults"))
        elif value < 1:
            errors.append(make_error("OQL_MAX_RESULTS_ERROR", "maxResults must be greater than or equal to 1", "$.maxResults"))

    objects = oql.get("objects", []) if isinstance(oql.get("objects", []), list) else []
    obj_aliases: set[str] = set()
    rel_aliases: set[str] = set()
    metric_aliases: set[str] = set()

    for i, obj in enumerate(objects):
        alias = obj.get("alias") if isinstance(obj, dict) else None
        if isinstance(alias, str):
            if alias in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"duplicate object alias: {alias}", f"$.objects[{i}].alias"))
            obj_aliases.add(alias)

    relationships = oql.get("relationships", []) if isinstance(oql.get("relationships", []), list) else []
    for i, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            continue
        alias = rel.get("alias")
        if isinstance(alias, str):
            if alias in rel_aliases or alias in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"invalid relationship alias: {alias}", f"$.relationships[{i}].alias"))
            rel_aliases.add(alias)
        for key in ("from", "to"):
            if rel.get(key) not in obj_aliases:
                errors.append(make_error("OQL_SEMANTIC_ERROR", f"relationships[{i}].{key} must reference object alias", f"$.relationships[{i}].{key}"))

    all_aliases = obj_aliases | rel_aliases
    refs: list[str] = []
    walk_condition(oql.get("conditions"), refs, errors, "$.conditions")

    returns = oql.get("returns", []) if isinstance(oql.get("returns", []), list) else []
    for i, ret in enumerate(returns):
        if not isinstance(ret, dict):
            continue
        path = f"$.returns[{i}]"
        kind = ret.get("kind")
        if isinstance(ret.get("ref"), str):
            refs.append(ret["ref"])
        if kind == "EXPR":
            walk_expr(ret.get("expr"), refs, errors, f"{path}.expr")
        if kind == "FIELDS":
            fields = ret.get("fields", []) if isinstance(ret.get("fields", []), list) else []
            for j, field in enumerate(fields):
                if is_id_name(field) or is_lower_id_name(field):
                    errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must use returns.kind=FUNCTION, not FIELDS.fields[]", f"{path}.fields[{j}]"))
        if kind == "FUNCTION":
            field = ret.get("field")
            if not is_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "returns.kind=FUNCTION.field must be ID(fieldName) or NAME(fieldName) with uppercase function name", f"{path}.field"))
            if is_lower_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "id()/name() must be normalized to uppercase ID()/NAME()", f"{path}.field"))
            if op == "AGGREGATE":
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() does not express aggregate metric; use GROUP_BY or METRIC in AGGREGATE", path))
        if kind in ("GROUP_BY", "METRIC"):
            field = ret.get("field")
            if is_id_name(field) or is_lower_id_name(field):
                errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in AGGREGATE returns", f"{path}.field"))
        if kind == "METRIC" and isinstance(ret.get("alias"), str):
            metric_aliases.add(ret["alias"])
        if kind == "METRIC" and ret.get("function") != "COUNT" and ret.get("field") == "*":
            errors.append(make_error("OQL_SEMANTIC_ERROR", "only COUNT can use field '*'", f"{path}.field"))

    orders = oql.get("orders", []) if isinstance(oql.get("orders", []), list) else []
    for i, order in enumerate(orders):
        if isinstance(order, dict) and (is_id_name(order.get("field")) or is_lower_id_name(order.get("field"))):
            errors.append(make_error("OQL_ID_NAME_USAGE_ERROR", "ID()/NAME() must not be used in orders", f"$.orders[{i}].field"))

    for ref in refs:
        if ref not in all_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"unknown alias reference: {ref}"))

    aggregate_aliases: list[str] = []
    walk_aggregate_filter(oql.get("aggregateFilter"), aggregate_aliases)
    for alias in aggregate_aliases:
        if alias not in metric_aliases:
            errors.append(make_error("OQL_SEMANTIC_ERROR", f"unknown metricAlias: {alias}", "$.aggregateFilter"))
    return errors


def main() -> int:
    """OQL校验主函数

    该函数协调整个校验流程：解析命令行参数、加载OQL语句、
    执行schema校验、执行语义校验、汇总结果并输出。

    命令行参数：
        --oac-json: 直接传递OQL的JSON字符串
        --input: 从指定文件或标准输入读取OQL JSON

    Returns:
        校验通过返回0，校验失败返回1
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--oac-json")
    parser.add_argument("--input")
    args = parser.parse_args()
    try:
        oql = load_oql(args)
        op = str(oql.get("operation", "")).upper()
        schema_path = SCHEMAS.get(op)
        if not schema_path:
            raise ValueError(f"unsupported operation: {op}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)
        validator = Draft7Validator(schema)
        schema_errors = [make_error("OQL_SCHEMA_ERROR", item.message, "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in item.path)) for item in validator.iter_errors(oql)]
        semantic_errors = semantic(oql)
        errors = schema_errors + semantic_errors
        return emit(not errors, errors)
    except Exception as exc:
        return emit(False, [make_error("OQL_VALIDATION_ERROR", str(exc))])


if __name__ == "__main__":
    raise SystemExit(main())
