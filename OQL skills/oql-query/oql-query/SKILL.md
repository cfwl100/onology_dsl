---
name: oql-query
description: generate strict canonical oql query json from natural-language requests for single-object queries, list retrieval, and multi-object logical queries. use when the request is a read operation without aggregation, without explicit path traversal, and without link-query semantics.
---

# OQL Query

Generate only `QUERY` operation JSON.

## Use this skill when

- The user wants to read objects or lists of objects.
- The request does not require aggregation.
- The request does not require explicit relationship path traversal.
- The request does not require one-hop link-query semantics.

## Required shape

- `operation` must be `QUERY`.
- `objects` must be present.
- `returns` must be present.
- `returns.kind` may only be `FIELDS`.
- `relationships`, `linkQuery`, and `mutation` must not appear.

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
  "operation": "QUERY",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [{"kind": "FIELDS", "ref": "o", "fields": ["id", "orderNo", "amount"]}],
  "maxResults": 1000
}
```
