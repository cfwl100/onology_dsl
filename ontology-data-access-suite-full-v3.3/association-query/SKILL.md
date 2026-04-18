---
name: association-query
description: 处理需要显式关系路径或多跳遍历的对象关联读取请求。用于链式关系导航、图式对象访问、路径起点终点或中间节点联合筛选；当当前 schema 或调用约束要求单跳关系也走关联查询时同样使用。
---
# OQL 显式关系路径编译插件

仅生成 `ASSOCIATION_QUERY` 的规范结果，并且优先使用本插件内的确定性脚本完成**同壳 S-OQL → canonical OQL** 的转换、组装与校验。

## 工作方式

1. 先确认当前请求是否属于本插件负责的操作边界。
2. 再按需读取：
   - [OQL 规范关键描述](references/oql-spec-essentials.md)
   - [OQL 模板与样例](references/oql-examples.md)
   - [关联查询模式](references/association-patterns.md)
   - [条件树指导](references/conditions-guidance.md)
   - [样例对齐补充规则](references/example-alignment.md)
3. 先把自然语言请求整理为**同壳 S-OQL 结构化计划**，不要直接跳到最终 canonical JSON。
4. 使用 `scripts/s_oql_to_oql.py` 将同壳 S-OQL 归一化为 canonical OQL 计划。
5. 使用 `scripts/oql_builder.py` 补齐默认值、固定键顺序并清理空字段。
6. 使用 `scripts/oql_validator.py` 验证结构是否满足本操作及通用 OQL 约束。
7. 仅在校验通过后输出最终 canonical OQL JSON；若缺信息或校验失败，则输出结构化错误 JSON。

## 本插件关键规则

- 只负责 `ASSOCIATION_QUERY`。
- `relationships` 必须存在，且按路径顺序声明。
- `relationships` 仅用于 `ASSOCIATION_QUERY`。
- 默认情况下，单跳直接关系更适合 `LINK_QUERY`；但如果当前 schema/profile/调用方约束要求“单跳也走 `ASSOCIATION_QUERY`”，则必须服从该约束。
- 可在 `returns` 中返回对象字段；仅当用户明确需要关系字段时，才返回关系 alias 的字段。
- 如调用方已经明确给出当前步骤目标、主路径、补充路径、条件归属，应优先使用这些信息，而不是重新猜测路径。

## 同壳 S-OQL 简化语法

同壳 S-OQL **保留 canonical 顶层字段名不变**，仅允许简化 `conditions`、`returns`、`mutation` 的内部结构；`objects`、`relationships`、`orders`、`sourceQuery`、`linkQuery` 等继续使用 canonical 写法。

- `conditions` 可使用：
  - 叶子条件三元组：`["d.status", "EQ", "running"]`
  - 逻辑组：`{"all": [...]}` / `{"any": [...]}` / `{"not": ...}`
- `returns` 可使用：
  - 对象字段：`["FIELDS", "d", ["id", "name", "status"]]`
  - 关系字段：`["FIELDS", "r1", ["relationshipType"]]`
- `relationships` 继续使用 canonical 写法，不提供并行简写。
- 本操作不使用 `mutation` 简写。

## 当前步骤查询结构

在调用转换脚本前，先整理出最小必要结构：

- `schemaRef`
- `operation`
- `objects`
- 视操作需要补充 `relationships` / `conditions` / `returns` / `orders` / `sourceQuery`
- 如存在 profile 级约束，补充 `profile` 或等效上下文开关

建议优先级：

1. 当前步骤已经明确的目标、主路径、补充路径、条件归属
2. 前序步骤返回的真实结果
3. 当前激活的 schema 与子图线索
4. 用户原始问题中的约束

## 确定性脚本

- [脚本说明](scripts/README.md)
- `scripts/s_oql_to_oql.py`：把同壳 S-OQL 中简化的 `conditions` / `returns` / `mutation` 还原为 canonical OQL 结构，并递归处理 `sourceQuery` 与 `BATCH.items`
- `scripts/oql_builder.py`：补齐默认值、固定键顺序、清理空字段、递归处理 `sourceQuery` 与 `BATCH.items`，并支持可选 profile 覆盖
- `scripts/oql_validator.py`：检查字段合法性、数量约束、条件树、返回投影、嵌套限制与 profile 覆盖

## 输出约定

- 只输出严格规范的 **canonical OQL JSON**，或结构化错误 JSON。
- 不输出 Markdown、解释、注释或散文。
- 不输出 `null`、空对象或空数组。
- 不要为了凑齐 JSON 而猜测 schema 中不存在的对象、关系或字段。
- 如果调用方提供的 profile 约束与通用规范冲突，应优先遵守已激活的 profile 约束，并在结构化计划中显式记录该约束来源。
- 若输入使用了同壳 S-OQL 简写，也必须先完成转换，再输出 canonical OQL。

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
