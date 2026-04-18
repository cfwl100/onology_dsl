# S-OQL 差异说明（association-query）

> 说明：本目录中的 canonical OQL 参考文件保持原样，不删除、不改写；本文件仅记录 S-OQL 生成层语法规范带来的差异约束。

## 本次差异点

1. 文档表述统一由“第 9 章”调整为“S-OQL 生成层语法规范”。
2. Skill 主文档仅保留稳定入口约束，具体语法细节下沉到 references。
3. canonical OQL 示例与规范文件继续作为转换后的目标语义参考，本文件不替代 canonical 文档。

## S-OQL 生成层语法规范细节

### A. `conditions` 五类（统一规则）

允许的五类结构：
1. 比较三元组：`["alias.field", "OP", value]`
2. 空值判断：`["alias.field", "IS_NULL"]`
3. 非空判断：`["alias.field", "IS_NOT_NULL"]`
4. 逻辑组：`{"all": [...]}` 或 `{"any": [...]}`
5. 逻辑取反：`{"not": ...}`

细节约束：
- `alias.field` 中 `alias` 必须已在 `objects` 声明，`field` 必须可解析。
- `OP` 仅允许比较操作符（如 `= != > >= < <= IN NOT_IN LIKE`）。
- `value` 必须与字段语义兼容；`IN/NOT_IN` 的值必须为非空数组。


### B. `returns` 定长元组（ASSOCIATION_QUERY）

- 仅允许：`["FIELDS", "<alias>", ["field1", "field2"]]`
- 默认优先对象 alias；关系 alias 字段仅在明确要求时使用。

### C. `mutation` 简化规则（ASSOCIATION_QUERY）

- 查询操作禁止 `mutation` 字段。
