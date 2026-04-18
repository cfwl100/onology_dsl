# 关系路径与条件指导

## 关系路径

- `relationships` 使用 `{relationshipType, alias, from, to}`
- `from` 与 `to` 必须引用 `objects[].alias`
- 多跳路径按数组顺序声明
- 若存在多跳，前一个关系的 `to` 应与下一个关系的 `from` 连通，除非调用方明确要求多分支结构

## 条件树

- 单个叶子条件可直接使用 `PREDICATE`
- 多个条件应使用 `GROUP`
- `GROUP.relation` 只能是 `AND` / `OR` / `NOT`
- 当需要用同一个前置变量匹配目标对象的多个候选字段时，应在外层 `AND` 下嵌套一个 `OR` 分组

## 字段与值

- `field` 必须是 schema 中真实存在的逻辑字段名
- 不要根据对象名臆造字段前缀
- `values` 必须基于当前上下文中已知的真实值，不要凭空猜测
- 若当前 profile 要求字符串化，应将所有 `values` 写成字符串数组

## 返回与排序

- 默认推荐显式列出 `FIELDS.fields`
- 若当前 profile 约定关联查询返回 `fields = ["*"]`，则可以按 profile 规则执行
- 需要排序时，使用 `{ref, field, direction}`
