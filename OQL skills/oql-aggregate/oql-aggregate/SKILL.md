---
name: oql-aggregate
description: generate strict canonical oql aggregate json from natural-language requests for counts, sums, averages, min, max, rankings, or grouped statistics. use when the request is a read operation centered on aggregation or grouping.
---

# OQL Aggregate

Generate only `AGGREGATE` operation JSON.

## Required shape

- `operation` must be `AGGREGATE`.
- `objects` must be present.
- `returns` must contain at least one `METRIC`.
- `returns` may contain `GROUP_BY` and `METRIC` only.
- `relationships`, `linkQuery`, and `mutation` must not appear.

## Ordering rule

When sorting on aggregation output, use the `alias` defined in `returns` as `orders[].field`.

## Output contract

- Output strict canonical OQL JSON only.
- Do not output markdown, explanation, comments, or prose.
- Do not output null, empty objects, or empty arrays.
- Use only fields defined by the OQL v1.0 canonical form.
- Use logical object types, logical fields, and logical relationship types from the active schema.
- Use alias for all cross-block references.
- If critical information is missing, output a structured error JSON instead of guessing.

## Canonical OQL rules

- Top level required fields: `version`, `schemaRef`, `strict`, `operation`.
- Always set `version` to `"1.0"` and `strict` to `true`.
- `objects` only declares objects. Never generate `by`, `byList`, `byComposite`, `target`, or `locator`.
- `conditions` is the only place for query/update/delete targeting.
- `UPSERT` existence matching uses `mutation.matchBy`, not `conditions`.
- `returns` must always be an array of objects.
- `orders` must always use `{ref, field, direction}`.
- Function values must use object form like `{ "$fn": "now" }`.
- Do not use `FIELDS.fields = ["*"]`.
- `sourceQuery` may appear only in read operations.

## Error output

If the request lacks enough information to generate safe OQL, output this shape:

```json
{
  "success": false,
  "errors": [
    {
      "code": "MISSING_REQUIRED_INFORMATION",
      "message": "..."
    }
  ]
}
```

## Example

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "returns": [
    {"kind": "GROUP_BY", "ref": "o", "field": "region", "alias": "region"},
    {"kind": "METRIC", "ref": "o", "field": "amount", "function": "SUM", "alias": "totalAmount"}
  ],
  "orders": [{"ref": "o", "field": "totalAmount", "direction": "DESC"}],
  "maxResults": 100
}
```

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `AGGREGATE`。
2. **objects/returns 必填**：`objects` 与 `returns` 必须存在。
3. **returns kind 约束**：仅允许 `GROUP_BY` 与 `METRIC`，且至少一个 `METRIC`。
4. **禁止字段**：不得出现 `relationships`、`linkQuery`、`mutation`。
5. **alias 闭包**：聚合/分组 alias 必须可被 `orders` 正确引用。
6. **排序规则**：聚合结果排序优先使用 `returns[].alias`。
7. **sourceQuery 深度**：若使用 `sourceQuery`，必须符合读操作深度限制。
8. **缺失信息处理**：缺聚合指标或分组语义不清时返回结构化错误。
