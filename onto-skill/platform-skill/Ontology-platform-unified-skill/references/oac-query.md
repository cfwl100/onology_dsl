# QUERY - 无关联对象查询

## 何时使用

`QUERY` 用于单对象或多个独立对象的明细查询，不沿对象关系路径遍历。

适用场景：

- 查询某类对象的字段、列表、明细。
- 对对象做普通过滤后返回字段。
- 多个对象彼此独立查询，但不声明 relationships。

不适用场景：

- 出现关系、路径、归属、一跳、多跳 → 使用 `ASSOCIATION_QUERY`。
- 出现统计、分组、计数、求和、平均、最大、最小 → 使用 `AGGREGATE`。

## 必读资产

- Schema：`schemas/oql-query.schema.json`
- Validator：`scripts/validate_oql.py`

本文件已包含 QUERY 所需公共规则和最小示例，不再读取 `oql-common-rules.md` 或独立 examples 目录。

## 结构边界

结构契约以 schema 为准。本手册只补充 Agent 生成时必须理解的语义规则。

- `version` 使用本体 Skill 初始版本 `1.0`，并以 schema 为准。
- `operation` 固定为 `QUERY`。
- 必须声明 `objects` 和 `returns`。
- 不使用 `relationships`、`aggregateFilter`、`mutation`。
- `maxResults` 使用数字格式，例如 `1000`，不使用 `{"limit":1000,"offset":0}`。
- 用户或上层计划已提供 `schemaRef` 时必须原样保留，不得编造。

## returns 规则

`returns` 的结构、可选类型和字段语法以 `schemas/oql-query.schema.json` 为准。本手册只强调业务生成原则：

- 用户明确指定返回字段时必须显式列出。
- 用户未指定返回字段时，可按平台默认规则返回对象字段，但不要覆盖用户已指定字段。
- 返回项的 `ref` 必须引用 `objects[].alias`。
- 不要把聚合指标或关系路径结果写入 `QUERY` 的 `returns`。

## conditions 规则

- 条件使用 `PREDICATE` 或 `GROUP`。
- `ref` 必须引用 `objects[].alias`。
- 条件字段必须是当前对象真实字段，不得根据对象名臆造字段前缀。
- 条件值必须来自用户输入、上一步明确结果或已确认上下文，不得虚构。

## 生成步骤

1. 判断是否确实不需要关系路径和聚合。
2. 声明 `objects` 和 alias。
3. 将用户过滤条件写入 `conditions`。
4. 将返回字段写入 `returns`。
5. 生成给执行脚本的 OQL JSON 时使用紧凑单行格式。
6. 调用 `validate_oql.py` 校验。

## 校验与修复

校验失败时根据错误修复 OQL。常见错误：

- 错误加入 `relationships`。
- 把统计需求误写成 `QUERY`。
- `returns` 结构不符合 schema。
- `maxResults` 使用旧对象格式。
- `version` 未使用 schema 声明的初始版本。

## 最小示例

```json
{
  "version": "1.0",
  "schemaRef": "demo@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    { "objectType": "device", "alias": "d" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "d",
    "field": "status",
    "operator": "EQ",
    "values": ["running"]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "d", "fields": ["device_id", "status"] }
  ],
  "maxResults": 1000
}
```