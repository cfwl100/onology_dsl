---
name: link-query
description: 处理通过单一关系类型获取关联对象的一跳读取请求。仅在语义明确是一跳关联获取、且不需要显式多跳路径时使用。
---
# OQL 单跳关联编译插件

仅生成 `LINK_QUERY` 的规范结果，并且优先使用本插件内的确定性脚本完成组装与校验。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 再按需读取：
   - [OQL 规范关键描述](references/oql-spec-essentials.md)
   - [OQL 模板与样例](references/oql-examples.md)
   - [单跳关联边界](references/link-query-boundaries.md)
3. 先把自然语言请求整理为结构化计划，不要直接跳到最终 JSON。
4. 使用 `scripts/oql_builder.py` 将结构化计划组装成 canonical OQL。
5. 使用 `scripts/oql_validator.py` 验证结构是否满足本操作及通用 OQL 约束。
6. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `LINK_QUERY`。
- `objects` 长度必须为 2。
- `linkQuery` 必须存在。
- 不得出现 `relationships`。
- `conditions` 应用于源对象。

## 结构化计划要求

在调用组装脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- 视操作需要补充 `relationships` / `conditions` / `returns` / `orders` / `sourceQuery` / `linkQuery` / `mutation`

结构化计划允许省略默认值，例如 `version = "1.0"`、`strict = true`、查询类 `maxResults = 1000`，这些可由组装脚本补齐。

## 确定性脚本

- [脚本说明](scripts/README.md)
- `scripts/oql_builder.py`：补齐默认值、固定键顺序、清理空字段、递归处理 `sourceQuery` 与 `BATCH.items`
- `scripts/oql_validator.py`：检查字段合法性、数量约束、条件树、返回投影、嵌套限制与写操作约束

## 输出约定

- 只输出严格规范的 OQL JSON，或结构化错误 JSON。
- 不输出 Markdown、解释、注释或散文。
- 不输出 `null`、空对象或空数组。
- 不要为了凑齐 JSON 而猜测 schema 中不存在的对象、关系或字段。
