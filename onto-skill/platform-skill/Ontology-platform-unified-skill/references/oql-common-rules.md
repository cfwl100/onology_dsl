# OQL 公共规则

本文件承载 QUERY、ASSOCIATION_QUERY、AGGREGATE 共用的规则。操作专属规则仍以各自 reference 和 schema 为准。

## 版本与 schemaRef

- `operation` 必须明确，只能是当前操作文档指定的值。
- `schemaRef` 表示本体 schema 标识。用户或上层计划已提供时必须原样保留。
- 不得编造 `schemaRef`、对象类型、关系类型、字段名或函数名。

## maxResults

- `maxResults` 使用数字格式，例如：`"maxResults": 1000`。
- 不使用旧对象格式，例如 `{"limit": 1000, "offset": 0}`。
- 未指定时可省略，由执行侧或服务端默认值处理。

## ID / NAME 字段类型指定

- 用户表达 ID、标识、编号、编码时，在 `returns` 中使用 `ID(field)`。
- 用户表达名称、名字、显示名时，在 `returns` 中使用 `NAME(field)`。
- 标准格式：`{"kind":"FUNCTION","ref":"o","field":"NAME(fieldName)","alias":"field_name"}`。
- `ID` / `NAME` 只用于 `returns`，不用于 `conditions`、`orders`、`mutation`。
- 不使用小写 `id()`、`name()`。
- 不使用旧式 `EXPR + expr.kind = FUNCTION` 表达 ID / NAME。
- 聚合查询中不得使用 `FUNCTION` 表达指标，聚合指标必须用 `METRIC`。

## conditions

- 条件使用 `PREDICATE` 或 `GROUP` 递归树。
- `PREDICATE.ref` 必须引用已声明的对象 alias，ASSOCIATION_QUERY 中也可引用关系 alias。
- 条件值必须来自用户输入、上一步明确结果或已确认上下文，不得虚构。

## returns

- 用户明确指定返回字段时，必须显式列出，不要用 `*` 覆盖用户意图。
- 用户没有指定返回字段时，可以按操作文档默认规则处理。
- 跨对象、关系、指标引用必须使用 alias。

## 输出和执行

- 生成给执行脚本的 OQL JSON 使用紧凑单行格式。
- 仓库中的 schema JSON 保持格式化多行，便于 Agent 阅读和维护。
- 执行前必须使用 `scripts/validate_oql.py` 校验。
- 校验失败时先修复，不得直接调用 `execute_oac_operation.py`。
