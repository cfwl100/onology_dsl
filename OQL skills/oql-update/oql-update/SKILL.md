---
name: oql-update
description: generate strict canonical oql update json from natural-language requests that modify existing objects selected by conditions. use when the request means update, change, modify, set, or patch existing objects.
---

# OQL Update

Generate only `UPDATE` operation JSON.

## Required shape

- `operation` must be `UPDATE`.
- `objects` must contain exactly one object.
- `conditions` must be present.
- `mutation.scope` must be `ONE` or `MANY`.
- `mutation.set` must be present and non-empty.
- `returns`, `orders`, `sourceQuery`, `relationships`, and `linkQuery` must not appear.

## Scope rule

- Use `ONE` when the user targets one specific object.
- Use `MANY` when the user clearly requests a bulk update.

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
  "schemaRef": "catalog@1.0",
  "strict": true,
  "operation": "UPDATE",
  "objects": [{"objectType": "Product", "alias": "p"}],
  "conditions": {"kind": "PREDICATE", "ref": "p", "field": "id", "operator": "EQ", "values": ["prod_001"]},
  "mutation": {"scope": "ONE", "set": {"price": 7999, "updatedAt": {"$fn": "now"}}}
}
```

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `UPDATE`。
2. **objects 数量**：`objects` 必须且仅有 1 个。
3. **必填块**：`conditions`、`mutation.scope`、`mutation.set` 必须存在。
4. **scope 合法性**：`mutation.scope` 仅允许 `ONE` 或 `MANY`。
5. **禁止字段**：不得出现 `returns`、`orders`、`sourceQuery`、`relationships`、`linkQuery`。
6. **alias 闭包**：`conditions`/`mutation` 中引用都必须落在已声明 alias 上。
7. **mutation.set 约束**：更新字段不可为空，且字段名应来自目标对象逻辑字段。
8. **缺失信息处理**：无法确定筛选条件或更新内容时返回结构化错误。
