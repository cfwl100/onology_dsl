---
name: delete-object
description: 处理按条件删除既有对象的写入请求。仅在需要删除一个或一批已经存在的对象时使用，并生成符合 S-OQL 生成层语法规范的 `DELETE` S-OQL。
---
# S-OQL 删除生成插件

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

- 只负责 `DELETE`。
- `objects` 长度必须为 1。
- `conditions` 使用 S-OQL 简化语法。
- `mutation.scope` 必须存在，且只允许 `ONE` 或 `MANY`。
- 不得出现 `mutation.set`、`mutation.data`、`returns`、`orders`、`sourceQuery`、`relationships`、`linkQuery`。

## 固定语法约束（S-OQL 生成层语法规范）

> 具体语法细节统一放在 `references/soql-diff-notes.md`，本节仅保留稳定边界与入口约束。

### 1) `conditions` 五类约束

仅允许五类：比较三元组、空值判断、非空判断、逻辑组（`all/any`）、逻辑取反（`not`）。具体的 `alias.field`、操作符和值类型约束详见 references。

### 2) `returns` 定长元组规则

`DELETE` 禁止 `returns`。 具体元组形态与字段位置约束详见 references。

### 3) `mutation` 简化规则

`DELETE` 仅允许 `mutation.scope` 简化写法。 具体允许/禁止字段清单详见 references。

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

1. **operation 边界**：必须是 `DELETE`。
2. **objects 数量**：`objects` 必须且仅有 1 个。
3. **必填块**：`conditions` 与 `mutation.scope` 必须存在。
4. **scope 合法性**：`mutation.scope` 仅允许 `ONE` 或 `MANY`。
5. **禁止字段**：不得出现 `mutation.set`、`mutation.data`、`returns`、`orders`、`sourceQuery`、`relationships`、`linkQuery`。
6. **alias 闭包**：`conditions` 引用的 ref 必须为已声明对象 alias。
7. **S-OQL 转 canonical**：若输入使用了条件三元组或 `all|any|not` 逻辑组，必须先调用转换脚本。
8. **空删防护**：条件语义不清或过宽时不得冒险删除。
9. **缺失信息处理**：无法确定删除范围时返回结构化错误。
