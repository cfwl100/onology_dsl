---
name: link-query
description: 处理通过单一关系类型获取关联对象的一跳读取请求。仅在语义明确是一跳关联获取、且不需要显式多跳路径时使用，并生成符合第 9 章的 `LINK_QUERY` S-OQL。
---
# S-OQL 单跳关联生成插件

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

- 只负责 `LINK_QUERY`。
- `objects` 必须恰好 2 个，分别表示源对象与目标对象。
- `linkQuery` 必须存在，且 `sourceRef/targetRef` 只引用对象 alias。
- `returns` 默认面向目标对象，若需唯一结果才使用 `linkQuery.mode = 'ONE'`。
- 不得出现 `relationships`、`mutation`。

## S-OQL 结构化计划要求

在进入转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- 视操作需要补充 `conditions` / `returns` / `orders` / `linkQuery`

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

1. **operation 边界**：必须是 `LINK_QUERY`，且语义为单跳关联。
2. **objects 数量**：`objects` 必须恰好 2 个（源对象/目标对象）。
3. **必填块**：`conditions`（源侧）与 `linkQuery` 必须存在。
4. **linkQuery 合法性**：`mode` 仅 `LIST/ONE`，`sourceRef/targetRef` 必须引用对象 alias。
5. **禁止字段**：不得出现 `relationships`、`mutation`。
6. **alias 闭包**：`conditions`、`returns`、`linkQuery` 的引用必须闭合。
7. **S-OQL 转 canonical**：若输入使用了条件三元组或 `FIELDS` 元组，必须先调用转换脚本。
8. **ONE/LIST 判定**：只有在唯一性明确时才使用 `ONE`。
9. **缺失信息处理**：关系类型或源筛选条件不明确时返回结构化错误。
