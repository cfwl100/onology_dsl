---
name: oql-delete
description: generate strict canonical oql delete json from natural-language requests that delete existing objects selected by conditions. use when the request means remove, delete, purge, or drop existing objects.
---

# OQL Delete

Generate only `DELETE` operation JSON.

## Required shape

- `operation` must be `DELETE`.
- `objects` must contain exactly one object.
- `conditions` must be present.
- `mutation.scope` must be `ONE` or `MANY`.
- `mutation.set` and `mutation.data` must not appear.
- `returns`, `orders`, `sourceQuery`, `relationships`, and `linkQuery` must not appear.

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
  "operation": "DELETE",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {"kind": "PREDICATE", "ref": "o", "field": "orderNo", "operator": "EQ", "values": ["ORD-001"]},
  "mutation": {"scope": "ONE"}
}
```

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `DELETE`。
2. **objects 数量**：`objects` 必须且仅有 1 个。
3. **必填块**：`conditions` 与 `mutation.scope` 必须存在。
4. **scope 合法性**：`mutation.scope` 仅允许 `ONE` 或 `MANY`。
5. **禁止字段**：不得出现 `mutation.set`、`mutation.data`、`returns`、`orders`、`sourceQuery`、`relationships`、`linkQuery`。
6. **alias 闭包**：`conditions` 引用的 ref 必须为已声明对象 alias。
7. **空删防护**：条件语义不清或过宽时不得冒险删除。
8. **缺失信息处理**：无法确定删除范围时返回结构化错误。
