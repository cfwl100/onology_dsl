# 脚本说明

## oql_builder.py

作用：

- 补齐 `version = "1.0"`
- 补齐 `strict = true`
- 读取并应用可选 profile 覆盖
- 为查询类操作补齐默认 `maxResults`
- 固定顶层键顺序
- 清理空字段
- 递归处理 `sourceQuery` 与 `BATCH.items`

当前支持的 profile 开关：

- `singleHopUsesAssociation`
- `allowWildcardFieldsInAssociation`
- `stringifyConditionValues`
- `requireLowerCaseTypes`
- `defaultMaxResults`

## oql_validator.py

作用：

- 验证 canonical OQL 结构
- 验证本操作的必填字段与边界
- 验证 `conditions` / `returns` / `orders` / `sourceQuery` / `mutation`
- 验证可选 profile 覆盖约束
