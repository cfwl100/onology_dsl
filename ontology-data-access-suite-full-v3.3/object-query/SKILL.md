---
name: object-query
description: 处理不涉及聚合、不涉及显式关系路径、也不属于单跳关联语义的普通对象读取请求。用于生成符合第 9 章的 `QUERY` S-OQL；仅在需要查询结构且尚未得到完整可执行请求时使用。
---
# S-OQL 普通查询生成插件

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

- 只负责 `QUERY`。
- `returns` 只允许 `FIELDS` 项，写法为 `['FIELDS', '<alias>', ['field1', 'field2']]`。
- 不得出现 `relationships`、`linkQuery`、`mutation`。
- 可使用 `orders` 与 `maxResults` 控制结果规模。

## S-OQL 结构化计划要求

在进入转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- 视操作需要补充 `relationships` / `conditions` / `returns` / `orders` / `sourceQuery` / `linkQuery` / `mutation`

默认值可以省略并交给脚本补齐，例如：

- `version = "1.0"`
- `strict = true`
- 查询类 `maxResults = 1000`

## 输出约定

- 最终只输出脚本转换后的 JSON，或结构化错误 JSON。
- 不输出 Markdown、解释、注释或散文。
- 不输出 `null`、空对象或空数组。
- 不要为了凑齐 JSON 而猜测 schema 中不存在的对象、关系或字段。
- 不要在文本层描述 canonical OQL 展开细节；所有展开逻辑都交给脚本。

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `QUERY`。
2. **objects/returns 必填**：`objects` 与 `returns` 必须存在。
3. **returns 约束**：`returns` 只能使用 `FIELDS` 元组。
4. **禁止字段**：不得出现 `relationships`、`linkQuery`、`mutation`。
5. **conditions 合法性**：过滤条件仅引用已声明对象 alias。
6. **sourceQuery 约束**：仅在规范允许时使用，且嵌套深度受控。
7. **排序与引用**：`orders` 的 `ref/field` 必须可解析到查询结果。
8. **缺失信息处理**：对象范围或返回字段缺失时返回结构化错误。
