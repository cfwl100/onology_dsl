---
name: aggregate-query
description: 处理以统计、分组、计数、求和、平均值、最值或排行为中心的读取请求。仅在结果以聚合指标或分组结果为核心时使用，并生成符合 S-OQL 生成层语法规范的 `AGGREGATE` S-OQL。
---
# S-OQL 聚合统计生成插件

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

- 只负责 `AGGREGATE`。
- `returns` 只允许 `['GROUP_BY', '<alias>.<field>', '<resultAlias>']` 与 `['METRIC', '<function>', '<alias>.<field>|<alias>.*', '<resultAlias>']`。
- `returns` 中至少包含一个 `METRIC`。
- 不得出现 `relationships`、`linkQuery`、`mutation`。
- 对聚合结果排序时，优先使用 `returns` 中显式定义的结果别名。

## 固定语法约束（S-OQL 生成层语法规范）

> 具体语法细节统一放在 `references/soql-diff-notes.md`，本节仅保留稳定边界与入口约束。

### 1) `conditions` 五类约束

仅允许五类：比较三元组、空值判断、非空判断、逻辑组（`all/any`）、逻辑取反（`not`）。具体的 `alias.field`、操作符和值类型约束详见 references。

### 2) `returns` 定长元组规则

`AGGREGATE` 仅允许 `GROUP_BY` / `METRIC` 定长元组，且至少一个 `METRIC`。 具体元组形态与字段位置约束详见 references。

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

1. **operation 边界**：必须是 `AGGREGATE`。
2. **objects/returns 必填**：`objects` 与 `returns` 必须存在。
3. **returns kind 约束**：仅允许 `GROUP_BY` 与 `METRIC`，且至少一个 `METRIC`。
4. **禁止字段**：不得出现 `relationships`、`linkQuery`、`mutation`。
5. **alias 闭包**：聚合/分组 alias 必须可被 `orders` 正确引用。
6. **排序规则**：聚合结果排序优先使用 `returns` 中定义的结果别名。
7. **sourceQuery 深度**：若使用 `sourceQuery`，必须符合读操作深度限制。
8. **缺失信息处理**：缺聚合指标或分组语义不清时返回结构化错误。
