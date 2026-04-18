---
name: upsert-batch
description: 处理存在则更新否则创建，或多个写操作需要作为一个批次执行的请求。用于显式 upsert 语义或需要原子批处理的场景，并生成符合 S-OQL 生成层语法规范的 `UPSERT` / `BATCH` S-OQL。
---
# S-OQL 插入或批处理生成插件

仅在本插件负责的操作边界内工作。先生成符合 S-OQL 生成层语法规范的 **S-OQL**，再通过 `scripts/soql_to_oql.py` 做确定性转换，并使用 `scripts/oql_validator.py` 校验转换结果。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 先把自然语言请求整理为最小必要的结构化计划，不要直接跳到最终 JSON。
3. 顶层字段继续使用统一字段集：`version`、`schemaRef`、`strict`、`operation`、`objects`、`relationships`、`conditions`、`returns`、`orders`、`maxResults`、`sourceQuery`、`linkQuery`、`mutation`、`options`、`extensions`。
4. 仅允许对 `conditions`、`returns`、`mutation` 使用 S-OQL 简化语法；其余字段继续保持标准顶层结构。
5. 写操作中优先使用 `mutation.data` 的直接属性对象写法，由脚本恢复为标准写入结构。
6. `BATCH.items` 子项也必须先按 S-OQL 生成，再递归交给脚本转换。
7. 用 `scripts/oql_validator.py` 校验转换结果。
8. 仅在校验通过后输出最终 JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `UPSERT / BATCH`。
- `UPSERT` 中 `mutation.matchBy` 必须是字段名数组，`mutation.data` 必须是直接属性对象。
- `BATCH` 中 `mutation.atomic` 与非空 `mutation.items` 必须存在，且子项不得再使用 `BATCH`。
- `BATCH.items` 子项也必须先按 S-OQL 生成，再递归交给脚本转换。
- `UPSERT` 场景不得出现 `conditions`。

## 固定语法约束（S-OQL 生成层语法规范）

> 具体语法细节统一放在 `references/soql-diff-notes.md`，本节仅保留稳定边界与入口约束。

### 1) `conditions` 五类约束

仅允许五类：比较三元组、空值判断、非空判断、逻辑组（`all/any`）、逻辑取反（`not`）。具体的 `alias.field`、操作符和值类型约束详见 references。

### 2) `returns` 定长元组规则

`UPSERT/BATCH` 顶层禁止 `returns`。 具体元组形态与字段位置约束详见 references。

### 3) `mutation` 简化规则

`UPSERT` 仅允许 `matchBy + data`；`BATCH` 仅允许 `atomic + items`。 具体允许/禁止字段清单详见 references。

## S-OQL 结构化计划要求

在进入转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- 视操作需要补充 `relationships` / `conditions` / `returns` / `orders` / `sourceQuery` / `linkQuery` / `mutation`

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

1. **operation 边界**：仅允许 `UPSERT` 或 `BATCH`。
2. **UPSERT 约束**：`objects` 必须 1 个，且 `mutation.matchBy`、`mutation.data` 必填。
3. **matchBy 闭包**：`matchBy` 中每个字段都必须出现在 `mutation.data` 中。
4. **UPSERT 禁止字段**：`UPSERT` 场景不得出现 `conditions`。
5. **BATCH 约束**：`mutation.atomic` 与非空 `mutation.items` 必填，子项不得再是 `BATCH`。
6. **子项结构**：每个 item 必须是合法单操作结构，且继承顶层上下文。
7. **alias 与引用**：各子项内引用独立闭包，不跨 item 悬空引用。
8. **缺失信息处理**：缺匹配键或批次子项不完整时返回结构化错误。
