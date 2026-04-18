---
name: aggregate-query
description: 处理以统计、分组、计数、求和、平均值、最值或排行为中心的读取请求。仅在结果以聚合指标或分组结果为核心时使用。
---
# OQL 聚合统计编译插件

仅生成 `AGGREGATE` 的规范结果，并且优先使用本插件内的确定性脚本完成**同壳 S-OQL → canonical OQL** 的转换、组装与校验。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 再按需读取：
   - [OQL 规范关键描述](references/oql-spec-essentials.md)
   - [OQL 模板与样例](references/oql-examples.md)
   - [聚合模式与边界](references/aggregate-patterns.md)
3. 先把自然语言请求整理为**同壳 S-OQL 结构化计划**，不要直接跳到最终 canonical JSON。
4. 使用 `scripts/s_oql_to_oql.py` 将同壳 S-OQL 归一化为 canonical OQL 计划。
5. 使用 `scripts/oql_builder.py` 补齐默认值、固定键顺序并清理空字段。
6. 使用 `scripts/oql_validator.py` 验证结构是否满足本操作及通用 OQL 约束。
7. 仅在校验通过后输出最终 canonical OQL JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `AGGREGATE`。
- `returns` 中至少包含一个 `METRIC`。
- `returns` 只能使用 `GROUP_BY` 和 `METRIC`。
- 对聚合结果排序时，优先使用 `returns[].alias`。

## 同壳 S-OQL 简化语法

同壳 S-OQL **保留 canonical 顶层字段名不变**，仅允许简化 `conditions`、`returns`、`mutation` 的内部结构；`objects`、`relationships`、`orders`、`sourceQuery`、`linkQuery` 等继续使用 canonical 写法。

- `conditions` 可使用：
  - 叶子条件三元组：`["o.status", "EQ", "completed"]`
  - 逻辑组：`{"all": [...]}` / `{"any": [...]}` / `{"not": ...}`
- `returns` 可使用：
  - 分组元组：`["GROUP_BY", "o.region", "region"]`
  - 指标元组：`["METRIC", "SUM", "o.amount", "totalAmount"]`
  - 计数元组：`["METRIC", "COUNT", "o.*", "orderCount"]`
- 本操作不使用 `mutation` 简写。

## 结构化计划要求

在调用转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- 视操作需要补充 `relationships` / `conditions` / `returns` / `orders` / `sourceQuery` / `linkQuery` / `mutation`

结构化计划允许省略默认值，例如 `version = "1.0"`、`strict = true`、查询类 `maxResults = 1000`，这些可由组装脚本补齐。

## 确定性脚本

- [脚本说明](scripts/README.md)
- `scripts/s_oql_to_oql.py`：把同壳 S-OQL 中简化的 `conditions` / `returns` / `mutation` 还原为 canonical OQL 结构，并递归处理 `sourceQuery` 与 `BATCH.items`
- `scripts/oql_builder.py`：补齐默认值、固定键顺序、清理空字段、递归处理 `sourceQuery` 与 `BATCH.items`
- `scripts/oql_validator.py`：检查字段合法性、数量约束、条件树、返回投影、嵌套限制与写操作约束

## 输出约定

- 只输出严格规范的 **canonical OQL JSON**，或结构化错误 JSON。
- 不输出 Markdown、解释、注释或散文。
- 不输出 `null`、空对象或空数组。
- 不要为了凑齐 JSON 而猜测 schema 中不存在的对象、关系或字段。
- 若输入使用了同壳 S-OQL 简写，也必须先完成转换，再输出 canonical OQL。

## 输出前必须逐项检查（Checklist）

在给出最终输出前，必须逐项自检，全部满足后才可输出：

1. **operation 边界**：必须是 `AGGREGATE`。
2. **objects/returns 必填**：`objects` 与 `returns` 必须存在。
3. **returns kind 约束**：仅允许 `GROUP_BY` 与 `METRIC`，且至少一个 `METRIC`。
4. **禁止字段**：不得出现 `relationships`、`linkQuery`、`mutation`。
5. **alias 闭包**：聚合/分组 alias 必须可被 `orders` 正确引用。
6. **S-OQL 转 canonical**：若输入使用了 `GROUP_BY` / `METRIC` 元组，必须先调用转换脚本。
7. **排序规则**：聚合结果排序优先使用 `returns[].alias`。
8. **sourceQuery 深度**：若使用 `sourceQuery`，必须符合读操作深度限制。
9. **缺失信息处理**：缺聚合指标或分组语义不清时返回结构化错误。
