---
name: association-query
description: 处理需要显式关系路径或多跳遍历的对象关联读取请求。用于链式关系导航、图式对象访问、路径起点终点或中间节点联合筛选，并生成符合 S-OQL 生成层语法规范的 `ASSOCIATION_QUERY` S-OQL。
---
# S-OQL 显式关系路径生成插件

仅在本插件负责的操作边界内工作。先生成符合 S-OQL 生成层语法规范的 **S-OQL**，再通过 `scripts/soql_to_oql.py` 做确定性转换，并使用 `scripts/oql_validator.py` 校验转换结果。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 先把自然语言请求整理为最小必要的结构化计划，不要直接跳到最终 JSON。
3. 顶层字段继续使用统一字段集：`version`、`schemaRef`、`strict`、`operation`、`objects`、`relationships`、`conditions`、`returns`、`orders`、`maxResults`、`sourceQuery`、`linkQuery`、`mutation`、`options`、`extensions`。
4. 仅允许对 `conditions`、`returns`、`mutation` 使用 S-OQL 简化语法；其余字段继续保持标准顶层结构。
5. `conditions` 只允许五类结构：
   - 比较三元组：`["alias.field", "OP", value]`
   - 空值判断：`["alias.field", "IS_NULL"]`
   - 非空判断：`["alias.field", "IS_NOT_NULL"]`
   - 逻辑组：`{"all": [...]}` 或 `{"any": [...]}`
   - 逻辑取反：`{"not": ...}`
6. 先完成 S-OQL，再调用 `scripts/soql_to_oql.py` 转成可执行结果；不要在文本层手工展开 canonical 结构。
7. 用 `scripts/oql_validator.py` 校验转换结果。
8. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `ASSOCIATION_QUERY`。
- `relationships` 必须存在，且按路径顺序声明。
- 默认返回对象字段；仅在用户明确需要时返回关系 alias 的字段。
- 不得出现 `linkQuery`、`mutation`。
- 如存在 profile 级调用约束，应先在 S-OQL 结构化计划中记录该约束，再进入脚本转换。

## 固定语法约束（S-OQL 生成层语法规范）

> 具体语法细节统一放在 `references/soql-diff-notes.md`，本节仅保留稳定边界与入口约束。

### 1) `conditions` 五类约束

仅允许五类：比较三元组、空值判断、非空判断、逻辑组（`all/any`）、逻辑取反（`not`）。具体的 `alias.field`、操作符和值类型约束详见 references。

### 2) `returns` 定长元组规则

`ASSOCIATION_QUERY` 仅允许 `FIELDS` 三元组（关系 alias 字段仅在明确要求时使用）。 具体元组形态与字段位置约束详见 references。

### 3) `mutation` 简化规则

读取操作禁止 `mutation`。 具体允许/禁止字段清单详见 references。

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

1. **operation 边界**：必须是 `ASSOCIATION_QUERY`。
2. **必填块**：`objects`、`relationships`、`returns` 必须存在。
3. **路径合法性**：`relationships` 必须按路径顺序，`from/to` 都引用对象 alias。
4. **禁止字段**：不得出现 `linkQuery`、`mutation`。
5. **alias 闭包**：关系 alias 与对象 alias 的引用必须闭合且无悬空。
6. **S-OQL 转 canonical**：若输入使用了条件三元组或 `FIELDS` 元组，必须先调用转换脚本。
7. **returns 归属**：默认返回对象字段，仅在明确需要时返回关系字段。
8. **sourceQuery 深度**：若使用 `sourceQuery`，路径与层级需可解释且受控。
9. **缺失信息处理**：路径起终点或关系类型不明确时返回结构化错误。
