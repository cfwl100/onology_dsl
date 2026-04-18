# 具体语法细节（按《S-OQL到OQL转换.md》刷新）

> 本文件用于生成阶段语法约束，`conditions`、`returns`、`mutation` 采用 S-OQL 结构；进入执行前必须映射回 canonical OQL。

## 1. 顶层外壳（保持 canonical）

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "<OPERATION>",
  "objects": [...],
  "relationships": [...],
  "conditions": ...,
  "returns": ...,
  "orders": [...],
  "maxResults": 1000,
  "sourceQuery": [...],
  "linkQuery": {...},
  "mutation": ...,
  "options": {...},
  "extensions": {...}
}
```

- 顶层字段名与 canonical OQL 完全一致。
- 仅 `conditions` / `returns` / `mutation` 允许 S-OQL 简化结构。
- 未使用字段必须省略，不允许 `null`、空对象、空数组。

## 2. `conditions` 语法（S-OQL）

仅允许以下五类：

1. 三元组：`["<alias>.<field>", "<OP>", <value>]`
2. 二元空值判断：`["<alias>.<field>", "IS_NULL"]` / `["<alias>.<field>", "IS_NOT_NULL"]`
3. `{"all": [<condition>, ...]}`
4. `{"any": [<condition>, ...]}`
5. `{"not": <condition>}`

约束：
- 字段引用必须是 `<alias>.<field>`。
- `IN/NOT_IN` 第 3 项必须是非空数组。
- `BETWEEN` 第 3 项必须是长度 2 的数组。
- `IS_NULL/IS_NOT_NULL` 不得携带第 3 项。
- `all/any` 必须是非空数组，`not` 必须是单个条件节点。

映射要点：
- 三元组/二元组映射为 canonical `PREDICATE`。
- `all/any/not` 分别映射为 canonical `GROUP(AND/OR/NOT)`。

## 3. `returns` 语法（S-OQL）

`returns` 必须是非空数组，且每项必须是固定元组：

- `FIELDS`：`["FIELDS", "<ref>", ["field1", "field2"]]`
- `GROUP_BY`：`["GROUP_BY", "<alias>.<field>", "<resultAlias>"]`
- `METRIC`：`["METRIC", "<function>", "<alias>.<field>|<alias>.*", "<resultAlias>"]`

约束：
- `FIELDS` 长度必须 3，第三项必须是显式字段数组（不允许 `*`）。
- `GROUP_BY` 长度必须 3。
- `METRIC` 长度必须 4，函数仅允许 `COUNT/SUM/AVG/MIN/MAX`。
- 仅 `COUNT` 允许 `o.*` 形式；非 `COUNT` 禁止 `*`。
- `GROUP_BY` 与 `METRIC` 的结果别名在同层必须唯一。

operation 约束：
- `QUERY/LINK_QUERY/ASSOCIATION_QUERY`：仅允许 `FIELDS`。
- `AGGREGATE`：仅允许 `GROUP_BY/METRIC`，且至少一个 `METRIC`。

映射要点：
- 元组数组逐项映射为 canonical `{kind, ref, field/function/alias}` 对象。

## 4. `mutation` 语法（S-OQL）

### CREATE / UPSERT 的 `data`

```json
{"mutation": {"data": {"k1": "v1", "k2": 2, "ts": {"$fn":"now"} } } }
```

### UPDATE 的 `set`

```json
{"mutation": {"scope":"ONE|MANY", "set": {"k1": "v1", "updatedAt": {"$fn":"now"} } } }
```

### DELETE 的 `scope`

```json
{"mutation": {"scope":"ONE|MANY"} }
```

### UPSERT 的 `matchBy + data`

```json
{"mutation": {"matchBy":["k1","k2"], "data": {"k1":"v1","k2":"v2"} } }
```

### BATCH

```json
{"mutation": {"atomic": true, "items": [{...}]} }
```

约束：
- `CREATE` 必须有 `mutation.data`。
- `UPDATE` 必须有 `mutation.scope` 与 `mutation.set`。
- `DELETE` 必须有 `mutation.scope`。
- `UPSERT` 必须有 `mutation.matchBy` 与 `mutation.data`。
- `matchBy` 中字段必须全部出现在 `mutation.data`。
- `BATCH.items` 非空，且子项不允许 `BATCH`。

映射要点：
- `mutation.data`（直接属性对象）映射到 canonical `mutation.data.properties`。
- `mutation.set` 保持对象结构并映射到 canonical 更新字段结构。

## 5. 当前插件操作约束

- 操作边界：`QUERY`（读取）。
- 关键边界：必须包含 `objects` 与 `returns`；禁止 `relationships/linkQuery/mutation`。

## 6. 最小合法样例（S-OQL 形态）

```json
{"version":"1.0","schemaRef":"demo","strict":true,"operation":"QUERY","objects":[{"objectType":"Order","alias":"o"}],"conditions":{"all":[["o.status","EQ","PAID"],["o.amount","GTE",100]]},"returns":[["FIELDS","o",["id","orderNo","amount"]]]}
```
