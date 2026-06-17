# ASSOCIATION_QUERY - 关联查询

Schema: `schemas/oql-association-query.schema.json`

本文件用于 `operation = "ASSOCIATION_QUERY"`。

必填字段：`version`、`schemaRef`、`operation`、`objects`、`relationships`、`returns`。

可选字段：`strict`、`conditions`、`orders`、`maxResults`、`sourceQuery`、`options`、`extensions`。

不使用字段：`aggregateFilter`、`mutation`。

生成完成后，使用 `scripts/validate_oql.py` 做结构和语义校验。
