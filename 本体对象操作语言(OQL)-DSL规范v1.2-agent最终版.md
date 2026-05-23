# 本体对象操作语言（OQL）DSL 规范 v1.2 - Agent 最终版

> 本文档定义面向 Agent / 大模型直接生成的 canonical OQL 规范。Agent 不再先生成中间简化语法，也不再依赖二次转换层；应直接输出可校验、可解释、可执行的 OQL JSON。
>
> 本版本已将历史 `LINK_QUERY` 合并到 `ASSOCIATION_QUERY`。一跳关系导航是关系路径长度为 1 的特例，统一通过 `relationships` 表达。`LINK_QUERY` 与 `linkQuery` 仅作为历史兼容输入，不属于 canonical OQL 标准输出。

---

## 0. 本次修订说明

| 修订项 | 处理方式 |
| --- | --- |
| `LINK_QUERY` | 从 canonical operation 中移除，仅保留历史兼容说明 |
| `linkQuery` | 从顶层标准结构中移除，历史请求由 Builder / Validator 归一化 |
| 一跳关系导航 | 统一使用 `ASSOCIATION_QUERY + relationships[0]` 表达 |
| `relationships` | 增加 `direction` 与 `mode`，覆盖原 `linkQuery.direction` 与 `linkQuery.mode` |
| Agent 生成规则 | 禁止新生成 `LINK_QUERY` 和 `linkQuery` |

---

## 1. 定位与设计原则

### 1.1 定位

OQL（Ontology Query Language）是面向本体对象模型的声明式逻辑查询与操作语言，用于表达：

- 查询或操作哪些本体对象；
- 对象之间有哪些逻辑关系；
- 需要满足哪些筛选条件；
- 需要返回哪些字段、表达式或聚合指标；
- 需要执行哪些创建、更新、删除或批处理动作。

OQL 不直接面向物理表、物理列或数据库方言。执行时由 OAC（Ontology Access）负责根据本体模型、映射信息和数据源能力，完成绑定、校验、翻译、执行和结果装配。

### 1.2 面向 Agent 的核心原则

1. **直接生成 canonical OQL**：Agent 输出的 JSON 即为标准 OQL，不使用中间简化层。
2. **命名字段优先**：所有关键语义通过字段名表达，避免依赖数组槽位位置。
3. **对象中心**：围绕 `objects`、`relationships`、`conditions`、`returns`、`mutation` 表达逻辑意图。
4. **引用闭包**：所有 `ref`、`sourceRef`、`targetRef`、`from`、`to` 必须引用当前层已声明 alias。
5. **结构可校验**：生成后必须能通过结构校验、引用校验、操作约束校验和执行期语义校验。
6. **字段显式**：返回字段、排序字段、更新字段必须显式列出，不使用隐式 `*`，除 `COUNT` 指标允许 `field = "*"`。
7. **省略未使用字段**：不得输出 `null`、空对象或空数组占位。
8. **查询与写入分离**：查询类操作不得出现 `mutation`；写入类操作不得混入返回、排序或关系路径字段，除非本规范明确允许。
9. **关系查询统一入口**：对象关系、路径关联、一跳关系导航均使用 `ASSOCIATION_QUERY`。

### 1.3 不再使用中间转换层的原因

面向 Agent 时，OQL 比压缩式中间语法更稳定，原因是：

1. OQL 使用命名字段表达语义，减少位置错位。
2. OQL 能直接暴露 `kind`、`ref`、`field`、`operator`、`relation` 等结构信息，便于模型自检。
3. 嵌套查询、批处理、表达式和关联路径在 OQL 中更容易保持引用闭包。
4. 校验错误可以定位到具体字段路径，便于 Agent 修复。
5. 取消“先生成中间语法再转换”的链路后，减少语义损耗和转换误差。

---

## 2. 顶层结构

### 2.1 标准结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [],
  "relationships": [],
  "conditions": {},
  "returns": [],
  "orders": [],
  "maxResults": 1000,
  "sourceQuery": [],
  "mutation": {},
  "options": {},
  "extensions": {}
}
```

上面仅展示全部可能字段。实际生成时必须省略未使用字段。

`linkQuery` 为历史兼容字段，不属于 canonical OQL 标准输出字段；Agent 不得新生成。

### 2.2 推荐字段顺序

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
mutation
options
extensions
```

### 2.3 顶层字段定义

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `version` | string | 是 | 固定为 `1.0` |
| `schemaRef` | string | 是 | 本次请求绑定的本体 schema 标识 |
| `strict` | boolean | 否 | 是否启用严格校验，默认 `true` |
| `operation` | enum | 是 | `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `CREATE` / `UPDATE` / `DELETE` / `UPSERT` / `BATCH` |
| `objects` | array | 条件必填 | 对象声明 |
| `relationships` | array | 条件必填 | 关系路径声明，仅 `ASSOCIATION_QUERY` 使用；一跳关系导航也通过该字段表达 |
| `conditions` | object | 条件必填 | 条件树；`UPDATE` / `DELETE` 必填 |
| `returns` | array | 条件必填 | 返回定义；查询类操作必填 |
| `orders` | array | 否 | 排序定义 |
| `maxResults` | integer | 否 | 最大返回数量，默认 `1000`，最大 `100000` |
| `sourceQuery` | array | 否 | 中间结果查询，仅查询类操作使用 |
| `mutation` | object | 条件必填 | 写操作专用参数块 |
| `options` | object | 否 | 执行选项 |
| `extensions` | object | 否 | 扩展字段，无明确约定时省略 |

兼容说明：`LINK_QUERY` 与 `linkQuery` 仅用于接收旧版请求。规范化后必须转换为 `ASSOCIATION_QUERY + relationships`，canonical OQL 不得输出 `LINK_QUERY` 或 `linkQuery`。

---

## 3. 通用模块

### 3.1 `objects`：对象声明

`objects` 只声明参与请求的对象类型和别名，不承担实例定位职责。

```json
"objects": [
  {
    "objectType": "Order",
    "alias": "o"
  }
]
```

使用中间结果作为对象来源：

```json
"objects": [
  {
    "objectType": "CompletedOrder",
    "alias": "co",
    "fromSource": "completed_orders"
  }
]
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `objectType` | string | 是 | 本体对象类型 |
| `alias` | string | 是 | 当前请求层内唯一别名 |
| `fromSource` | string | 否 | 引用同层 `sourceQuery[].outputAs` |

约束：

1. `alias` 在当前层必须唯一。
2. `fromSource` 只能引用同层 `sourceQuery[].outputAs`。
3. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 中 `objects` 必须且仅有一个对象。
4. `ASSOCIATION_QUERY` 中 `objects` 必须覆盖 `relationships[].from` / `relationships[].to` 引用到的全部对象 alias。
5. 一跳关系导航场景通常包含两个对象；多跳路径关联场景可以包含两个及以上对象。
6. `BATCH` 顶层不得出现 `objects`。

### 3.2 `relationships`：关系路径声明

`relationships` 仅用于 `ASSOCIATION_QUERY`，用于显式声明对象之间的关系路径。数组顺序即路径顺序。

一跳关系导航也必须通过 `relationships` 表达，表现为 `relationships` 数组中只有一条关系。

```json
"relationships": [
  {
    "relationshipType": "installed_on",
    "alias": "r1",
    "from": "d",
    "to": "s",
    "direction": "OUTBOUND",
    "mode": "LIST"
  },
  {
    "relationshipType": "deployed_in",
    "alias": "r2",
    "from": "s",
    "to": "dc",
    "direction": "OUTBOUND"
  }
]
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `relationshipType` | string | 是 | 本体关系类型 |
| `alias` | string | 是 | 关系别名 |
| `from` | string | 是 | 起点对象 alias |
| `to` | string | 是 | 终点对象 alias |
| `direction` | enum | 否 | `OUTBOUND` / `INBOUND` / `BIDIRECTIONAL`，默认 `OUTBOUND` |
| `mode` | enum | 否 | `LIST` / `ONE`，默认 `LIST`；由原 `linkQuery.mode` 合并而来，用于声明该关系的结果期望 |

约束：

1. `from` / `to` 必须引用当前层 `objects[].alias`。
2. 关系 alias 不得与对象 alias 冲突。
3. `relationships` 仅允许出现在 `ASSOCIATION_QUERY` 中。
4. `relationships` 至少包含一条关系。
5. 一跳关系导航使用单条 `relationships` 表达。
6. 多跳路径关联按数组顺序表达路径。
7. `mode = ONE` 时，该关系扩展结果必须恰好一条，否则应返回错误。

### 3.3 表达式 `Expr`

表达式用于条件、返回派生列、函数型分组、写入值等位置。

字段表达式：

```json
{
  "kind": "FIELD",
  "ref": "o",
  "field": "amount"
}
```

字面量表达式：

```json
{
  "kind": "VALUE",
  "value": 100
}
```

函数表达式：

```json
{
  "kind": "FUNCTION",
  "name": "ABS",
  "args": [
    {
      "kind": "FIELD",
      "ref": "o",
      "field": "deltaAmount"
    }
  ]
}
```

内置函数名称建议使用大写。常见函数包括：

- 数值：`ABS`、`ROUND`、`CEIL`、`FLOOR`
- 字符串：`LENGTH`、`LOWER`、`UPPER`、`TRIM`、`SUBSTRING`
- 时间：`NOW`、`DATE_TRUNC`、`YEAR`、`MONTH`、`DAY`
- 空值处理：`COALESCE`、`IFNULL`

聚合函数不使用 `Expr` 表达，必须通过 `returns.kind = "METRIC"` 表达。

### 3.4 `conditions`：条件树

字段条件：

```json
"conditions": {
  "kind": "PREDICATE",
  "ref": "o",
  "field": "status",
  "operator": "EQ",
  "values": ["completed"]
}
```

表达式条件：

```json
"conditions": {
  "kind": "PREDICATE",
  "left": {
    "kind": "FUNCTION",
    "name": "LENGTH",
    "args": [
      {
        "kind": "FIELD",
        "ref": "o",
        "field": "comment"
      }
    ]
  },
  "operator": "GT",
  "values": [100]
}
```

逻辑组：

```json
"conditions": {
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

字段说明：

| 字段 | 说明 |
| --- | --- |
| `kind` | `PREDICATE` 或 `GROUP` |
| `ref` / `field` | 字段条件左值；适用于普通字段条件 |
| `left` | 表达式条件左值；与 `ref` / `field` 二选一 |
| `operator` | 条件操作符 |
| `values` | 条件右值数组；可包含字面量或 `Expr` |
| `relation` | `AND` / `OR` / `NOT` |
| `children` | 子条件数组 |

操作符：`EQ` / `NE` / `GT` / `GTE` / `LT` / `LTE` / `IN` / `NOT_IN` / `BETWEEN` / `LIKE` / `CONTAINS` / `STARTS_WITH` / `ENDS_WITH` / `IS_NULL` / `IS_NOT_NULL`。

约束：

1. `PREDICATE` 必须使用 `ref + field` 或 `left` 表达左值。
2. `ref` 必须引用当前层对象 alias 或关系 alias。
3. `BETWEEN` 的 `values` 必须恰好包含两个值。
4. `IS_NULL` / `IS_NOT_NULL` 不得包含 `values`。
5. `GROUP.relation = NOT` 时，`children` 必须且仅有一个子条件。
6. `GROUP.children` 必须非空。

### 3.5 `returns`：返回定义

字段返回：

```json
{
  "kind": "FIELDS",
  "ref": "o",
  "fields": ["id", "orderNo", "amount", "status"]
}
```

派生表达式返回：

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "name": "ABS",
    "args": [
      {
        "kind": "FIELD",
        "ref": "o",
        "field": "deltaAmount"
      }
    ]
  },
  "alias": "absDeltaAmount"
}
```

分组字段：

```json
{
  "kind": "GROUP_BY",
  "ref": "o",
  "field": "region",
  "alias": "region"
}
```

聚合指标：

```json
{
  "kind": "METRIC",
  "function": "COUNT",
  "ref": "o",
  "field": "*",
  "alias": "orderCount"
}
```

约束：

1. `QUERY`、`ASSOCIATION_QUERY` 允许 `FIELDS` 和 `EXPR`。
2. `AGGREGATE` 只允许 `GROUP_BY` 和 `METRIC`。
3. `FIELDS.fields` 必须显式列出，不允许 `*`。
4. `EXPR`、`GROUP_BY`、`METRIC` 必须声明 `alias`。
5. `COUNT` 允许 `field = "*"`，其他聚合函数不允许 `*`。
6. 聚合函数仅允许 `COUNT`、`SUM`、`AVG`、`MIN`、`MAX`。

### 3.6 `orders`：排序定义

```json
"orders": [
  {
    "ref": "o",
    "field": "createdAt",
    "direction": "DESC"
  }
]
```

约束：

1. `direction` 只能为 `ASC` 或 `DESC`。
2. 普通查询排序字段必须可从对象字段或返回字段解释。
3. 聚合查询排序字段优先引用 `returns.alias`。
4. 多个排序条件按数组顺序生效。

### 3.7 `sourceQuery`：中间结果查询

`sourceQuery` 用于先生成中间结果，再让当前层对象通过 `fromSource` 引用。

```json
"sourceQuery": [
  {
    "outputAs": "completed_orders",
    "operation": "QUERY",
    "objects": [
      {
        "objectType": "Order",
        "alias": "o"
      }
    ],
    "conditions": {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    "returns": [
      {
        "kind": "FIELDS",
        "ref": "o",
        "fields": ["id", "customerId", "amount"]
      }
    ]
  }
]
```

约束：

1. `outputAs` 在同层必须唯一。
2. `sourceQuery` 只能用于查询类操作。
3. `sourceQuery` 内部必须继续使用 canonical OQL。
4. `sourceQuery` 不允许引用外层 alias。
5. `strict = true` 时，建议最大嵌套深度为 2。

### 3.8 `linkQuery`：历史兼容字段（Deprecated）

`linkQuery` 已合并到 `relationships`，不再作为 canonical OQL 标准字段。

旧版 `LINK_QUERY` 请求可在兼容期继续被解析，但必须在 Builder / Validator 阶段归一化为 `ASSOCIATION_QUERY`。

兼容转换规则：

```json
{
  "operation": "LINK_QUERY",
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "has_invoice",
    "sourceRef": "o",
    "targetRef": "i",
    "direction": "OUTBOUND"
  }
}
```

等价转换为：

```json
{
  "operation": "ASSOCIATION_QUERY",
  "relationships": [
    {
      "relationshipType": "has_invoice",
      "alias": "r1",
      "from": "o",
      "to": "i",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ]
}
```

兼容约束：

1. Agent 不得新生成 `LINK_QUERY`。
2. Agent 不得新生成 `linkQuery`。
3. 接收到历史 `LINK_QUERY` 时，Builder 应自动转换为 `ASSOCIATION_QUERY`。
4. 转换后必须移除 `linkQuery` 字段。
5. 转换时应返回 deprecated warning，例如：`LINK_QUERY is deprecated; use ASSOCIATION_QUERY with relationships instead.`

### 3.9 `mutation`：写操作参数

#### 3.9.1 `CREATE`

```json
"mutation": {
  "data": {
    "properties": {
      "name": "iPhone 16",
      "createdAt": {
        "kind": "FUNCTION",
        "name": "NOW",
        "args": []
      }
    }
  }
}
```

#### 3.9.2 `UPDATE`

```json
"mutation": {
  "scope": "ONE",
  "set": {
    "status": "paid",
    "updatedAt": {
      "kind": "FUNCTION",
      "name": "NOW",
      "args": []
    }
  }
}
```

#### 3.9.3 `DELETE`

```json
"mutation": {
  "scope": "ONE"
}
```

#### 3.9.4 `UPSERT`

```json
"mutation": {
  "matchBy": ["sourceSystem", "orderNo"],
  "data": {
    "properties": {
      "sourceSystem": "ERP",
      "orderNo": "ORD-001",
      "status": "paid"
    }
  }
}
```

#### 3.9.5 `BATCH`

```json
"mutation": {
  "atomic": true,
  "items": []
}
```

约束：

1. `CREATE` 与 `UPSERT` 必须使用 `mutation.data.properties`。
2. `UPDATE` 必须包含 `mutation.scope` 与非空 `mutation.set`。
3. `DELETE` 只能包含删除范围相关字段，不得出现 `set` 或 `data`。
4. `UPSERT.matchBy` 必须非空，且其中每个字段都必须出现在 `data.properties` 中。
5. `BATCH.items[]` 内部子请求使用 canonical OQL，且不得嵌套 `BATCH`。
6. `BATCH.items[]` 不包含 `version`、`schemaRef`、`strict`，这些值继承外层。

---

## 4. Operation 规范

### 4.1 `QUERY`：普通对象查询

```json
{
  "version": "1.0",
  "schemaRef": "sales-v1",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount", "status"]
    }
  ],
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    }
  ],
  "maxResults": 100
}
```

约束：

1. 必须包含 `objects` 与 `returns`。
2. 不得出现 `relationships`、`linkQuery`、`mutation`。
3. 多对象查询必须用 `conditions` 明确对象之间的关联条件。

### 4.2 `AGGREGATE`：聚合查询

```json
{
  "version": "1.0",
  "schemaRef": "sales-v1",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "o",
      "field": "region",
      "alias": "region"
    },
    {
      "kind": "METRIC",
      "function": "SUM",
      "ref": "o",
      "field": "amount",
      "alias": "totalAmount"
    }
  ]
}
```

约束：

1. `returns` 至少包含一个 `METRIC`。
2. `returns` 只允许 `GROUP_BY` 与 `METRIC`。
3. 不得出现 `relationships`、`linkQuery`、`mutation`。

### 4.3 `ASSOCIATION_QUERY`：对象关系 / 路径关联查询

`ASSOCIATION_QUERY` 用于表达对象之间的关系查询，包括：

1. 一跳关系导航；
2. 多跳路径关联；
3. 明确关系类型、方向和路径顺序的关联查询。

#### 4.3.1 一跳关系导航示例

```json
{
  "version": "1.0",
  "schemaRef": "sales-v1",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    },
    {
      "objectType": "Invoice",
      "alias": "i"
    }
  ],
  "relationships": [
    {
      "relationshipType": "has_invoice",
      "alias": "r1",
      "from": "o",
      "to": "i",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "orderNo",
    "operator": "EQ",
    "values": ["ORD-001"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "i",
      "fields": ["id", "invoiceNo", "amount"]
    }
  ]
}
```

#### 4.3.2 多跳路径关联示例

```json
{
  "version": "1.0",
  "schemaRef": "infra-v1",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    },
    {
      "objectType": "Service",
      "alias": "s"
    },
    {
      "objectType": "DataCenter",
      "alias": "dc"
    }
  ],
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s",
      "direction": "OUTBOUND"
    },
    {
      "relationshipType": "deployed_in",
      "alias": "r2",
      "from": "s",
      "to": "dc",
      "direction": "OUTBOUND"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "d",
    "field": "status",
    "operator": "EQ",
    "values": ["running"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "dc",
      "fields": ["id", "name", "region"]
    }
  ]
}
```

约束：

1. 必须包含 `objects`、`relationships`、`returns`。
2. `relationships` 至少包含一条关系。
3. `relationships` 按路径顺序声明。
4. `relationships[].from` / `relationships[].to` 必须引用当前层 `objects[].alias`。
5. 不得出现 `linkQuery`、`mutation`。
6. 一跳关系导航不得使用 `LINK_QUERY`，必须使用 `ASSOCIATION_QUERY`。

### 4.4 `LINK_QUERY`：Deprecated

`LINK_QUERY` 已合并到 `ASSOCIATION_QUERY`，不再作为 canonical OQL 的标准 operation。

历史 `LINK_QUERY` 请求必须按以下规则转换：

| 原字段 | 新字段 |
| --- | --- |
| `operation = LINK_QUERY` | `operation = ASSOCIATION_QUERY` |
| `linkQuery.relationshipType` | `relationships[0].relationshipType` |
| `linkQuery.sourceRef` | `relationships[0].from` |
| `linkQuery.targetRef` | `relationships[0].to` |
| `linkQuery.direction` | `relationships[0].direction` |
| `linkQuery.mode` | `relationships[0].mode` |

Agent 不得新生成 `LINK_QUERY`。

### 4.5 `CREATE`：创建对象

```json
{
  "version": "1.0",
  "schemaRef": "catalog-v1",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "mutation": {
    "data": {
      "properties": {
        "name": "iPhone 16",
        "price": 7999,
        "createdAt": {
          "kind": "FUNCTION",
          "name": "NOW",
          "args": []
        }
      }
    }
  }
}
```

约束：

1. `objects` 必须且仅有一个。
2. `mutation.data.properties` 必须非空。
3. 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

### 4.6 `UPDATE`：更新对象

```json
{
  "version": "1.0",
  "schemaRef": "catalog-v1",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "p",
    "field": "id",
    "operator": "EQ",
    "values": ["prod_001"]
  },
  "mutation": {
    "scope": "ONE",
    "set": {
      "price": 6999,
      "updatedAt": {
        "kind": "FUNCTION",
        "name": "NOW",
        "args": []
      }
    }
  }
}
```

约束：

1. `objects` 必须且仅有一个。
2. 必须包含 `conditions`。
3. `mutation.scope` 只能为 `ONE` 或 `MANY`。
4. `mutation.set` 必须非空。
5. 不得出现 `returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

### 4.7 `DELETE`：删除对象

```json
{
  "version": "1.0",
  "schemaRef": "sales-v1",
  "strict": true,
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "orderNo",
    "operator": "EQ",
    "values": ["ORD-001"]
  },
  "mutation": {
    "scope": "ONE"
  }
}
```

约束：

1. `objects` 必须且仅有一个。
2. 必须包含 `conditions`。
3. `mutation.scope` 只能为 `ONE` 或 `MANY`。
4. 不得出现 `mutation.set`、`mutation.data`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
5. 当删除范围不明确时，Agent 必须请求用户补充条件，不得生成宽泛删除请求。

### 4.8 `UPSERT`：存在则更新，否则创建

```json
{
  "version": "1.0",
  "schemaRef": "sales-v1",
  "strict": true,
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "properties": {
        "sourceSystem": "ERP",
        "orderNo": "ORD-001",
        "status": "paid"
      }
    }
  }
}
```

约束：

1. `objects` 必须且仅有一个。
2. `mutation.matchBy` 必须非空。
3. `mutation.data.properties` 必须非空。
4. `matchBy` 中列出的字段必须全部出现在 `data.properties` 中。
5. 不得出现 `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。

### 4.9 `BATCH`：批处理

```json
{
  "version": "1.0",
  "schemaRef": "catalog-v1",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "CREATE",
        "objects": [
          {
            "objectType": "Product",
            "alias": "p1"
          }
        ],
        "mutation": {
          "data": {
            "properties": {
              "name": "Product A"
            }
          }
        }
      },
      {
        "operation": "UPDATE",
        "objects": [
          {
            "objectType": "Product",
            "alias": "p2"
          }
        ],
        "conditions": {
          "kind": "PREDICATE",
          "ref": "p2",
          "field": "id",
          "operator": "EQ",
          "values": ["prod_002"]
        },
        "mutation": {
          "scope": "ONE",
          "set": {
            "status": "active"
          }
        }
      }
    ]
  }
}
```

约束：

1. `BATCH` 顶层不得出现 `objects`、`conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`。
2. 必须包含 `mutation.atomic` 与非空 `mutation.items`。
3. 子项只允许 `CREATE` / `UPDATE` / `DELETE` / `UPSERT`。
4. 子项不得再使用 `BATCH`。
5. 子项不包含 `version`、`schemaRef`、`strict`。
6. 每个子项的 alias 引用只在子项内部闭包。

---

## 5. Agent 生成流程

### 5.1 生成步骤

1. 识别用户意图属于查询、聚合、对象关系/路径关联、创建、更新、删除、存在则更新或批处理；一跳关系导航归入对象关系/路径关联。
2. 选择唯一 `operation`。
3. 明确 `schemaRef`。
4. 声明参与对象与 alias。
5. 根据 operation 填写必要模块。
6. 使用 canonical OQL 对象结构直接生成 JSON。
7. 省略所有未使用字段。
8. 调用 builder 做字段顺序和默认值稳定化。
9. 调用 validator 做结构与引用校验。
10. 仅当用户明确要求执行且请求校验通过时，才进入执行。

### 5.2 缺失信息处理

当缺少必要信息时，不要猜测，应返回结构化错误：

```json
{
  "success": false,
  "errors": [
    {
      "code": "MISSING_REQUIRED_INFORMATION",
      "message": "缺少要查询的对象类型和返回字段。",
      "missing": ["objectType", "returns"]
    }
  ]
}
```

### 5.3 生成禁忌

1. 不输出 Markdown 包装的 JSON。
2. 不输出注释。
3. 不输出 `null` 字段。
4. 不输出空数组或空对象占位。
5. 不使用位置元组表达对象、关系、条件、返回或排序。
6. 不在查询操作中输出 `mutation`。
7. 不在写操作中输出 `returns` 或 `orders`，除非未来扩展明确允许。
8. 不跨 `sourceQuery` 层级引用 alias。
9. 不在 `BATCH.items[]` 中嵌套 `BATCH`。
10. 不伪造 schema 中不存在的对象、关系或字段。
11. 不生成 `LINK_QUERY`；一跳关系导航必须生成 `ASSOCIATION_QUERY`。
12. 不生成 `linkQuery`；关系类型、方向和返回模式必须通过 `relationships` 表达。

---

## 6. 校验规则摘要

### 6.1 通用校验

- `version` 必须为 `1.0`。
- `schemaRef` 必须非空。
- `operation` 必须为 canonical 合法枚举。
- canonical OQL 的 `operation` 不得为 `LINK_QUERY`。
- canonical OQL 顶层不得出现 `linkQuery`。
- 接收到历史 `LINK_QUERY` 时，应在兼容层转换为 `ASSOCIATION_QUERY` 后再执行标准校验。
- 顶层不得出现未知字段。
- 所有 alias 必须先声明后引用。
- 所有对象、关系、字段必须存在于绑定 schema。

### 6.2 条件校验

- `conditions.kind` 必须为 `PREDICATE` 或 `GROUP`。
- `PREDICATE` 必须有合法左值和合法操作符。
- `GROUP.children` 必须非空。
- `NOT` 组只能有一个子条件。
- 操作符与 `values` 个数必须匹配。

### 6.3 返回校验

- 查询类操作必须有 `returns`。
- `FIELDS.fields` 不得为空且不得包含 `*`。
- `EXPR.alias` 必须存在。
- `GROUP_BY.alias` 必须存在。
- `METRIC.alias` 必须存在。
- `AGGREGATE` 必须至少有一个 `METRIC`。

### 6.4 写入校验

- `CREATE` 必须有 `mutation.data.properties`。
- `UPDATE` 必须有 `conditions`、`mutation.scope`、`mutation.set`。
- `DELETE` 必须有 `conditions` 与 `mutation.scope`。
- `UPSERT` 必须有 `mutation.matchBy` 与 `mutation.data.properties`。
- `BATCH` 必须有 `mutation.atomic` 与非空 `mutation.items`。

### 6.5 历史兼容转换校验

兼容层接收到旧版 `LINK_QUERY` 时，应执行如下归一化：

```pseudo
if oql.operation == "LINK_QUERY":
    assert oql.linkQuery exists
    lq = oql.linkQuery

    oql.operation = "ASSOCIATION_QUERY"
    oql.relationships = [
        {
            "relationshipType": lq.relationshipType,
            "alias": generateRelationshipAlias(oql, "r"),
            "from": lq.sourceRef,
            "to": lq.targetRef,
            "direction": lq.direction or "OUTBOUND",
            "mode": lq.mode or "LIST"
        }
    ]

    remove oql.linkQuery

    addWarning(
        code = "DEPRECATED_OPERATION",
        message = "LINK_QUERY is deprecated; use ASSOCIATION_QUERY with relationships instead.",
        path = "operation"
    )
```

---

## 7. 错误返回格式

校验或执行失败时，建议统一返回：

```json
{
  "success": false,
  "errors": [
    {
      "code": "OQL_VALIDATION_ERROR",
      "message": "returns.ref must reference known alias: x",
      "path": "returns[0].ref",
      "details": {
        "ref": "x"
      }
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `success` | 固定为 `false` |
| `errors[].code` | 错误码 |
| `errors[].message` | 可读错误信息 |
| `errors[].path` | 错误字段路径 |
| `errors[].details` | 可选上下文 |

---

## 8. 附录：最小操作模板

### 8.1 QUERY

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [{"objectType": "<ObjectType>", "alias": "o"}],
  "returns": [{"kind": "FIELDS", "ref": "o", "fields": ["id"]}]
}
```

### 8.2 AGGREGATE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [{"objectType": "<ObjectType>", "alias": "o"}],
  "returns": [{"kind": "METRIC", "function": "COUNT", "ref": "o", "field": "*", "alias": "cnt"}]
}
```

### 8.3 ASSOCIATION_QUERY

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "<SourceObjectType>", "alias": "s"},
    {"objectType": "<TargetObjectType>", "alias": "t"}
  ],
  "relationships": [
    {
      "relationshipType": "<RelationshipType>",
      "alias": "r1",
      "from": "s",
      "to": "t",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ],
  "returns": [{"kind": "FIELDS", "ref": "t", "fields": ["id"]}]
}
```

### 8.4 CREATE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "CREATE",
  "objects": [{"objectType": "<ObjectType>", "alias": "o"}],
  "mutation": {"data": {"properties": {"name": "value"}}}
}
```

### 8.5 UPDATE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [{"objectType": "<ObjectType>", "alias": "o"}],
  "conditions": {"kind": "PREDICATE", "ref": "o", "field": "id", "operator": "EQ", "values": ["id-001"]},
  "mutation": {"scope": "ONE", "set": {"name": "new value"}}
}
```

### 8.6 DELETE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "DELETE",
  "objects": [{"objectType": "<ObjectType>", "alias": "o"}],
  "conditions": {"kind": "PREDICATE", "ref": "o", "field": "id", "operator": "EQ", "values": ["id-001"]},
  "mutation": {"scope": "ONE"}
}
```
