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

