# 本体对象操作语言（OQL）DSL 规范

## 1. 设计原则与架构

### 1.1 设计目标

- **统一性**：查询、聚合、写入操作共享统一顶层结构
- **对象驱动**：以对象为中心，而非表驱动（借鉴 Palantir 风格）
- **AI 友好**：简化结构，便于 AI Agent 生成 DSL
- **可扩展**：支持业务注入自定义操作
- **企业级**：支持事务、并发控制、批量操作
- **多数据源映射**：支持对象属性映射到多个物理数据源

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| 声明式 | 描述"做什么"，而非"怎么做" |
| 幂等性 | 操作可安全重试 |
| 原子性 | 支持单条和批量原子操作 |
| 可追溯 | 支持请求追踪和执行审计 |
| 多数据源透明 | 属性来源透明，翻译引擎负责映射到 RDB SQL 或 GQL |

### 1.3 多数据源属性映射

本体模型中，**对象类型的每个属性可以独立映射到不同的物理数据源**：

```
┌─────────────────────────────────────────────────────────────────┐
│                      对象类型：Order                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  属性 sourceId     → MySQL 5.7/8.X (华为云版本) orders.id       │
│  属性 orderNo      → MySQL 5.7/8.X (华为云版本) orders.order_no │
│  属性 customerId   → Gauss V3 (GDE版本) customers表            │
│  属性 amount       → Postgre 15.X (华为云版本) payments表      │
│  属性 status       → Postgre 15.X (华为云版本) orders状态      │
│  属性 createdAt    → Carbon (GDE版本) 性能数据                 │
│  属性 metadata     → ElasticSearch (GDE版本) 历史数据          │
│                                                                 │
│  主键: [sourceId, orderNo]  → 复合主键，跨数据源               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**支持的物理数据源**：

| 数据库 | 版本/版本 | 用途场景 |
|--------|-----------|----------|
| **Nebula** | GDE版本 | 资源、拓扑、知识（图数据库） |
| **Gauss V3** | GDE版本 | 主业务数据（需要支持adc模型） |
| **MySQL** | 5.7 / 8.X (华为云) | 主业务数据（需要支持adc模型） |
| **ClickHouse** | GDE版本 | day2 trace、day2 roce流量、day2集合通信，日志 |
| **ElasticSearch** | GDE版本/华为云 | 历史业务数据（需要支持adc模型）、day2日志、day2指标 |
| **Carbon** | GDE版本（后续可能切Hudi） | 性能数据 |
| **PostgreSQL** | 15.X（华为云） | 资源、拓扑 |
| **Gauss V5** | GDE版本 | 向量数据 |

**设计要点**：

1. **属性级映射**：每个属性独立配置数据源
2. **翻译引擎职责**：
   - DSL 属性 → 物理数据源映射
   - 单对象查询 → 多数据源并行获取 → 结果合并
   - 支持条件过滤下推（Filter Pushdown）
   - 支持聚合下推（Aggregation Pushdown）
3. **查询行为**：
   - 查询单个对象时，翻译引擎并行从多个数据源获取数据
   
   - 属性来源对调用方透明，返回统一的 JSON 结构

   - 翻译引擎负责处理跨数据源 JOIN（如有必要）
   
     **补充哪些支持，哪些不支持？**
   

---

## 2. 统一顶层结构

> **设计原则**：OQL DSL 采用**顶层通用字段 + 操作专用块**的统一结构设计。
> - 顶层字段（通用）：所有操作共享的结构
> - 操作专用块（按 operation 激活）：根据 operation 类型选择性使用

### 2.1 完整结构定义

```json
{
  "version": "1.8.0",
  "operation": "QUERY | MULTI_OBJECT_QUERY | AGGREGATE | ASSOCIATION_QUERY | LIST_LINKED_OBJECTS | GET_LINKED_OBJECT | CREATE | UPDATE | DELETE | UPSERT | BATCH",

  "====== 顶层字段（通用） ======",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"},
      "byList": [{"id": "prod_001"}, {"id": "prod_002"}],
      "byComposite": {"sourceSystem": "ERP", "orderNo": "ORD-001"}
    }
  ],
  "relationships": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 100000,

  "====== 操作专用块（按 operation 激活） ======",
  "query": {},              // QUERY / MULTI_OBJECT_QUERY 专用
  "aggregations": {},       // AGGREGATE 专用
  "associationQuery": {},   // ASSOCIATION_QUERY 专用
  "linkQuery": {},          // LIST/GET LINKED 专用
  "mutation": {},           // CREATE/UPDATE/DELETE/UPSERT/BATCH 专用

  "options": {},
  "extensions": {}
}
```

> **说明**：第1.8.0 版本移除了 `targets` 字段，将多对象查询能力统一到 `objects` 数组中。通过 `objects[].byList` 支持批量主键查询，通过多个对象类型配置支持多对象联合查询。

### 2.2 顶层字段定义（通用）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| **objects** | array | 是 | 对象实例数组，定义查询的目标对象 |
| **objects[].objectType** | string | 是 | 对象类型标识符 |
| **objects[].alias** | string | 否 | 对象别名，用于后续引用 |
| **objects[].by** | object | 否 | 单主键定位，如 `{"id": "prod_001"}` |
| **objects[].byList** | array | 否 | 批量主键列表，用于图数据库一次查询多个点（VID），如 `[{"id": "a"}, {"id": "b"}]` |
| **objects[].byComposite** | object | 否 | 复合主键定位，如 `{"sourceSystem": "ERP", "orderNo": "ORD-001"}` |
| **relationships** | array | 否 | 关系类型数组，ASSOCIATION_QUERY 必填 |
| **conditions** | object | 否 | 统一的条件表达式（扁平化语法） |
| **returns** | array | 否 | 返回字段定义列表 |
| **orders** | array | 否 | 排序定义列表 |
| **maxResults** | integer | 否 | 最大返回数量，默认 100000 |

### 2.3 conditions - 统一条件表达式

conditions 定义统一的条件表达式，使用二叉树结构表示复杂条件：

```json
{
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["active"]},
      {"objectType": "Device", "property": "amount", "operator": "GTE", "values": [1000]}
    ]
  }
}
```

### 2.4 returns - 返回字段投影

```json
{
  "returns": [
    {"type": "object", "param": "p", "fields": ["id", "name", "price"]},
    {"type": "relationship", "param": "r", "fields": ["bizRelType"]}
  ]
}
```

### 2.5 orders - 排序定义

```json
{
  "orders": [
    {"param": "p", "property": "createdAt", "descending": true},
    {"param": "p", "property": "name", "descending": false}
  ]
}
```

### 2.5.1 sourceQuery - 嵌套查询

`sourceQuery` 是一个嵌套查询定义数组，允许在顶层查询中嵌套一个或多个子查询。子查询的查询结果作为数据源供外层查询使用。

**核心特性**：
- **结构一致性**：`sourceQuery` 中的子对象结构与顶层 JSON 对象结构保持完全一致
- **多层嵌套**：支持无限层级的嵌套查询，`sourceQuery` 内部可以再包含 `sourceQuery`
- **灵活组合**：每个嵌套层级可以使用不同的 `operation` 类型（QUERY / MULTI_OBJECT_QUERY / AGGREGATE）

**使用约束**：
- `objects` 和 `sourceQuery` **互斥**，只能使用其一
- 使用 `sourceQuery` 时，`objects` 仅用于定义输出结果的对象类型和别名
- `sourceQuery[].outputAs` 为必填，用于在外层查询中引用子查询结果
- 子查询可以再包含 `sourceQuery`，实现多层嵌套

**sourceQuery 字段定义**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| **sourceQuery** | array | 否（与 objects 二选一） | 嵌套查询定义数组，查询结果作为数据源 |
| **sourceQuery[].outputAs** | string | 是 | 中间表名，供外层查询引用（如 "order_sub"） |
| **sourceQuery[].operation** | enum | 是 | 查询类型：`QUERY`、`MULTI_OBJECT_QUERY` 或 `AGGREGATE` |
| **sourceQuery[].objects** | array | 是 | 子查询的目标对象配置 |
| **sourceQuery[].conditions** | object | 否 | 子查询的条件表达式 |
| **sourceQuery[].returns** | array | 否 | 子查询的返回字段定义 |
| **sourceQuery[].orders** | array | 否 | 子查询的排序规则 |
| **sourceQuery[].maxResults** | integer | 否 | 子查询返回的最大记录数，默认 100000 |
| **sourceQuery[].sourceQuery** | array | 否 | 多层嵌套，支持在子查询中再包含子查询 |

**示例 1：单层嵌套查询**

```json
{
  "operation": "QUERY",
  "objects": [
    {"objectType": "OrderStat", "alias": "o"}
  ],
  "sourceQuery": [{
    "outputAs": "order_sub",
    "operation": "QUERY",
    "objects": [{"objectType": "Order", "alias": "r"}],
    "conditions": {
      "objectType": "Order",
      "property": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    "returns": ["id", "amount", "customerId", "region"]
  }],
  "returns": [
    {"type": "object", "param": "o", "fields": ["id", "amount", "customerId", "region"]}
  ]
}
```

**示例 2：多层嵌套查询（子查询内再嵌套 sourceQuery）**

```json
{
  "operation": "QUERY",
  "objects": [
    {"objectType": "FinalReport", "alias": "f"}
  ],
  "sourceQuery": [{
    "outputAs": "step1_result",
    "operation": "QUERY",
    "objects": [{"objectType": "Order", "alias": "o"}],
    "conditions": {
      "objectType": "Order",
      "property": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    "returns": ["id", "amount", "customerId"],
    "sourceQuery": [{
      "outputAs": "step2_result",
      "operation": "MULTI_OBJECT_QUERY",
      "objects": [
        {"objectType": "Customer", "alias": "c"},
        {"objectType": "Order", "alias": "o"}
      ],
      "conditions": {
        "objectType": "Order",
        "property": "amount",
        "operator": "GTE",
        "values": [1000]
      },
      "returns": [
        {"type": "object", "param": "c", "fields": ["id", "name", "region"]},
        {"type": "object", "param": "o", "fields": ["id", "amount"]}
      ]
    }]
  }],
  "returns": [
    {"type": "object", "param": "f", "fields": ["*"]}
  ]
}
```

**嵌套层级结构说明**：

```
顶层 (Level 1)
├── operation: "QUERY"
├── objects: [...]
├── sourceQuery: [           ← Level 2
│   ├── outputAs: "step1"
│   ├── operation: "QUERY"
│   ├── objects: [...]
│   ├── conditions: {...}
│   ├── returns: [...]
│   └── sourceQuery: [       ← Level 3（多层嵌套）
│       ├── outputAs: "step2"
│       ├── operation: "MULTI_OBJECT_QUERY"
│       ├── objects: [...]
│       ├── conditions: {...}
│       └── returns: [...]
]
└── returns: [...]
```

### 2.6 Operation 类型速查表

| 类型 | 说明 | 专用块 | 使用场景 |
|------|------|-------|----------|
| **QUERY** | 查询对象 | `query` | 单对象查询、列表查询 |
| **MULTI_OBJECT_QUERY** | 多对象联合查询 | `query` | 同表多对象、跨对象条件查询 |
| **AGGREGATE** | 聚合计算 | `aggregations` | 统计、分组聚合 |
| **ASSOCIATION_QUERY** | 关联查询 | `associationQuery` + `relationships` | 图遍历、多跳关联查询 |
| **LIST_LINKED_OBJECTS** | 关联对象列表 | `linkQuery` | 通过 LinkType 列出关联对象 |
| **GET_LINKED_OBJECT** | 获取关联对象 | `linkQuery` | 通过 LinkType 获取特定关联对象 |
| **CREATE** | 创建对象 | `mutation` | 新建单个或批量对象 |
| **UPDATE** | 更新对象 | `mutation` | 修改单个或批量对象 |
| **DELETE** | 删除对象 | `mutation` | 删除单个或批量对象 |
| **UPSERT** | 插入或更新 | `mutation` | 存在更新/不存在创建 |
| **BATCH** | 批量操作 | `mutation` | 组合多个操作，支持事务 |

### 2.7 选择操作类型的决策树

```
开始
  │
  ├─ 需要查询数据？
  │     │
  │     ├─ 需要图遍历/多跳关联？
  │     │     └─ ASSOCIATION_QUERY
  │     │
  │     ├─ 需要通过 LinkType 查关联？
  │     │     ├─ 列出所有关联 → LIST_LINKED_OBJECTS
  │     │     └─ 获取特定关联 → GET_LINKED_OBJECT
  │     │
  │     ├─ 需要聚合统计？
  │     │     └─ AGGREGATE
  │     │
  │     ├─ 需要多对象联合查询？
  │     │     └─ MULTI_OBJECT_QUERY
  │     │
  │     └─ 简单单对象/列表查询
  │           └─ QUERY
  │
  └─ 需要修改数据？
        │
        ├─ 创建 → CREATE
        ├─ 修改 → UPDATE
        ├─ 删除 → DELETE
        └─ 存在更新/不存在创建 → UPSERT
```

### 2.8 请求示例

**查询请求**：
```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "objectType": "Order",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [
    {"type": "object", "param": "o", "fields": ["id", "orderNo", "amount"]}
  ]
}
```

**创建请求**：
```json
{
  "version": "1.8.0",
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
        "price": 8999
      }
    }
  }
}
```

**更新请求（简单主键）**：
```json
{
  "version": "1.8.0",
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "set": {
      "price": 7999,
      "updatedAt": "$now()"
    }
  }
}
```

**更新请求（复合主键）**：
```json
{
  "version": "1.8.0",
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"sourceSystem": "ERP", "orderId": "ORD-001"}
    }
  ],
  "mutation": {
    "set": {
      "status": "shipped",
      "shippedAt": "$now()"
    }
  }
}
```

**删除请求（复合主键）**：
```json
{
  "version": "1.8.0",
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"sourceSystem": "ERP", "orderId": "ORD-001"}
    }
  ],
  "mutation": {}
}
```

### 2.9 objects 统一对象定位

所有查询操作通过 `objects` 数组定义目标对象，支持多种定位方式：

```json
{
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}  // 单主键定位
    }
  ]
}
```

**objects 完整字段定义**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `objectType` | string | 是 | 对象类型标识符 |
| `alias` | string | 否 | 对象别名，用于后续引用 |
| `by` | object | 否 | 单主键定位，如 `{"id": "prod_001"}` |
| `byList` | array | 否 | 批量主键列表，如 `[{"id": "a"}, {"id": "b"}]`，用于图数据库一次查询多个点 |
| `byComposite` | object | 否 | 复合主键，如 `{"sourceSystem": "ERP", "orderNo": "ORD-001"}` |

> **说明**：`conditions` 统一放在顶层，不放在对象内部。详见 [2.3 conditions](#23-统一条件表达式)。

**单主键定位示例**：
```json
{
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ]
}
```

**批量主键定位示例**：
```json
{
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "byList": [
        {"id": "prod_001"},
        {"id": "prod_002"},
        {"id": "prod_003"}
      ]
    }
  ]
}
```

**复合主键定位示例**：

```json
{
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "byComposite": {
        "sourceSystem": "ERP",
        "orderNo": "ORD-20240301-001"
      }
    }
  ]
}
```

### 2.10 relationships 统一关系定义

`ASSOCIATION_QUERY` 操作通过 `relationships` 数组定义查询的关系类型：

```json
{
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo",
      "structRelType": "Association"
    },
    {
      "name": "installedOn",
      "alias": "install",
      "sourceObjectType": "Device",
      "targetObjectType": "Server",
      "bizRelType": "installedOn",
      "structRelType": "Composition"
    }
  ]
}
```

**relationships 字段定义**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `name` | string | 是 | 关系类型名称（驼峰命名） |
| `alias` | string | 否 | 关系别名，用于 returns 引用 |
| `sourceObjectType` | string | 是 | 源对象类型（遍历起点） |
| `targetObjectType` | string | 是 | 目标对象类型（遍历终点） |
| `bizRelType` | string | 否 | 业务语义类型 |
| `structRelType` | string | 否 | UML 结构关系类型 |

---

### 2.11 统一结构模板速查

以下是各操作类型的统一结构模板：

**QUERY 模板**：

```json
{
  "operation": "QUERY",
  "objects": [{ "objectType": "X", "alias": "x", "by": {...} }],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 10000
}
```

**MULTI_OBJECT_QUERY 模板**：
```json
{
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    { "objectType": "X", "alias": "x" },
    { "objectType": "Y", "alias": "y" }
  ],
  "conditions": {...},
  "returns": [...]
}
```

**AGGREGATE 模板**：
```json
{
  "operation": "AGGREGATE",
  "objects": [{ "objectType": "X", "alias": "x" }],
  "returns": [
    {
      "type": "object",
      "param": "x",
      "fields": ["category"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "x",
      "field": "amount",
      "function": "sum",
      "alias": "totalAmount"
    }
  ],
  "conditions": {...}
}
```

**ASSOCIATION_QUERY 模板**：
```json
{
  "operation": "ASSOCIATION_QUERY",
  "objects": [...],
  "relationships": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 10000,
  "associationQuery": { "action": "go" }
}
```

**LIST_LINKED_OBJECTS 模板**：
```json
{
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [{ "objectType": "X", "alias": "x", "by": {...} }],
  "relationships": "L",
  "conditions": {...},
  "returns": [...]
}
```

**GET_LINKED_OBJECT 模板**：
```json
{
  "operation": "GET_LINKED_OBJECT",
  "objects": [{ "objectType": "X", "alias": "x", "by": {...} }],
  "relationships": "L",
  "linkQuery": { "linkedObjectKey": {...} },
  "conditions": {...},
  "returns": [...]
}
```

---

### 2.12 无过滤条件查询（查询所有对象）

当 `query` 节点中省略 `filter` 时，QUERY 操作将返回指定对象类型的**所有对象**。这适用于需要获取对象类型完整列表的场景。

#### 2.12.1 请求示例（无过滤条件）

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "User",
      "alias": "u"
    }
  ],
  "returns": [
    {"type": "object", "param": "u", "fields": ["id", "firstName", "lastName"]}
  ]
}
```

> **说明**：
> - 无 conditions 时表示不限制查询条件，返回对象类型的全部数据
> - 单次查询最大返回 10 万条记录，可通过 `maxResults` 控制

#### 2.5.2 响应格式

查询操作的响应采用以下结构：

```json
{
  "success": true,
  "data": [
    {
      "objectType": "User",
      "rid": "ri.phonograph2-objects.main.object.88a6fccb-f333-46d6-a07e-7725c5f18b61",
      "properties": {
        "id": 50030,
        "firstName": "John",
        "lastName": "Doe"
      }
    },
    {
      "objectType": "User",
      "rid": "ri.phonograph2-objects.main.object.dcd887d1-c757-4d7a-8619-71e6ec2c25ab",
      "properties": {
        "id": 20090,
        "firstName": "John",
        "lastName": "Haymore"
      }
    }
  ],
  "metadata": {
    "totalCount": 2500,
    "executionTime": 25
  }
}
```

#### 2.5.3 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| data | array | 对象列表 |
| data[].objectType | string | 对象类型名称 |
| data[].rid | string | 对象资源标识符（全局唯一） |
| data[].properties | object | 对象属性，键值对形式 |
| metadata.totalCount | integer | 符合条件对象的总数量（可选） |
| metadata.executionTime | integer | 执行时间（毫秒） |

#### 2.5.4 结果数量限制

单次查询通过 `maxResults` 控制最大返回数量限制：

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["id", "orderNo", "amount"]
    }
  ],
  "conditions": {
    "objectType": "o",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "orders": [
    {"param": "o", "property": "createdAt", "descending": true}
  ],
  "maxResults": 10000
}
```

**说明**：
- 默认 `maxResults` 为 100000，最大支持 100000
- 超出限制的结果将被截断，不会返回
- OQL v1.8.0 移除了分页语法，统一使用 `maxResults` 限制结果数量

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "objectType": "Order",
      "rid": "ri.phonograph2-objects.main.object.order-001",
      "properties": {
        "id": "order-001",
        "orderNo": "ORD-20240301-001",
        "amount": 19999.00
      }
    }
  ],
  "metadata": {
    "totalCount": 156,
    "truncated": false
  },
  "trace": {
    "executionTime": 25
  }
}
```

**超出限制时的响应**：

```json
{
  "success": true,
  "data": [
    // 前 100000 条记录
  ],
  "metadata": {
    "totalCount": 150000,
    "truncated": true,
    "truncatedCount": 50000
  },
  "trace": {
    "executionTime": 150
  }
}
```

---

#### 2.5.5 使用属性过滤条件查询（无需指定 objectKey）

QUERY 操作通过顶层的 `conditions` 进行属性过滤查询，无需指定主键。

**请求示例（使用 conditions 查询）**：

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Order", "property": "amount", "operator": "GTE", "values": [1000]},
      {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
      {"objectType": "Order", "property": "customerName", "operator": "CONTAINS", "values": ["张"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "o", "fields": ["id", "orderNo", "amount", "status", "customerName", "createdAt"]}
  ],
  "orders": [
    {"field": "createdAt", "direction": "DESC"}
  ],
  "maxResults": 10000
}
```

**请求示例（多条件组合 OR）**：

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    }
  ],
  "conditions": {
    "relation": "OR",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"]},
      {
        "relation": "AND",
        "children": [
          {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["warning"]},
          {"objectType": "Device", "property": "alertLevel", "operator": "LTE", "values": [2]}
        ]
      }
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "alertLevel", "location"]}
  ],
  "maxResults": 10000
}
```

**使用规则**：
- `conditions` 与 `objects[].by`/`objects[].byList`/`objects[].byComposite` 二选一
- `conditions` 统一使用二叉树结构，详见 [2.3 conditions](#23-统一条件表达式)
- 嵌套条件通过 `children` 数组实现

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "objectType": "Order",
      "rid": "ri.phonograph2-objects.main.object.order-001",
      "properties": {
        "id": "order-001",
        "orderNo": "ORD-20240301-001",
        "amount": 1500.00,
        "status": "completed",
        "customerName": "张三",
        "createdAt": "2024-03-01T10:30:00Z"
      }
    },
    {
      "objectType": "Order",
      "rid": "ri.phonograph2-objects.main.object.order-002",
      "properties": {
        "id": "order-002",
        "orderNo": "ORD-20240301-002",
        "amount": 2300.00,
        "status": "completed",
        "customerName": "张丽",
        "createdAt": "2024-03-01T11:00:00Z"
      }
    }
  ],
  "metadata": {
    "totalCount": 2,
    "executionTime": 25
  }
}
```

---

### 2.14 多对象查询（MULTI_OBJECT_QUERY）

当需要在一个查询请求中查询多个对象的属性时，使用 `MULTI_OBJECT_QUERY` 操作类型。

### 2.14.1 使用场景

1. **同表多对象查询**：多个对象类型对应同一个数据库表，合并查询返回
2. **跨对象条件查询**：对象A的属性作为对象B的过滤条件（如用户→小区）
3. **关联属性聚合**：从不同对象类型聚合数据进行联合分析

### 2.14.2 objects 字段定义（多对象定位）

> **说明**：`objects` 字段定义详见 [第2.2节顶层字段定义](#22-顶层字段定义通用)。

多对象查询通过 `objects` 数组定义目标对象，支持多种定位方式：

```json
{
  "objects": [
    {
      "objectType": "User",
      "alias": "u"
    },
    {
      "objectType": "Community",
      "alias": "c"
    }
  ]
}
```

### 2.14.3 query 块结构（whereFrom 跨对象条件查询）

`query` 块用于定义多对象查询的条件，`whereFrom` 用于跨对象条件查询：

```json
{
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "u"},
    {"objectType": "Community", "alias": "c"}
  ],
  "conditions": {
    "objectType": "Community",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  },
  "returns": [
    {"type": "object", "param": "c", "fields": ["id", "name", "address"]}
  ],
  "query": {
    "whereFrom": {
      "from": "u.id",
      "to": "c.userId",
      "operator": "eq"
    }
  }
}
```

**query.whereFrom 字段定义**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| query.whereFrom.from | string | 是 | 来源对象属性（格式：alias.field 或 objectType.field） |
| query.whereFrom.to | string | 是 | 目标对象过滤字段 |
| query.whereFrom.operator | string | 否 | 比较操作符，默认 eq |

### 2.14.4 conditions 统一条件表达式

> **说明**：`conditions` 字段定义详见 [第2.3节](#23-conditions---统一条件表达式)。

### 2.14.5 returns 返回字段投影

> **说明**：`returns` 字段定义详见 [第2.4节](#24-returns---返回字段投影)。

### 2.14.6 sourceQuery 嵌套查询

> **说明**：`sourceQuery` 字段定义详见 [第2.5.1节](#251-sourcequery---嵌套查询)，包含完整的字段定义、多层嵌套说明和使用示例。

MULTI_OBJECT_QUERY 操作支持通过顶层 `sourceQuery` 定义嵌套查询，使查询数据源从一个子查询的中间结果集获取。
**使用约束**：
- `objects` 和 `sourceQuery` **互斥**，只能使用其一
- 使用 `sourceQuery` 时，`objects` 可以为空，也可以为其他对象类型，用于满足多对象类型查询的诉求
- 子查询结构与顶层结构一致，支持多层嵌套

### 2.13.7 同表多对象查询示例
      {"type": "object", "param": "o", "fields": ["id", "amount", "orderDate"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "a", "fields": ["id", "name", "region", "amount", "orderDate"]}
  ]
}
```

### 2.14.7 同表多对象查询示例

**场景**：User 和 Customer 两个对象类型对应同一张表 person

```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "u"},
    {"objectType": "Customer", "alias": "c"}
  ],
  "conditions": {
    "relation": "OR",
    "children": [
      {"objectType": "User", "property": "type", "operator": "EQ", "values": ["admin"]},
      {"objectType": "Customer", "property": "type", "operator": "EQ", "values": ["vip"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "u", "fields": ["id", "name", "email"]},
    {"type": "object", "param": "c", "fields": ["id", "name", "email"]}
  ]
}
```

#### 2.14.7.1 同表多对象联合查询（User + Cell 关联表场景）

**场景**：User 和 Cell 两个对象类型对应同一张物理表 `tbl_user_cell`，通过该表的 `user_id` 和 `cell_id` 字段建立关联。查询条件为 `user = '123' AND cell = '456'`，返回 `cell.volume`。

**表结构说明**：
```sql
CREATE TABLE tbl_user_cell (
    user_id VARCHAR(50),     -- 标识用户
    cell_id VARCHAR(50),      -- 标识小区
    cell_volume DECIMAL(10,2), -- 小区容积率
    cell_name VARCHAR(100),   -- 小区名称
    PRIMARY KEY (user_id, cell_id)
);
```

**DSL 请求**：
```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "user"},
    {"objectType": "Cell", "alias": "cell"}
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {
        "objectType": "User",
        "property": "user_id",
        "operator": "EQ",
        "values": ["123"]
      },
      {
        "objectType": "Cell",
        "property": "cell_id",
        "operator": "EQ",
        "values": ["456"]
      }
    ]
  },
  "returns": [
    {
      "type": "object",
      "param": "cell",
      "fields": ["volume"]
    }
  ]
}
```

**对应物理 SQL**：
```sql
SELECT
    t.cell_volume AS volume
FROM tbl_user_cell t
WHERE t.user_id = '123'
  AND t.cell_id = '456';
```

**响应结果**：
```json
{
  "success": true,
  "data": [
    {
      "objectType": "Cell",
      "rid": "ri.phonograph2-objects.main.object.cell-456",
      "properties": {
        "volume": 3.5
      }
    }
  ],
  "metadata": {
    "totalCount": 1
  }
}
```

> **说明**：
> - User 和 Cell 共用同一张物理表 `tbl_user_cell`，但通过不同的字段（`user_id` vs `cell_id`）标识
> - `conditions` 中需要同时指定 User 的 `user_id` 和 Cell 的 `cell_id` 条件
> - `returns` 中 `param: "cell"` 表示返回 Cell 对象的属性

#### 2.14.7.2 跨表外键关联查询（User + Cell 外键关联场景）

**场景**：User 和 Cell 是两张独立的表，通过外键关联。User 表通过 `cell_id` 外键指向 Cell 表。查询条件为 `user.id = '123'`，返回关联的 `cell.volume`。

**表结构说明**：
```sql
-- 用户表（User），通过 cell_id 外键指向小区
CREATE TABLE tbl_user (
    id VARCHAR(50) PRIMARY KEY,      -- 用户ID
    name VARCHAR(100),                -- 用户名
    cell_id VARCHAR(50),              -- 外键，关联小区
    FOREIGN KEY (cell_id) REFERENCES tbl_cell(id)
);

-- 小区表（Cell）
CREATE TABLE tbl_cell (
    id VARCHAR(50) PRIMARY KEY,       -- 小区ID
    name VARCHAR(100),                -- 小区名
    volume DECIMAL(10,2),             -- 容积率
    address VARCHAR(200)              -- 地址
);
```

**DSL 请求**：
```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "user", "by": {"id": "123"}},
    {"objectType": "Cell", "alias": "cell"}
  ],
  "returns": [
    {
      "type": "object",
      "param": "cell",
      "fields": ["id", "name", "volume", "address"]
    }
  ],
  "query": {
    "whereFrom": {
      "from": "user.cell_id",
      "to": "cell.id",
      "operator": "eq"
    }
  }
}
```

**对应物理 SQL**：
```sql
SELECT
    c.id,
    c.name,
    c.volume,
    c.address
FROM tbl_cell c
INNER JOIN tbl_user u ON c.id = u.cell_id
WHERE u.id = '123';
```

**响应结果**：
```json
{
  "success": true,
  "data": [
    {
      "objectType": "Cell",
      "rid": "ri.phonograph2-objects.main.object.cell-456",
      "properties": {
        "id": "456",
        "name": "阳光小区",
        "volume": 3.5,
        "address": "XX路XX号"
      }
    }
  ],
  "metadata": {
    "totalCount": 1,
    "sourceObjects": ["User", "Cell"]
  }
}
```

> **说明**：
> - User 和 Cell 是两张独立的表，通过外键 `user.cell_id = cell.id` 关联
> - `query.whereFrom` 用于定义跨表关联条件（`from`: 来源对象属性，`to`: 目标对象字段）
> - `conditions` 可省略，关联条件由 `whereFrom` 自动生成 JOIN 逻辑
> - 外键关联支持 `INNER JOIN`（默认）、`LEFT JOIN`、`RIGHT JOIN` 可通过 `joinType` 配置

---

### 2.14.8 跨对象条件查询示例（用户→小区）

**场景**：通过用户 id 查询该用户关联的小区

```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "user", "by": {"id": "user_001"}},
    {"objectType": "Community", "alias": "community"}
  ],
  "returns": [
    {"type": "object", "param": "community", "fields": ["id", "name", "address"]}
  ],
  "query": {
    "whereFrom": {
      "from": "user.id",
      "to": "community.ownerId",
      "operator": "eq"
    }
  }
}
```

### 2.14.9 多对象查询响应格式

```json
{
  "success": true,
  "data": [
    {
      "objectType": "Community",
      "rid": "ri.phonograph2-objects.main.object.comm-001",
      "properties": {
        "id": "comm-001",
        "name": "阳光小区",
        "address": "XX路XX号",
        "ownerId": "user_001"
      }
    },
    {
      "objectType": "Community",
      "rid": "ri.phonograph2-objects.main.object.comm-002",
      "properties": {
        "id": "comm-002",
        "name": "幸福小区",
        "address": "YY路YY号",
        "ownerId": "user_001"
      }
    }
  ],
  "metadata": {
    "totalCount": 2,
    "sourceObjects": ["User", "Community"]
  }
}
```

---

### 2.14.10 MySQL SQL 转换示例

以下展示 MULTI_OBJECT_QUERY 如何转换为 MySQL SQL 查询语句。

#### 2.6.9.1 示例一：同表多对象查询

**场景**：User 和 Customer 两个对象类型对应同一个数据库表 `persons`

**DSL 请求**：
```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "u"},
    {"objectType": "Customer", "alias": "c"}
  ],
  "conditions": {
    "relation": "OR",
    "children": [
      {"objectType": "User", "property": "type", "operator": "EQ", "values": ["admin"]},
      {"objectType": "Customer", "property": "type", "operator": "EQ", "values": ["vip"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "u", "fields": ["id", "name", "email"]},
    {"type": "object", "param": "c", "fields": ["id", "name", "email"]}
  ]
}
```

**转换为 MySQL SQL**：

```sql
-- 查询同一个表，根据 type 字段区分对象类型
SELECT
    id,
    name,
    email,
    type,
    CASE
        WHEN type = 'admin' THEN 'User'
        WHEN type = 'vip' THEN 'Customer'
        ELSE type
    END AS objectType
FROM persons
WHERE
    type IN ('admin', 'vip')
ORDER BY id;
```

**或使用 UNION 方式**：

```sql
-- 方式一：UNION 查询
(SELECT id, name, email, 'admin' AS type, 'User' AS objectType FROM persons WHERE type = 'admin')
UNION ALL
(SELECT id, name, email, 'vip' AS type, 'Customer' AS objectType FROM persons WHERE type = 'vip')
ORDER BY id;

-- 方式二：UNION ALL 查询（保留所有匹配记录）
(SELECT id, name, email, type, 'User' AS objectType FROM persons WHERE type = 'admin')
UNION ALL
(SELECT id, name, email, type, 'Customer' AS objectType FROM persons WHERE type = 'vip')
ORDER BY id;
```

**响应结果**：

| id | name | email | type | objectType |
|----|------|-------|------|------------|
| 1 | 张三 | zhangsan@example.com | admin | User |
| 2 | 李四 | lisi@example.com | vip | Customer |

---

#### 2.6.9.2 示例二：跨对象条件查询（whereFrom）

**场景**：通过用户 id 查询该用户关联的小区（User.id = Community.ownerId）

**DSL 请求**：
```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "user", "by": {"id": "user_001"}},
    {"objectType": "Community", "alias": "community"}
  ],
  "returns": [
    {"type": "object", "param": "community", "fields": ["id", "name", "address"]}
  ],
  "query": {
    "whereFrom": {
      "from": "user.id",
      "to": "community.ownerId",
      "operator": "eq"
    }
  }
}
```

**转换为 MySQL SQL**：

```sql
-- 假设 User 表和 Community 表通过 ownerId 关联
SELECT
    c.id,
    c.name,
    c.address
FROM users u
INNER JOIN communities c ON u.id = c.owner_id
WHERE u.id = 'user_001';
```

**响应结果**：

| id | name | address |
|----|------|---------|
| comm-001 | 阳光小区 | XX路XX号 |
| comm-002 | 幸福小区 | YY路YY号 |

---

#### 2.6.9.3 示例三：跨对象条件查询（多条件过滤）

**场景**：查询状态为"运行中"的设备所在机房的信息

**DSL 请求**：
```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "Device", "alias": "device"},
    {"objectType": "EquipmentRoom", "alias": "room"}
  ],
  "conditions": {
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "room", "fields": ["id", "name", "location"]}
  ],
  "query": {
    "whereFrom": {
      "from": "device.roomId",
      "to": "room.id",
      "operator": "eq"
    }
  }
}
```

**转换为 MySQL SQL**：

```sql
-- 关联查询设备与机房
SELECT
    r.id,
    r.name,
    r.location
FROM devices d
INNER JOIN equipment_rooms r ON d.room_id = r.id
WHERE d.status = 'running'
ORDER BY r.name;
```

**或使用子查询**：

```sql
-- 使用子查询方式
SELECT
    r.id,
    r.name,
    r.location
FROM equipment_rooms r
WHERE r.id IN (
    SELECT d.room_id
    FROM devices d
    WHERE d.status = 'running'
)
ORDER BY r.name;
```

**响应结果**：

| id | name | location |
|----|------|---------|
| room-001 | 主机房 | A座1楼 |
| room-002 | 备机房 | B座2楼 |

---

#### 2.6.9.4 示例四：objects + conditions 组合查询

**场景**：查询指定用户组下的所有设备及其关联的机房

**DSL 请求**：
```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    },
    {
      "objectType": "EquipmentRoom",
      "alias": "r"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "groupId", "operator": "EQ", "values": ["group-001"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status"]},
    {"type": "object", "param": "r", "fields": ["name"]}
  ],
  "query": {
    "whereFrom": {
      "from": "d.roomId",
      "to": "r.id",
      "operator": "eq"
    }
  }
}
```

**转换为 MySQL SQL**：

```sql
-- 组合 conditions 和 whereFrom 条件
SELECT
    d.id,
    d.name,
    d.status,
    r.name AS room_name
FROM devices d
INNER JOIN equipment_rooms r ON d.room_id = r.id
WHERE d.group_id = 'group-001'
ORDER BY d.name;
```

**响应结果**：

| id | name | status | room_name |
|----|------|--------|-----------|
| device-001 | Web服务器 | running | 主机房 |
| device-002 | 数据库 | running | 主机房 |

---

#### 2.6.9.5 SQL 转换规则总结

| OQL 场景 | MySQL 转换方式 |
|----------|----------------|
| 同表多对象（UNION） | 使用 `UNION` 或 `UNION ALL` 合并多个对象的查询结果 |
| 跨对象条件（whereFrom） | 使用 `INNER JOIN` 或 `LEFT JOIN` 关联查询 |
| 跨对象 + 过滤 | `JOIN` 配合 `WHERE` 条件过滤 |
| 单对象 conditions 查询 | 直接在 `WHERE` 子句中使用过滤条件 |
| 多条件组合 | 使用 `AND`/`OR` 构建复杂 WHERE 条件 |

---

## 3. 查询操作（QUERY）

> **前置说明**：QUERY 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义（第2.9节）
> - `conditions` - 统一条件表达式（第2.3节）
> - `returns` - 返回字段投影（第2.4节）
> - `orders` - 排序定义（第2.5节）
> - `maxResults` - 结果限制（第2.5.4节）

QUERY 操作使用统一顶层结构，通过 `conditions` 定义过滤条件，通过 `returns` 定义返回字段：

### 3.1 查询结构

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    { "objectType": "Product", "alias": "p", "by": {"id": "prod_001"} }
  ],
  "conditions": {
    "objectType": "Product",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  },
  "returns": [
    {"type": "object", "param": "p", "fields": ["id", "name", "price"]}
  ],
  "orders": [
    {"param": "p", "property": "createdAt", "descending": true}
  ],
  "maxResults": 100000
}
```

### 3.1.1 sourceQuery 嵌套查询

> **说明**：`sourceQuery` 字段定义详见 [第2.5.1节](#251-sourcequery---嵌套查询)。

QUERY 操作支持通过顶层 `sourceQuery` 定义嵌套查询，使查询数据源从一个子查询的中间结果集获取。

**使用约束**：
- `objects` 和 `sourceQuery` **互斥**，只能使用其一
- 使用 `sourceQuery` 时，`objects` 仅用于定义输出结果的对象类型和别名
- `sourceQuery[].outputAs` 为必填，用于在外层查询中引用子查询结果

**示例 1：嵌套 QUERY 查询**

```json
{
  "operation": "QUERY",
  "objects": [
    {"objectType": "OrderStat", "alias": "o"}
  ],
  "sourceQuery": [{
    "outputAs": "order_sub",
    "operation": "QUERY",
    "objects": [{"objectType": "Order", "alias": "r"}],
    "conditions": {
      "objectType": "Order",
      "property": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    "returns": ["id", "amount", "customerId", "region"]
  }],
  "returns": [
    {"type": "object", "param": "o", "fields": ["id", "amount", "customerId", "region"]}
  ]
}
```

**示例 2：嵌套 MULTI_OBJECT_QUERY 查询**

```json
{
  "operation": "QUERY",
  "objects": [
    {"objectType": "RevenueReport", "alias": "r"}
  ],
  "sourceQuery": [{
    "outputAs": "revenue_source",
    "operation": "MULTI_OBJECT_QUERY",
    "objects": [
      {"objectType": "Customer", "alias": "c"},
      {"objectType": "Order", "alias": "o"}
    ],
    "conditions": {
      "relation": "AND",
      "children": [
        {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]}
      ]
    },
    "returns": [
      {"type": "object", "param": "c", "fields": ["id", "name", "region"]},
      {"type": "object", "param": "o", "fields": ["id", "amount", "orderDate"]}
    ]
  }],
  "returns": [
    {"type": "object", "param": "r", "fields": ["id", "name", "region", "amount", "orderDate"]}
  ]
}
```

**多层嵌套说明**：

`sourceQuery` 支持多层嵌套，即在子查询中可以再包含 `sourceQuery`。嵌套层级的子对象结构与顶层完全一致。

**结构示例**：
```json
{
  "operation": "QUERY",
  "objects": [{"objectType": "Final", "alias": "f"}],
  "sourceQuery": [{
    "outputAs": "level1",
    "operation": "QUERY",
    "objects": [{"objectType": "Level1", "alias": "l1"}],
    "sourceQuery": [{
      "outputAs": "level2",
      "operation": "MULTI_OBJECT_QUERY",
      "objects": [...],
      "sourceQuery": [{
        "outputAs": "level3",
        "operation": "AGGREGATE",
        "objects": [...]
      }]
    }]
  }]
}
```

> **详细说明**：多层嵌套的完整定义和使用示例请参阅 [第2.5.1节](#251-sourcequery---嵌套查询)。

### 3.2 QUERY 专用语法

QUERY 操作使用统一顶层结构（详见第2章），本节仅说明与 QUERY 操作相关的差异化内容。

| 通用字段 | 说明 | 引用章节 |
|----------|------|----------|
| `objects` | 对象实例定义 | 第2.9节 |
| `conditions` | 统一条件表达式 | 第2.3节 |
| `returns` | 返回字段投影 | 第2.4节 |
| `orders` | 排序定义 | 第2.5节 |
| `maxResults` | 结果限制 | 第2.5.4节 |

QUERY 操作使用 `query` 专用块定义查询参数，但实际使用中 query 块通常是空的，查询条件通过 `conditions` 定义。

**完整查询示例**：

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
      {"objectType": "Order", "property": "createdAt", "operator": "GTE", "values": ["2024-01-01T00:00:00Z"]}
    ]
  },
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["id", "orderNo", "amount", "status"]
    }
  ],
  "orders": [
    {"param": "o", "property": "createdAt", "descending": true}
  ],
  "maxResults": 10000
}
```

### 3.3 时序属性查询（TIMESERIES_QUERY）

#### 3.4.1 时序属性概述

时序属性具有以下特征：
- **时间戳（Timestamp）**：表示该值发生的具体时间
- **值（Value）**：在该时间点上的测量量
- **有序性**：数据按时间顺序排列
- **seriesIdProperty**：用于匹配时序数据的对象属性键

**元数据配置**（在对象模型中定义）：

```json
{
  "propertyName": "fanSpeed",
  "dataType": "time series",
  "seriesIdProperty": "machineId",
  "units": "RPM",
  "interpolation": "LINEAR"
}
```

#### 3.4.2 时序查询结构

```json
{
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Machine",
      "alias": "m"
    }
  ],
  "conditions": {
    "objectType": "Machine",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  },
  "returns": [
    {
      "type": "object",
      "param": "m",
      "fields": ["id", "name"],
      "timeseries": {
        "property": "fanSpeed",
        "from": "2026-02-07T00:00:00Z",
        "to": "2026-02-07T23:59:59Z",
        "orderBy": "ASC",
        "limit": 100
      }
    }
  ]
}
```

> **说明**：时间格式统一使用 ISO 8601，翻译引擎根据本体模型配置自动转换为对应数据源的格式。

#### 3.4.3 timeseries 配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|:----:|:----:|------|
| property | string | 是 | 时序属性名，如 `fanSpeed`、`temperature` |
| from | string | 否 | 开始时间（ISO 8601 格式） |
| to | string | 否 | 结束时间（ISO 8601 格式） |
| orderBy | string | 否 | 排序方向：`ASC`（升序）或 `DESC`（降序），默认 ASC |
| limit | integer | 否 | 最大返回点数，默认 100 |
| interpolation | string | 否 | 插值方法：LINEAR / NEAREST / PREVIOUS / NEXT / NONE |

#### 3.4.4 时序数据返回格式

**响应结构**：

```json
{
  "success": true,
  "data": [
    {
      "objectType": "Machine",
      "rid": "ri.phonograph2-objects.main.object.machine-001",
      "properties": {
        "id": "machine-001",
        "name": "Web服务器-1",
        "fanSpeed": {
          "2026-02-07T17:53:00Z": 1000,
          "2026-02-07T17:54:00Z": 1005,
          "2026-02-07T17:55:00Z": 1020
        }
      }
    }
  ],
  "metadata": {
    "queryTimeRange": {
      "from": "2026-02-07T00:00:00Z",
      "to": "2026-02-07T23:59:59Z"
    },
    "dataPointCount": 3
  }
}
```

**时序属性返回格式**：

时序属性值以 `{timestamp: value}` 的 KV 结构返回，按时间排序：

| 格式 | 示例 |
|------|------|
| ASC 升序 | `{"2026-02-07T17:53:00Z": 1000, "2026-02-07T17:54:00Z": 1005}` |
| DESC 降序 | `{"2026-02-07T17:55:00Z": 1020, "2026-02-07T17:54:00Z": 1005}` |

#### 3.7.5 完整时序查询示例

**请求**：

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Machine",
      "alias": "m"
    }
  ],
  "conditions": {
    "objectType": "Machine",
    "property": "machineType",
    "operator": "EQ",
    "values": ["server"]
  },
  "returns": [
    {
      "type": "object",
      "param": "m",
      "fields": ["id", "name"],
      "timeseries": {
        "property": "fanSpeed",
        "from": "2026-02-07T00:00:00Z",
        "to": "2026-02-07T23:59:59Z",
        "orderBy": "ASC",
        "limit": 50
      }
    }
  ]
}
```

**响应**：

```json
{
  "success": true,
  "data": [
    {
      "rid": "ri.phonograph2-objects.main.object.M-001",
      "properties": {
        "id": "M-001",
        "name": "Web服务器-1",
        "fanSpeed": {
          "2026-02-07T17:53:00Z": 1000,
          "2026-02-07T17:54:00Z": 1005,
          "2026-02-07T17:55:00Z": 1020,
          "2026-02-07T17:56:00Z": 980
        }
      }
    },
    {
      "rid": "ri.phonograph2-objects.main.object.M-002",
      "properties": {
        "id": "M-002",
        "name": "数据库服务器",
        "fanSpeed": {
          "2026-02-07T17:53:00Z": 1500,
          "2026-02-07T17:54:00Z": 1800,
          "2026-02-07T17:55:00Z": 1700
        }
      }
    }
  ],
  "metadata": {
    "queryTimeRange": {
      "from": "2026-02-07T00:00:00Z",
      "to": "2026-02-07T23:59:59ZZ"
    },
    "dataPointCount": 7
  }
}
```

#### 3.6.6 时序查询转换为 GQL

**NebulaGraph 时序查询**：

```gql
LOOKUP ON Machine
WHERE Machine.machineType == "server"
YIELD Machine.id AS id, Machine.name AS name
| GO FROM $-.id OVER has_metric
WHERE has_metric.timestamp >= datetime('2026-02-07T00:00:00Z')
  AND has_metric.timestamp <= datetime('2026-02-07T23:59:59Z')
YIELD
  $-.id AS machineId,
  has_metric.timestamp AS timestamp,
  has_metric.value AS value
ORDER BY timestamp ASC
LIMIT 50
```

**结果组装**（翻译引擎内部处理）：

```json
{
  "id": "M-001",
  "fanSpeed": {
    "2026-02-07T17:53:00Z": 1000,
    "2026-02-07T17:54:00Z": 1005
  }
}
```

---

## 4. 聚合操作（AGGREGATE）

> **重要说明**：AGGREGATE 操作**仅支持单一对象类型**的聚合查询。`objects` 数组中只能包含一个对象配置，聚合计算的所有字段必须来自同一个对象类型。如需对多个对象类型进行聚合分析，请使用应用层处理或先进行数据预处理。

> **前置说明**：AGGREGATE 操作使用统一顶层结构（详见 [第2章统一顶层结构](#2-统一顶层结构)），聚合计算通过 `returns` 中的 `function` 字段定义。

### 4.1 聚合结构

> **约束说明**：AGGREGATE 操作仅支持单一对象类型，`objects` 中只能配置一个对象。

`returns` 节点用于定义分组聚合查询，聚合函数通过 `function` 字段指定：

#### 4.1.1 完整结构定义（JSON Schema）

以下 JSON Schema 定义了 AGGREGATE 操作的有效结构，支持嵌套 `sourceQuery`：

```json
{
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "OutputObject",
      "alias": "o"
    }
  ],
  "sourceQuery": [{
    "outputAs": "intermediate_table",
    "operation": "QUERY",
    "objects": [{ "objectType": "SourceObject", "alias": "s" }],
    "conditions": {...},
    "returns": [...]
  }],
  "conditions": {...},
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["category", "region"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalAmount"
    },
    {
      "type": "object",
      "param": "o",
      "field": "id",
      "function": "count",
      "alias": "orderCount"
    }
  ],
  "having": {...},
  "orders": [...],
  "maxResults": 100000
}
```

      "fields": ["category"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalAmount"
    },
    {
      "type": "object",
      "param": "o",
      "field": "id",
      "function": "count",
      "alias": "orderCount"
    }
  ]
}
```

哪些库不支持，哪些库支持？

**返回结果**：

```json
{
  "data": [
    {
      "metrics": [
        {"name": "totalAmount", "value": 150000},
        {"name": "orderCount", "value": 150}
      ],
      "group": {
        "category": "electronics"
      }
    },
    {
      "metrics": [
        {"name": "totalAmount", "value": 80000},
        {"name": "orderCount", "value": 200}
      ],
      "group": {
        "category": "clothing"
      }
    }
  ]
}
```

#### 4.1.4 多字段分组示例

```json
{
  "operation": "AGGREGATE",
  "objects": [{ "objectType": "Order", "alias": "o" }],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["region", "category", "status"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalSales"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "avg",
      "alias": "avgSales"
    }
  ]
}
```

**返回结构**：

```json
{
  "data": [
    {
      "metrics": [
        {"name": "totalSales", "value": 50000},
        {"name": "avgSales", "value": 2500}
      ],
      "group": {
        "region": "华东",
        "category": "electronics",
        "status": "completed"
      }
    }
  ]
}
```

#### 4.1.5 无分组聚合（全局聚合）

如果 `function: groupBy` 不存在，返回整个数据集的聚合结果：

```json
{
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "Order", "alias": "o" }
  ],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "grandTotal"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "avg",
      "alias": "avgOrderValue"
    },
    {
      "type": "object",
      "param": "o",
      "field": "id",
      "function": "count",
      "alias": "totalOrders"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "min",
      "alias": "minOrder"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "max",
      "alias": "maxOrder"
    }
  ]
}
```

**返回结果**：

```json
{
  "data": [
    {
      "metrics": [
        {"name": "grandTotal", "value": 230000},
        {"name": "avgOrderValue", "value": 1150},
        {"name": "totalOrders", "value": 200},
        {"name": "minOrder", "value": 50},
        {"name": "maxOrder", "value": 5000}
      ],
      "group": {}
    }
  ]
}
```

#### 4.1.6 带 conditions 的聚合示例

```json
{
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "Order", "alias": "o" }
  ],
  "conditions": {
    "objectType": "Order",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["category"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalAmount"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "count",
      "alias": "highValueOrders"
    }
  ]
}
```

#### 4.1.7 distinct 去重示例

```json
{
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "Order", "alias": "o" }
  ],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["customerId"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "orderId",
      "function": "count",
      "alias": "totalOrders"
    },
    {
      "type": "object",
      "param": "o",
      "field": "productId",
      "function": "countDistinct",
      "alias": "uniqueProducts"
    },
    {
      "type": "object",
      "param": "o",
      "field": "city",
      "function": "countDistinct",
      "alias": "uniqueCities"
    }
  ]
}
```

#### 4.1.8 having - 聚合后过滤示例

```json
{
  "operation": "AGGREGATE",
  "objects": [{ "objectType": "Order", "alias": "o" }],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["category"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalSales"
    },
    {
      "type": "object",
      "param": "o",
      "field": "id",
      "function": "count",
      "alias": "orderCount"
    }
  ],
  "having": {
    "and": [
      {"gte": {"totalSales": 10000}},
      {"gte": {"orderCount": 50}}
    ]
  }
}
```

**说明**：`conditions` 与 `having` 的区别：
- `conditions` - 在聚合前过滤源数据
- `having` - 对聚合结果进行过滤

#### 4.1.9 聚合结果排序示例

```json
{
  "operation": "AGGREGATE",
  "objects": [{ "objectType": "Order", "alias": "o" }],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "fields": ["category"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalSales"
    }
  ],
  "orders": [
    {"field": "totalSales", "direction": "DESC"}
  ],
  "maxResults": 10
}
```

#### 4.1.10 嵌套查询聚合

AGGREGATE 操作支持通过顶层 `sourceQuery` 定义嵌套查询，使聚合数据源从一个子查询的中间结果集获取。

**使用约束**：
- `objects` 和 `sourceQuery` **互斥**，只能使用其一
- 使用 `sourceQuery` 时，`objects` 仅用于定义输出结果的对象类型和别名
- 聚合字段 (`field`) 引用 `sourceQuery.returns` 中定义的返回字段名称

**适用场景**：
- 需要先通过复杂条件查询获取对象子集，再进行聚合统计
- 需要从源对象经过子查询过滤后，再对结果进行汇总分析
- 需要对查询结果进行二次加工后再聚合

**DSL 结构**：

在顶层 `sourceQuery` 中定义嵌套查询：

```json
{
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "OutputObject",
      "alias": "o"
    }
  ],
  "sourceQuery": [{
    "outputAs": "order_sub",
    "operation": "QUERY",
    "objects": [{ "objectType": "SourceObject", "alias": "s" }],
    "conditions": {...},
    "returns": [...]
  }],
  "returns": [
    {
      "type": "object",
      "param": "o",
      "field": "resultField",
      "function": "sum",
      "alias": "totalSum"
    }
  ]
}
```

**sourceQuery 字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| **sourceQuery** | array | 否（与 objects 二选一） | 嵌套查询定义数组，查询结果作为聚合数据源 |
| **sourceQuery[].outputAs** | string | 是 | 中间表名，供外层查询引用（如 "order_sub"） |
| **sourceQuery[].operation** | enum | 是 | 查询类型：`QUERY` 或 `MULTI_OBJECT_QUERY` |
| **sourceQuery[].objects** | array | 是 | 子查询的目标对象配置 |
| **sourceQuery[].conditions** | object | 否 | 子查询的条件表达式 |
| **sourceQuery[].returns** | array | 否 | 子查询的返回字段定义（聚合字段来源） |
| **sourceQuery[].orders** | array | 否 | 子查询的排序规则 |
| **sourceQuery[].maxResults** | integer | 否 | 子查询返回的最大记录数，默认 100000 |

**使用约束**：
- `objects` 和 `sourceQuery` **互斥**，只能使用其一
- 使用 `sourceQuery` 时，`objects` 仅用于定义输出结果的对象类型和别名
- `sourceQuery.outputAs` 为必填，用于在外层查询中引用子查询结果
- 聚合字段 (`field`) 引用 `sourceQuery.returns` 中定义的返回字段名称
- 外层查询通过 `outputAs` 作为表名访问子查询结果

**SQL 转换示意**：

```sql
-- 子查询：sourceQuery
SELECT id, amount, customerId
FROM "Order" AS r
WHERE r.status = 'completed'

-- 外层查询：使用 outputAs 作为中间表
SELECT
  SUM(amount) AS totalSales,
  COUNT(id) AS orderCount
FROM order_sub
```

**示例 1：嵌套 QUERY 聚合**

```json
{
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "OrderStat",
      "alias": "o"
    }
  ],
  "sourceQuery": [{
    "outputAs": "order_sub",
    "operation": "QUERY",
    "objects": [{ "objectType": "Order", "alias": "r" }],
    "conditions": {
      "objectType": "Order",
      "property": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    "returns": [
      {"type": "object", "param": "r", "fields": ["id", "amount", "customerId"]}
    ]
  },
  "returns": [
    {
      "type": "object",
      "param": "o",
      "field": "amount",
      "function": "sum",
      "alias": "totalSales"
    },
    {
      "type": "object",
      "param": "o",
      "field": "id",
      "function": "count",
      "alias": "orderCount"
    }
  ]
}
```

**示例 2：嵌套 MULTI_OBJECT_QUERY 聚合**

```json
{
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "RevenueAnalysis",
      "alias": "a"
    }
  ],
  "sourceQuery": [{
    "outputAs": "revenue_source",
    "operation": "MULTI_OBJECT_QUERY",
    "objects": [
      { "objectType": "Customer", "alias": "c" },
      { "objectType": "Order", "alias": "o" }
    ],
    "conditions": {
      "relation": "AND",
      "children": [
        {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]}
      ]
    },
    "returns": [
      {"type": "object", "param": "c", "fields": ["id", "name", "region"]},
      {"type": "object", "param": "o", "fields": ["id", "amount", "orderDate"]}
    ]
  },
  "returns": [
    {
      "type": "object",
      "param": "a",
      "fields": ["region"],
      "function": "groupBy"
    },
    {
      "type": "object",
      "param": "a",
      "field": "amount",
      "function": "sum",
      "alias": "totalRevenue"
    },
    {
      "type": "object",
      "param": "a",
      "field": "amount",
      "function": "avg",
      "alias": "avgOrderValue"
    },
    {
      "type": "object",
      "param": "a",
      "field": "id",
      "function": "countDistinct",
      "alias": "customerCount"
    }
  ]
}
```

**示例 3：带分组维度的嵌套查询聚合**

```json
{
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "RegionReport",
      "alias": "r"
    }
  ],
  "sourceQuery": [{
    "outputAs": "sales_report",
    "operation": "QUERY",
    "objects": [{ "objectType": "SalesOrder", "alias": "s" }],
    "conditions": {
      "objectType": "SalesOrder",
      "property": "orderDate",
      "operator": "BETWEEN",
      "values": ["2024-01-01", "2024-12-31"]
    },
    "returns": ["region", "category", "amount", "quantity"]
  }],
  "aggregations": {
    "groupBy": {
      "fields": ["region", "category"]
    },
    "aggregations": [
      {
        "field": "amount",
        "function": "sum",
        "alias": "regionalSales"
      },
      {
        "field": "quantity",
        "function": "sum",
        "alias": "totalQuantity"
      }
    ]
  }
}
```

**响应结果**：

```json
{
  "data": [
    {
      "metrics": [
        {"name": "regionalSales", "value": 150000},
        {"name": "totalQuantity", "value": 500}
      ],
      "group": {
        "region": "华东",
        "category": "电子产品"
      }
    },
    {
      "metrics": [
        {"name": "regionalSales", "value": 85000},
        {"name": "totalQuantity", "value": 320}
      ],
      "group": {
        "region": "华东",
        "category": "服装"
      }
    }
  ]
}
```

> **说明**：
> - `sourceQuery` 的执行结果作为聚合计算的数据源
> - `objects` 仅用于定义输出结果的对象类型和别名
> - 聚合字段 (`field`) 引用 `sourceQuery.returns` 中定义的返回字段名称
> - `objects` 和 `sourceQuery` 互斥，只能使用其一

---

### 4.2 聚合函数

| 函数 | 说明 | 输入类型 | 输出类型 |
|------|------|----------|----------|
| count | 计数 | 任意 | integer |
| countDistinct | 去重计数 | 任意 | integer |
| sum | 求和 | numeric | numeric |
| avg | 平均值 | numeric | double |
| min | 最小值 | 任意 | 同输入 |
| max | 最大值 | 任意 | 同输入 |
| first | 第一个 | 任意 | 同输入 |
| last | 最后一个 | 任意 | 同输入 |
| arrayAgg | 聚合为数组 | 任意 | array |

#### 4.2.1 聚合响应结构

聚合操作的响应采用以下结构：

```json
{
  "data": [
    {
      "metrics": [
        {
          "name": "metricAlias",
          "value": 123
        }
      ],
      "group": {
        "fieldName": "groupValue"
      }
    }
  ]
}
```

**响应结构说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data | array | 聚合结果数组 |
| data[].metrics | array | 指标数组，每个指标包含名称和值 |
| data[].metrics[].name | string | 指标别名（对应 aggregation 中的 alias） |
| data[].metrics[].value | number | 聚合计算结果值 |
| data[].group | object | 分组键值对，key 为字段名，value 为该组的分组值 |

#### 4.2.2 完整响应示例

**请求**：
```json
{
  "operation": "AGGREGATE",
  "objects": [{ "objectType": "Employee", "alias": "e" }],
  "aggregations": {
    "groupBy": {
      "fields": ["city", "department"]
    },
    "aggregations": [
      {
        "field": "tenure",
        "function": "min",
        "alias": "min_tenure"
      },
      {
        "field": "tenure",
        "function": "avg",
        "alias": "avg_tenure"
      },
      {
        "field": "id",
        "function": "count",
        "alias": "headcount"
      }
    ]
  }
}
```

**响应**：
```json
{
  "data": [
    {
      "metrics": [
        {
          "name": "min_tenure",
          "value": 1
        },
        {
          "name": "avg_tenure",
          "value": 3.5
        },
        {
          "name": "headcount",
          "value": 45
        }
      ],
      "group": {
        "city": "New York City",
        "department": "Engineering"
      }
    },
    {
      "metrics": [
        {
          "name": "min_tenure",
          "value": 2
        },
        {
          "name": "avg_tenure",
          "value": 4.2
        },
        {
          "name": "headcount",
          "value": 32
        }
      ],
      "group": {
        "city": "San Francisco",
        "department": "Engineering"
      }
    },
    {
      "metrics": [
        {
          "name": "min_tenure",
          "value": 0
        },
        {
          "name": "avg_tenure",
          "value": 1.8
        },
        {
          "name": "headcount",
          "value": 28
        }
      ],
      "group": {
        "city": "New York City",
        "department": "Sales"
      }
    }
  ]
}
```

#### 4.2.3 全局聚合响应（无分组）

```json
{
  "data": [
    {
      "metrics": [
        {
          "name": "totalSales",
          "value": 1500000
        },
        {
          "name": "avgOrderValue",
          "value": 1250.5
        },
        {
          "name": "orderCount",
          "value": 1200
        },
        {
          "name": "minOrder",
          "value": 50
        },
        {
          "name": "maxOrder",
          "value": 9999
        }
      ],
      "group": {}
    }
  ]
}
```

#### 4.2.4 带分组的聚合响应

```json
{
  "data": [
    {
      "metrics": [
        {
          "name": "totalSales",
          "value": 500000
        },
        {
          "name": "orderCount",
          "value": 500
        }
      ],
      "group": {
        "category": "Electronics",
        "region": "华东"
      }
    },
    {
      "metrics": [
        {
          "name": "totalSales",
          "value": 300000
        },
        {
          "name": "orderCount",
          "value": 350
        }
      ],
      "group": {
        "category": "Clothing",
        "region": "华东"
      }
    }
  ],
  "metadata": {
    "totalGroups": 8,
    "hasMore": true,
    "nextOffset": 2
  }
}
```

---

### 4.3 聚合示例

```json
{
  "operation": "AGGREGATE",
  "objects": [{ "objectType": "Order", "alias": "o" }],
  "conditions": {
    "objectType": "Order",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "aggregations": {
    "groupBy": {
      "fields": ["product.category", "region"]
    },
    "aggregations": [
      {
        "field": "amount",
        "function": "sum",
        "alias": "totalSales"
      },
      {
        "field": "id",
        "function": "count",
        "alias": "orderCount"
      },
      {
        "field": "amount",
        "function": "avg",
        "alias": "avgAmount"
      }
    ]
  }
}
```

---

## 5. 创建操作（CREATE）

> **前置说明**：CREATE 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义（第2.9节）
> - `mutation` - 变更操作定义（本章节）
> - `extensions` - 扩展信息（可选）

CREATE 操作使用 `mutation` 块定义创建数据，支持单对象创建和批量创建。

### 5.1 操作概述

CREATE 操作用于创建新对象，支持单对象创建和批量创建。

```
┌─────────────────────────────────────────────────────────────┐
│                     CREATE 操作流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐     ┌──────────────┐     ┌───────────┐  │
│   │ 单对象创建    │     │ 批量创建     │     │ 响应返回  │  │
│   │ data{}       │────▶│ batch[]      │────▶│ created[] │  │
│   └──────────────┘     └──────────────┘     └───────────┘  │
│                                                             │
│   主键处理：                                               │
│   • 指定 objectKey → 使用指定主键                          │
│   • 指定 compositeKey → 使用复合主键                       │
│   • 不指定主键 → 系统自动生成主键                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 完整结构定义（JSON Schema）

以下 JSON Schema 定义了 CREATE 操作的有效结构：

```json
{
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "mutation": {
    "type": "object",
    "properties": {
      "data": {
        "type": "object",
        "description": "单对象创建数据",
        "properties": {
          "objectKey": {
            "type": "object",
            "description": "对象主键（简单主键），若不指定则自动生成"
          },
          "compositeKey": {
            "type": "object",
            "description": "复合主键，KV 结构"
          },
          "properties": {
            "type": "object",
            "description": "对象属性键值对"
          }
        }
      },
      "batch": {
        "type": "array",
        "description": "批量创建数据数组",
        "items": {
          "type": "object",
          "properties": {
            "objectKey": {"type": "object"},
            "compositeKey": {"type": "object"},
            "properties": {"type": "object"}
          }
        }
      },
      "options": {
        "type": "object",
        "description": "创建选项"
      }
    },
    "oneOf": [
      {"required": ["data"]},
      {"required": ["batch"]}
    ]
  }
}
```

| mutation.batch[].properties | object | 是 | 单个对象的属性 |
| mutation.options | object | 否 | 创建选项 |

### 5.4 创建选项（options）

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| batchSize | integer | 100 | 每批处理数量 |
| continueOnFailure | boolean | false | 单个失败时是否继续处理其他 |
| skipValidation | boolean | false | 跳过数据验证 |
| generateTimestamps | boolean | true | 自动生成 createdAt/updatedAt |
| onDuplicateKey | string | "error" | 主键冲突处理：error / update / ignore |
| returnCreated | boolean | false | 是否返回创建的对象数据 |

### 5.5 单对象创建

#### 5.5.1 指定主键创建

```json
{
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "mutation": {
    "data": {
      "by": {"id": "prod_001"},
      "properties": {
        "name": "iPhone 16",
        "price": 8999,
        "status": "active",
        "category": "electronics",
        "stock": 100
      }
    }
  }
}
```

#### 5.5.2 复合主键创建

```json
{
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "mutation": {
    "data": {
      "byComposite": {"sourceSystem": "ERP", "orderId": "ORD-001"},
      "properties": {
        "sourceSystem": "ERP",
        "orderId": "ORD-20240301-001",
        "customerId": "cust_001",
        "amount": 19997,
        "status": "pending"
      }
    }
  }
}
```

#### 5.5.3 无指定主键创建（自动生成）

```json
{
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
        "name": "新产品",
        "price": 999,
        "category": "electronics"
      }
    }
  }
}
```

### 5.6 批量创建

#### 5.6.1 批量创建简单主键对象

```json
{
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "mutation": {
    "batch": [
      {
        "objectKey": {"id": "prod_002"},
        "properties": {
          "name": "MacBook Pro",
          "price": 19999,
          "category": "electronics"
        }
      },
      {
        "objectKey": {"id": "prod_003"},
        "properties": {
          "name": "iPad",
          "price": 4999,
          "category": "electronics"
        }
      },
      {
        "objectKey": {"id": "prod_004"},
        "properties": {
          "name": "Apple Watch",
          "price": 2999,
          "category": "wearables"
        }
      }
    ],
    "options": {
      "batchSize": 100,
      "continueOnFailure": true,
      "returnCreated": true
    }
  }
}
```

#### 5.6.2 批量创建复合主键对象

```json
{
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "OrderItem",
      "alias": "oi"
    }
  ],
  "mutation": {
    "batch": [
      {
        "compositeKey": {"sourceSystem": "ERP", "orderId": "ORD-001", "productId": "PROD-001"},
        "properties": {
          "sourceSystem": "ERP",
          "orderId": "ORD-001",
          "productId": "PROD-001",
          "quantity": 2,
          "unitPrice": 8999
        }
      },
      {
        "compositeKey": {"sourceSystem": "ERP", "orderId": "ORD-001", "productId": "PROD-002"},
        "properties": {
          "sourceSystem": "ERP",
          "orderId": "ORD-001",
          "productId": "PROD-002",
          "quantity": 1,
          "unitPrice": 19999
        }
      }
    ]
  }
}
```

### 5.7 批量创建选项示例

```json
{
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "mutation": {
    "batch": [...],
    "options": {
      "batchSize": 100,
      "continueOnFailure": true,
      "skipValidation": false,
      "generateTimestamps": true,
      "onDuplicateKey": "update",
      "returnCreated": true
    }
  }
}
```

### 5.8 CREATE 响应格式

#### 5.8.1 成功响应

```json
{
  "success": true,
  "data": {
    "created": [
      {
        "objectKey": {"id": "prod_002"},
        "compositeKey": null,
        "etag": "\"abc123\"",
        "object": {
          "id": "prod_002",
          "name": "MacBook Pro",
          "price": 19999,
          "createdAt": "2024-03-01T10:00:00Z"
        }
      }
    ],
    "failed": [],
    "summary": {
      "totalRequested": 3,
      "totalCreated": 3,
      "totalFailed": 0
    }
  },
  "metadata": {
    "executionTime": 150,
    "transactionId": "txn_create_001"
  }
}
```

#### 5.8.2 部分失败响应

```json
{
  "success": false,
  "data": {
    "created": [
      {
        "objectKey": {"id": "prod_002"},
        "etag": "\"abc123\""
      }
    ],
    "failed": [
      {
        "index": 1,
        "objectKey": {"id": "prod_003"},
        "error": {
          "code": "VALIDATION_ERROR",
          "message": "价格不能为空",
          "field": "price"
        }
      },
      {
        "index": 2,
        "objectKey": {"id": "prod_004"},
        "error": {
          "code": "DUPLICATE_KEY",
          "message": "主键已存在",
          "existingKey": "prod_004"
        }
      }
    ],
    "summary": {
      "totalRequested": 3,
      "totalCreated": 1,
      "totalFailed": 2
    }
  }
}
```

#### 5.8.3 主键冲突响应

```json
{
  "success": false,
  "error": {
    "code": "DUPLICATE_KEY",
    "message": "对象主键已存在",
    "details": {
      "objectType": "Product",
      "objectKey": {"id": "prod_001"},
      "compositeKey": null
    }
  }
}
```

### 5.9 字段类型支持（Follow本体模型）

| 类型 | 示例值 | 说明 |
|------|--------|------|
| string | "iPhone 16" | 字符串 |
| integer | 100 | 整数 |
| number | 99.99 | 浮点数 |
| boolean | true | 布尔值 |
| array | ["a", "b", "c"] | 字符串数组 |
| object | {"key": "value"} | 嵌套对象 |
| datetime | "2024-03-01T10:00:00Z" | ISO 8601 日期时间 |
| null | null | 空值 |

### 5.10 CREATE 操作速查

| 场景 | 必填字段 | 可选字段 |
|------|----------|----------|
| 单对象（简单主键） | target.objectType, mutation.data.properties | mutation.data.objectKey, options |
| 单对象（复合主键） | target.objectType, mutation.data.properties | mutation.data.compositeKey, options |
| 批量创建 | target.objectType, mutation.batch[].properties | mutation.batch[].objectKey, options |

---

## 6. 更新操作（UPDATE）

> **前置说明**：UPDATE 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义，支持主键或条件定位（第2.9节）
> - `conditions` - 统一条件表达式，用于批量条件更新（第2.3节）
> - `mutation` - 变更操作定义（本章节）
> - `extensions` - 扩展信息（可选）

UPDATE 操作使用 `mutation` 块定义更新内容，使用 `conditions` 定义批量更新条件。

### 6.1 操作概述

UPDATE 操作用于更新现有对象的属性，支持：
- 单对象更新（通过 `objects[].by` 指定主键）
- 批量条件更新（通过顶层 `conditions`）
- 部分更新（只更新指定字段）
- 全量替换
- 表达式更新（计算字段值）
- 数组操作（追加/移除数组元素）

```
┌─────────────────────────────────────────────────────────────┐
│                     UPDATE 操作流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   单对象更新：                                              │
│   objects[].by + mutation.set/unset/increment               │
│                                                             │
│   复合主键更新：                                            │
│   objects[].by (compositeKey) + mutation.set                │
│                                                             │
│   批量条件更新：                                            │
│   conditions + mutation.set                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 完整结构定义（JSON Schema）

以下 JSON Schema 定义了 UPDATE 操作的有效结构：

```json
{
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "conditions": {...},
  "mutation": {
    "type": "object",
    "properties": {
      "by": {
        "type": "object",
        "description": "单对象主键定位，与 conditions 二选一"
      },
      "byList": {
        "type": "array",
        "description": "批量主键定位，批量更新多个对象"
      },
      "set": {
        "type": "object",
        "description": "要设置的字段及值"
      },
      "unset": {
        "type": "array",
        "description": "要移除的字段列表",
        "items": {"type": "string"}
      },
      "increment": {
        "type": "object",
        "description": "数值字段递增（正数）或递减（负数）"
      },
      "arrayOps": {
        "type": "object",
        "description": "数组操作：push、pop、pull 等"
      },
      "options": {
        "type": "object",
        "description": "更新选项"
      }
    },
    "anyOf": [
      {"required": ["by"]},
      {"required": ["byList"]}
    ]
  }
}
```

### 6.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **objects** | array | 是 | 对象实例定义数组，详见第2.9节 |
| **conditions** | object | 否 | 统一条件表达式，用于批量条件更新（详见第2.3节），与 mutation.by/byList 二选一 |
| **mutation** | object | 是 | 变更定义节点 |
| mutation.by | object | by/byList/conditions 三选一 | 主键定位（KV 结构），如 `{"id": "prod_001"}` |
| mutation.byList | array | by/byList/conditions 三选一 | 批量主键定位 |
| mutation.set | object | set/unset/increment/arrayOps 至少一个 | 要设置的字段及值 |
| mutation.unset | array | set/unset/increment/arrayOps 至少一个 | 要移除的字段列表 |
| mutation.increment | object | set/unset/increment/arrayOps 至少一个 | 数值字段递增 |
| mutation.arrayOps | object | set/unset/increment/arrayOps 至少一个 | 数组操作 |
| mutation.options | object | 否 | 更新选项 |

### 6.4 更新选项（options）

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| updateMode | string | "partial" | partial=部分更新, full=全量替换 |
| upsertIfNotFound | boolean | false | 不存在时是否创建 |
| returnUpdated | boolean | false | 是否返回更新后的数据 |
| returnBeforeState | boolean | false | 是否返回更新前的数据 |
| validationMode | string | "strict" | strict=严格验证, relaxed=宽松验证 |

### 6.5 单对象更新

#### 6.5.1 简单主键更新

```json
{
  "version": "1.8.0",
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "set": {
      "price": 7999,
      "status": "active"
    },
    "unset": ["discount", "expiredAt"],
    "increment": {
      "viewCount": 1,
      "version": 1
    }
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| set | 要设置的字段及新值，覆盖旧值 |
| unset | 要移除的字段列表，设为 null 或删除 |
| increment | 数值字段递增，支持正数（增）或负数（减） |

#### 6.5.2 复合主键更新

```json
{
  "version": "1.8.0",
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"sourceSystem": "ERP", "orderId": "ORD-001"}
    }
  ],
  "mutation": {
    "set": {
      "status": "shipped",
      "shippedAt": "$now()",
      "trackingNo": "SF123456789"
    }
  }
}
```

### 6.6 批量条件更新

```json
{
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "conditions": {
    "objectType": "Product",
    "property": "status",
    "operator": "EQ",
    "values": ["inactive"]
  },
  "mutation": {
    "set": {
      "status": "archived",
      "archivedAt": "$now()"
    }
  }
}
```

### 6.7 表达式更新

支持使用表达式动态计算字段值：

```json
{
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "mutation": {
    "set": {
      "totalAmount": {
        "$add": ["$current.totalAmount", "$input.shippingFee"]
      },
      "version": {"$inc": 1},
      "updatedAt": "$now()"
    }
  }
}
```

**表达式操作符**：

| 操作符 | 说明 | 示例 |
|--------|------|------|
| $add | 加法 | `$add: ["$field", 10]` |
| $sub | 减法 | `$sub: ["$field", 5]` |
| $multiply | 乘法 | `$multiply: ["$field", 0.9]` |
| $divide | 除法 | `$divide: ["$field", 2]` |
| $inc | 递增 | `$inc: 1` |
| $dec | 递减 | `$dec: 1` |
| $concat | 字符串拼接 | `$concat: ["$field", "_v2"]` |
| $upper | 转大写 | `$upper: "$field"` |
| $lower | 转小写 | `$lower: "$field"` |
| $now | 当前时间 | `$now()` |
| $uuid | 生成 UUID | `$uuid()` |

### 6.8 条件更新（case）

根据条件设置不同的值：

```json
{
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "mutation": {
    "set": {
      "$case": [
        {
          "when": {"gte": {"totalAmount": 1000}},
          "then": {
            "level": "vip",
            "discountRate": 0.15,
            "points": {"$add": ["$current.points", 100]}
          }
        },
        {
          "when": {"gte": {"totalAmount": 500}},
          "then": {
            "level": "silver",
            "discountRate": 0.05,
            "points": {"$add": ["$current.points", 50]}
          }
        },
        {
          "else": {
            "level": "normal",
            "discountRate": 0,
            "points": {"$add": ["$current.points", 10]}
          }
        }
      ]
    }
  }
}
```

### 6.9 数组更新操作

```json
{
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "arrayOps": {
      "tags": {
        "$push": ["新标签", "热门"]
      },
      "prices": {
        "$push": {
          "effectiveDate": "$now()",
          "amount": 99.00
        }
      },
      "viewCount": {
        "$inc": 1
      }
    }
  }
}
```

**数组操作符**：

| 操作符 | 说明 | 示例 |
|--------|------|------|
| $push | 追加元素 | `$push: ["a", "b"]` |
| $pushAll | 追加多个 | `$pushAll: ["a", "b", "c"]` |
| $pop | 移除末尾 | `$pop: 1` |
| $shift | 移除开头 | `$shift: -1` |
| $pull | 移除匹配 | `$pull: {"status": "expired"}` |
| $addToSet | 添加去重 | `$addToSet: "newItem"` |
| $pullAll | 移除多个 | `$pullAll: ["a", "b"]` |
| $inc | 递增 | `$inc: 1` |

### 6.10 并发控制

```json
{
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "set": {
      "price": 7999
    }
  },
  "extensions": {
    "ifMatch": "\"etag-abc123\""
  }
}
```

### 6.11 UPDATE 响应格式

#### 6.11.1 成功响应

```json
{
  "success": true,
  "data": {
    "updated": [
      {
        "objectKey": {"id": "prod_001"},
        "compositeKey": null,
        "etag": "\"def456\"",
        "changedFields": ["price", "updatedAt"]
      }
    ],
    "summary": {
      "totalMatched": 1,
      "totalUpdated": 1,
      "totalSkipped": 0,
      "totalFailed": 0
    }
  },
  "metadata": {
    "executionTime": 80
  }
}
```

#### 6.11.2 批量更新响应

```json
{
  "success": true,
  "data": {
    "updated": [
      {"objectKey": "prod_001", "changedFields": ["status"]},
      {"objectKey": "prod_002", "changedFields": ["status"]},
      {"objectKey": "prod_003", "changedFields": ["status"]}
    ],
    "summary": {
      "totalMatched": 150,
      "totalUpdated": 150,
      "totalSkipped": 0,
      "totalFailed": 0
    }
  }
}
```

#### 6.11.3 并发冲突响应

```json
{
  "success": false,
  "error": {
    "code": "OPTIMISTIC_LOCK_FAILURE",
    "message": "对象已被其他操作修改",
    "details": {
      "objectType": "Product",
      "objectKey": {"id": "prod_001"},
      "expectedEtag": "\"etag-abc123\"",
      "currentEtag": "\"xyz789\"",
      "lastModified": "2024-03-01T12:30:00Z"
    }
  }
}
```

#### 6.11.4 对象不存在响应

```json
{
  "success": false,
  "error": {
    "code": "OBJECT_NOT_FOUND",
    "message": "对象不存在",
    "details": {
      "objectType": "Product",
      "objectKey": {"id": "prod_999"},
      "compositeKey": null
    }
  }
}
```

### 6.12 UPDATE 操作速查

| 场景 | 必填字段 | 说明 |
|------|----------|------|
| 单对象（简单主键） | objects[].by, mutation.set | 必须指定主键和更新内容 |
| 单对象（复合主键） | objects[].by (compositeKey), mutation.set | 复合主键用 KV 结构 |
| 批量条件更新 | conditions, mutation.set | 根据条件更新多个对象（conditions 详见第2.3节） |
| 部分更新 | mutation.set | 只更新指定字段 |
| 全量替换 | mutation.set + options.updateMode: "full" | 替换整个对象 |
| 递增字段 | mutation.increment | 数值字段递增/递减 |
| 数组操作 | mutation.arrayOps | 追加/移除数组元素 |

---

## 7. 删除操作（DELETE）

> **前置说明**：DELETE 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义，支持主键或条件定位（第2.9节）
> - `conditions` - 统一条件表达式，用于批量条件删除（第2.3节）
> - `mutation` - 变更操作定义（本章节）

### 7.1 操作概述

DELETE 操作用于删除对象，支持：
- 单对象删除（通过 objectKey 或 compositeKey）
- 批量条件删除（通过 filter）
- 软删除（标记删除）
- 硬删除（物理删除）
- 级联删除关联对象

```
┌─────────────────────────────────────────────────────────────┐
│                     DELETE 操作流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   单对象删除：                                              │
│   target.objectKey + mutation                               │
│                                                             │
│   复合主键删除：                                            │
│   target.compositeKey + mutation                            │
│                                                             │
│   批量条件删除：                                            │
│   conditions + mutation                                     │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  deleteMode 说明                                    │   │
│   │  • soft  → 标记 status='deleted'（默认）            │   │
│   │  • hard  → 物理删除数据                             │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
