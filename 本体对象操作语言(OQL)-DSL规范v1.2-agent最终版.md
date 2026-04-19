# 本体对象操作语言（OQL）DSL 规范 v1.2 - Agent 最终版

## 1. 定位与设计原则

### 1.1 定位

OQL 是面向本体对象模型的声明式逻辑查询与操作语言，用于表达：

- 查询或操作哪些对象
- 对象之间有哪些逻辑关系
- 需要满足哪些条件
- 需要返回哪些字段
- 需要执行哪些写入动作

OQL 不直接面向物理表、物理列和具体数据库方言。执行时由 OAC（Ontology Access）完成从逻辑结构到物理查询或写入语句的绑定、翻译与编排。

### 1.2 设计目标

1. 统一：不同操作共享统一顶层结构。
2. 对象中心：围绕对象、属性、关系表达，而不是围绕表与 Join 表达。
3. 面向 Agent：采用固定槽位、固定元组、最少层级，降低生成歧义。
4. 可校验：支持结构校验、引用校验、语义校验和执行期校验。
5. 可编排：支持 `sourceQuery` 作为中间结果集。
6. 可扩展：通过 schema 扩展对象类型、关系类型、属性与映射。
7. 多数据源透明：对象属性的物理来源对调用方透明，由 OAC 负责映射与装配。

### 1.3 规范原则

1. 同一语义只保留一种面向 Agent 的主写法，不定义并行等价写法。
2. `objects` 只声明对象，不承担实例定位职责。
3. `relationships` 只声明路径关系，不承担过滤职责。
4. 筛选、更新目标、删除目标统一通过 `conditions` 表达；`UPSERT` 的存在性判断通过 `matchBy` 表达。
5. 所有跨模块引用统一使用 alias。
6. 未使用字段必须省略，不允许输出 `null`、空对象或空数组占位。
7. 面向 Agent 的输入统一采用最终 S-OQL；执行前必须转换为 canonical OQL。
8. 顶层字段名保持稳定，不引入并行顶层语法。

---

## 2. 顶层结构与通用约束

### 2.1 顶层结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "<OPERATION>",

  "objects": [...],
  "relationships": [...],
  "conditions": ...,
  "returns": [...],
  "orders": [...],
  "maxResults": 1000,

  "sourceQuery": [...],

  "linkQuery": {...},
  "mutation": {...},

  "options": {...},
  "extensions": {...}
}
```

### 2.2 顶层字段顺序

推荐固定如下顺序：

```text
version
schemaRef
strict
operation
objects
relationships
conditions
returns
orders
maxResults
sourceQuery
linkQuery
mutation
options
extensions
```

### 2.3 顶层字段定义

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `version` | string | 是 | 固定为 `1.0` |
| `schemaRef` | string | 是 | 本次请求绑定的 schema 标识 |
| `strict` | boolean | 否 | 是否启用严格校验，默认 `true` |
| `operation` | enum | 是 | `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `LINK_QUERY` / `CREATE` / `UPDATE` / `DELETE` / `UPSERT` / `BATCH` |
| `objects` | array | 条件必填 | 对象声明 |
| `relationships` | array | 条件必填 | 关系路径声明，仅 `ASSOCIATION_QUERY` 使用 |
| `conditions` | array\|object | 条件必填 | 条件表达式；`UPDATE` / `DELETE` 必填 |
| `returns` | array | 条件必填 | 返回定义；查询类操作必填 |
| `orders` | array | 否 | 排序定义 |
| `maxResults` | integer | 否 | 最大返回数量，默认 `1000`，最大 `100000` |
| `sourceQuery` | array | 否 | 子查询定义 |
| `linkQuery` | object | 条件必填 | `LINK_QUERY` 专用块 |
| `mutation` | object | 条件必填 | 写操作专用块 |
| `options` | object | 否 | 执行选项 |
| `extensions` | object | 否 | 扩展字段；无明确约定时应省略 |

### 2.4 通用约束

1. 顶层必须包含 `version`、`schemaRef`、`operation`。
2. `strict` 缺省时按 `true` 处理。
3. 未使用字段必须省略。
4. 所有 alias 必须显式声明。
5. 所有对象类型、关系类型、字段名都必须与 `schemaRef` 对应的 schema 定义一致。
6. `sourceQuery` 内部若出现 `conditions`、`returns`、`orders`、`mutation`，也必须继续使用本规范的最终写法。
7. `BATCH.items[]` 中的子请求若出现 `conditions`、`returns`、`orders`、`mutation`，也必须继续使用本规范的最终写法。

---

## 3. 通用模块语法

### 3.1 `objects`：对象声明

`objects` 只负责声明参与本次操作的对象类型与别名，不负责实例定位。

#### 3.1.1 最终写法

```json
"objects": [
  ["Order", "o"]
]
```

带 `fromSource`：

```json
"objects": [
  ["CompletedOrder", "co", "completed_orders"]
]
```

#### 3.1.2 槽位定义

| 位置 | 含义 | 必填 |
| --- | --- | :--: |
| 第 1 槽 | `objectType` | 是 |
| 第 2 槽 | `alias` | 是 |
| 第 3 槽 | `fromSource` | 否 |

#### 3.1.3 使用约束

1. 每个对象元组长度只能为 2 或 3。
2. `alias` 必须在当前层唯一。
3. `fromSource` 仅可引用同层 `sourceQuery[].outputAs`。
4. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 中，`objects` 长度必须为 1。
5. `LINK_QUERY` 中，`objects` 长度必须为 2。
6. `BATCH` 顶层不得出现 `objects`。

---

### 3.2 `relationships`：关系路径声明

`relationships` 用于 `ASSOCIATION_QUERY` 中显式声明关系路径。数组顺序即路径顺序。

#### 3.2.1 最终写法

```json
"relationships": [
  ["installed_on", "r1", "d", "s"],
  ["deployed_in", "r2", "s", "dc"]
]
```

#### 3.2.2 槽位定义

| 位置 | 含义 | 必填 |
| --- | --- | :--: |
| 第 1 槽 | `relationshipType` | 是 |
| 第 2 槽 | `alias` | 是 |
| 第 3 槽 | `from` | 是 |
| 第 4 槽 | `to` | 是 |

#### 3.2.3 使用约束

1. 每个关系元组长度必须为 4。
2. `from` / `to` 必须引用当前层 `objects[].alias`。
3. 关系 alias 不得与对象 alias 冲突。
4. `relationships` 仅允许出现在 `ASSOCIATION_QUERY` 中。

---

### 3.3 `conditions`：条件表达式

`conditions` 统一表达查询筛选、更新目标与删除目标。最终写法使用固定元组与逻辑组。

#### 3.3.1 允许形态

1. 三元组字段条件：`["<alias>.<field>", "<operator>", <value>]`
2. 三元组表达式条件：`[<Expr>, "<operator>", <value-or-expr>]`
3. 二元空值条件：`["<alias>.<field>", "IS_NULL"]` / `["<alias>.<field>", "IS_NOT_NULL"]`
4. 二元表达式空值条件：`[<Expr>, "IS_NULL"]` / `[<Expr>, "IS_NOT_NULL"]`
5. AND 逻辑组：`{ "all": [<ConditionNode>, ...] }`
6. OR 逻辑组：`{ "any": [<ConditionNode>, ...] }`
7. NOT 逻辑组：`{ "not": <ConditionNode> }`

#### 3.3.2 操作符

- `EQ` / `NE`
- `GT` / `GTE` / `LT` / `LTE`
- `IN` / `NOT_IN`
- `BETWEEN`
- `LIKE` / `CONTAINS` / `STARTS_WITH` / `ENDS_WITH`
- `IS_NULL` / `IS_NOT_NULL`

#### 3.3.3 示例

```json
"conditions": {
  "all": [
    ["o.status", "EQ", "completed"],
    ["o.amount", "GTE", 1000]
  ]
}
```

```json
"conditions": {
  "any": [
    ["d.status", "EQ", "running"],
    {
      "all": [
        [
          { "$fn": "LENGTH", "args": ["d.message"] },
          "GT",
          100
        ],
        ["d.alertLevel", "LTE", 2]
      ]
    }
  ]
}
```

#### 3.3.4 使用约束

1. `<alias>.<field>` 中的 alias 必须引用当前层对象 alias 或关系 alias。
2. `IN` / `NOT_IN` 的第 3 槽必须为数组。
3. `BETWEEN` 的第 3 槽必须为长度 2 的数组。
4. `IS_NULL` / `IS_NOT_NULL` 不得出现第 3 槽。
5. `all` / `any` 的值必须为非空数组。
6. `not` 的值必须是单个合法条件节点。

---

### 3.4 `returns`：返回定义

`returns` 统一采用固定元组数组写法。

#### 3.4.1 元组类型

| 类型 | 结构 | 说明 |
| --- | --- | --- |
| `FIELDS` | `["FIELDS", "<ref>", ["field1", "field2", "..."]]` | 返回字段列表 |
| `EXPR` | `["EXPR", <Expr>, "<alias>"]` | 返回派生表达式列 |
| `GROUP_BY` | `["GROUP_BY", "<ref>.<field>" \| <Expr>, "<alias>"]` | 定义分组键 |
| `METRIC` | `["METRIC", "<function>", "<ref>.<field|*>", "<alias>"]` | 定义聚合指标 |

#### 3.4.2 示例

普通查询：

```json
"returns": [
  ["FIELDS", "o", ["id", "orderNo", "amount", "status"]]
]
```

带派生列：

```json
"returns": [
  ["FIELDS", "o", ["id", "orderNo", "amount"]],
  ["EXPR", { "$fn": "ABS", "args": ["o.deltaAmount"] }, "absDeltaAmount"]
]
```

聚合查询：

```json
"returns": [
  ["GROUP_BY", "o.region", "region"],
  ["METRIC", "SUM", "o.amount", "totalAmount"],
  ["METRIC", "COUNT", "o.*", "orderCount"]
]
```

#### 3.4.3 使用约束

1. `FIELDS` 只能用于 `QUERY`、`ASSOCIATION_QUERY`、`LINK_QUERY`。
2. `FIELDS` 的字段必须显式列出，且不允许 `*`。
3. `EXPR` 必须显式声明结果别名。
4. `GROUP_BY` 与 `METRIC` 必须显式声明结果别名。
5. `COUNT` 允许 `<ref>.*`；其他聚合函数不允许 `*`。
6. `EXPR` 中不得直接使用聚合函数；聚合函数必须通过 `METRIC` 表达。
7. `AGGREGATE` 中只允许 `GROUP_BY` 与 `METRIC`。

---

### 3.5 `orders`：排序定义

`orders` 统一采用固定元组数组写法。

#### 3.5.1 最终写法

```json
"orders": [
  ["ORDER_BY", "o", "createdAt", "DESC"],
  ["ORDER_BY", "o", "orderNo", "ASC"]
]
```

#### 3.5.2 槽位定义

| 位置 | 含义 | 必填 |
| --- | --- | :--: |
| 第 1 槽 | 固定为 `ORDER_BY` | 是 |
| 第 2 槽 | `ref` | 是 |
| 第 3 槽 | `field` | 是 |
| 第 4 槽 | `direction` | 是 |

#### 3.5.3 使用约束

1. `ref` 必须引用当前层对象 alias。
2. `field` 可为对象逻辑字段名，也可为 `returns` 中已定义的结果别名。
3. `direction` 仅允许 `ASC` / `DESC`。
4. 多个排序条件按数组顺序生效。

---

### 3.6 `sourceQuery`：子查询

`sourceQuery` 表示当前层依赖的中间结果集，而不仅是语法级子查询。

#### 3.6.1 字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `outputAs` | string | 是 | 子查询输出别名 |
| `operation` | enum | 是 | `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` |
| `objects` | array | 是 | 子查询对象声明 |
| `relationships` | array | 条件必填 | 子查询为 `ASSOCIATION_QUERY` 时必填 |
| `conditions` | array\|object | 否 | 子查询条件 |
| `returns` | array | 是 | 子查询返回定义 |
| `orders` | array | 否 | 子查询排序 |
| `maxResults` | integer | 否 | 子查询最大返回数 |
| `sourceQuery` | array | 否 | 嵌套子查询 |

#### 3.6.2 使用约束

1. `outputAs` 在同层必须唯一。
2. `sourceQuery` 不允许引用外层 alias。
3. 在 `strict=true` 时，最大嵌套深度为 2。
4. `sourceQuery` 只允许出现在查询类操作中。
5. 其内部若出现 `conditions`、`returns`、`orders`、`mutation`，必须继续使用本规范最终写法。

---

### 3.7 `linkQuery`：一跳关联参数

`linkQuery` 仅用于 `LINK_QUERY`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `mode` | enum | 是 | `LIST` / `ONE` |
| `relationshipType` | string | 是 | 关系类型 |
| `sourceRef` | string | 是 | 源对象 alias |
| `targetRef` | string | 是 | 目标对象 alias |
| `direction` | enum | 否 | `OUTBOUND` / `INBOUND` / `BIDIRECTIONAL`，默认 `OUTBOUND` |

#### 使用约束

1. `LINK_QUERY` 顶层 `objects` 必须恰好声明 2 个对象。
2. `sourceRef` / `targetRef` 必须引用当前层对象 alias。
3. `mode = ONE` 时，结果必须恰好 1 条，否则返回错误。
4. `LINK_QUERY` 不使用 `relationships`。

---

### 3.8 `mutation`：写操作块

#### 3.8.1 结构

`CREATE` / `UPSERT`：

```json
"mutation": {
  "data": {
    "name": "value",
    "createdAt": { "$fn": "NOW" }
  }
}
```

`UPDATE`：

```json
"mutation": {
  "scope": "ONE",
  "set": {
    "status": "paid"
  }
}
```

`DELETE`：

```json
"mutation": {
  "scope": "ONE"
}
```

`UPSERT`：

```json
"mutation": {
  "matchBy": ["sourceSystem", "orderNo"],
  "data": {
    "sourceSystem": "ERP",
    "orderNo": "ORD-001",
    "status": "paid"
  }
}
```

`BATCH`：

```json
"mutation": {
  "atomic": true,
  "items": [...]
}
```

#### 3.8.2 使用约束

1. `CREATE` 与 `UPSERT` 中，`mutation.data` 必须非空。
2. `UPDATE` 中，`mutation.scope` 与 `mutation.set` 必须同时出现。
3. `DELETE` 中，只允许出现 `mutation.scope`。
4. `UPSERT` 中，`mutation.matchBy` 必须非空，且列出的字段必须全部出现在 `mutation.data` 中。
5. `BATCH.items[]` 子项继续复用本规范中的最终写法。
6. `BATCH.items[]` 不允许 `BATCH`。

---

### 3.9 值表达式与内置函数

值表达式统一允许三类形态：

1. 字面量值
2. 字段引用：`"<ref>.<field>"`
3. 函数表达式：`{ "$fn": "<name>", "args": [...] }`

#### 示例

字段引用：

```json
"o.amount"
```

无参函数：

```json
{ "$fn": "NOW" }
```

带参数函数：

```json
{ "$fn": "ABS", "args": ["o.deltaAmount"] }
```

嵌套函数：

```json
{
  "$fn": "COALESCE",
  "args": [
    { "$fn": "TRIM", "args": ["o.customerName"] },
    "unknown"
  ]
}
```

#### 使用约束

1. `conditions` 的左值与右值都允许使用函数表达式。
2. `returns` 中 `EXPR` 与函数型 `GROUP_BY` 允许使用函数表达式。
3. `mutation.data` 与 `mutation.set` 允许使用函数表达式。
4. 聚合函数不通过 `"$fn"` 表达，仍通过 `METRIC` 表达。

---

## 4. 各 operation 规范

### 4.1 `QUERY`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [["Order", "o"]],
  "returns": [["FIELDS", "o", ["id", "orderNo"]]]
}
```

#### 约束

1. `objects` 必须非空。
2. `returns` 必须非空，且至少包含一个 `FIELDS`。
3. 不得出现 `relationships`、`linkQuery`、`mutation`。
4. 多对象联合查询时，联合语义必须通过 `conditions` 显式表达。

---

### 4.2 `AGGREGATE`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [["Order", "o"]],
  "returns": [["METRIC", "COUNT", "o.*", "cnt"]]
}
```

#### 约束

1. `returns` 中至少包含一个 `METRIC`。
2. 只允许 `GROUP_BY` 与 `METRIC`。
3. 不得出现 `relationships`、`linkQuery`、`mutation`。

---

### 4.3 `ASSOCIATION_QUERY`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [["A", "a"], ["B", "b"]],
  "relationships": [["rel_ab", "r1", "a", "b"]],
  "returns": [["FIELDS", "b", ["id", "name"]]]
}
```

#### 约束

1. `objects` 必须非空。
2. `relationships` 必须非空。
3. `returns` 必须非空，且只允许 `FIELDS`。
4. 不得出现 `linkQuery`、`mutation`。

---

### 4.4 `LINK_QUERY`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [["Order", "o"], ["Invoice", "i"]],
  "conditions": ["o.orderNo", "EQ", "ORD-001"],
  "returns": [["FIELDS", "i", ["id", "invoiceNo"]]],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "has_invoice",
    "sourceRef": "o",
    "targetRef": "i"
  }
}
```

#### 约束

1. `objects` 必须且仅能为 2 个。
2. `conditions` 必须存在。
3. `returns` 必须存在，且只允许 `FIELDS`。
4. `linkQuery` 必须存在。
5. 不得出现 `relationships`、`mutation`。

---

### 4.5 `CREATE`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "CREATE",
  "objects": [["Product", "p"]],
  "mutation": {
    "data": {
      "name": "iPhone 16"
    }
  }
}
```

#### 约束

1. `objects` 必须且仅能为 1 个。
2. `mutation.data` 必须存在且非空。
3. 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

---

### 4.6 `UPDATE`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [["Product", "p"]],
  "conditions": ["p.id", "EQ", "prod_001"],
  "mutation": {
    "scope": "ONE",
    "set": {
      "price": 7999
    }
  }
}
```

#### 约束

1. `objects` 必须且仅能为 1 个。
2. `conditions` 必须存在。
3. `mutation.scope` 与 `mutation.set` 必须存在。
4. `mutation.scope` 仅允许 `ONE` / `MANY`。
5. 不得出现 `returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

---

### 4.7 `DELETE`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "DELETE",
  "objects": [["Order", "o"]],
  "conditions": ["o.orderNo", "EQ", "ORD-001"],
  "mutation": {
    "scope": "ONE"
  }
}
```

#### 约束

1. `objects` 必须且仅能为 1 个。
2. `conditions` 必须存在。
3. `mutation.scope` 必须存在，且仅允许 `ONE` / `MANY`。
4. 不得出现 `mutation.set`、`mutation.data`。
5. 不得出现 `returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

---

### 4.8 `UPSERT`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPSERT",
  "objects": [["Order", "o"]],
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "sourceSystem": "ERP",
      "orderNo": "ORD-001"
    }
  }
}
```

#### 约束

1. `objects` 必须且仅能为 1 个。
2. `mutation.matchBy` 必须非空。
3. `mutation.data` 必须非空。
4. `matchBy` 中列出的字段必须全部出现在 `mutation.data` 中。
5. 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

---

### 4.9 `BATCH`

#### 最小结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "CREATE",
        "objects": [["Product", "p"]],
        "mutation": {
          "data": {
            "name": "iPhone 16"
          }
        }
      }
    ]
  }
}
```

#### 约束

1. 顶层不得出现 `objects`、`conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
2. `mutation.atomic` 与 `mutation.items` 必须存在。
3. `mutation.items` 必须非空。
4. 子项不得为 `BATCH`。
5. 子项不再包含 `version`、`schemaRef`、`strict`；这些值继承外层。

---

## 5. S-OQL 到 canonical OQL 的转换逻辑

### 5.1 总原则

1. 最终输入统一采用本规范定义的 S-OQL。
2. 执行前必须转换为 canonical OQL。
3. `sourceQuery` 与 `BATCH.items[]` 必须递归进行相同转换。
4. 转换完成后不得残留 S-OQL 元组或 `"$fn"` 原样结构。

---

### 5.2 `objects` 转换

S-OQL：

```json
["Order", "o"]
```

canonical：

```json
{ "objectType": "Order", "alias": "o" }
```

S-OQL：

```json
["CompletedOrder", "co", "completed_orders"]
```

canonical：

```json
{ "objectType": "CompletedOrder", "alias": "co", "fromSource": "completed_orders" }
```

---

### 5.3 `relationships` 转换

S-OQL：

```json
["installed_on", "r1", "d", "s"]
```

canonical：

```json
{ "relationshipType": "installed_on", "alias": "r1", "from": "d", "to": "s" }
```

---

### 5.4 `conditions` 转换

#### 字段条件

S-OQL：

```json
["o.status", "EQ", "completed"]
```

canonical：

```json
{
  "kind": "PREDICATE",
  "ref": "o",
  "field": "status",
  "operator": "EQ",
  "values": ["completed"]
}
```

#### 函数条件

S-OQL：

```json
[
  { "$fn": "ABS", "args": ["o.deltaAmount"] },
  "GT",
  10
]
```

canonical：

```json
{
  "kind": "PREDICATE",
  "expr": {
    "kind": "FUNCTION",
    "name": "ABS",
    "args": [
      { "kind": "FIELD_REF", "ref": "o", "field": "deltaAmount" }
    ]
  },
  "operator": "GT",
  "values": [10]
}
```

#### 逻辑组

S-OQL：

```json
{ "all": [["o.status", "EQ", "completed"], ["o.amount", "GTE", 1000]] }
```

canonical：

```json
{
  "kind": "GROUP",
  "relation": "AND",
  "children": [
    {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "amount",
      "operator": "GTE",
      "values": [1000]
    }
  ]
}
```

---

### 5.5 `returns` 转换

#### `FIELDS`

S-OQL：

```json
["FIELDS", "o", ["id", "orderNo"]]
```

canonical：

```json
{ "kind": "FIELDS", "ref": "o", "fields": ["id", "orderNo"] }
```

#### `EXPR`

S-OQL：

```json
["EXPR", { "$fn": "ABS", "args": ["o.deltaAmount"] }, "absDeltaAmount"]
```

canonical：

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "name": "ABS",
    "args": [
      { "kind": "FIELD_REF", "ref": "o", "field": "deltaAmount" }
    ]
  },
  "alias": "absDeltaAmount"
}
```

#### `GROUP_BY`

S-OQL：

```json
["GROUP_BY", "o.region", "region"]
```

canonical：

```json
{ "kind": "GROUP_BY", "ref": "o", "field": "region", "alias": "region" }
```

#### `METRIC`

S-OQL：

```json
["METRIC", "COUNT", "o.*", "orderCount"]
```

canonical：

```json
{ "kind": "METRIC", "ref": "o", "field": "*", "function": "COUNT", "alias": "orderCount" }
```

---

### 5.6 `orders` 转换

S-OQL：

```json
["ORDER_BY", "o", "createdAt", "DESC"]
```

canonical：

```json
{ "ref": "o", "field": "createdAt", "direction": "DESC" }
```

---

### 5.7 `mutation` 转换

#### `CREATE` / `UPSERT`

S-OQL：

```json
{
  "mutation": {
    "data": {
      "name": "iPhone 16",
      "price": 8999
    }
  }
}
```

canonical：

```json
{
  "mutation": {
    "data": {
      "properties": {
        "name": "iPhone 16",
        "price": 8999
      }
    }
  }
}
```

#### `UPDATE` / `DELETE`

`scope` 与 `set` 结构保持不变，只做递归值表达式转换。

#### `BATCH`

`BATCH` 顶层结构不变，但 `items[]` 中每个子项都要递归执行本章相同转换。

---

## 6. 校验与错误

### 6.1 校验阶段

1. 结构校验：顶层字段、类型、枚举、最小槽位。
2. 引用校验：alias、`from` / `to`、`sourceRef` / `targetRef`、`fromSource`。
3. 语义校验：operation 与专用块是否匹配。
4. 执行期校验：唯一性、存在性、后端执行失败等。

### 6.2 通用校验约束

1. `version`、`schemaRef`、`operation` 必须存在。
2. `objects[].alias` 在当前层必须唯一。
3. `relationships[].alias` 在当前层必须唯一，且不得与对象 alias 冲突。
4. 所有 `ref` / `from` / `to` / `sourceRef` / `targetRef` 必须引用当前层已声明 alias。
5. `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `LINK_QUERY` 必须包含非空 `returns`。
6. `UPDATE` / `DELETE` 必须包含 `conditions`。
7. `CREATE` / `UPSERT` 不得包含 `conditions`。
8. `UPSERT.matchBy` 中字段必须全部出现在 `mutation.data` 中。
9. `maxResults` 范围为 `1` 到 `100000`。
10. `sourceQuery` 在 `strict=true` 时最大嵌套深度为 2。
11. `BATCH.items[]` 必须非空，且子项不得为 `BATCH`。
12. `LINK_QUERY.mode = ONE` 时，结果必须恰好一条。

### 6.3 错误分类

| 分类 | 说明 |
| --- | --- |
| `VALIDATION_ERROR` | 结构、类型、枚举、必填项错误 |
| `REFERENCE_ERROR` | alias、source、返回别名等引用错误 |
| `SEMANTIC_ERROR` | 操作语义不成立 |
| `EXECUTION_ERROR` | 执行阶段失败 |
| `INTERNAL_ERROR` | 执行器内部异常 |

### 6.4 常用错误码

| 错误码 | 说明 |
| --- | --- |
| `MISSING_REQUIRED_FIELD` | 缺少必填字段 |
| `INVALID_FIELD` | 出现未知字段或不允许字段 |
| `INVALID_FIELD_TYPE` | 字段类型错误 |
| `INVALID_ENUM_VALUE` | 枚举值非法 |
| `UNDECLARED_ALIAS` | 引用了未声明 alias |
| `DUPLICATE_ALIAS` | alias 重复声明 |
| `INVALID_SOURCE_REFERENCE` | `fromSource` 或 `outputAs` 引用非法 |
| `INVALID_RELATION_ENDPOINT` | `relationships.from` / `to` 非法 |
| `INVALID_LINK_REFERENCE` | `linkQuery.sourceRef` / `targetRef` 非法 |
| `INVALID_OPERATION_FIELD` | 当前 operation 不允许出现某字段 |
| `INVALID_OBJECT_COUNT` | 当前 operation 的 `objects` 数量非法 |
| `MISSING_CONDITIONS` | 缺少必须提供的 `conditions` |
| `CONDITIONS_NOT_ALLOWED` | 当前 operation 不允许提供 `conditions` |
| `MISSING_METRIC` | `AGGREGATE` 缺少 `METRIC` |
| `INVALID_SCOPE` | `scope` 非法或与操作不匹配 |
| `MATCH_BY_FIELD_MISSING` | `matchBy` 字段未出现在 `mutation.data` 中 |
| `NESTED_BATCH_NOT_ALLOWED` | 不允许嵌套 `BATCH` |
| `NON_UNIQUE_RESULT` | 期望唯一结果却匹配多条 |
| `NO_RESULT` | 期望唯一结果却没有匹配 |
| `TIMEOUT` | 执行超时 |
| `BACKEND_UNAVAILABLE` | 后端不可用 |

### 6.5 标准错误响应

```json
{
  "success": false,
  "operation": "QUERY",
  "errors": [
    {
      "code": "MISSING_REQUIRED_FIELD",
      "category": "VALIDATION_ERROR",
      "message": "Missing required field: returns",
      "path": "$.returns"
    }
  ],
  "trace": {
    "executionTimeMs": 3,
    "requestId": "req_1001"
  }
}
```

---

## 7. 代表性完整样例

### 7.1 普通查询

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [["Order", "o"]],
  "conditions": {
    "all": [
      ["o.status", "EQ", "completed"],
      ["o.amount", "GTE", 1000]
    ]
  },
  "returns": [
    ["FIELDS", "o", ["id", "orderNo", "amount", "status"]],
    ["EXPR", { "$fn": "ABS", "args": ["o.deltaAmount"] }, "absDeltaAmount"]
  ],
  "orders": [
    ["ORDER_BY", "o", "createdAt", "DESC"]
  ],
  "maxResults": 1000
}
```

### 7.2 聚合查询

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [["Order", "o"]],
  "conditions": ["o.status", "EQ", "completed"],
  "returns": [
    ["GROUP_BY", "o.region", "region"],
    ["METRIC", "SUM", "o.amount", "totalAmount"],
    ["METRIC", "COUNT", "o.*", "orderCount"]
  ],
  "orders": [
    ["ORDER_BY", "o", "totalAmount", "DESC"]
  ],
  "maxResults": 1000
}
```

### 7.3 多跳关联查询

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    ["Device", "d"],
    ["Server", "s"],
    ["DataCenter", "dc"]
  ],
  "relationships": [
    ["installed_on", "r1", "d", "s"],
    ["deployed_in", "r2", "s", "dc"]
  ],
  "conditions": {
    "all": [
      ["d.status", "EQ", "running"],
      ["dc.region", "EQ", "华东"]
    ]
  },
  "returns": [
    ["FIELDS", "d", ["id", "name", "status"]],
    ["FIELDS", "s", ["id", "hostname"]],
    ["FIELDS", "dc", ["id", "name", "region"]]
  ],
  "maxResults": 5000
}
```

### 7.4 一跳关联查询

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    ["Order", "o"],
    ["Invoice", "i"]
  ],
  "conditions": ["o.orderNo", "EQ", "ORD-20240301-001"],
  "returns": [
    ["FIELDS", "i", ["id", "invoiceNo", "amount", "status"]]
  ],
  "linkQuery": {
    "mode": "ONE",
    "relationshipType": "has_invoice",
    "sourceRef": "o",
    "targetRef": "i",
    "direction": "OUTBOUND"
  },
  "maxResults": 1
}
```

### 7.5 创建

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
  "strict": true,
  "operation": "CREATE",
  "objects": [["Product", "p"]],
  "mutation": {
    "data": {
      "name": "iPhone 16",
      "price": 8999,
      "createdAt": { "$fn": "NOW" }
    }
  }
}
```

### 7.6 更新

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
  "strict": true,
  "operation": "UPDATE",
  "objects": [["Product", "p"]],
  "conditions": ["p.id", "EQ", "prod_001"],
  "mutation": {
    "scope": "ONE",
    "set": {
      "price": 7999,
      "updatedAt": { "$fn": "NOW" }
    }
  }
}
```

### 7.7 删除

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "DELETE",
  "objects": [["Order", "o"]],
  "conditions": ["o.orderNo", "EQ", "ORD-20240301-001"],
  "mutation": {
    "scope": "ONE"
  }
}
```

### 7.8 UPSERT

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "UPSERT",
  "objects": [["Order", "o"]],
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "sourceSystem": "ERP",
      "orderNo": "ORD-20240301-001",
      "status": "shipped",
      "amount": 19999
    }
  }
}
```

### 7.9 BATCH

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
        "objects": [["Order", "o"]],
        "conditions": ["o.orderNo", "EQ", "ORD-20240301-001"],
        "mutation": {
          "scope": "ONE",
          "set": {
            "status": "paid",
            "paidAt": { "$fn": "NOW" }
          }
        }
      },
      {
        "operation": "CREATE",
        "objects": [["Invoice", "i"]],
        "mutation": {
          "data": {
            "invoiceNo": "INV-20240301-001",
            "orderNo": "ORD-20240301-001",
            "amount": 19999
          }
        }
      }
    ]
  }
}
```