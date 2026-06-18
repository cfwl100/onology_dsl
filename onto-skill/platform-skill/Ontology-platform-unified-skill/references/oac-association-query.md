# ASSOCIATION_QUERY - 关联路径查询

## 何时使用

`ASSOCIATION_QUERY` 用于显式关系路径查询，包括一跳、多跳、归属、连接和路径遍历。只要用户问题需要沿对象关系查询，即使只有一跳，也应使用本操作。

适用场景：

- 查询 A 与 B 的关系或路径。
- 查询某对象归属、连接、经过、包含、承载的对象。
- 对路径起点、终点或中间节点做联合筛选。
- 需要返回路径上的对象和关系字段。

不适用场景：

- 只查询对象自身字段 → 使用 `QUERY`。
- 统计、分组、聚合指标 → 使用 `AGGREGATE`。

## 必读资产

- 公共规则：`oql-common-rules.md`
- Schema：`schemas/oql-association-query.schema.json`
- Example：`examples/association-query.example.json`
- Validator：`scripts/validate_oql.py`

## 顶层字段

必填：

- `operation`: 固定为 `ASSOCIATION_QUERY`。
- `objects`: 路径上的对象。
- `relationships`: 路径上的关系。
- `returns`: 返回对象或关系字段。

可选：

- `version`
- `schemaRef`
- `strict`
- `conditions`
- `orders`
- `maxResults`: 数字格式，例如 `1000`。
- `extensions`

禁止：

- `aggregateFilter`
- `mutation`

## relationships 规则

- 每条关系必须包含 `relationshipType`、`alias`、`from`、`to`。
- `from` 和 `to` 必须引用 `objects[].alias`。
- 多跳路径中，前一跳的 `to` 应与后一跳的 `from` 连续。
- 关系名必须来自已检索或已确认的本体关系，不得臆造。

## returns 规则

`returns` 允许：

- `FIELDS`：返回对象或关系字段。
- `EXPR`：返回表达式结果。
- `FUNCTION`：仅用于对象字段的 `ID(field)` / `NAME(field)` 类型指定。

关联查询应返回必要的路径关系。若业务需要完整路径，`returns` 中应包含每个 `relationships[].alias` 的返回项。

## conditions 规则

- `ref` 可以引用对象 alias，也可以引用关系 alias。
- 条件字段必须属于对应对象或关系。
- 不要把路径关系字段写到对象条件上。

## 生成步骤

1. 判断用户是否需要关系路径。
2. 声明路径上的 `objects`。
3. 按路径顺序声明 `relationships`。
4. 生成对象或关系上的 `conditions`。
5. 生成对象、关系或 ID/NAME 返回项。
6. 调用 `validate_oql.py` 校验。

## 校验与修复

校验失败时根据错误修复 OQL。常见错误：

- `relationships.from/to` 未引用对象 alias。
- 多跳路径被拆成多个单跳查询。
- 遗漏业务要求返回的关系路径。
- 把聚合需求误写为关联查询。

## 最小示例

```json
{
  "version": "2.0",
  "schemaRef": "demo@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    { "objectType": "cell", "alias": "c" },
    { "objectType": "grid", "alias": "g" }
  ],
  "relationships": [
    { "relationshipType": "belongs_to", "alias": "r1", "from": "c", "to": "g" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "c",
    "field": "cell_id",
    "operator": "EQ",
    "values": ["CELL_A"]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "c", "fields": ["cell_id"] },
    { "kind": "FIELDS", "ref": "g", "fields": ["grid_id"] },
    { "kind": "FIELDS", "ref": "r1", "fields": ["*"] }
  ],
  "maxResults": 1000
}
```
