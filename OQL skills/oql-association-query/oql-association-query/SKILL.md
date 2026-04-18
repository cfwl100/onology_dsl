---
name: oql-association-query
description: generate strict canonical oql association-query json from natural-language requests that require explicit relationship paths or multi-hop traversal between logical objects. use when the request describes path traversal, chained relations, or graph-style object navigation.
---

# OQL Association Query

Generate only `ASSOCIATION_QUERY` operation JSON.

## Required shape

- `operation` must be `ASSOCIATION_QUERY`.
- `objects` must be present.
- `relationships` must be present.
- `returns` must be present.
- `linkQuery` and `mutation` must not appear.

## Relationship rules

- `relationships` items must use `{relationshipType, alias, from, to}`.
- `from` and `to` must reference object aliases.
- Preserve path order in the `relationships` array.
- Use relation aliases in `returns` only when the user needs relationship fields.

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
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "Device", "alias": "d"},
    {"objectType": "Server", "alias": "s"},
    {"objectType": "DataCenter", "alias": "dc"}
  ],
  "relationships": [
    {"relationshipType": "installed_on", "alias": "r1", "from": "d", "to": "s"},
    {"relationshipType": "deployed_in", "alias": "r2", "from": "s", "to": "dc"}
  ],
  "returns": [
    {"kind": "FIELDS", "ref": "d", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "dc", "fields": ["id", "region"]}
  ],
  "maxResults": 1000
}
```

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `ASSOCIATION_QUERY`。
2. **必填块**：`objects`、`relationships`、`returns` 必须存在。
3. **路径合法性**：`relationships` 必须按路径顺序，`from/to` 都引用对象 alias。
4. **禁止字段**：不得出现 `linkQuery`、`mutation`。
5. **alias 闭包**：关系 alias 与对象 alias 的引用必须闭合且无悬空。
6. **returns 归属**：默认返回对象字段，仅在明确需要时返回关系字段。
7. **sourceQuery 深度**：若使用 `sourceQuery`，路径与层级需可解释且受控。
8. **缺失信息处理**：路径起终点或关系类型不明确时返回结构化错误。
