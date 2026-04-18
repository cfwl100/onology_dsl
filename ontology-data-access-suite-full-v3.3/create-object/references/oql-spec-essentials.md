# OQL 规范关键描述速查

本文件提炼 OQL 规范中最影响编译正确性的关键结构与约束。编译时优先遵守本文件，再结合当前插件的操作边界与样例。

## 1. 顶层字段

| 字段 | 说明 |
| --- | --- |
| `version` | DSL 版本，固定为 `"1.0"` |
| `schemaRef` | 当前请求绑定的本体 schema 标识 |
| `strict` | 是否启用严格校验，默认 `true` |
| `operation` | 操作类型：`QUERY`、`AGGREGATE`、`ASSOCIATION_QUERY`、`LINK_QUERY`、`CREATE`、`UPDATE`、`DELETE`、`UPSERT`、`BATCH` |
| `objects` | 统一对象声明 |
| `relationships` | 显式关系路径，仅 `ASSOCIATION_QUERY` 使用 |
| `conditions` | 统一条件表达式 |
| `returns` | 返回字段、分组字段、聚合指标 |
| `orders` | 排序定义 |
| `maxResults` | 默认 `1000`，最大 `100000` |
| `sourceQuery` | 嵌套只读子查询 |
| `linkQuery` | `LINK_QUERY` 专用块 |
| `mutation` | 写操作专用块 |
| `options` | 执行选项，如超时、dryRun、元数据返回 |
| `extensions` | 预留扩展区；无明确契约时应省略 |

## 2. `objects` 统一对象声明

- 只声明对象类型与别名，不负责实例定位。
- `alias` 必须显式声明，建议使用 `lower_snake_case`。
- `fromSource` 只能引用同层 `sourceQuery[].outputAs`。
- `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 中，`objects` 长度必须为 `1`。
- `LINK_QUERY` 中，`objects` 长度必须为 `2`。
- `BATCH` 顶层不使用 `objects`。

示例：

```json
{
  "objects": [
    {"objectType": "Order", "alias": "o"}
  ]
}
```

## 3. `relationships` 统一关系路径

- 仅用于 `ASSOCIATION_QUERY`。
- 使用 `{relationshipType, alias, from, to}`。
- `from` / `to` 必须引用当前层 `objects[].alias`。
- 数组顺序就是路径顺序。
- `relationships[].alias` 不能与对象 alias 重名。

## 4. `conditions` 统一条件表达式

- 使用递归逻辑树，不是自由拼装对象。
- `kind` 只能是 `GROUP` 或 `PREDICATE`。
- `GROUP` 使用 `relation` 和 `children`。
- `PREDICATE` 使用 `ref`、`field`、`operator`、`values`。
- `ref` 可引用对象 alias，也可在允许的情况下引用关系 alias。
- `conditions.values` 使用普通字面量值，不应使用函数表达式。

常见操作符约束：

- `EQ` / `NE`：恰好 1 个值
- `GT` / `GTE` / `LT` / `LTE`：恰好 1 个值
- `IN` / `NOT_IN`：至少 1 个值
- `BETWEEN`：恰好 2 个值
- `LIKE` / `CONTAINS` / `STARTS_WITH` / `ENDS_WITH`：恰好 1 个字符串值
- `IS_NULL` / `IS_NOT_NULL`：不出现 `values`

## 5. `returns` 统一返回投影

- `returns` 一律是对象数组。
- `kind` 只能是 `FIELDS`、`GROUP_BY`、`METRIC`。
- `FIELDS` 只能使用 `fields`，并且字段必须显式列出。
- `FIELDS.fields` 不允许出现 `"*"`。
- `GROUP_BY` 与 `METRIC` 必须显式声明 `alias`。
- `COUNT` 统计总行数时，`field` 可以是 `"*"`；其他函数必须显式字段名。

## 6. `orders` 排序定义

- 使用 `{ref, field, direction}`。
- `ref` 引用对象 alias 或与结果集关联的 alias。
- 当排序字段是聚合结果或分组别名时，应使用 `returns[].alias`。
- 当排序字段是原始对象字段时，应使用逻辑字段名。

## 7. `sourceQuery` 嵌套查询

- 只允许出现在查询类操作中。
- `outputAs` 在同层必须唯一。
- 当前层通过 `objects[].fromSource` 显式绑定子查询结果。
- 不支持引用外层 alias，即不支持相关子查询。
- `strict = true` 时，最大嵌套深度为 `2`。
- 写操作中不得出现 `sourceQuery`。

## 8. `linkQuery` 专用块

- 仅用于 `LINK_QUERY`。
- 顶层 `objects` 必须且仅能声明 2 个对象。
- 使用 `mode`、`relationshipType`、`sourceRef`、`targetRef`、`direction`。
- `mode = ONE` 时，语义上要求结果唯一。
- `LINK_QUERY` 不使用 `relationships`。

## 9. `mutation` 写操作专用块

- `CREATE`：必须有 `mutation.data.properties`；不得出现 `conditions`。
- `UPDATE`：必须有 `conditions`、`mutation.scope`、`mutation.set`。
- `DELETE`：必须有 `conditions`、`mutation.scope`。
- `UPSERT`：必须有 `mutation.matchBy` 与 `mutation.data.properties`；不得出现 `conditions`。
- `BATCH`：必须有 `mutation.atomic` 与非空 `mutation.items`。
- `BATCH.items[]` 只允许 `CREATE` / `UPDATE` / `DELETE` / `UPSERT`。
- `BATCH` 子项继承外层 `version`、`schemaRef`、`strict`，因此子项中不再重复这些字段。
- `BATCH` 不允许嵌套 `BATCH`。

## 10. 值表达式

- 函数表达式对象写法：`{"$fn": "now"}`。
- 带参数函数写法：`{"$fn": "coalesce", "args": ["customerName", "unknown"]}`。
- 函数表达式主要用于 `mutation.data.properties` 与 `mutation.set`。
- 不要在 `conditions.values` 中使用函数表达式。
