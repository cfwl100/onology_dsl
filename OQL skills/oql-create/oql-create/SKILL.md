---
name: oql-create
description: generate strict canonical oql create json from natural-language requests that create a single logical object. use when the request means create, add, insert, or register one object instance.
---

# OQL Create

Generate only `CREATE` operation JSON.

## Required shape

- `operation` must be `CREATE`.
- `objects` must contain exactly one object.
- `mutation.data.properties` must be present and non-empty.
- `conditions`, `returns`, `orders`, `sourceQuery`, `relationships`, and `linkQuery` must not appear.

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
  "operation": "CREATE",
  "objects": [{"objectType": "Product", "alias": "p"}],
  "mutation": {
    "data": {
      "properties": {
        "name": "iPhone 16",
        "price": 8999,
        "createdAt": {"$fn": "now"}
      }
    }
  }
}
```

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `CREATE`，不得路由到 `UPDATE/UPSERT/BATCH`。
2. **objects 数量**：`objects` 必须且仅有 1 个目标对象。
3. **禁止字段**：不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
4. **mutation.data 完整性**：`mutation.data.properties` 必须存在且非空。
5. **alias 闭包**：仅允许引用已声明对象 alias，不得出现悬空 ref。
6. **函数值规范**：如有函数值，使用对象形式（如 `{"$fn": "now"}`）。
7. **空值约束**：不得输出 `null`、空对象、空数组。
8. **缺失信息处理**：缺关键字段时返回结构化错误，禁止猜测补值。
