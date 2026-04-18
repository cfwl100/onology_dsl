---
name: create-object
description: 处理创建单个对象的写入请求。用于新增、创建、插入或登记一个对象实例，不用于更新、删除或批处理；生成符合第 9 章的 `CREATE` S-OQL。
---
# S-OQL 创建生成插件

仅在本插件负责的操作边界内工作。先生成符合第 9 章的 **S-OQL**，再通过 `scripts/soql_to_oql.py` 做确定性转换，并使用 `scripts/oql_validator.py` 校验转换结果。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 先把自然语言请求整理为最小必要的结构化计划，不要直接跳到最终 JSON。
3. 顶层字段继续使用统一字段集：`version`、`schemaRef`、`strict`、`operation`、`objects`、`relationships`、`conditions`、`returns`、`orders`、`maxResults`、`sourceQuery`、`linkQuery`、`mutation`、`options`、`extensions`。
4. 仅允许对 `conditions`、`returns`、`mutation` 使用 S-OQL 简化语法；其余字段继续保持标准顶层结构。
5. 写操作中优先使用 `mutation.data` 的直接属性对象写法，由脚本恢复为标准写入结构。
6. 先完成 S-OQL，再调用 `scripts/soql_to_oql.py` 转成可执行结果；不要在文本层手工展开 canonical 结构。
7. 用 `scripts/oql_validator.py` 校验转换结果。
8. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `CREATE`。
- `mutation.data` 必须是直接属性对象，由脚本恢复为标准写入结构。
- `objects` 长度必须为 1。
- 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

## S-OQL 结构化计划要求

在进入转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- `mutation`

默认值可以省略并交给脚本补齐，例如：

- `version = "1.0"`
- `strict = true`

## 输出约定

- 最终只输出脚本转换后的 JSON，或结构化错误 JSON。
- 不输出 Markdown、解释、注释或散文。
- 不输出 `null`、空对象或空数组。
- 不要为了凑齐 JSON 而猜测 schema 中不存在的对象、关系或字段。
- 不要在文本层描述 canonical OQL 展开细节；所有展开逻辑都交给脚本。

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `CREATE`，不得路由到 `UPDATE/UPSERT/BATCH`。
2. **objects 数量**：`objects` 必须且仅有 1 个目标对象。
3. **禁止字段**：不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
4. **mutation.data 完整性**：`mutation.data` 必须存在且非空。
5. **alias 闭包**：仅允许引用已声明对象 alias，不得出现悬空 ref。
6. **函数值规范**：如有函数值，使用对象形式（如 `{"$fn": "now"}`）。
7. **空值约束**：不得输出 `null`、空对象、空数组。
8. **缺失信息处理**：缺关键字段时返回结构化错误，禁止猜测补值。
