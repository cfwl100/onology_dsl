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
