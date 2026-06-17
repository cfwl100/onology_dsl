# QUERY - 无关联对象查询

Schema: `schemas/oql-query.schema.json`

Example: `examples/query.example.json`

生成 `operation = "QUERY"` 的 OQL JSON 时，只使用普通对象查询结构。

必填字段：`version`、`schemaRef`、`operation`、`objects`、`returns`。

可选字段：`strict`、`conditions`、`orders`、`maxResults`、`sourceQuery`、`options`、`extensions`。

不使用字段：`relationships`、`aggregateFilter`、`mutation`。

`returns` 只使用 `FIELDS` 或 `EXPR`。

生成前可参考 `examples/query.example.json` 的最小结构；生成完成后，使用 `scripts/validate_oql.py` 做结构和语义校验。

校验器内置示例映射：`QUERY` 对应 `examples/query.example.json`。
