---
name: update-object
description: 处理按条件修改既有对象的写入请求。用于更新、修改、设置、修补一个或一批对象的字段值，不用于创建、删除或存在则更新；生成符合第 9 章的 `UPDATE` S-OQL。
---
# S-OQL 更新生成插件

仅在本插件负责的操作边界内工作。先生成符合第 9 章的 **S-OQL**，再通过 `scripts/soql_to_oql.py` 做确定性转换，并使用 `scripts/oql_validator.py` 校验转换结果。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 先把自然语言请求整理为最小必要的结构化计划，不要直接跳到最终 JSON。
3. 顶层字段继续使用统一字段集：`version`、`schemaRef`、`strict`、`operation`、`objects`、`relationships`、`conditions`、`returns`、`orders`、`maxResults`、`sourceQuery`、`linkQuery`、`mutation`、`options`、`extensions`。
4. 仅允许对 `conditions`、`returns`、`mutation` 使用 S-OQL 简化语法；其余字段继续保持标准顶层结构。
5. `conditions` 只允许以下六种形态：
   - `["alias.field", "OP", value]`
   - `["alias.field", "IS_NULL"]`
   - `["alias.field", "IS_NOT_NULL"]`
   - `{"all": [...]}`
   - `{"any": [...]}`
   - `{"not": ...}`
6. 先完成 S-OQL，再调用 `scripts/soql_to_oql.py` 转成可执行结果；不要在文本层手工展开 canonical 结构。
7. 用 `scripts/oql_validator.py` 校验转换结果。
8. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `UPDATE`。
- `objects` 长度必须为 1。
- `conditions` 使用 S-OQL 简化语法。
- `mutation.scope` 只能是 `ONE` 或 `MANY`，`mutation.set` 必须存在且非空。
- 不得出现 `returns`、`orders`、`sourceQuery`、`relationships`、`linkQuery`。

## S-OQL 结构化计划要求

在进入转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- `conditions`
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

1. **operation 边界**：必须是 `UPDATE`。
2. **objects 数量**：`objects` 必须且仅有 1 个。
3. **必填块**：`conditions`、`mutation.scope`、`mutation.set` 必须存在。
4. **scope 合法性**：`mutation.scope` 仅允许 `ONE` 或 `MANY`。
5. **禁止字段**：不得出现 `returns`、`orders`、`sourceQuery`、`relationships`、`linkQuery`。
6. **alias 闭包**：`conditions`/`mutation` 中引用都必须落在已声明 alias 上。
7. **S-OQL 转 canonical**：若输入使用了条件三元组或 `all|any|not` 逻辑组，必须先调用转换脚本。
8. **mutation.set 约束**：更新字段不可为空，且字段名应来自目标对象逻辑字段。
9. **缺失信息处理**：无法确定筛选条件或更新内容时返回结构化错误。
