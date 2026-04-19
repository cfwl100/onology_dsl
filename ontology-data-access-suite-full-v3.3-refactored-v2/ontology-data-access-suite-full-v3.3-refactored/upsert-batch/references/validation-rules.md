# 存在则更新 / 批量写入校验规则

1. `operation` 只允许 `UPSERT` 或 `BATCH`。
2. `UPSERT` 必须且仅有一个对象。
3. `UPSERT` 中 `matchBy` 与 `data` 必填，且 `matchBy` 字段必须全部存在于 `data`。
4. `UPSERT` 不得出现 `conditions`。
5. `BATCH` 必须包含布尔型 `atomic` 与非空 `items`。
6. `BATCH.items` 只允许创建、更新、删除、存在则更新子项。
7. 不允许嵌套 `BATCH`。
8. 任一子项信息不完整时，应返回结构化错误。
