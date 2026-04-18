---
name: create-object
description: 处理创建单个对象的写入请求。用于新增、创建、插入或登记一个对象实例，不用于更新、删除或批处理。
---
# 创建对象生成规则

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
- 仅负责 `CREATE`。
- `objects` 长度必须为 1。
- `mutation.data` 必须存在且非空。
- 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

## 输出前检查（Checklist）
1. `operation` 必须是 `CREATE`。
2. `objects` 必须且仅有 1 个目标对象。
3. `mutation.data` 必须存在且非空。
4. 禁止字段：`conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
5. 仅允许引用已声明 alias，不得悬空。
6. 缺关键字段时返回结构化错误。
