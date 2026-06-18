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

- 公共规则：`oql-common-rules.md`
- Schema：`schemas/oql-query.schema.json`
- Example：`examples/query.example.json`
- Validator：`scripts/validate_oql.py`

## 顶层字段

必填：

- `operation`: 固定为 `QUERY`。
- `objects`: 至少一个对象。
- `returns`: 至少一个返回项。

可选：

- `version`
- `schemaRef`
- `strict`
- `conditions`
- `orders`
- `maxResults`: 数字格式，例如 `1000`。
- `extensions`

禁止：

- `relationships`
- `aggregateFilter`
- `mutation`

## returns 规则

`returns` 允许：

- `FIELDS`：返回对象字段。
- `EXPR`：返回表达式结果。
- `FUNCTION`：仅用于 `ID(field)` / `NAME(field)` 字段类型指定。

用户明确指定返回字段时必须显式列出。用户未指定返回字段时，可按平台默认规则返回对象字段，但不要覆盖用户已指定字段。

## conditions 规则

- 条件使用 `PREDICATE` 或 `GROUP`。
- `ref` 必须引用 `objects[].alias`。
- 条件字段必须是当前对象真实字段，不得根据对象名臆造字段前缀。

## 生成步骤

1. 判断是否确实不需要关系路径和聚合。
2. 声明 `objects` 和 alias。
3. 将用户过滤条件写入 `conditions`。
4. 将返回字段写入 `returns`。
5. 如需 ID/NAME 语义，使用 `returns.kind = FUNCTION`。
6. 生成后调用 `validate_oql.py` 校验。

## 校验与修复

校验失败时根据错误修复 OQL。常见错误：

- 错误加入 `relationships`。
- 把统计需求误写成 `QUERY`。
- 把 `ID/NAME` 写成 `EXPR` 函数。
- `maxResults` 使用旧对象格式。

## 最小示例

```json
{
  "version": "2.0",
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
