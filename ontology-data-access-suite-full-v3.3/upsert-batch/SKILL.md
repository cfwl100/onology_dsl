---
name: upsert-batch
description: 处理存在则更新否则创建，或多个写操作需要作为一个批次执行的请求。用于显式 upsert 语义或需要原子批处理的场景。
---
# OQL 插入或批处理编译插件

仅生成 `UPSERT / BATCH` 的规范结果，并且优先使用本插件内的确定性脚本完成组装与校验。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 再按需读取：
   - [OQL 规范关键描述](references/oql-spec-essentials.md)
   - [OQL 模板与样例](references/oql-examples.md)
   - [UPSERT / BATCH 模式与边界](references/upsert-batch-patterns.md)
3. 先把自然语言请求整理为结构化计划，不要直接跳到最终 JSON。
4. 使用 `scripts/oql_builder.py` 将结构化计划组装成 canonical OQL。
5. 使用 `scripts/oql_validator.py` 验证结构是否满足本操作及通用 OQL 约束。
6. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `UPSERT / BATCH`。
- `UPSERT`：必须有 `mutation.matchBy` 和 `mutation.data.properties`，且 `matchBy` 中每个字段都必须出现在 `data.properties` 中。
- `BATCH`：必须有 `mutation.atomic` 和非空 `mutation.items`；子项不得再使用 `BATCH`。

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

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：仅允许 `UPSERT` 或 `BATCH`。
2. **UPSERT 约束**：`objects` 必须 1 个，且 `mutation.matchBy`、`mutation.data.properties` 必填。
3. **matchBy 闭包**：`matchBy` 中每个字段都必须出现在 `data.properties` 中。
4. **UPSERT 禁止字段**：`UPSERT` 场景不得出现 `conditions`。
5. **BATCH 约束**：`mutation.atomic` 与非空 `mutation.items` 必填，子项不得再是 `BATCH`。
6. **子项结构**：每个 item 必须是合法单操作结构，且继承顶层上下文。
7. **alias 与引用**：各子项内引用独立闭包，不跨 item 悬空引用。
8. **缺失信息处理**：缺匹配键或批次子项不完整时返回结构化错误。
