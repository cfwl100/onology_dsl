---
name: oql-upsert-batch
description: generate strict canonical oql upsert or batch json from natural-language requests that mean create-or-update by match key, or execute multiple operations atomically. use when the request explicitly implies upsert semantics or a multi-step batch.
---

# OQL Upsert Batch

Generate only `UPSERT` or `BATCH` operation JSON.

## Use `UPSERT` when

- The request means update if exists, otherwise create.
- A stable match key can be inferred.

## Use `BATCH` when

- The user asks for multiple operations in one request.
- Atomic grouped execution is explicitly needed or strongly implied.

## UPSERT required shape

- `objects` must contain exactly one object.
- `mutation.matchBy` must be present.
- `mutation.data.properties` must be present.
- Every field in `matchBy` must also appear in `data.properties`.
- `conditions` must not appear.

## BATCH required shape

- Top-level `operation` must be `BATCH`.
- Top-level `mutation.atomic` and `mutation.items` must be present.
- Items must not use `BATCH`.
- Items inherit `version`, `schemaRef`, and `strict` from the top level.

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

## UPSERT example

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "UPSERT",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "properties": {
        "sourceSystem": "ERP",
        "orderNo": "ORD-001",
        "status": "shipped",
        "amount": 19999
      }
    }
  }
}
```

## BATCH example

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
        "objects": [{"objectType": "Order", "alias": "o"}],
        "conditions": {"kind": "PREDICATE", "ref": "o", "field": "orderNo", "operator": "EQ", "values": ["ORD-001"]},
        "mutation": {"scope": "ONE", "set": {"status": "paid"}}
      },
      {
        "operation": "CREATE",
        "objects": [{"objectType": "Invoice", "alias": "i"}],
        "mutation": {"data": {"properties": {"invoiceNo": "INV-001", "orderNo": "ORD-001"}}}
      }
    ]
  }
}
```
