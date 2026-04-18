---
name: oql-router
description: route natural-language ontology object requests to the correct oql operation and generate strict canonical oql json. use when a request may map to query, aggregate, association-query, link-query, create, update, delete, upsert, or batch and the model must first choose the correct operation before emitting oql.
---

# OQL Router

Select the correct OQL operation from the user request, then emit strict canonical OQL JSON.

## Routing rules

- Use `QUERY` for ordinary object lookup and list retrieval.
- Use `AGGREGATE` for count, sum, avg, min, max, ranking, grouping, or statistics.
- Use `ASSOCIATION_QUERY` for explicit multi-hop path traversal.
- Use `LINK_QUERY` for one-hop link-type retrieval.
- Use `CREATE` for creating one object.
- Use `UPDATE` for modifying existing objects by condition.
- Use `DELETE` for deleting existing objects by condition.
- Use `UPSERT` when the request means update if exists, otherwise create.
- Use `BATCH` only when the user clearly asks for multiple operations in one request.

## Generation workflow

1. Infer the operation.
2. Infer the participating logical objects.
3. Infer conditions, returns, orders, and operation-specific blocks.
4. Emit only the canonical JSON for that operation.
5. If the request is ambiguous between operations, return structured error JSON.

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

## Minimal example

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "returns": [{"kind": "FIELDS", "ref": "o", "fields": ["id"]}]
}
```

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **路由边界**：先判定是否应走 `QUERY/AGGREGATE/ASSOCIATION_QUERY/LINK_QUERY/CREATE/UPDATE/DELETE/UPSERT/BATCH`。
2. **单一路由**：同一请求只输出一个最终 operation，不混合多个操作。
3. **objects 约束**：路由后必须满足目标 operation 的 objects 数量与形态要求。
4. **禁止字段继承**：输出必须满足目标 operation 的禁用字段约束。
5. **conditions/returns 合法**：按目标 operation 校验必填与结构。
6. **alias 闭包**：跨块引用必须全部可解析。
7. **sourceQuery/mutation 合法性**：仅在目标 operation 允许时出现。
8. **不确定性处理**：操作意图歧义时返回结构化错误，不强行猜测路由。
