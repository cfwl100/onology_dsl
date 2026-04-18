---
name: create-object
description: 处理创建单个对象的写入请求。用于新增、创建、插入或登记一个对象实例，不用于更新、删除或批处理。
---
# OQL 创建编译插件

仅生成 `CREATE` 的规范结果，并且优先使用本插件内的确定性脚本完成**同壳 S-OQL → canonical OQL** 的转换、组装与校验。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 再按需读取：
   - [OQL 规范关键描述](references/oql-spec-essentials.md)
   - [OQL 模板与样例](references/oql-examples.md)
   - [写操作边界](references/operation-boundaries.md)
3. 先把自然语言请求整理为**同壳 S-OQL 结构化计划**，不要直接跳到最终 canonical JSON。
4. 使用 `scripts/s_oql_to_oql.py` 将同壳 S-OQL 归一化为 canonical OQL 计划。
5. 使用 `scripts/oql_builder.py` 补齐默认值、固定键顺序并清理空字段。
6. 使用 `scripts/oql_validator.py` 验证结构是否满足本操作及通用 OQL 约束。
7. 仅在校验通过后输出最终 canonical OQL JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `CREATE`。
- `objects` 长度必须为 1。
- `mutation.data.properties` 必须存在且非空。
- 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`。

## 同壳 S-OQL 简化语法

同壳 S-OQL **保留 canonical 顶层字段名不变**，仅允许简化 `conditions`、`returns`、`mutation` 的内部结构；`objects`、`relationships`、`orders`、`sourceQuery`、`linkQuery` 等继续使用 canonical 写法。

- 本操作不使用 `conditions` 简写。
- 本操作不使用 `returns` 简写。
- `mutation` 可使用：
  - 直接数据对象：
    `{"data": {"name": "iPhone 16", "price": 8999, "createdAt": {"$fn": "now"}}}`
  - 转换后会归一化为 `mutation.data.properties`。

## 结构化计划要求

在调用转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- `mutation`

结构化计划允许省略默认值，例如 `version = "1.0"`、`strict = true`，这些可由组装脚本补齐。

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

1. **operation 边界**：必须是 `CREATE`，不得路由到 `UPDATE/UPSERT/BATCH`。
2. **objects 数量**：`objects` 必须且仅有 1 个目标对象。
3. **禁止字段**：不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
4. **mutation.data 完整性**：`mutation.data.properties` 必须存在且非空；若输入是同壳 S-OQL，必须先由转换脚本补为 `properties`。
5. **alias 闭包**：仅允许引用已声明对象 alias，不得出现悬空 ref。
6. **函数值规范**：如有函数值，使用对象形式（如 `{"$fn": "now"}`）。
7. **空值约束**：不得输出 `null`、空对象、空数组。
8. **缺失信息处理**：缺关键字段时返回结构化错误，禁止猜测补值。
