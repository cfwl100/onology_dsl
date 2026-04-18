---
name: aggregate-query
description: 处理以统计、分组、计数、求和、平均值、最值或排行为中心的读取请求。仅在结果以聚合指标或分组结果为核心时使用。
---
# 聚合查询生成规则

仅在本插件负责的操作边界内工作。

## 规范来源（必须完整遵循）
- 必须完整遵循 `/workspace/onology_dsl/本体对象操作语言(OQL)-DSL规范v1.2.md` 的全部语法与校验规则，不得删减、改写或自定义平行语法。
- 具体语法细节、差异说明与示例统一下沉到 `references/` 与 `scripts/`，本文件仅保留边界、生成流程和检查清单。
- 具体语法细节优先参考 `references/syntax-details.md`，并结合同目录其余 references 与 scripts 执行。

## 生成流程
1. 先确认请求是否属于本插件职责边界。
2. 将自然语言整理为最小必要结构化计划，再生成最终 JSON。
3. 使用统一顶层字段：`version`、`schemaRef`、`strict`、`operation`、`objects`、`relationships`、`conditions`、`returns`、`orders`、`maxResults`、`sourceQuery`、`linkQuery`、`mutation`、`options`、`extensions`。
4. 通过 `scripts/oql_builder.py` 组装请求，必要时调用 `scripts/soql_to_oql.py` 做结构归一化。
5. 使用 `scripts/oql_validator.py` 校验。
6. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，输出结构化错误 JSON。

## 输出约定
- 只输出最终 JSON 或结构化错误 JSON。
- 不输出 Markdown、解释、注释或散文。
- 不输出 `null`、空对象或空数组。
- 不猜测 schema 中不存在的对象、关系或字段。


## 本插件关键规则
- 仅负责 `AGGREGATE`。
- `returns` 仅允许 `GROUP_BY` 与 `METRIC` 元组，且至少一个 `METRIC`。
- 不得出现 `relationships`、`linkQuery`、`mutation`。
- 聚合结果排序优先引用 `returns` 中显式定义的结果别名。

## 输出前检查（Checklist）
1. `operation` 必须是 `AGGREGATE`。
2. `objects` 与 `returns` 必填。
3. `returns` 仅允许 `GROUP_BY/METRIC` 且至少一个 `METRIC`。
4. 禁止字段：`relationships`、`linkQuery`、`mutation`。
5. 聚合/分组别名必须可被 `orders` 正确引用。
6. `sourceQuery` 使用需满足深度限制。
7. 缺聚合指标或分组语义不清时返回结构化错误。
