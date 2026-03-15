---
name: oql-link-query
description: generate strict canonical oql link-query json from natural-language requests that ask for one-hop linked objects through a single relationship type. use when the request means get linked objects or get one linked object, not multi-hop path traversal.
---

# OQL Link Query

Generate only `LINK_QUERY` operation JSON.

## Required shape

- `operation` must be `LINK_QUERY`.
- `objects` must contain exactly two objects.
- `conditions` must target the source object.
- `returns` must be present.
- `linkQuery` must be present.
- `relationships` and `mutation` must not appear.

## Link rules

- `linkQuery.mode` is `LIST` or `ONE`.
- `linkQuery.sourceRef` and `linkQuery.targetRef` must reference object aliases.
- Use `ONE` only when the request clearly expects a unique linked object.

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
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {"objectType": "Order", "alias": "o"},
    {"objectType": "Invoice", "alias": "i"}
  ],
  "conditions": {"kind": "PREDICATE", "ref": "o", "field": "orderNo", "operator": "EQ", "values": ["ORD-001"]},
  "returns": [{"kind": "FIELDS", "ref": "i", "fields": ["id", "invoiceNo", "status"]}],
  "linkQuery": {"mode": "ONE", "relationshipType": "has_invoice", "sourceRef": "o", "targetRef": "i", "direction": "OUTBOUND"},
  "maxResults": 1
}
```
