# AGGREGATE - 聚合查询

## 何时使用

`AGGREGATE` 用于面向对象集合的统计、分组、指标计算和聚合后过滤。

适用场景：

- 统计数量、求和、平均、最大、最小。
- 按字段或时间桶分组统计。
- 对聚合指标做二次过滤。

不适用场景：

- 返回对象明细 → 使用 `QUERY`。
- 沿关系路径查询明细 → 使用 `ASSOCIATION_QUERY`。

## 必读资产

- 公共规则：`oql-common-rules.md`
- Schema：`schemas/oql-aggregate.schema.json`
- Example：`examples/agg.example.json`
- Validator：`scripts/validate_oql.py`

## 顶层字段

必填：

- `operation`: 固定为 `AGGREGATE`。
- `objects`: 聚合对象。
- `returns`: 至少一个 `METRIC`，可包含 `GROUP_BY`。

可选：

- `version`
- `schemaRef`
- `strict`
- `conditions`: 聚合前过滤。
- `aggregateFilter`: 聚合后过滤。
- `orders`
- `maxResults`: 数字格式，例如 `1000`。
- `extensions`

禁止：

- `relationships`
- `mutation`
- `returns.kind = FUNCTION`

## returns 规则

`returns` 只允许：

- `GROUP_BY`：分组字段或分组表达式。
- `METRIC`：聚合指标，函数只能是 `COUNT`、`SUM`、`AVG`、`MIN`、`MAX`。

约束：

- 至少一个 `METRIC`。
- `COUNT` 可以使用 `field = "*"`。
- `SUM`、`AVG`、`MIN`、`MAX` 不允许使用 `field = "*"`。
- 不使用 `ID(field)` / `NAME(field)` 表达聚合指标。

## aggregateFilter 规则

`aggregateFilter` 用于聚合后过滤，语义类似 HAVING。

- `metricAlias` 必须引用 `returns` 中 `METRIC.alias`。
- 可使用 `METRIC_PREDICATE` 或 `GROUP`。
- 不得引用未声明指标。

## conditions 规则

`conditions` 是聚合前的明细级过滤。

- `ref` 必须引用 `objects[].alias`。
- 条件字段必须属于对应对象。

## 生成步骤

1. 判断用户是否要求统计或分组。
2. 声明聚合对象。
3. 将明细级过滤写入 `conditions`。
4. 将分组写入 `GROUP_BY`。
5. 将统计指标写入 `METRIC`。
6. 将聚合后过滤写入 `aggregateFilter`。
7. 调用 `validate_oql.py` 校验。

## 校验与修复

校验失败时根据错误修复 OQL。常见错误：

- 没有 `METRIC`。
- 在聚合中使用 `FUNCTION`。
- `aggregateFilter.metricAlias` 未引用已声明指标。
- `SUM/AVG/MIN/MAX` 使用 `field = "*"`。
- 把明细查询误写成聚合。

## 最小示例

```json
{
  "version": "2.0",
  "schemaRef": "demo@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "cell_kpi", "alias": "k" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "k",
    "field": "collect_date",
    "operator": "EQ",
    "values": ["2026-06-18"]
  },
  "returns": [
    { "kind": "GROUP_BY", "ref": "k", "field": "city", "alias": "city" },
    { "kind": "METRIC", "function": "AVG", "ref": "k", "field": "prb_usage", "alias": "avg_prb_usage" }
  ],
  "aggregateFilter": {
    "kind": "METRIC_PREDICATE",
    "metricAlias": "avg_prb_usage",
    "operator": "GT",
    "values": [80]
  },
  "orders": [
    { "field": "avg_prb_usage", "direction": "DESC" }
  ],
  "maxResults": 1000
}
```
