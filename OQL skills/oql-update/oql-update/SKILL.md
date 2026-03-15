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
