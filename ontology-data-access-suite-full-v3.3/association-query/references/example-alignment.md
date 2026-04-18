# 与目标样例对齐的补充规则

本文件用于处理某些 schema / 调用方上下文中的专项约束。若这些约束与通用规则冲突，应以**当前已激活的 schema/profile 约束**优先。

## 1. 单跳也使用 `ASSOCIATION_QUERY`

默认情况下，单跳直接关系更适合 `LINK_QUERY`。

但当满足以下任一条件时，单跳也应使用 `ASSOCIATION_QUERY`：

- 调用方明确要求“即使单跳，也必须使用 `ASSOCIATION_QUERY`”
- 当前 schema/profile 已约定单跳关系统一走显式路径查询
- 用户虽然只描述一跳，但同时要求显式声明 `relationships`

## 2. `returns[].fields = ["*"]` 的兼容模式

通用规范建议 `FIELDS.fields` 显式列出字段名。

但若当前 profile 明确约定关联查询返回采用：

```json
{"kind": "FIELDS", "ref": "x", "fields": ["*"]}
```

则在该 profile 下允许 `FIELDS.fields = ["*"]`。

## 3. 条件值字符串化

通用 OQL 允许 `conditions.values` 使用字面量值。

但若当前 profile 明确要求条件值全部字符串化，则应将：

- `10` 写为 `"10"`
- `2` 写为 `"2"`

同时禁止在 `conditions.values` 中引入函数表达式。

## 4. 小写对象类型与关系类型

如果当前 schema/profile 规定对象类型、关系类型与 alias 必须使用小写命名，则应严格遵守，避免生成大小写混用的逻辑标识。

## 5. 固定 schemaRef / 默认 maxResults

若调用上下文已经激活固定 `schemaRef` 或默认 `maxResults`，必须完全保留，不要私自替换为其他 schema。

## 6. 组合条件的 OR 包裹模式

当同一个前置变量需要匹配目标对象上的多个候选字段时，应在外层 `AND` 下嵌套一个 `OR` 分组，例如同时匹配 `aEndPortName` 与 `zEndPortName`。
