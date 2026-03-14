# 本体对象操作语言（OQL）DSL 规范

---

## 阅读导航

- 第 1 章：设计原则与多数据源映射
- 第 2 章：统一顶层结构与通用字段（`objects` / `conditions` / `returns` / `orders`）
- 第 3-11 章：各操作类型（查询、聚合、写入、关联、批量）
- 第 12-13 章：执行选项与表达式
- 第 14-16 章：完整示例与 DSL→物理查询转换
- 附录：关键字速查与字段参考

> 建议阅读顺序：先读第 2 章统一结构，再按操作类型阅读对应章节。

---

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


**跨数据源查询支持边界（建议）**：
- 支持：单对象跨源属性拼装、过滤下推、聚合下推、有限字段级 JOIN。
- 限制：超大结果集跨源全量 JOIN、跨源分布式事务强一致写入、不同源时区/精度不兼容字段直接比较。
- 建议：优先单源下推，跨源只做必要字段合并；对不可下推场景在响应 metadata 标注 degraded=true。


---

## 2. 统一顶层结构

> **设计原则**：OQL DSL 采用**顶层通用字段 + 操作专用块**的统一结构设计。
> - 顶层字段（通用）：所有操作共享的结构
> - 操作专用块（按 operation 激活）：根据 operation 类型选择性使用

### 2.1 完整结构定义

```json
{
  "version": "1.0",
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

> **说明**：第1.0 版本移除了 `targets` 字段，将多对象查询能力统一到 `objects` 数组中。通过 `objects[].byList` 支持批量主键查询，通过多个对象类型配置支持多对象联合查询。

> **命名规范说明（统一写法）**：
> - 规范主写法：`objects[]` + `by` / `byComposite`
> - 历史写法仅用于背景说明，不作为规范字段使用
> - 新增/改写示例统一使用规范主写法

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
- 原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明
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
  "version": "1.0",
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
  "version": "1.0",
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
  "version": "1.0",
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
  "version": "1.0",
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
  "version": "1.0",
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
  "version": "1.0",
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

#### 2.12.2 响应格式

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

#### 2.12.3 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| data | array | 对象列表 |
| data[].objectType | string | 对象类型名称 |
| data[].rid | string | 对象资源标识符（全局唯一） |
| data[].properties | object | 对象属性，键值对形式 |
| metadata.totalCount | integer | 符合条件对象的总数量（可选） |
| metadata.executionTime | integer | 执行时间（毫秒） |

#### 2.12.4 结果数量限制

单次查询通过 `maxResults` 控制最大返回数量限制：

```json
{
  "version": "1.0",
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
- OQL v1.0 移除了分页语法，统一使用 `maxResults` 限制结果数量

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

#### 2.12.5 使用属性过滤条件查询（无需指定主键）

QUERY 操作通过顶层的 `conditions` 进行属性过滤查询，无需指定主键。

**请求示例（使用 conditions 查询）**：

```json
{
  "version": "1.0",
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
  "version": "1.0",
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

### 2.13 多对象查询（MULTI_OBJECT_QUERY）

当需要在一个查询请求中查询多个对象的属性时，使用 `MULTI_OBJECT_QUERY` 操作类型。

### 2.13.1 使用场景

1. **同表多对象查询**：多个对象类型对应同一个数据库表，合并查询返回
2. **跨对象条件查询**：对象A的属性作为对象B的过滤条件（如用户→小区）
3. **关联属性聚合**：从不同对象类型聚合数据进行联合分析

### 2.13.2 objects 字段定义（多对象定位）

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

### 2.13.3 query 块结构（whereFrom 跨对象条件查询）

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

### 2.13.4 conditions 统一条件表达式

> **说明**：`conditions` 字段定义详见 [第2.3节](#23-conditions---统一条件表达式)。

### 2.13.5 returns 返回字段投影

> **说明**：`returns` 字段定义详见 [第2.4节](#24-returns---返回字段投影)。

### 2.13.6 sourceQuery 嵌套查询

> **说明**：`sourceQuery` 字段定义详见 [第2.5.1节](#251-sourcequery---嵌套查询)，包含完整的字段定义、多层嵌套说明和使用示例。

MULTI_OBJECT_QUERY 操作支持通过顶层 `sourceQuery` 定义嵌套查询，使查询数据源从一个子查询的中间结果集获取。

**使用约束**：
- 原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明
- 使用 `sourceQuery` 时，`objects` 可以为空，也可以为其他对象类型，用于满足多对象类型查询的诉求
- 子查询结构与顶层结构一致，支持多层嵌套

### 2.13.7 同表多对象查询示例

**场景**：User 和 Customer 两个对象类型对应同一张表 person

```json
{
  "version": "1.0",
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

#### 2.13.7.1 同表多对象联合查询（User + Cell 关联表场景）

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
  "version": "1.0",
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

#### 2.13.7.2 跨表外键关联查询（User + Cell 外键关联场景）

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
  "version": "1.0",
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

### 2.13.8 跨对象条件查询示例（用户→小区）

**场景**：通过用户 id 查询该用户关联的小区

```json
{
  "version": "1.0",
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

### 2.13.9 多对象查询响应格式

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

### 2.13.10 MySQL SQL 转换示例

以下展示 MULTI_OBJECT_QUERY 如何转换为 MySQL SQL 查询语句。

#### 2.13.10.1 示例一：同表多对象查询

**场景**：User 和 Customer 两个对象类型对应同一个数据库表 `persons`

**DSL 请求**：
```json
{
  "version": "1.0",
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

#### 2.13.10.2 示例二：跨对象条件查询（whereFrom）

**场景**：通过用户 id 查询该用户关联的小区（User.id = Community.ownerId）

**DSL 请求**：
```json
{
  "version": "1.0",
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

#### 2.13.10.3 示例三：跨对象条件查询（多条件过滤）

**场景**：查询状态为"运行中"的设备所在机房的信息

**DSL 请求**：
```json
{
  "version": "1.0",
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

#### 2.13.10.4 示例四：objects + conditions 组合查询

**场景**：查询指定用户组下的所有设备及其关联的机房

**DSL 请求**：
```json
{
  "version": "1.0",
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

#### 2.13.10.5 SQL 转换规则总结

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
  "version": "1.0",
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
- 原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明
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
  "version": "1.0",
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

#### 3.3.1 时序属性概述

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

#### 3.3.2 时序查询结构

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

#### 3.3.3 timeseries 配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|:----:|:----:|------|
| property | string | 是 | 时序属性名，如 `fanSpeed`、`temperature` |
| from | string | 否 | 开始时间（ISO 8601 格式） |
| to | string | 否 | 结束时间（ISO 8601 格式） |
| orderBy | string | 否 | 排序方向：`ASC`（升序）或 `DESC`（降序），默认 ASC |
| limit | integer | 否 | 最大返回点数，默认 100 |
| interpolation | string | 否 | 插值方法：LINEAR / NEAREST / PREVIOUS / NEXT / NONE |

#### 3.3.4 时序数据返回格式

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

#### 3.3.5 完整时序查询示例

**请求**：

```json
{
  "version": "1.0",
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
      "to": "2026-02-07T23:59:59Z"
    },
    "dataPointCount": 7
  }
}
```

#### 3.3.6 时序查询转换为 GQL

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

#### 4.1.2 关键字说明

> **嵌套查询说明**：如需使用嵌套查询，请通过顶层 `sourceQuery` 定义，详见 [4.1.10 嵌套查询聚合](#4110-嵌套查询聚合)。原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明。

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| **objects** | array | 否（与 sourceQuery 二选一） | 直接查询的对象实例定义，详见第2.9节 |
| **sourceQuery** | array | 否（与 objects 二选一） | 嵌套查询定义数组，查询结果作为聚合数据源 |
| **sourceQuery[].outputAs** | string | 是（当 sourceQuery 存在时） | 中间表名，供外层查询引用（如 "order_sub"） |
| **sourceQuery[].operation** | enum | 是（当 sourceQuery 存在时） | 查询类型：`QUERY` 或 `MULTI_OBJECT_QUERY` |
| **sourceQuery[].objects** | array | 是（当 sourceQuery 存在时） | 子查询的目标对象配置 |
| **sourceQuery[].conditions** | object | 否 | 子查询的条件表达式 |
| **sourceQuery[].returns** | array | 否 | 子查询的返回字段定义（聚合字段来源） |
| **sourceQuery[].orders** | array | 否 | 子查询的排序规则 |
| **sourceQuery[].maxResults** | integer | 否 | 子查询返回的最大记录数，默认 100000 |
| **returns** | array | 是 | 返回字段投影定义，聚合函数通过 function 指定 |
| **returns[].type** | string | 是 | 固定为 "object" |
| **returns[].param** | string | 是 | 对象别名，对应 objects 中的 alias |
| **returns[].fields** | array | 否（与 field 二选一） | 分组字段列表，如 `["category", "region"]` |
| **returns[].field** | string | 否（与 fields 二选一） | 聚合源字段名 |
| **returns[].function** | string | 是 | 聚合函数：groupBy/count/sum/avg/min/max/first/last/arrayAgg |
| **returns[].alias** | string | 否 | 结果字段别名 |
| **returns[].filter** | object | 否 | 聚合条件过滤（只聚合满足条件的记录） |
| **returns[].distinct** | boolean | 否 | 是否去重计数，默认 false |
| **having** | object | 否 | 聚合后过滤条件（对聚合结果过滤） |
| **orders** | array | 否 | 聚合结果排序 |
| **maxResults** | integer | 否 | 最大返回数量，默认 100000，最大 100000 |

> **通用字段说明**：表中 `objects`、`conditions` 等通用字段的详细定义见 [第2章统一顶层结构](#2-统一顶层结构)。`sourceQuery` 相关字段为 AGGREGATE 操作特有，用于定义嵌套查询。

#### 4.1.3 简单聚合示例

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
- 原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明
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
- 原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明
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
> - 原则上 `objects` 与 `sourceQuery` 应二选一；若同层同时出现，则 `sourceQuery` 作为输入数据源，`objects` 仅作为输出对象声明

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
│   • 指定 by → 使用指定主键                          │
│   • 指定 byComposite → 使用复合主键                       │
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
          "by": {
            "type": "object",
            "description": "对象主键（简单主键），若不指定则自动生成"
          },
          "byComposite": {
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
            "by": {"type": "object"},
            "byComposite": {"type": "object"},
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

### 5.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **objects** | array | 是 | 对象实例定义数组，详见第2.9节 |
| **mutation** | object | 是 | 变更定义节点 |
| mutation.data | object | data/batch 二选一 | 单对象创建数据 |
| mutation.data.by | object | 否 | 单主键定位，如 `{"id": "prod_001"}` |
| mutation.data.byComposite | object | 否 | 复合主键，如 `{"sourceSystem": "ERP", "orderId": "ORD-001"}` |
| mutation.data.properties | object | 是 | 对象属性键值对 |
| mutation.batch | array | data/batch 二选一 | 批量创建数据数组 |
| mutation.batch[].by | object | 否 | 单个对象的单主键定位 |
| mutation.batch[].byComposite | object | 否 | 单个对象的复合主键 |
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
        "by": {"id": "prod_002"},
        "properties": {
          "name": "MacBook Pro",
          "price": 19999,
          "category": "electronics"
        }
      },
      {
        "by": {"id": "prod_003"},
        "properties": {
          "name": "iPad",
          "price": 4999,
          "category": "electronics"
        }
      },
      {
        "by": {"id": "prod_004"},
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
        "byComposite": {"sourceSystem": "ERP", "orderId": "ORD-001", "productId": "PROD-001"},
        "properties": {
          "sourceSystem": "ERP",
          "orderId": "ORD-001",
          "productId": "PROD-001",
          "quantity": 2,
          "unitPrice": 8999
        }
      },
      {
        "byComposite": {"sourceSystem": "ERP", "orderId": "ORD-001", "productId": "PROD-002"},
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
        "by": {"id": "prod_002"},
        "byComposite": null,
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
        "by": {"id": "prod_002"},
        "etag": "\"abc123\""
      }
    ],
    "failed": [
      {
        "index": 1,
        "by": {"id": "prod_003"},
        "error": {
          "code": "VALIDATION_ERROR",
          "message": "价格不能为空",
          "field": "price"
        }
      },
      {
        "index": 2,
        "by": {"id": "prod_004"},
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
      "by": {"id": "prod_001"},
      "byComposite": null
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
| 单对象（简单主键） | objects[].objectType, mutation.data.properties | mutation.data.by, options |
| 单对象（复合主键） | objects[].objectType, mutation.data.properties | mutation.data.byComposite, options |
| 批量创建 | objects[].objectType, mutation.batch[].properties | mutation.batch[].by, options |

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
│   objects[].by (byComposite) + mutation.set                │
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
  "version": "1.0",
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
  "version": "1.0",
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
        "by": {"id": "prod_001"},
        "byComposite": null,
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
      {"by": "prod_001", "changedFields": ["status"]},
      {"by": "prod_002", "changedFields": ["status"]},
      {"by": "prod_003", "changedFields": ["status"]}
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
      "by": {"id": "prod_001"},
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
      "by": {"id": "prod_999"},
      "byComposite": null
    }
  }
}
```

### 6.12 UPDATE 操作速查

| 场景 | 必填字段 | 说明 |
|------|----------|------|
| 单对象（简单主键） | objects[].by, mutation.set | 必须指定主键和更新内容 |
| 单对象（复合主键） | objects[].by (byComposite), mutation.set | 复合主键用 KV 结构 |
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
- 单对象删除（通过 by 或 byComposite）
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
│   objects[].by + mutation                               │
│                                                             │
│   复合主键删除：                                            │
│   objects[].byComposite + mutation                            │
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

### 7.2 完整结构定义（JSON Schema）

以下 JSON Schema 定义了 DELETE 操作的有效结构：

```json
{
  "operation": "DELETE",
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
      "deleteMode": {
        "type": "string",
        "description": "删除模式：soft=软删除, hard=硬删除",
        "enum": ["soft", "hard"],
        "default": "soft"
      },
      "cascade": {
        "type": "boolean",
        "description": "是否级联删除关联对象",
        "default": false
      },
      "cascadeLinks": {
        "type": "array",
        "description": "指定要级联删除的关联类型",
        "items": {"type": "string"}
      },
      "permanent": {
        "type": "boolean",
        "description": "永久删除（硬删除后不可恢复）",
        "default": false
      },
      "returnDeleted": {
        "type": "boolean",
        "description": "是否返回删除的对象数据",
        "default": false
      },
      "limit": {
        "type": "integer",
        "description": "限制删除数量（防止误删）"
      }
    },
    "anyOf": [
      {"required": ["by"]},
      {"required": ["conditions"]}
    ]
  }
}
```

### 7.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **objects** | array | 是 | 对象实例定义数组，详见第2.9节 |
| **conditions** | object | 否 | 统一条件表达式，用于批量条件删除（详见第2.3节），与 mutation.by 二选一 |
| **mutation** | object | 是 | 变更定义节点 |
| mutation.by | object | by/conditions 二选一 | 主键定位（KV 结构），如 `{"id": "prod_001"}` |
| mutation.deleteMode | string | 否 | 删除模式：soft（软删除，默认）或 hard（硬删除） |
| mutation.cascade | boolean | 否 | 是否级联删除关联对象，默认 false |
| mutation.cascadeLinks | array | 否 | 指定要级联删除的关联类型 |
| mutation.permanent | boolean | 否 | 永久删除（不可恢复），默认 false |
| mutation.returnDeleted | boolean | 否 | 是否返回删除的对象数据，默认 false |
| mutation.limit | integer | 否 | 限制删除数量（防止误删） |

### 7.4 删除选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| deleteMode | string | "soft" | soft=软删除, hard=硬删除 |
| cascade | boolean | false | 是否级联删除关联对象 |
| cascadeLinks | array | [] | 指定要级联删除的关联类型列表 |
| permanent | boolean | false | 永久删除（硬删除后不可恢复） |
| returnDeleted | boolean | false | 是否返回删除的对象数据 |
| limit | integer | null | 限制删除数量（防止误删） |

### 7.5 单对象删除

#### 7.5.1 简单主键软删除

```json
{
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "deleteMode": "soft",
    "returnDeleted": true
  }
}
```

#### 7.5.2 复合主键软删除

```json
{
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"sourceSystem": "ERP", "orderId": "ORD-001"}
    }
  ],
  "mutation": {
    "deleteMode": "soft"
  }
}
```

#### 7.5.3 硬删除

```json
{
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "TempData",
      "alias": "t",
      "by": {"id": "temp_data_001"}
    }
  ],
  "mutation": {
    "deleteMode": "hard",
    "permanent": true
  }
}
```

### 7.6 批量条件删除

```json
{
  "operation": "DELETE",
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
    "values": ["deleted"]
  },
  "mutation": {
    "deleteMode": "hard",
    "limit": 1000
  }
}
```

### 7.7 级联删除

#### 7.7.1 级联删除关联对象

```json
{
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "mutation": {
    "deleteMode": "hard",
    "cascade": true,
    "cascadeLinks": ["items", "payments", "shippingRecords"],
    "returnDeleted": true
  }
}
```

#### 7.7.2 只删除指定关联

```json
{
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c",
      "by": {"id": "cust_001"}
    }
  ],
  "mutation": {
    "deleteMode": "soft",
    "cascade": true,
    "cascadeLinks": ["orders", "addresses", "paymentMethods"],
    "returnDeleted": true
  }
}
```

### 7.8 DELETE 响应格式

#### 7.8.1 成功响应

```json
{
  "success": true,
  "data": {
    "deleted": [
      {
        "by": {"id": "prod_001"},
        "byComposite": null,
        "object": {
          "id": "prod_001",
          "name": "iPhone 16",
          "price": 8999,
          "status": "deleted",
          "deletedAt": "2024-03-01T12:00:00Z"
        }
      }
    ],
    "summary": {
      "totalMatched": 1,
      "totalDeleted": 1,
      "totalSkipped": 0,
      "totalFailed": 0
    },
    "cascadeDeleted": null
  },
  "metadata": {
    "executionTime": 60
  }
}
```

#### 7.8.2 级联删除响应

```json
{
  "success": true,
  "data": {
    "deleted": [
      {
        "by": {"id": "order_001"},
        "object": {
          "id": "order_001",
          "orderNo": "ORD-20240301-001",
          "status": "deleted"
        }
      }
    ],
    "summary": {
      "totalMatched": 1,
      "totalDeleted": 1,
      "totalSkipped": 0,
      "totalFailed": 0
    },
    "cascadeDeleted": {
      "OrderItem": 5,
      "Payment": 2,
      "ShippingRecord": 1
    }
  }
}
```

#### 7.8.3 批量删除响应

```json
{
  "success": true,
  "data": {
    "deleted": [
      {"by": "prod_001"},
      {"by": "prod_002"},
      {"by": "prod_003"}
    ],
    "summary": {
      "totalMatched": 150,
      "totalDeleted": 150,
      "totalSkipped": 0,
      "totalFailed": 0
    }
  }
}
```

#### 7.8.4 对象不存在响应

```json
{
  "success": false,
  "error": {
    "code": "OBJECT_NOT_FOUND",
    "message": "对象不存在",
    "details": {
      "objectType": "Product",
      "by": {"id": "prod_999"},
      "byComposite": null
    }
  }
}
```

### 7.9 软删除内部实现

软删除实际上是对对象进行更新操作：

```json
{
  "mutation": {
    "set": {
      "status": "deleted",
      "deletedAt": "$now()",
      "deletedBy": "$currentUser()"
    }
  }
}
```

### 7.10 DELETE 操作速查

| 场景 | 必填字段 | 可选字段 |
|------|----------|----------|
| 单对象（简单主键） | objects[].by | mutation.deleteMode, mutation.returnDeleted |
| 单对象（复合主键） | objects[].by (byComposite) | mutation.deleteMode, mutation.returnDeleted |
| 批量条件删除 | conditions | mutation.deleteMode, mutation.limit, mutation.returnDeleted（conditions 详见第2.3节） |
| 级联删除 | objects[] + mutation.cascade | mutation.cascadeLinks, mutation.returnDeleted |
| 硬删除 | objects[] + mutation.deleteMode: "hard" | mutation.permanent |

### 7.11 最佳实践

1. **优先使用软删除**：除非有明确需求，否则使用 `deleteMode: "soft"`
2. **限制批量删除数量**：使用 `limit` 防止误删大量数据
3. **谨慎使用级联删除**：级联删除会删除关联对象，确认业务影响
4. **记录删除操作**：审计日志记录删除操作的用户、时间、原因

---

## 8. 插入或更新（UPSERT）

> **前置说明**：UPSERT 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义，支持主键或条件定位（第2.9节）
> - `mutation` - 变更操作定义（本章节）

### 8.1 操作概述

UPSERT 操作用于**存在时更新、不存在时创建**，是 CREATE 和 UPDATE 的组合。适用于：
- 数据同步场景（同步数据到本体模型）
- 配置管理（存在则更新，不存在则创建）
- 幂等写入（多次执行结果一致）

```
┌─────────────────────────────────────────────────────────────┐
│                     UPSERT 操作流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌───────────────────────────────────────────────────┐     │
│   │                     UPSERT 逻辑                    │     │
│   ├───────────────────────────────────────────────────┤     │
│   │                                                   │     │
│   │   ┌─────────────┐                                  │     │
│   │   │  查询对象   │── 存在 ──▶ UPDATE 现有对象       │     │
│   │   └─────────────┘                                  │     │
│   │         │                                          │     │
│   │         ▼ 不存在                                   │     │
│   │   ┌─────────────┐                                  │     │
│   │   │  CREATE 新  │── 新建对象                       │     │
│   │   └─────────────┘                                  │     │
│   │                                                   │     │
│   └───────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 完整结构定义（JSON Schema）

```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "string",
      "alias": "string",
      "by": {...}  // 单主键
    }
  ],
  "conditions": {...},  // 可选，批量匹配条件
  "mutation": {
    "type": "object",
    "properties": {
      "by": {
        "type": "object",
        "description": "主键定位（KV 结构），与 objects[].by 互斥"
      },
      "batch": {
        "type": "array",
        "description": "批量操作，每项包含主键和 onCreate/onUpdate"
      },
      "batch[].by": {
        "type": "object",
        "description": "批量项的主键"
      },
      "onCreate": {
        "type": "object",
        "description": "对象不存在时创建的属性"
      },
      "onUpdate": {
        "type": "object",
        "description": "对象存在时更新的属性"
      },
      "options": {
        "type": "object",
        "description": "UPSERT 选项"
      }
    }
  }
}
```

### 8.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **objects** | array | 是 | 对象实例定义数组，详见第2.9节 |
| **conditions** | object | 否 | 统一条件表达式，用于批量匹配（详见第2.3节） |
| **mutation** | object | 是 | 变更定义节点 |
| mutation.by | object | 是（单对象时） | 主键定位（KV 结构） |
| mutation.batch | array | 是（批量时） | 批量操作列表 |
| mutation.batch[].by | object | 是 | 批量项主键定位 |
| mutation.onCreate | object | onCreate/onUpdate 至少一个 | 不存在时创建的属性 |
| mutation.onUpdate | object | onCreate/onUpdate 至少一个 | 存在时更新的属性 |
| mutation.options | object | 否 | UPSERT 选项 |

### 8.4 UPSERT 选项（options）

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| updateMode | string | "partial" | partial=部分更新, full=全量替换 |
| updateOnMatch | boolean | true | 匹配到时是否更新 |
| createOnNoMatch | boolean | true | 未匹配到时是否创建 |
| mergeStrategy | string | "overwrite" | 合并策略 |
| returnResult | boolean | true | 是否返回结果详情 |
| skipValidation | boolean | false | 跳过数据验证 |

### 8.5 合并策略（mergeStrategy）

| 策略 | 说明 | 示例场景 |
|------|------|----------|
| **overwrite** | 直接覆盖（默认） | 完全替换旧值 |
| **merge** | 深度合并（嵌套对象） | 部分更新嵌套属性 |
| **keepFirst** | 保留原值 | 只创建不覆盖 |
| **keepLast** | 保留新值 | 以新数据为准 |

### 8.6 单对象 UPSERT

#### 8.6.1 按主键 UPSERT

```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "onCreate": {
      "name": "iPhone 16",
      "price": 8999,
      "category": "electronics",
      "status": "active",
      "createdAt": "$now()"
    },
    "onUpdate": {
      "name": "iPhone 16 Pro",
      "price": 9999,
      "updatedAt": "$now()"
    }
  }
}
```

#### 8.6.2 复合主键 UPSERT

```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "OrderItem",
      "alias": "oi",
      "by": {"sourceSystem": "ERP", "orderId": "ORD-001", "productId": "PROD-001"}
    }
  ],
  "mutation": {
    "onCreate": {
      "quantity": 1,
      "unitPrice": 8999,
      "createdAt": "$now()"
    },
    "onUpdate": {
      "quantity": {"$inc": 1},
      "updatedAt": "$now()"
    }
  }
}
```

### 8.7 多字段匹配 UPSERT

#### 8.7.1 按多个字段匹配

```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": {
    "objectType": "Customer",
    "relation": "AND",
    "children": [
      {"property": "email", "operator": "EQ", "values": ["user@example.com"]},
      {"property": "tenantId", "operator": "EQ", "values": ["tenant_001"]}
    ]
  },
  "mutation": {
    "onCreate": {
      "name": "新用户",
      "level": "normal",
      "createdAt": "$now()"
    },
    "onUpdate": {
      "lastActiveTime": "$now()",
      "loginCount": {"$inc": 1}
    }
  }
}
```

#### 8.7.2 部分更新嵌套对象（merge 策略）

```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "User",
      "alias": "u",
      "by": {"id": "user_001"}
    }
  ],
  "mutation": {
    "onCreate": {
      "name": "张三",
      "profile": {
        "email": "zhangsan@example.com",
        "phone": "13800138000"
      },
      "settings": {
        "theme": "dark",
        "language": "zh-CN"
      }
    },
    "onUpdate": {
      "profile": {
        "phone": "13900139000"
      },
      "settings": {
        "theme": "light"
      }
    },
    "options": {
      "mergeStrategy": "merge"
    }
  }
}
```

### 8.8 批量 UPSERT

```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "SystemConfig",
      "alias": "sc"
    }
  ],
  "mutation": {
    "batch": [
      {
        "by": {"configKey": "MAX_UPLOAD_SIZE", "environment": "production"},
        "onCreate": {"value": "100MB"},
        "onUpdate": {"value": "100MB", "updatedAt": "$now()"}
      },
      {
        "by": {"configKey": "ENABLE_CACHE", "environment": "production"},
        "onCreate": {"value": "true"},
        "onUpdate": {"value": "true"}
      },
      {
        "by": {"configKey": "SESSION_TIMEOUT", "environment": "production"},
        "onCreate": {"value": "3600"},
        "onUpdate": {"value": "3600"}
      }
    ],
    "options": {
      "updateMode": "partial",
      "continueOnFailure": true
    }
  }
}
```

### 8.9 UPSERT 响应格式

#### 8.9.1 创建新对象响应

```json
{
  "success": true,
  "data": {
    "action": "created",
    "by": "prod_001",
    "byComposite": null,
    "etag": "\"abc123\"",
    "object": {
      "id": "prod_001",
      "name": "iPhone 16",
      "price": 8999,
      "status": "active",
      "createdAt": "2024-03-01T10:00:00Z"
    }
  },
  "metadata": {
    "executionTime": 80
  }
}
```

#### 8.9.2 更新现有对象响应

```json
{
  "success": true,
  "data": {
    "action": "updated",
    "by": "prod_001",
    "byComposite": null,
    "etag": "\"def456\"",
    "before": {
      "name": "iPhone 16",
      "price": 7999
    },
    "after": {
      "name": "iPhone 16 Pro",
      "price": 9999
    },
    "changedFields": ["name", "price", "updatedAt"]
  }
}
```

#### 8.9.3 批量 UPSERT 响应

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "matchOn": ["configKey", "environment"],
        "action": "created",
        "by": null,
        "etag": "\"etag_001\""
      },
      {
        "matchOn": ["configKey", "environment"],
        "action": "updated",
        "by": null,
        "changedFields": ["value", "updatedAt"]
      }
    ],
    "summary": {
      "totalProcessed": 2,
      "totalCreated": 1,
      "totalUpdated": 1,
      "totalFailed": 0
    }
  }
}
```

#### 8.9.4 匹配失败响应

```json
{
  "success": true,
  "data": {
    "action": "no_match",
    "matchOn": ["email", "tenantId"],
    "onCreate": {...},
    "onUpdate": {...},
    "message": "未匹配到现有对象，但 createOnNoMatch 为 false"
  }
}
```

### 8.10 UPSERT 操作速查

| 场景 | 必填字段 | 可选字段 |
|------|----------|----------|
| 按主键 UPSERT | objects[].objectType, mutation.by, mutation.onCreate/onUpdate | options |
| 复合主键 UPSERT | objects[].objectType, mutation.byComposite, mutation.onCreate/onUpdate | options |
| 多字段匹配 UPSERT | objects[].objectType, mutation.matchOn, mutation.onCreate/onUpdate | options |
| 批量 UPSERT | objects[].objectType, mutation.batch[].matchOn, mutation.onCreate/onUpdate | options |
| 部分更新嵌套 | mutation + mergeStrategy: "merge" | - |

### 8.11 最佳实践

1. **幂等性保证**：使用相同的 by/matchOn 执行多次，结果一致
2. **选择合适的匹配方式**：
    - 简单主键使用 `by`
    - 联合唯一键使用 `matchOn`
3. **更新策略选择**：
    - 完全替换用 `overwrite`
    - 部分更新嵌套对象用 `merge`
4. **批量操作**：大数据量使用 `continueOnFailure: true` 处理部分失败


## 9. 关联对象查询（LINKED_OBJECT_QUERY）

> **前置说明**：LIST_LINKED_OBJECTS / GET_LINKED_OBJECT 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义（第2.9节）
> - `conditions` - 统一条件表达式（第2.3节）
> - `returns` - 返回字段投影（第2.4节）
> - `orders` - 排序定义（第2.5节）
> - `linkQuery` - 关联查询专用块（[9.7节](#97-linkquery---关联查询过滤)）

> **说明**：OQL v1.0 移除了 Link 操作（CREATE/UPDATE/DELETE Link），因为本体模型中**属性都在对象上，边上没有属性**。对象之间的关联通过 LinkType 在图数据库中表达，关联本身不带属性。关联对象查询用于通过 LinkType 查询与当前对象关联的其他对象。

**LINKED 操作使用 `linkQuery` 专用块**，可通过 ASSOCIATION_QUERY 实现，保留此快捷操作以便 API 路由兼容。

### 9.1 Operation 类型

OQL 提供了两个专门的关联查询 Operation：

| Operation | 说明 | API 对应 |
|----------|------|----------|
| **LIST_LINKED_OBJECTS** | 列出关联对象列表 | `POST /objects/list/linked/{objectType}/{by}/{linkType}` |
| **GET_LINKED_OBJECT** | 获取特定关联对象 | `POST /objects/query/linked/{objectType}/{by}/{linkType}/{linkedObjectType}` |

### 9.2 LIST_LINKED_OBJECTS - 列出关联对象列表（可被 ASSOCIATION_QUERY 替代）

> **说明**：此操作可通过 ASSOCIATION_QUERY 实现。保留此快捷操作以便 API 路由兼容。

#### 9.2.1 基础结构

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "relationships": "items"
}
```

#### 9.2.2 完整结构

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "relationships": "items",
  "conditions": {
    "objectType": "OrderItem",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  },
  "returns": {
    "fields": ["id", "name", "price"]
  },
  "orders": [
    {"field": "createdAt", "direction": "DESC"}
  ],
  "maxResults": 10000
}
```

#### 9.2.3 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **objects** | array | 是 | 对象实例定义数组，详见第2.9节 |
| **relationships** | string | 是 | 关联类型标识符 |
| **conditions** | object | 否 | 统一条件表达式（详见第2.3节） |
| **returns** | object | 否 | 返回字段投影（详见第2.4节） |
| **orders** | array | 否 | 排序定义（详见第2.5节） |
| **maxResults** | integer | 否 | 最大返回数量，默认 100000，最大 100000 |

#### 9.2.4 filterObjectType - 源对象类型属性过滤

在 conditions 中通过 `objectType` 指定源对象类型，使用 `property`、`operator`、`values` 定义过滤条件：

```json
{
  "conditions": {
    "objectType": "OrderItem",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  }
}

#### 9.2.5 filterLinkType - 关联类型属性过滤

在 conditions 中通过 `objectType` 指定关联类型名称，`property` 指定关联类型属性（如 structRelType、bizRelType）：

​```json
{
  "conditions": {
    "objectType": "items",
    "property": "structRelType",
    "operator": "EQ",
    "values": ["Composition"]
  }
}


#### 9.2.6 完整示例

> **完整示例**见 [9.6.1 查询订单的所有商品项](#961-查询订单的所有商品项)，该节包含请求与响应的完整示例。

---

### 9.3 GET_LINKED_OBJECT - 获取特定关联对象（可被 ASSOCIATION_QUERY 替代）

> **说明**：此操作可通过 ASSOCIATION_QUERY 实现。保留此快捷操作以便 API 路由兼容。

**使用场景**：基于 relationships 和 linkedObjectKey 查询与源对象关联的特定目标对象。

#### 9.3.1 基础结构

```json
{
  "version": "1.0",
  "operation": "GET_LINKED_OBJECT",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "relationships": "items",
  "linkQuery": {
    "linkedObjectKey": {"id": "prod_001"}
  }
}
```

#### 9.3.2 完整结构

```json
{
  "version": "1.0",
  "operation": "GET_LINKED_OBJECT",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"id": "order_001"}
    }
  ],
  "relationships": "items",
  "linkQuery": {
    "linkedObjectKey": {"id": "prod_001"}
  },
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "OrderItem", "property": "status", "operator": "EQ", "values": ["active"]},
      {"objectType": "Product", "property": "category", "operator": "EQ", "values": ["electronics"]}
    ]
  },
  "returns": {
    "fields": ["id", "name", "price", "category", "brand"]
  }
}
```

#### 9.3.3 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **objects** | array | 是 | 对象实例定义数组，详见第2.9节 |
| **relationships** | string | 是 | 关联类型标识符 |
| **linkQuery.linkedObjectKey** | object | 是 | 目标对象主键定位，如 `{"id": "prod_001"}` |
| **conditions** | object | 否 | 统一条件表达式（详见第2.3节），可对源对象类型和目标对象类型进行属性过滤 |
| **returns** | object | 否 | 返回字段投影（详见第2.4节） |

#### 9.3.4 GET_LINKED_OBJECT 完整示例

```json
{
  "version": "1.0",
  "operation": "GET_LINKED_OBJECT",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"orderNo": "ORD-20240301-001"}
    }
  ],
  "relationships": "items",
  "linkQuery": {
    "linkedObjectKey": {"id": "prod_001"}
  },
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "OrderItem", "property": "status", "operator": "EQ", "values": ["completed"]},
      {"objectType": "Product", "property": "brand", "operator": "EQ", "values": ["Apple"]}
    ]
  },
  "returns": {
    "fields": ["id", "name", "price", "category", "brand"]
  }
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "id": "prod_001",
    "name": "iPhone 16",
    "price": 7999,
    "category": "electronics",
    "brand": "Apple"
  },
  "metadata": {
    "relationships": "items",
    "sourceObjectType": "Order",
    "sourceObjectKey": "ORD-20240301-001",
    "etag": "\"def456\"",
    "lastModified": "2024-03-01T10:00:00Z"
  }
}
```

#### 9.3.5 关联不存在响应（404 Not Found）

```json
{
  "success": false,
  "error": {
    "code": "LINKED_OBJECT_NOT_FOUND",
    "message": "关联对象不存在",
    "details": {
      "objectType": "Order",
      "by": {"id": "order_001"},
      "relationships": "items",
      "linkedObjectKey": "prod_999"
    }
  }
}
```

---

### 9.4 反向关联查询

部分关联支持反向查询，即从目标对象查询源对象。

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "relationships": "orderItems",
  "direction": "reverse",
  "conditions": {
    "objectType": "Order",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": {
    "fields": ["id", "orderNo", "status"]
  },
  "maxResults": 10000
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| **direction** | string | forward | 查询方向：forward（正向）或 reverse（反向），放在顶层 |

---

### 9.5 关联查询速查

| Operation | objects 必填 | 必填字段 | 说明 |
|-----------|--------------|----------|------|
| LIST_LINKED_OBJECTS | objectType, by | relationships | 列出关联对象列表 |
| GET_LINKED_OBJECT | objectType, by | relationships, linkedObjectType | 获取特定关联对象 |

**GET_LINKED_OBJECT 使用 linkQuery.linkedObjectKey 指定目标对象主键**，用于获取特定关联对象。

---

### 9.6 关联查询完整示例

#### 9.6.1 查询订单的所有商品项

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"orderNo": "ORD-20240301-001"}
    }
  ],
  "relationships": "items",
  "conditions": {
    "objectType": "OrderItem",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  },
  "returns": {
    "fields": ["id", "name", "price", "sku"]
  },
  "orders": [
    {"field": "createdAt", "direction": "ASC"}
  ],
  "maxResults": 10000
}
```

#### 9.6.2 查询用户的所有订单

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c",
      "by": {"id": "cust_001"}
    }
  ],
  "relationships": "orders",
  "conditions": {
    "objectType": "Order",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": {
    "fields": ["id", "orderNo", "amount", "status", "createdAt"]
  },
  "orders": [
    {"field": "createdAt", "direction": "DESC"}
  ],
  "maxResults": 10000
}
```

#### 9.6.3 获取特定关联对象（带并发控制）

```json
{
  "version": "1.0",
  "operation": "GET_LINKED_OBJECT",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"orderNo": "ORD-20240301-001"}
    }
  ],
  "relationships": "items",
  "linkQuery": {
    "linkedObjectKey": "prod_001",
    "concurrency": {
      "ifNoneMatch": "\"current-etag\""
    }
  },
  "returns": {
    "fields": ["id", "name", "price", "specifications"]
  }
}
```

#### 9.6.4 反向查询（某商品的所有订单）

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": {"id": "prod_001"}
    }
  ],
  "relationships": "orderItems",
  "direction": "reverse",
  "conditions": {
    "objectType": "Order",
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": {
    "fields": ["id", "orderNo", "customerId", "status"]
  },
  "maxResults": 10000
}
```

**示例（包含关联属性）**：
```json
{
  "select": {
    "fields": ["id", "name", "price"],
    "includeLinkProperties": true
  }
}
```

**响应数据**：
```json
{
  "data": [
    {
      "id": "prod_001",
      "name": "iPhone 16",
      "price": 7999,
      "_linkProperties": {
        "quantity": 2,
        "price": 7999
      }
    }
  ]
}
```

---

## 10. 关联查询（ASSOCIATION_QUERY）

> **说明**：OQL v1.0 新增的图关联查询操作，支持复杂图遍历、多跳关系查询。

> **前置说明**：ASSOCIATION_QUERY 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义（第2.2节）
> - `relationships` - 关系类型定义（本章节 10.2.3.1）
> - `conditions` - 统一条件表达式（第2.3节）
> - `returns` - 返回字段投影（第2.4节）
> - `orders` - 排序定义（第2.5节）
> - `associationQuery` - 关联查询专用块（本章节 10.2.3.2）

### 10.1 Operation 类型

ASSOCIATION_QUERY 是 OQL v1.0 专门为图关联查询设计的操作类型，支持：
- **多对象查询**：从多个对象类型出发进行关联查询
- **多跳关系遍历**：支持 1-N 跳的图遍历
- **关系过滤**：在关联路径上进行条件筛选
- **嵌套结果返回**：返回对象和关联关系的完整图结构

---

### 10.2 详细规范与示例

#### 10.2.1 概述与使用场景

关联查询操作用于**批量多对象 + 多关联关系**的复杂查询场景。当需要给定一组对象（如同一类别的多个设备），查询它们之间的关联关系时，使用 `ASSOCIATION_QUERY` 操作。

**核心概念**：

本体模型定义了对象和关联的图结构：
- **对象（Object）**：查询的主体，包含对象属性
- **关系（Relationship）**：对象间的关联，连接对象

**⚠️ 重要约束**：

> 进行关联查询时，必须明确指定要查询的关系类型（`relationships` 字段）。不能仅传入对象集合而忽略关系定义，原因如下：
> 1. **无法确定遍历路径**：翻译引擎需要根据关系类型构建 GQL 的 OVER 子句
> 2. **无法保证结果顺序**：对象和关系的先后顺序由关系定义决定
> 3. **无法返回有意义的关联结果**：缺少关系类型，GQL 无法执行有效的关联查询
>
> **注意**：图查询仅支持对象间关系（object-to-object），不支持属性间关系（property-to-property）。

**与其他查询类型的关系**：

`ASSOCIATION_QUERY` 是 OQL 中功能最强大的查询操作类型，可替代以下查询类型：

| 被替代的查询类型        | 替代方式                              | 说明                                                   |
| ----------------------- | ------------------------------------- | ------------------------------------------------------ |
| **QUERY**               | `objects[].conditions` + `conditions` | 单对象/列表查询可转换为从单个对象类型出发的关联查询    |
| **MULTI_OBJECT_QUERY**  | `objects` + relationships             | 多对象联合查询可通过定义关联关系实现                   |
| **LIST_LINKED_OBJECTS** | `relationships` | 翻译引擎根据 relationships 查找对应的 relationship 定义 |
| **GET_LINKED_OBJECT**   | `linkedObjectType` + 条件过滤         | 通过指定目标对象类型和过滤条件获取关联对象             |

**说明**：
- 保留 `QUERY`、`MULTI_OBJECT_QUERY`、`LIST_LINKED_OBJECTS`、`GET_LINKED_OBJECT` 等快捷操作类型是为了：
    1. **API 路由兼容**：不同 operation 对应不同的 API endpoint
    2. **请求简洁**：无需定义空的 `relationships` 结构
    3. **语义清晰**：操作类型即意图，降低使用门槛
- **AGGREGATE** 无法被替代，因其需要专门的聚合语义（groupBy、metrics 等）

**选择建议**：

- 简单列表查询 → 使用 `QUERY`
- 跨对象条件查询 → 使用 `MULTI_OBJECT_QUERY`
- 基于 LinkType 的关联查询 → 使用 `LIST_LINKED_OBJECTS` / `GET_LINKED_OBJECT`
- 复杂图遍历、多跳查询 → 使用 `ASSOCIATION_QUERY`

**支持的查询模式**：

| 模式               | 说明                                         | 示例                                |
| ------------------ | -------------------------------------------- | ----------------------------------- |
| **对象+关系查询**  | 同时指定对象集合和关系类型，精准查询特定关联 | 查询设备间的 connectedTo 关系       |
| **多对象类型查询** | 跨不同对象类型的关联查询                     | Device → Server 的 installedOn 关系 |

**典型使用场景**：

| 场景       | 说明                                        |
| ---------- | ------------------------------------------- |
| 拓扑分析   | 给定一批设备，查询设备间的网络连接/依赖关系 |
| 知识图谱   | 给定多个实体，查询它们之间的多跳关联关系    |
| 关联追溯   | 给定异常对象，追溯其关联的影响范围          |
| 多实体关系 | 查询跨越多种对象类型的关联                  |

**现有能力的对比**：

| 操作                  | 支持多对象  | 支持关系查询 | 返回结果              |
| --------------------- | ----------- | ------------ | --------------------- |
| QUERY                 | ✅ 单/多对象 | ❌            | 仅对象属性            |
| LIST_LINKS            | ❌ 仅单对象  | ✅            | 关联对象              |
| **ASSOCIATION_QUERY** | ✅ 多对象    | ✅            | 对象+关系完整关联结果 |

#### 10.2.2 Operation 类型

OQL 提供了 `ASSOCIATION_QUERY` 操作类型：

| Operation             | 说明           | API 对应              |
| --------------------- | -------------- | --------------------- |
| **ASSOCIATION_QUERY** | 多对象关联查询 | `POST /objects/query` |

#### 10.2.3 完整结构定义

> **使用说明**：本节提供所有 DSL 参数的完整定义汇总。如需了解参数的使用规则、详细约束和示例，请参见后续章节 [10.2.4](#1024-字段详细说明)。
>
> **核心约束**：图查询只支持 **对象间关系（object-to-object）**，不支持属性间关系（property-to-property）。所有关系查询均为对象与对象之间的关联。

##### 10.2.3.1 顶层参数定义

| 字段                               | 类型   | 必填 | 说明                                                         |
| ---------------------------------- | ------ | :--: | ------------------------------------------------------------ |
| `version`                          | string |  是  | DSL 版本号，固定为 "1.0"                                   |
| `operation`                        | string |  是  | 操作类型，固定为 "ASSOCIATION_QUERY"                         |
| `objects`                          | array  |  是  | 对象实例数组，包含起始对象定义                               |
| `objects[].objectType`             | string |  是  | 对象类型标识符                                               |
| `objects[].alias`                  | string |  否  | 对象别名，用于后续引用                                       |
| `objects[].by`                     | object |  否  | 单主键（KV 结构），如 `{"id": "prod_001"}`，图数据库场景对应 VID（兼容旧字段 `by`） |
| `objects[].byComposite`            | object |  否  | 复合主键（KV 结构），如 `{"sourceSystem": "ERP", "orderNo": "ORD-001"}`（兼容旧字段 `byComposite`） |
| `relationships`                    | array  |  是  | 关系类型数组，指定查询的关系类型                             |
| `relationships[].name`             | string |  是  | 关系类型名称（驼峰命名）                                     |
| `relationships[].alias`            | string |  否  | 关系别名，用于 returns 引用                                  |
| `relationships[].sourceObjectType` | string |  是  | 源对象类型                                                   |
| `relationships[].targetObjectType` | string |  是  | 目标对象类型                                                 |
| `relationships[].bizRelType`       | string |  否  | 业务语义类型                                                 |
| `relationships[].structRelType`    | string |  否  | UML 结构关系类型                                             |
| `relationships[].cardinality`      | string |  否  | 关系基数                                                     |

**使用规则**：

- `objects` 必填，用于定义查询的起始对象
- `objects[].by` 单主键，如 `{"id": "prod_001"}`（兼容旧字段 `by`）
- `objects[].byComposite` 复合主键，如 `{"sourceSystem": "ERP", "orderNo": "ORD-001"}`（兼容旧字段 `byComposite`）
- `by` 与 `byComposite` 二选一，不可同时使用
- `relationships` 必填，指定要查询的关系类型
- 遍历方向由 `relationships[].sourceObjectType` 和 `relationships[].targetObjectType` 决定，无需额外指定 direction

> **使用建议**：对于简单查询场景，可考虑使用更简洁的操作类型：
> - 单对象/列表查询 → 使用 `QUERY`
> - 跨对象条件查询 → 使用 `MULTI_OBJECT_QUERY`
> - 基于 LinkType 的关联查询 → 使用 `LIST_LINKED_OBJECTS` / `GET_LINKED_OBJECT`
> - 复杂图遍历查询 → 使用 `ASSOCIATION_QUERY`

##### 10.2.3.2 associationQuery 参数定义

| 字段                    | 类型   | 必填 | 说明                                                         |
| ----------------------- | ------ | :--: | ------------------------------------------------------------ |
| `action`                | enum   |  是  | 执行动作类型，定义查询/操作的执行方式                        |
| `conditions`            | object |  否  | 条件表达式对象，支持二叉树结构，统一放在 associationQuery 下 |
| `conditions.relation`   | string |  否  | 逻辑关系：AND / OR                                           |
| `conditions.children`   | array  |  否  | 条件子节点列表                                               |
| `conditions.property`   | string |  是  | 属性名称                                                     |
| `conditions.objectType` | string |  是  | 对象类型名称，对应 objects 中的 objectType                   |
| `conditions.operator`   | string |  是  | 比较运算符                                                   |
| `conditions.values`     | array  |  是  | 右侧操作值列表                                               |
| `returns`               | array  |  是  | 返回字段定义列表                                             |
| `orders`                | array  |  否  | 排序定义列表                                                 |

**action 执行动作类型**：

action 定义了查询的执行方式，根据数据源类型有不同的关键字：

| action   | 数据源              | 说明         | 原生查询语言关键字  |
| -------- | ------------------- | ------------ | ------------------- |
| `match`  | 图数据库            | 模式匹配查询 | `MATCH`             |
| `go`     | 图数据库            | 图遍历查询   | `GO ... OVER`       |
| `lookup` | 图数据库/关系数据库 | 索引查询     | `LOOKUP` / 索引命中 |
| `fetch`  | 图数据库            | 属性获取查询 | `FETCH`             |
| `select` | 关系数据库          | 标准查询     | `SELECT`            |
| `find`   | 文档数据库          | 文档查询     | `find` / `findOne`  |
| `query`  | 搜索引擎            | 全文检索     | `search` / `query`  |
| `get`    | 键值存储            | 直接读取     | `GET`               |

**说明**：

- 不同数据源的翻译引擎根据 action 生成对应数据源的原生查询语句
- 图数据库支持 `match`、`go`、`lookup`、`fetch` 四种动作
- 关系数据库主要使用 `select`
- 文档数据库（如 MongoDB）使用 `find`
- 搜索引擎（如 Elasticsearch）使用 `query`
- 键值存储使用 `get`

**operator 支持的运算符**：

| 运算符     | 说明       | GQL 对应      |
| ---------- | ---------- | ------------- |
| EQ         | 等于       | `==`          |
| NE         | 不等于     | `!=`          |
| GT         | 大于       | `>`           |
| GE         | 大于等于   | `>=`          |
| LT         | 小于       | `<`           |
| LE         | 小于等于   | `<=`          |
| IN         | 在列表中   | `IN`          |
| NOTIN      | 不在列表中 | `NOT IN`      |
| CONTAINS   | 包含       | `CONTAINS`    |
| STARTSWITH | 开头为     | `STARTS WITH` |
| ENDSWITH   | 结尾为     | `ENDS WITH`   |
| ISNULL     | 为空       | `IS NULL`     |
| ISNOTNULL  | 不为空     | `IS NOT NULL` |

##### 10.2.3.3 orders 参数定义

| 字段                  | 类型    | 必填 | 说明                                                         |
| --------------------- | ------- | :--: | ------------------------------------------------------------ |
| `orders`              | array   |  否  | 排序定义列表                                                 |
| `orders[].param`      | string  |  是  | 排序对象别名（对应 objects 或 relationships 中的 alias） |
| `orders[].property`   | string  |  是  | 排序字段名称                                                 |
| `orders[].descending` | boolean |  否  | 是否降序，默认 false                                         |

##### 10.2.3.4 associationQuery.returns 参数定义

`returns` 用于定义返回的字段投影，合并了原 select 的功能。

| 字段                 | 类型   | 必填 | 说明                                                   |
| -------------------- | ------ | :--: | ------------------------------------------------------ |
| `returns`            | array  |  是  | 返回字段定义列表                                       |
| `returns[].type`     | string |  是  | 类型：object / relationship                            |
| `returns[].param`    | string |  是  | 变量名称，对应 objects 或 relationships 中的 alias |
| `returns[].fields`   | array  |  否  | 要返回的字段列表，null 表示返回全部                    |
| `returns[].alias`    | string |  否  | 返回结果别名                                           |
| `returns[].function` | string |  否  | 聚合函数：count / avg / max / min / collect            |
| `returns[].property` | string |  否  | 聚合属性名称                                           |

**returns 聚合函数**：

| 函数    | 说明       | 示例                                                         |
| ------- | ---------- | ------------------------------------------------------------ |
| count   | 计数       | `{function: "count", param: "d", alias: "total"}`            |
| avg     | 平均值     | `{function: "avg", property: "cpuUsage", param: "d", alias: "avgCpu"}` |
| max     | 最大值     | `{function: "max", property: "temperature", param: "d", alias: "maxTemp"}` |
| min     | 最小值     | `{function: "min", property: "temperature", param: "d", alias: "minTemp"}` |
| collect | 合并为列表 | `{function: "collect", param: "d", alias: "list"}`           |

##### 10.2.3.5 关系类型枚举

**bizRelType 业务语义类型**：

| 业务关系    | 说明     |
| ----------- | -------- |
| connectedTo | 连接关系 |
| covers      | 覆盖关系 |
| serves      | 服务关系 |
| groupedWith | 分组关系 |

| 结构关系       | 说明     |
| -------------- | -------- |
| Association    | 一般关联 |
| Aggregation    | 聚合     |
| Composition    | 组合     |
| Generalization | 泛化     |
| Dependency     | 依赖     |
| Realization    | 实现     |

##### 10.2.3.6 完整 JSON 示例

**示例一（指定起始对象 + 指定关系）**：

```
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device_001"},
        {"id": "device_002"},
        {"id": "device_003"}
      ]
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo",
      "structRelType": "Association"
    }
  ],
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**示例二（条件筛选 + 多对象类型）**：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device_001"},
        {"id": "device_002"}
      ]
    },
    {
      "objectType": "Server",
      "alias": "s"
    }
  ],
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
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"]},
      {"objectType": "Device", "property": "cpuUsage", "operator": "GT", "values": [50]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "cpuUsage"]},
    {"type": "object", "param": "s", "fields": ["id", "name", "ip"]},
    {"type": "relationship", "param": "install", "fields": ["bizRelType", "cardinality"]}
  ],
  "orders": [
    {"param": "d", "property": "name", "descending": false}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**示例三（条件查询 + 关联筛选）**：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": {"id": "device_001"}
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo",
      "structRelType": "Association"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"property": "cpuUsage", "param": "d", "operator": "GT", "values": [80]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "cpuUsage"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

#### 10.2.4 字段详细说明

> **说明**：图查询仅支持对象间关系（object-to-object），所有关系均为点与点之间的关联。关系类型定义请参见 [10.2.3.4](#10734-关系类型枚举)。
>
> **遍历方向说明**：遍历方向由 `relationships[].sourceObjectType` 和 `relationships[].targetObjectType` 决定，无需额外指定 direction 参数。源对象类型即为遍历的起点类型，目标对象类型即为遍历的终点类型。

##### 10.2.4.1 通用字段引用

ASSOCIATION_QUERY 使用统一顶层结构，以下通用字段的详细说明请参见第2章：

| 字段 | 引用章节 | 说明 |
|------|----------|------|
| conditions | [第2.3节](#23-conditions---统一条件表达式) | 统一条件表达式 |
| returns | [第2.4节](#24-returns---返回字段投影) | 返回字段投影 |
| orders | [第2.5节](#25-orders---排序定义) | 排序定义 |

##### 10.2.4.2 nGQL 引用符号说明

在 NebulaGraph nGQL 中进行图遍历查询时，`$^` 和 `$$` 是两个核心引用符号：

| 符号 | 指代对象 | 说明 |
|------|----------|------|
| `$^` | 起点（源对象） | 引用遍历的起始顶点属性 |
| `$$` | 终点（目标对象） | 引用遍历的目标顶点属性 |
| `$-` | 管道输入 | 复合查询中引用管道符前的输出（需使用管道符 `|`） |

**示例**：

```gql
-- 引用源设备属性（起点）
$^.d.id AS d_id, $^.d.name AS d_name
-- 引用目标服务器属性（终点）
$$.s.id AS s_id, $$.s.name AS s_name
```

##### 10.2.4.3 relationships 字段详解（ASSOCIATION_QUERY 特有）

`relationships` 定义关联查询的关系类型，是 ASSOCIATION_QUERY 操作的核心字段。

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| name | string | 是 | 关系类型名称（驼峰命名），对应 LinkType |
| alias | string | 否 | 关系别名，用于 returns 引用 |
| sourceObjectType | string | 是 | 源对象类型，遍历的起点类型 |
| targetObjectType | string | 是 | 目标对象类型，遍历的终点类型 |
| bizRelType | string | 否 | 业务语义类型 |
| structRelType | string | 否 | UML 结构关系类型 |
| cardinality | string | 否 | 关系基数 |

##### 10.2.4.4 associationQuery 字段详解（ASSOCIATION_QUERY 特有）

`associationQuery` 是关联查询的专用配置块，定义查询的执行方式和行为。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| action | enum | 是 | 执行动作类型：match / go / lookup / fetch / select / find / query / get |
| select | object | 否 | 返回字段投影配置，详见 [10.2.3.4](#10234-associationqueryreturns-参数定义) |

**action 执行动作类型说明**：

| action | 数据源 | 说明 | 原生查询语言关键字 |
|--------|--------|------|-------------------|
| `match` | 图数据库 | 模式匹配查询 | `MATCH` |
| `go` | 图数据库 | 图遍历查询 | `GO ... OVER` |
| `lookup` | 图数据库/关系数据库 | 索引查询 | `LOOKUP` / 索引命中 |
| `fetch` | 图数据库 | 属性获取查询 | `FETCH` |

**select 字段说明**：

`select` 用于定义返回的字段投影，包含以下子字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| returns | array | 返回字段定义列表 |
| returns[].type | string | 类型：object / relationship |
| returns[].param | string | 变量名称，对应 objects 或 relationships 中的 alias |
| returns[].fields | array | 要返回的字段列表 |
| returns[].alias | string | 返回结果别名 |
| returns[].function | string | 聚合函数：count / avg / max / min / collect |`

---

**后续章节**：

- [10.2.5](#1025-查询场景示例)：查询场景示例
- [10.2.6](#1026-响应格式)：响应格式
- [10.2.7](#1027-gql-转换规则)：GQL 转换规则
- [10.2.8](#1028-association_query-完整示例)：完整示例
- [10.2.9](#1029-dsl-与-nebulagraph-ngql-对应关系)：DSL 与 nGQL 对应关系
- [10.2.10](#10210-错误码说明)：错误码说明

#### 10.2.5 查询场景示例

##### 10.2.5.1 示例一：多设备拓扑关系查询

**场景**：运维平台选择 3 台设备，查询它们之间的网络连接关系

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "srv-001"},
        {"id": "srv-002"},
        {"id": "srv-003"}
      ]
    }
  ],
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
      "name": "dependsOn",
      "alias": "dep",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "dependsOn",
      "structRelType": "Dependency"
    }
  ],
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "type"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType", "bandwidth"]},
    {"type": "relationship", "param": "dep", "fields": ["bizRelType", "structRelType"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 GQL 语句**：

```gql
GO FROM ["srv-001", "srv-002", "srv-003"] OVER connectedTo, dependsOn
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name,
  $^.d.status AS d_status, $^.d.type AS d_type,
  conn.bizRelType AS conn_bizRelType, conn.structRelType AS conn_structRelType,
  conn.bandwidth AS conn_bandwidth,
  dep.bizRelType AS dep_bizRelType, dep.structRelType AS dep_structRelType
```

> **说明**：使用 `$^.d` 引用起始设备（源对象）的属性。`$^` 代表当前遍历的起点，`$$` 代表当前遍历的终点。

##### 10.2.5.2 示例二：条件查询关联对象

**场景**：查询所有状态异常的设备及其关联关系

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device_001"},
        {"id": "device_002"}
      ]
    }
  ],
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
      "name": "dependsOn",
      "alias": "dep",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "dependsOn",
      "structRelType": "Dependency"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"property": "status", "param": "d", "operator": "EQ", "values": ["error"]},
      {"property": "cpuUsage", "param": "d", "operator": "GT", "values": [80]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "cpuUsage", "location"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType"]},
    {"type": "relationship", "param": "dep", "fields": ["bizRelType", "structRelType"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 GQL 语句**：

```gql
GO FROM ["device_001", "device_002"] OVER connectedTo, dependsOn
WHERE $^.d.status == "error" AND $^.d.cpuUsage > 80
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name,
  $^.d.status AS d_status, $^.d.cpuUsage AS d_cpuUsage, $^.d.location AS d_location,
  conn.bizRelType AS conn_bizRelType, conn.structRelType AS conn_structRelType,
  dep.bizRelType AS dep_bizRelType, dep.structRelType AS dep_structRelType
```

##### 10.2.5.3 示例三：知识图谱多实体关联查询

**场景**：查询多个产品及其相关的供应商、分类关系

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p",
      "by": [
        {"id": "prod-001"},
        {"id": "prod-002"}
      ]
    },
    {
      "objectType": "Supplier",
      "alias": "s"
    },
    {
      "objectType": "Category",
      "alias": "c"
    }
  ],
  "relationships": [
    {
      "name": "suppliedBy",
      "alias": "sb",
      "sourceObjectType": "Product",
      "targetObjectType": "Supplier",
      "bizRelType": "suppliedBy",
      "structRelType": "Association"
    },
    {
      "name": "belongsTo",
      "alias": "bt",
      "sourceObjectType": "Product",
      "targetObjectType": "Category",
      "bizRelType": "belongsTo",
      "structRelType": "Association"
    }
  ],
  "returns": [
    {"type": "object", "param": "p", "fields": ["id", "name", "price", "sku"]},
    {"type": "object", "param": "s", "fields": ["id", "name", "contact", "address"]},
    {"type": "object", "param": "c", "fields": ["id", "name", "parentId"]},
    {"type": "relationship", "param": "sb", "fields": ["bizRelType"]},
    {"type": "relationship", "param": "bt", "fields": ["bizRelType"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 GQL 语句**：

```gql
GO FROM ["prod-001", "prod-002"] OVER suppliedBy, belongsTo
YIELD
  $^.p.id AS p_id, $^.p.name AS p_name, $^.p.price AS p_price, $^.p.sku AS p_sku,
  $$.s.id AS s_id, $$.s.name AS s_name, $$.s.contact AS s_contact, $$.s.address AS s_address,
  $$.c.id AS c_id, $$.c.name AS c_name, $$.c.parentId AS c_parentId,
  sb.bizRelType AS sb_bizRelType, bt.bizRelType AS bt_bizRelType
```

> **说明**：使用 `$^.p` 引用起始产品（源对象），使用 `$$` 引用终点供应商和分类（目标对象）。`$$` 代表当前遍历的终点。

##### 10.2.5.4 示例四：多对象类型+多关系查询

**场景**：查询设备（Device）和服务器（Server）之间的关联关系

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    },
    {
      "objectType": "Server",
      "alias": "s"
    }
  ],
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
      "structRelType": "Composition",
      "cardinality": "Many-to-One"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "type", "location"]},
    {"type": "object", "param": "s", "fields": ["id", "name", "ip", "os", "cpuUsage"]},
    {"type": "relationship", "param": "install", "fields": ["bizRelType", "structRelType", "cardinality", "installedAt"]}
  ],
  "orders": [
    {"param": "d", "property": "name", "descending": false}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 GQL 语句**：

```gql
GO FROM $-.d.ids OVER installedOn
WHERE $^.d.status == "running"
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name, $^.d.status AS d_status,
  $^.d.type AS d_type, $^.d.location AS d_location,
  $$.s.id AS s_id, $$.s.name AS s_name, $$.s.ip AS s_ip,
  $$.s.os AS s_os, $$.s.cpuUsage AS s_cpuUsage,
  install.bizRelType AS install_bizRelType, install.structRelType AS install_structRelType,
  install.cardinality AS install_cardinality, install.installedAt AS install_installedAt
ORDER BY d_name ASC
```

##### 10.2.5.5 示例五：聚合查询

**场景**：查询设备的关联数量统计

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device_001"},
        {"id": "device_002"},
        {"id": "device_003"}
      ]
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo",
      "structRelType": "Association"
    }
  ],
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name"]},
    {
      "type": "relationship",
      "param": "conn",
      "function": "count",
      "alias": "connectionCount"
    }
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 GQL 语句**：

```gql
GO FROM ["device_001", "device_002", "device_003"] OVER connectedTo
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name,
  count(conn) AS connectionCount
GROUP BY $^.d.id
```

#### 10.2.6 响应格式

##### 10.2.6.1 响应结构规范

关联查询的响应采用以下统一结构（基于本体模型定义）：

```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "id": "obj-001",
        "objectType": "Device",
        "alias": "d",
        "name": "显示名称",
        "properties": {
          "status": "running",
          "type": "server",
          "location": "机房A"
        }
      }
    ],
    "relationships": [
      {
        "id": "rel-001",
        "name": "connectedTo",
        "alias": "conn",
        "bizRelType": "connectedTo",
        "structRelType": "Association",
        "cardinality": "Many-to-One",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "obj-001"
        },
        "target": {
          "objectType": "Device",
          "alias": "d",
          "id": "obj-002"
        },
        "properties": {
          "bandwidth": 1000,
          "latency": 5
        }
      }
    ]
  },
  "metadata": {
    "objectCount": 10,
    "relationshipCount": 15,
    "queryDepth": 2,
    "objectTypes": ["Device", "Server"],
    "relationships": ["connectedTo", "installedOn"],
    "executionTime": 45
  }
}
```

##### 10.2.6.2 响应字段详细说明

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| **success** | boolean | 请求是否成功 | 系统 |
| **data** | object | 关联查询结果数据 | - |
| **data.objects** | array | 查询返回的对象列表 | GQL YIELD 结果 |
| **data.objects[].id** | string | 对象唯一标识（主键值） | GQL 查询结果 |
| **data.objects[].objectType** | string | 对象类型名称（对应 ObjectType 本体定义） | DSL 配置 |
| **data.objects[].alias** | string | 对象别名（用于引用关系中的 source/target） | DSL 配置 |
| **data.objects[].name** | string | 对象显示名称（来自 name 或 display 字段） | GQL 查询结果 |
| **data.objects[].properties** | object | 对象属性键值对（来自 returns 配置） | GQL YIELD 结果 |
| **data.relationships** | array | 查询返回的关系列表 | GQL 查询结果 |
| **data.relationships[].id** | string | 关系唯一标识 | 系统生成 |
| **data.relationships[].name** | string | 关系类型名称（对应 Relationship 本体定义） | DSL 配置 |
| **data.relationships[].alias** | string | 关系别名（用于 returns 引用） | DSL 配置 |
| **data.relationships[].bizRelType** | string | 业务语义类型（如 connectedTo、covers） | DSL/本体 |
| **data.relationships[].structRelType** | string | UML 结构关系类型（Association/Aggregation/Composition） | DSL/本体 |
| **data.relationships[].cardinality** | string | 关系基数（One-to-Many/One-to-One/Many-to-One） | 本体定义 |
| **data.relationships[].source** | object | 源对象引用 | GQL 查询结果 |
| **data.relationships[].source.objectType** | string | 源对象类型 | GQL 结果 |
| **data.relationships[].source.alias** | string | 源对象别名 | GQL 结果 |
| **data.relationships[].source.id** | string | 源对象 ID | GQL 结果 |
| **data.relationships[].target** | object | 目标对象引用 | GQL 查询结果 |
| **data.relationships[].target.objectType** | string | 目标对象类型 | GQL 结果 |
| **data.relationships[].target.alias** | string | 目标对象别名 | GQL 结果 |
| **data.relationships[].target.id** | string | 目标对象 ID | GQL 结果 |
| **data.relationships[].properties** | object | 关系属性（来自 returns 配置） | GQL YIELD 结果 |
| **metadata** | object | 元数据信息 | - |
| **metadata.objectCount** | integer | 返回的对象总数 | 系统统计 |
| **metadata.relationshipCount** | integer | 返回的关系总数 | 系统统计 |
| **metadata.queryDepth** | integer | 实际查询深度（遍历层数） | DSL 配置 |
| **metadata.objectTypes** | array | 查询涉及的对象类型列表 | DSL 配置 |
| **metadata.relationships** | array | 查询涉及的关系类型列表 | DSL 配置 |
| **metadata.executionTime** | integer | 执行时间（毫秒） | 系统统计 |

##### 10.2.6.3 响应示例（完整样例）

**场景**：查询设备间的 connectedTo 关系

**请求**：
```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device-001"},
        {"id": "device-002"},
        {"id": "device-003"},
        {"id": "device-004"}
      ]
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo",
      "structRelType": "Association"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "type", "location"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType", "bandwidth"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "id": "device-001",
        "objectType": "Device",
        "alias": "d",
        "name": "核心交换机",
        "properties": {
          "status": "running",
          "type": "core_switch",
          "location": "机房A-1F"
        }
      },
      {
        "id": "device-002",
        "objectType": "Device",
        "alias": "d",
        "name": "汇聚交换机-1",
        "properties": {
          "status": "running",
          "type": "aggregation_switch",
          "location": "机房A-1F"
        }
      },
      {
        "id": "device-003",
        "objectType": "Device",
        "alias": "d",
        "name": "汇聚交换机-2",
        "properties": {
          "status": "running",
          "type": "aggregation_switch",
          "location": "机房A-2F"
        }
      },
      {
        "id": "device-004",
        "objectType": "Device",
        "alias": "d",
        "name": "接入交换机-1",
        "properties": {
          "status": "running",
          "type": "access_switch",
          "location": "机房A-1F"
        }
      }
    ],
    "relationships": [
      {
        "id": "rel-001",
        "name": "connectedTo",
        "alias": "conn",
        "bizRelType": "connectedTo",
        "structRelType": "Association",
        "cardinality": "Many-to-One",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-001"
        },
        "target": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-002"
        },
        "properties": {
          "bandwidth": 10000
        }
      },
      {
        "id": "rel-002",
        "name": "connectedTo",
        "alias": "conn",
        "bizRelType": "connectedTo",
        "structRelType": "Association",
        "cardinality": "Many-to-One",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-001"
        },
        "target": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-003"
        },
        "properties": {
          "bandwidth": 10000
        }
      },
      {
        "id": "rel-003",
        "name": "connectedTo",
        "alias": "conn",
        "bizRelType": "connectedTo",
        "structRelType": "Association",
        "cardinality": "Many-to-Many",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-002"
        },
        "target": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-004"
        },
        "properties": {
          "bandwidth": 1000
        }
      },
      {
        "id": "rel-004",
        "name": "connectedTo",
        "alias": "conn",
        "bizRelType": "connectedTo",
        "structRelType": "Association",
        "cardinality": "Many-to-Many",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-003"
        },
        "target": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-004"
        },
        "properties": {
          "bandwidth": 1000
        }
      }
    ]
  },
  "metadata": {
    "objectCount": 4,
    "relationshipCount": 4,
    "queryDepth": 2,
    "objectTypes": ["Device"],
    "relationships": ["connectedTo"],
    "executionTime": 67
  }
}
```

##### 10.2.6.4 跨对象类型响应示例

**场景**：Device.installedOn.Server 关系查询

**响应**：
```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "id": "device-001",
        "objectType": "Device",
        "alias": "d",
        "name": "Web服务器-1",
        "properties": {
          "id": "device-001",
          "name": "Web服务器-1",
          "status": "running",
          "type": "web_server"
        }
      },
      {
        "id": "server-001",
        "objectType": "Server",
        "alias": "s",
        "name": "应用服务器",
        "properties": {
          "id": "server-001",
          "name": "应用服务器",
          "cpu": "Intel Xeon",
          "memory": "64GB"
        }
      }
    ],
    "relationships": [
      {
        "id": "rel-001",
        "name": "installedOn",
        "alias": "install",
        "bizRelType": "installedOn",
        "structRelType": "Composition",
        "cardinality": "Many-to-One",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-001"
        },
        "target": {
          "objectType": "Server",
          "alias": "s",
          "id": "server-001"
        },
        "properties": {
          "installedAt": "2025-01-15T10:30:00Z",
          "environment": "production"
        }
      }
    ]
  },
  "metadata": {
    "objectCount": 2,
    "relationshipCount": 1,
    "queryDepth": 1,
    "objectTypes": ["Device", "Server"],
    "relationships": ["installedOn"],
    "executionTime": 35
  }
}
```

**说明**：
- 对象通过 `alias` 字段区分，便于在前端进行渲染和关联展示
- 关系通过 `source` 和 `target` 字段明确引用源对象和目标对象
- `properties` 字段包含从 returns 配置中指定的属性值
- metadata 中汇总了查询统计信息，便于分页和性能监控

#### 10.2.7 GQL 转换规则

##### 10.2.7.1 翻译引擎处理流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ASSOCIATION_QUERY → GQL 翻译流程                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 解析 DSL，获取 objects + relationships + returns 配置            │
│                     ↓                                               │
│  2. 从本体模型定义中补全 relationship 元信息                         │
│     - 获取 sourceObjectType / targetObjectType                      │
│     - 获取 bizRelType / structRelType                               │
│                     ↓                                               │
│  3. 根据 returns 配置构建 GQL YIELD 子句                             │
│     - objects 字段映射为对象属性输出                                  │
│     - relationships 字段映射为关系属性输出                            │
│                     ↓                                               │
│  4. 分析数据源分布（单图空间/多数据源）                               │
│                     ↓                                               │
│  5. 根据数据源情况选择处理策略：                                      │
│     - 单图空间：构建单条 GQL 语句                                    │
│     - 多数据源：拆分为多个子查询 → 组装结果                          │
│                     ↓                                               │
│  6. 执行查询，获取结果                                               │
│                     ↓                                               │
│  7. 解析结果，按对象/关系分类，字段投影                              │
│                     ↓                                               │
│  8. 返回统一格式                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**DSL returns → GQL YIELD 映射规则**：

| DSL returns 配置 | GQL YIELD 子句 |
|-----------------|----------------|
| `returns[].type: "object"` | `alias.field1 AS alias_field1, alias.field2 AS alias_field2` |
| `returns[].type: "relationship"` | `alias.attr1 AS alias_attr1, alias.attr2 AS alias_attr2` |
| 元数据输出 | `$-._src AS _src, $-._dst AS _dst, $-._src_type, $-._dst_type` |

**本体模型查询流程**：
- 翻译引擎根据 DSL 中的 `relationships[].name` 查询本体模型定义
- 补全 `sourceObjectType`, `targetObjectType`, `bizRelType`, `structRelType`
- 如果 DSL 中已指定，则使用 DSL 中的值（优先级更高）

##### 10.2.7.2 多数据源处理策略

**策略一：单图空间查询（转换为单条 GQL）**

当所有对象和关系属于同一个图数据库的同一个图空间时，翻译引擎生成单条 GQL 语句：

```gql
-- 多设备拓扑查询（Device + connectedTo + dependsOn）
GO 2 STEPS FROM ["srv-001", "srv-002", "srv-003"]
OVER connectedTo, dependsOn
WHERE bizRelType NOT IN ["heartbeat"]
YIELD
  $-._src AS src,
  $-._dst AS dst,
  connectedTo._type AS bizRelType,
  dependsOn._type AS bizRelType
| GROUP BY $-.src, $-.dst
YIELD $-.src, $-.dst, collect($-.bizRelType) AS bizRelTypes
```

**策略二：多数据源查询（拆分子查询 + 组装）**

当对象或关系来自不同的数据源时，翻译引擎执行以下流程：

```
┌─────────────────────────────────────────────────────────────────────┐
│                      多数据源处理流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 分析 objects + relationships 的数据源分布                        │
│     ┌─────────────────────────────────────────────┐                 │
│     │ 数据源A: Device + connectedTo (Nebula)      │                 │
│     │ 数据源B: Server + installedOn (MySQL)       │                 │
│     │ 数据源C: 跨数据源关联 (组合关系)              │                 │
│     └─────────────────────────────────────────────┘                 │
│                           ↓                                         │
│  2. 并行执行子查询                                                   │
│     ┌────────────┐ ┌────────────┐ ┌────────────┐                   │
│     │ 子查询A    │ │ 子查询B    │ │ 子查询C    │                   │
│     │ (Nebula)   │ │ (MySQL)    │ │ (Network)  │                   │
│     └────────────┘ └────────────┘ └────────────┘                   │
│                           ↓                                         │
│  3. 关联组装图结构                                                   │
│     - Device 节点 ← connectedTo → Server 节点                      │
│     - 按 src/dst ID 进行关联                                         │
│                           ↓                                         │
│  4. 返回统一子图结构                                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**多数据源查询示例**：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device-001"},
        {"id": "device-002"}
      ]
    },
    {
      "objectType": "Server",
      "alias": "s"
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo"
    },
    {
      "name": "installedOn",
      "alias": "install",
      "sourceObjectType": "Device",
      "targetObjectType": "Server",
      "bizRelType": "installedOn"
    }
  ],
  "associationQuery": {
  }
}
```

**翻译引擎处理**：
1. 查询本体模型定义，补全 relationships 元信息
2. 从 Nebula 查询 Device 节点列表
3. 从关联数据源查询 connectedTo 和 installedOn 边
4. 根据 src/dst 引用组装完整图结构
5. 返回统一格式的子图响应

##### 10.2.7.3 关系类型映射 GQL

**object-to-object 关系查询**（基于 Relationship 本体定义）：

```gql
-- Device.connectedTo.Device
GO FROM $-.d.ids OVER connectedTo
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name, $^.d.status AS d_status,
  $$.d.id AS dst_id, $$.d.name AS dst_name, $$.d.status AS dst_status,
  connectedTo.bizRelType AS conn_bizRelType, connectedTo.structRelType AS conn_structRelType
```

**跨对象类型关系查询**（基于多 ObjectType 本体定义）：

```gql
-- Device.installedOn.Server
GO FROM $-.d.ids OVER installedOn
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name, $^.d.status AS d_status,
  $$.s.id AS s_id, $$.s.name AS s_name, $$.s.ip AS s_ip,
  installedOn.bizRelType AS install_bizRelType, installedOn.structRelType AS install_structRelType
```

##### 10.2.7.4 典型场景 GQL 模板

| 场景 | GQL 模板 |
|------|----------|
| **单图空间单跳** | `GO FROM $ids OVER $rels YIELD ...` |
| **单图空间多跳** | `GO N STEPS FROM $ids OVER $rels YIELD ...` |
| **跨对象类型** | `GO FROM $ids OVER $rel WHERE $-._src_type == "TypeA" AND $-._dst_type == "TypeB"` |
| **多数据源拆分** | 拆分为多个子查询，组装结果 |
| **仅出边** | `GO FROM $ids OVER $rels YIELD ...` |
| **仅入边** | `GO FROM $ids OVER $rels REVERSELY YIELD ...` |
| **关系类型过滤** | `GO FROM $ids OVER $rels WHERE bizRelType IN [...] YIELD ...` |
| **深度限制** | `GO 2 STEPS FROM $ids OVER $rels YIELD ...` |
| **去重** | `GO FROM $ids OVER $rels YIELD DISTINCT ...` |

**翻译引擎处理**：
1. 从数据源查询对象列表
2. 从关联数据源查询关系
3. 根据 source/target 引用组装完整关联结构
4. 按 returns 配置进行字段投影
5. 返回统一格式的关联查询响应

##### 10.2.7.5 多对象类型查询 GQL

**跨对象类型查询（单图空间）**：

```gql
-- Device + Server 关联查询
GO FROM $-.d.ids OVER connectsTo, installedOn
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name, $^.d.status AS d_status,
  $$.s.id AS s_id, $$.s.name AS s_name, $$.s.ip AS s_ip,
  connectsTo.bizRelType AS connectsTo_bizRelType,
  installedOn.bizRelType AS installedOn_bizRelType
```

**带对象类型过滤的查询**：

```gql
GO FROM $-.d.ids OVER *
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name,
  $$.s.id AS s_id, $$.s.name AS s_name
```


#### 10.2.8 ASSOCIATION_QUERY 完整示例

**请求**（多对象类型 + 多关系查询）：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": [
        {"id": "device-a"},
        {"id": "device-b"},
        {"id": "device-c"}
      ]
    },
    {
      "objectType": "Server",
      "alias": "s"
    }
  ],
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
      "structRelType": "Composition",
      "cardinality": "Many-to-One"
    }
  ],
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "type", "location"]},
    {"type": "object", "param": "s", "fields": ["id", "name", "ip", "os"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType", "bandwidth"]},
    {"type": "relationship", "param": "install", "fields": ["bizRelType", "structRelType", "cardinality", "installedAt"]}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 GQL 语句**：

```gql
-- 多对象类型+多关系查询
GO 2 STEPS FROM ["device-a", "device-b", "device-c"] OVER connectedTo, installedOn
YIELD
  $^.d.id AS d_id, $^.d.name AS d_name, $^.d.status AS d_status,
  $^.d.type AS d_type, $^.d.location AS d_location,
  $.s.id AS s_id, $.s.name AS s_name, $.s.ip AS s_ip, $.s.os AS s_os,
  conn.bizRelType AS conn_bizRelType, conn.structRelType AS conn_structRelType,
  conn.bandwidth AS conn_bandwidth,
  install.bizRelType AS install_bizRelType, install.structRelType AS install_structRelType,
  install.cardinality AS install_cardinality, install.installedAt AS install_installedAt
```

**响应**：

```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "id": "device-a",
        "objectType": "Device",
        "alias": "d",
        "name": "Web服务器",
        "properties": {
          "status": "running",
          "type": "server",
          "location": "机房A"
        }
      },
      {
        "id": "device-b",
        "objectType": "Device",
        "alias": "d",
        "name": "数据库",
        "properties": {
          "status": "running",
          "type": "database",
          "location": "机房A"
        }
      },
      {
        "id": "device-c",
        "objectType": "Device",
        "alias": "d",
        "name": "负载均衡",
        "properties": {
          "status": "running",
          "type": "loadbalancer",
          "location": "机房B"
        }
      },
      {
        "id": "server-001",
        "objectType": "Server",
        "alias": "s",
        "name": "应用服务器",
        "properties": {
          "status": "running",
          "ip": "192.168.1.100",
          "os": "Ubuntu 22.04"
        }
      }
    ],
    "relationships": [
      {
        "id": "rel-001",
        "name": "connectedTo",
        "alias": "conn",
        "bizRelType": "connectedTo",
        "structRelType": "Association",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-a"
        },
        "target": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-b"
        },
        "properties": {
          "bandwidth": 1000
        }
      },
      {
        "id": "rel-002",
        "name": "installedOn",
        "alias": "install",
        "bizRelType": "installedOn",
        "structRelType": "Composition",
        "cardinality": "Many-to-One",
        "source": {
          "objectType": "Device",
          "alias": "d",
          "id": "device-a"
        },
        "target": {
          "objectType": "Server",
          "alias": "s",
          "id": "server-001"
        },
        "properties": {
          "installedAt": "2025-01-01T00:00:00Z"
        }
      }
    ]
  },
  "metadata": {
    "objectCount": 4,
    "relationshipCount": 2,
    "queryDepth": 2,
    "objectTypes": ["Device", "Server"],
    "relationships": ["connectedTo", "installedOn"],
    "executionTime": 67
  }
}
```

**对应的 NebulaGraph GQL**：

```gql
GO 2 STEPS FROM ["device-a", "device-b", "device-c"] OVER connectedTo, installedOn
YIELD
  $^.d.id AS src_id, $^.d.name AS src_name,
  $.s.id AS dst_id, $.s.name AS dst_name,
  connectedTo.bizRelType AS conn_bizRelType,
  connectedTo.structRelType AS conn_structRelType,
  connectedTo.bandwidth AS conn_bandwidth,
  installedOn.bizRelType AS install_bizRelType,
  installedOn.structRelType AS install_structRelType,
  installedOn.cardinality AS install_cardinality
```

#### 10.2.9 DSL 与 NebulaGraph nGQL 对应关系

本节说明 OQL DSL 参数与 NebulaGraph 原生 nGQL 语句的对应关系，帮助理解 DSL 到 GQL 的转换逻辑。

##### 10.2.9.1 核心参数对应表

| OQL DSL 参数 | nGQL 语句 | 说明 |
|-------------|-----------|------|
| `objects[].by` | `FROM $ids` | 单主键或多主键列表 |
| `objects[].byComposite` | `FROM $ids` | 复合主键 |
| `objects[].conditions` | `WHERE ...` | 起始点过滤条件 |
| `relationships[].sourceObjectType` / `targetObjectType` | 遍历方向由 source/target 决定 | 源对象为起点，目标对象为终点 |
| `relationships[].name` | `OVER $relName` | 关系类型 |
| `associationQuery.conditions` | `WHERE ...` | 过滤条件 |
| `returns` | `YIELD ... AS ...` | 返回字段定义 |
| `orders` | `ORDER BY ...` | 排序定义 |
| `distinct` | `YIELD DISTINCT` | 去重 |

##### 10.2.9.2 action 类型对应关系

ASSOCIATION_QUERY 支持四种查询模式，与 nGQL 的对应关系如下：

| DSL action | nGQL 语句 | 适用场景 |
|------------|-----------|----------|
| **match** | `MATCH (v)-[e]->(v2)` | 模式匹配查询，支持复杂图模式 |
| **go** | `GO N STEPS FROM ... OVER ...` | 多跳遍历查询 |
| **lookup** | `LOOKUP ON ... WHERE ...` | 索引点查询 |
| **fetch** | `FETCH PROP ON ...` | 属性获取查询 |

**action: match**（模式匹配）：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": {"id": "device-001"}
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device"
    }
  ],
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType"]}
  ],
  "associationQuery": {
    "action": "match"
  }
}
```

**对应 nGQL**：

```gql
MATCH (d:Device)-[conn:connectedTo]->(d2:Device)
WHERE id(d) == "device-001"
YIELD
  d.id AS Device_id, d.name AS Device_name, d.status AS Device_status,
  conn.bizRelType AS conn_bizRelType
```

**action: go**（多跳遍历）：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": {"id": "device-001"}
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device"
    }
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 nGQL**：

```gql
GO 2 STEPS FROM "device-001" OVER connectedTo BIDIRECT
YIELD
  $^.d.id AS src_id, $.d.id AS dst_id,
  connectedTo.bizRelType AS conn_bizRelType
```

**action: lookup**（索引查询）：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    }
  ],
  "conditions": {
    "property": "name",
    "param": "d",
    "operator": "CONTAINS",
    "values": ["server"]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status"]}
  ],
  "associationQuery": {
    "action": "lookup"
  }
}
```

**对应 nGQL**：

```gql
LOOKUP ON Device WHERE Device.name CONTAINS "server"
YIELD id(vertex) AS id, Device.name AS name, Device.status AS status
```

**action: fetch**（属性获取）：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d",
      "by": {"id": "device-001"}
    }
  ],
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "cpuUsage", "memory"]}
  ],
  "associationQuery": {
    "action": "fetch"
  }
}
```

**对应 nGQL**：

```gql
FETCH PROP ON Device "device-001"
YIELD properties(vertex)
```

##### 10.2.9.3 elements 与 GQL 模式对应

**点边模式定义**：

| DSL elements | nGQL 模式 | 说明 |
|--------------|-----------|------|
| `{type: "tag", name: ["Device"], alias: "d"}` | `(d:Device)` | 匹配 Device 类型点 |
| `{type: "edge", name: ["connectedTo"], alias: "e"}` | `[e:connectedTo]` | 匹配 connectedTo 边 |
| `{type: "edge", direction: "out"}` | `->` | 出边方向 |
| `{type: "edge", direction: "in"}` | `<-` | 入边方向 |
| `{type: "edge", direction: "both"}` | `-` | 双向边 |
| `{minHop: 1, maxHop: 3}` | `*1..3` | 多跳范围 |

**elements 模式组合示例**：

```json
{
  "elements": [
    {
      "type": "tag",
      "name": ["Device"],
      "alias": "d1"
    },
    {
      "type": "edge",
      "name": ["connectedTo"],
      "alias": "e",
      "direction": "out",
      "minHop": 1,
      "maxHop": 2
    },
    {
      "type": "tag",
      "name": ["Device"],
      "alias": "d2"
    }
  ]
}
```

**对应 nGQL**：

```gql
MATCH (d1:Device)-[e:connectedTo*1..2]->(d2:Device)
YIELD d1, e, d2
```

##### 10.2.9.4 conditions 与 GQL WHERE 对应

**conditions 二叉树结构 → WHERE 子句**：

```json
{
  "relation": "AND",
  "children": [
    { "objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"] },
    {
      "relation": "OR",
      "children": [
        { "objectType": "Device", "property": "type", "operator": "EQ", "values": ["server"] },
        { "objectType": "Device", "property": "type", "operator": "EQ", "values": ["router"] }
      ]
    }
  ]
}
```

**对应 GQL WHERE**：

```gql
WHERE d.status == "running" AND (d.type == "server" OR d.type == "router")
```

**operator → WHERE 运算符映射**：

| DSL operator | GQL | 说明 |
|-------------|-----|------|
| EQ | `==` | 等于 |
| NE | `!=` | 不等于 |
| GT | `>` | 大于 |
| GE | `>=` | 大于等于 |
| LT | `<` | 小于 |
| LE | `<=` | 小于等于 |
| IN | `IN` | 在列表中 |
| NOTIN | `NOT IN` | 不在列表中 |
| CONTAINS | `CONTAINS` | 字符串包含 |
| STARTSWITH | `STARTS WITH` | 开头匹配 |
| ENDSWITH | `ENDS WITH` | 结尾匹配 |

##### 10.2.9.5 returns/orders 与 GQL 投影对应

**returns 函数映射**：

| returns function | GQL YIELD | 说明 |
|-----------------|-----------|------|
| `{function: "id", param: "d"}` | `id(d) AS id` | 获取点 ID |
| `{function: "src", param: "e"}` | `src(e) AS srcId` | 获取边起点 |
| `{function: "dst", param: "e"}` | `dst(e) AS dstId` | 获取边终点 |
| `{function: "properties", param: "d"}` | `properties(d) AS props` | 获取所有属性 |
| `{function: "type", param: "d"}` | `labels(d) AS type` | 获取点类型 |
| `{function: "count", param: "*"}` | `count(*) AS count` | 计数 |
| `{function: "avg", property: "cpu", param: "d"}` | `avg(d.cpu) AS avgCpu` | 平均值 |
| `{function: "max", property: "cpu", param: "d"}` | `max(d.cpu) AS maxCpu` | 最大值 |
| `{function: "min", property: "cpu", param: "d"}` | `min(d.cpu) AS minCpu` | 最小值 |
| `{function: "collect", param: "d"}` | `collect(d) AS list` | 合并为列表 |

**orders 排序映射**：

| orders 配置 | GQL ORDER BY |
|------------|--------------|
| `{"name": "id", "descending": false}` | `ORDER BY id ASC` |
| `{"name": "cpuUsage", "descending": true}` | `ORDER BY cpuUsage DESC` |
| 多字段排序 | `ORDER BY field1 ASC, field2 DESC` |

##### 10.2.9.6 完整 DSL → GQL 转换示例

**DSL 请求**：

```json
{
  "version": "1.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    }
  ],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "conn",
      "sourceObjectType": "Device",
      "targetObjectType": "Device"
    }
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"property": "status", "param": "d", "operator": "EQ", "values": ["running"]},
      {"property": "cpuUsage", "param": "d", "operator": "GT", "values": [50]},
      {"property": "memory", "param": "d", "operator": "LT", "values": [8192]}
    ]
  },
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status", "cpuUsage", "memory"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType"]}
  ],
  "orders": [
    {"param": "d", "property": "name", "descending": false}
  ],
  "associationQuery": {
    "action": "go"
  }
}
```

**对应 nGQL**：

```gql
GO 2 STEPS FROM $-.ids OVER connectedTo BIDIRECT
WHERE
  $^.d.status == "running" AND
  $^.d.cpuUsage > 50 AND
  $^.d.memory < 8192
YIELD
  Device.id AS d_id, Device.name AS d_name, Device.status AS d_status,
  Device.cpuUsage AS d_cpuUsage, Device.memory AS d_memory,
  conn.bizRelType AS conn_bizRelType, conn.structRelType AS conn_structRelType
ORDER BY d_name ASC
```

**DSL → GQL 转换流程**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DSL → GQL 转换流程                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. objects[].by / byComposite → FROM $ids                             │
│     - 单主键: {"id": "device_001"} → FROM "device_001"                   │
│     - 多主键: [{"id": "d1"}, {"id": "d2"}] → FROM ["d1", "d2"]          │
│     - 复合主键: {"sourceSystem": "ERP", "orderNo": "ORD-001"}            │
│                                                                         │
│  2. action 类型决定查询语句：                                             │
│     - match  → MATCH (v)-[e]->(v2) 模式匹配                             │
│     - go     → GO N STEPS FROM ... OVER ... 遍历查询                    │
│     - lookup → LOOKUP ON ... WHERE ... 索引查询                         │
│     - fetch  → FETCH PROP ON ... 属性查询                               │
│                                                                         │
│  3. sourceObjectType/targetObjectType → 遍历方向                        │
│     - sourceObjectType 为起点，targetObjectType 为终点                  │
│     - 遍历方向由 source → target 决定                                   │
│                                                                         │
│  4. relationships[].name → OVER $relName1, $relName2                    │
│                                                                         │
│  5. associationQuery.conditions → WHERE 子句（二叉树表达式）            │
│                                                                         │
│  6. returns → YIELD 子句（字段投影）                                     │
│                                                                         │
│  7. orders → ORDER BY 子句                                              │
│                                                                         │
│  8. distinct → YIELD DISTINCT                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

##### 10.2.9.7 NebulaGraph nGQL 语句对应关系

以下说明 NebulaGraph 原生 nGQL 语句与 DSL 的对应关系：

| Nebula 查询 | 等价 DSL | 说明 |
|-------------|----------|------|
| `GO 3 STEPS FROM "player102" OVER follow YIELD dst(edge)` | `action: go` | 多跳遍历查询 |
| `LOOKUP ON player WHERE player.name == "Tony Parker" YIELD id(vertex)` | `action: lookup` | 索引点查询 |
| `FETCH PROP ON player "player100" YIELD properties(vertex)` | `action: fetch` | 属性获取查询 |
| `MATCH (v)-[e:follow*3]-(v2) WHERE id(v) == "player102" RETURN dst(e)` | `action: match` | 模式匹配查询 |

**Go → Match 语句转换**：

```gql
-- Nebula Go 语句
GO 3 STEPS FROM "player102" OVER follow YIELD dst(edge)
-- 等价 Match 语句
MATCH (v)-[e:follow*3]-(v2) WHERE id(v) == "player102" RETURN dst(e)
```

**Lookup → Match 语句转换**：

```gql
-- Nebula Lookup 语句
LOOKUP ON player WHERE player.name == "Tony Parker" YIELD id(vertex)
-- 等价 Match 语句
MATCH (v:player) WHERE v.name == "Tony Parker" RETURN id(v)
```

**Fetch → Match 语句转换**：

```gql
-- Nebula Fetch 语句
FETCH PROP ON player "player100" YIELD properties(vertex)
-- 等价 Match 语句
MATCH (v:player) WHERE id(v) == "player100" RETURN v.player
```

#### 10.2.10 错误码说明

ASSOCIATION_QUERY 操作可能返回的错误码：

| code | 说明 | 处理建议 |
|------|------|----------|
| 20000 | 请求成功 | - |
| 40001 | 参数校验失败 | 检查 DSL 语法和必填字段 |
| 40002 | 查询参数不合法 | 检查 objectType / relationships 配置 |
| 40007 | GQL 执行异常 | 检查 GQL 语句语法 |
| 50000 | 查询执行失败 | 检查数据源连接和权限 |

---

## 11. 批量操作（BATCH）

> **前置说明**：BATCH 操作使用统一顶层结构，详见 [第2章统一顶层结构](#2-统一顶层结构)：
> - `objects` - 对象实例定义，用于指定操作的目标对象类型
> - `mutation` - 变更操作定义（本章节 11.2）
> - `links` - 关联操作定义（本章节 11.3）

### 11.1 操作概述

BATCH 操作支持**事务性批量操作**、**非事务批量操作**、**批量导入（IMPORT）**和**批量导出（EXPORT）**。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BATCH 操作类型                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐ │
│   │  事务批量操作    │    │ 非事务批量操作   │    │   导入导出操作  │ │
│   │  transaction    │    │  continueOn     │    │ IMPORT / EXPORT│ │
│   │  = true         │    │  Failure        │    │                │ │
│   └─────────────────┘    └─────────────────┘    └────────────────┘ │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                    支持的子操作                              │  │
│   ├─────────────────────────────────────────────────────────────┤  │
│   │  • CREATE    • UPDATE    • DELETE    • UPSERT              │  │
│   │  • BATCH_CREATE  • BATCH_UPDATE  • BATCH_DELETE            │  │
│   │  • BATCH_LINKS   • IMPORT    • EXPORT                      │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 完整结构定义（JSON Schema）

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "string"}
  ],
  "options": {
    "transaction": true,
    "isolationLevel": "READ_COMMITTED",
    "timeoutMs": 30000,
    "continueOnFailure": false,
    "returnAffectedCount": true
  },
  "mutation": {
    "type": "object",
    "properties": {
      "batch": {
        "type": "array",
        "description": "批量操作列表"
      },
      "batch[].by": {
        "type": "object",
        "description": "主键定位（KV结构）"
      },
      "batch[].data": {
        "type": "object",
        "description": "创建/更新的属性数据"
      },
      "batch[].set": {
        "type": "object",
        "description": "更新时设置的属性"
      },
      "batch[].unset": {
        "type": "array",
        "description": "要删除的属性名列表"
      },
      "batch[].increment": {
        "type": "object",
        "description": "要递增的属性"
      }
    }
  },
  "links": {
    "description": "关联操作定义（本章节 11.3）"
  }
}
```

### 11.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| **objects** | array | 是 | 对象类型定义数组 |
| **objects[].objectType** | string | 是 | 对象类型标识符 |
| **options** | object | 否 | 执行选项（详见第12章） |
| **mutation** | object | 否 | 对象变更操作定义 |
| **mutation.batch** | array | 是（批量时） | 批量操作列表 |
| **mutation.batch[].by** | object | 是 | 主键定位（KV结构） |
| **mutation.batch[].data** | object | 否 | 创建/更新的属性数据 |
| **mutation.batch[].set** | object | 否 | 更新时设置的属性 |
| **mutation.batch[].unset** | array | 否 | 要删除的属性名列表 |
| **mutation.batch[].increment** | object | 否 | 要递增的属性（原子操作） |
| **mutation.batch[].arrayOps** | object | 否 | 数组操作（push/pull） |
| **links** | object | 否 | 关联操作定义 |

### 11.4 事务性批量操作

#### 11.4.1 基础结构

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "options": {
    "transaction": true,
    "isolationLevel": "READ_COMMITTED",
    "timeoutMs": 30000
  },
  "mutation": {
    "batch": [
      {
        "objectType": "Order",
        "by": {"id": "order_001"},
        "data": {
          "orderNo": "ORD-20240301-001",
          "customerId": "cust_001",
          "status": "pending"
        }
      },
      {
        "objectType": "OrderItem",
        "by": {"orderId": "order_001", "productId": "prod_001"},
        "data": {
          "quantity": 2,
          "unitPrice": 8999
        }
      }
    ]
  }
}
```

#### 11.4.2 混合操作类型

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "options": {
    "transaction": true,
    "returnAffectedCount": true
  },
  "mutation": {
    "batch": [
      {
        "operation": "CREATE",
        "objectType": "Order",
        "by": {"id": "order_002"},
        "data": {
          "orderNo": "ORD-20240301-002",
          "customerId": "cust_002"
        }
      }
    ]
  },
  "links": {
    "create": [
      {
        "relationships": "items",
        "from": {"objectType": "Order", "by": {"id": "order_002"}},
        "to": {"objectType": "Product", "by": {"id": "prod_001"}},
        "properties": {"quantity": 1}
      }
    ]
  }
}
```

### 11.5 非事务批量操作

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "SystemConfig"}
  ],
  "options": {
    "transaction": false,
    "continueOnFailure": true
  },
  "mutation": {
    "batch": [
      {
        "objectType": "SystemConfig",
        "by": {"configKey": "ENABLE_CACHE", "env": "production"},
        "data": {"value": "true", "updatedAt": "$now()"}
      },
      {
        "objectType": "SystemConfig",
        "by": {"configKey": "MAX_CONNECTIONS", "env": "production"},
        "data": {"value": "1000", "updatedAt": "$now()"}
      },
      {
        "objectType": "SystemConfig",
        "by": {"configKey": "TIMEOUT", "env": "production"},
        "set": {"value": "3600"}
      }
    ]
  }
}
```

### 11.6 批量对象操作

#### 11.6.1 批量创建（BATCH_CREATE）

批量创建多个对象，支持不同对象类型：

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Product"},
    {"objectType": "Category"}
  ],
  "mutation": {
    "batch": [
      {
        "operation": "CREATE",
        "objectType": "Product",
        "by": {"id": "prod_001"},
        "data": {
          "name": "iPhone 16",
          "price": 8999,
          "categoryId": "cat_electronics"
        }
      },
      {
        "operation": "CREATE",
        "objectType": "Product",
        "by": {"id": "prod_002"},
        "data": {
          "name": "MacBook Pro",
          "price": 19999,
          "categoryId": "cat_electronics"
        }
      },
      {
        "operation": "CREATE",
        "objectType": "Category",
        "by": {"id": "cat_electronics"},
        "data": {
          "name": "电子产品",
          "parentId": null
        }
      }
    ]
  }
}
```

#### 11.6.2 批量更新（BATCH_UPDATE）

批量更新多个对象：

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Product"}
  ],
  "mutation": {
    "batch": [
      {
        "objectType": "Product",
        "by": {"id": "prod_001"},
        "set": {
          "price": 7999,
          "updatedAt": "$now()"
        },
        "increment": {"viewCount": 1}
      },
      {
        "objectType": "Product",
        "by": {"id": "prod_002"},
        "set": {
          "status": "inactive",
          "updatedAt": "$now()"
        }
      },
      {
        "objectType": "Product",
        "by": {"id": "prod_003"},
        "unset": ["temporaryField", "draftData"]
      }
    ]
  }
}
```

#### 11.6.3 批量删除（BATCH_DELETE）

批量删除多个对象：

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"}
  ],
  "mutation": {
    "batch": [
      {
        "objectType": "Order",
        "by": {"id": "order_001"}
      },
      {
        "objectType": "Order",
        "by": {"id": "order_002"}
      },
      {
        "objectType": "Order",
        "by": {"id": "order_003"}
      }
    ]
  }
}
```

#### 11.6.4 条件批量操作

根据条件批量操作对象：

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Product"}
  ],
  "conditions": {
    "objectType": "Product",
    "relation": "AND",
    "children": [
      {"property": "status", "operator": "EQ", "values": ["out_of_stock"]},
      {"property": "stock", "operator": "LT", "values": [10]}
    ]
  },
  "mutation": {
    "set": {
      "status": "discontinued",
      "updatedAt": "$now()"
    }
  }
}
```

### 11.7 批量关联操作（BATCH_LINKS）

#### 11.7.1 批量创建关联

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "links": {
    "relationships": "items",
    "create": [
      {
        "from": {"objectType": "Order", "by": {"id": "order_001"}},
        "to": {"objectType": "Product", "by": {"id": "prod_001"}},
        "properties": {"quantity": 2, "price": 8999}
      },
      {
        "from": {"objectType": "Order", "by": {"id": "order_001"}},
        "to": {"objectType": "Product", "by": {"id": "prod_002"}},
        "properties": {"quantity": 1, "price": 19999}
      },
      {
        "from": {"objectType": "Order", "by": {"id": "order_002"}},
        "to": {"objectType": "Product", "by": {"id": "prod_001"}},
        "properties": {"quantity": 3, "price": 8999}
      }
    ]
  }
}
```

#### 11.7.2 批量删除关联

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "links": {
    "relationships": "items",
    "delete": [
      {
        "from": {"objectType": "Order", "by": {"id": "order_001"}},
        "to": {"objectType": "Product", "by": {"id": "prod_001"}}
      },
      {
        "from": {"objectType": "Order", "by": {"id": "order_002"}},
        "to": {"objectType": "Product", "by": {"id": "prod_003"}}
      }
    ]
  }
}
```

#### 11.7.3 批量更新关联属性

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "links": {
    "relationships": "items",
    "update": [
      {
        "from": {"objectType": "Order", "by": {"id": "order_001"}},
        "to": {"objectType": "Product", "by": {"id": "prod_001"}},
        "set": {"quantity": 5, "price": 8499}
      }
    ]
  }
}
```

### 11.8 数据导入（IMPORT）

数据导入操作用于从外部数据源批量导入对象数据。

#### 11.8.1 完整结构

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Product"}
  ],
  "options": {
    "transaction": true,
    "returnAffectedCount": true
  },
  "mutation": {
    "import": {
      "source": "excel",
      "sourceConfig": {
        "url": "https://storage.example.com/data/products.xlsx",
        "sheetName": "Sheet1",
        "hasHeader": true
      },
      "mapping": {
        "id": {"column": "A", "transform": "trim"},
        "name": {"column": "B"},
        "price": {"column": "C", "transform": "number"},
        "categoryId": {"column": "D"},
        "stock": {"column": "E", "transform": "number"}
      },
      "onConflict": "upsert",
      "batchSize": 1000,
      "skipErrors": true,
      "errorLogUrl": "https://storage.example.com/logs/import_errors.json"
    }
  }
}
```

#### 11.8.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| **mutation.import** | object | 是 | 导入配置 |
| mutation.import.source | string | 是 | 数据源类型：`excel` / `csv` / `json` / `database` / `api` |
| mutation.import.sourceConfig | object | 是 | 数据源配置（见下表） |
| mutation.import.mapping | object | 是 | 字段映射关系 |
| mutation.import.onConflict | string | 否 | 冲突处理策略：`skip` / `upsert` / `error` / `override` |
| mutation.import.batchSize | integer | 否 | 批次大小，默认 1000 |
| mutation.import.skipErrors | boolean | 否 | 是否跳过错误行，默认 false |
| mutation.import.errorLogUrl | string | 否 | 错误日志存储 URL |

**sourceConfig 配置说明**：

| source | 配置项 | 说明 |
|--------|--------|------|
| excel | url, sheetName, hasHeader | Excel 文件 URL、工作表名称、是否含表头 |
| csv | url, delimiter, hasHeader | CSV 文件 URL、分隔符、是否含表头 |
| json | url, path, arrayPath | JSON 文件 URL、数据路径、数组路径 |
| database | connectionString, query, driver | 数据库连接字符串、查询语句、驱动类型 |
| api | url, method, headers, body | API 地址、请求方法、请求头、请求体 |

**transform 转换函数**：

| 转换函数 | 说明 | 示例 |
|----------|------|------|
| trim | 去除首尾空白 | `"transform": "trim"` |
| number | 转为数字 | `"transform": "number"` |
| date | 解析日期 | `"transform": "date:YYYY-MM-DD"` |
| upper | 转大写 | `"transform": "upper"` |
| lower | 转小写 | `"transform": "lower"` |
| split | 分割字符串 | `"transform": "split:,"` |
| join | 合并数组 | `"transform": "join:-"` |
| lookup | 查找映射 | `"transform": "lookup:statusMap"` |

#### 11.8.3 CSV 导入示例

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Customer"}
  ],
  "mutation": {
    "import": {
      "source": "csv",
      "sourceConfig": {
        "url": "https://storage.example.com/data/customers.csv",
        "delimiter": ",",
        "hasHeader": true
      },
      "mapping": {
        "id": {"column": "customer_id"},
        "name": {"column": "full_name"},
        "email": {"column": "email_address"},
        "phone": {"column": "phone_number"},
        "status": {"column": "status", "transform": "lower"}
      },
      "onConflict": "skip",
      "batchSize": 500
    }
  }
}
```

#### 11.8.4 JSON 导入示例

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"}
  ],
  "mutation": {
    "import": {
      "source": "json",
      "sourceConfig": {
        "url": "https://storage.example.com/data/orders.json",
        "path": "$.data",
        "arrayPath": "$.data.orders"
      },
      "mapping": {
        "id": {"path": "$.orderId"},
        "orderNo": {"path": "$.order_number"},
        "customerId": {"path": "$.customer.id"},
        "totalAmount": {"path": "$.amount", "transform": "number"},
        "createdAt": {"path": "$.created_at", "transform": "date:YYYY-MM-DDTHH:mm:ssZ"}
      },
      "onConflict": "upsert",
      "batchSize": 100
    }
  }
}
```

### 11.9 数据导出（EXPORT）

数据导出操作用于批量导出对象数据到外部系统。

#### 11.9.1 完整结构

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"}
  ],
  "options": {
    "returnData": true
  },
  "mutation": {
    "export": {
      "destination": "csv",
      "destinationConfig": {
        "url": "https://storage.example.com/export/orders.csv",
        "delimiter": ",",
        "encoding": "UTF-8"
      },
      "conditions": {
        "objectType": "Order",
        "relation": "AND",
        "children": [
          {"property": "status", "operator": "EQ", "values": ["completed"]},
          {"property": "createdAt", "operator": "GTE", "values": ["2024-01-01"]}
        ]
      },
      "returns": {
        "fields": ["id", "orderNo", "customerId", "totalAmount", "status", "createdAt"]
      },
      "orders": [
        {"field": "createdAt", "direction": "DESC"}
      ],
      "maxResults": 10000
    }
  }
}
```

#### 11.9.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| **mutation.export** | object | 是 | 导出配置 |
| mutation.export.destination | string | 是 | 目标类型：`excel` / `csv` / `json` / `database` / `api` |
| mutation.export.destinationConfig | object | 是 | 目标配置（见下表） |
| mutation.export.conditions | object | 否 | 导出条件（详见第2.3节） |
| mutation.export.returns | object | 否 | 返回字段投影（详见第2.4节） |
| mutation.export.orders | array | 否 | 排序定义（详见第2.5节） |
| mutation.export.maxResults | integer | 否 | 最大导出数量，默认 100000 |

**destinationConfig 配置说明**：

| destination | 配置项 | 说明 |
|-------------|--------|------|
| excel | url, sheetName, append | Excel 文件 URL、工作表名称、是否追加 |
| csv | url, delimiter, encoding, append | CSV 文件 URL、分隔符、编码、是否追加 |
| json | url, format, array, indent | JSON 文件 URL、格式、数组包装、缩进 |
| database | connectionString, table, mode | 数据库连接字符串、目标表名、写入模式 |
| api | url, method, headers, batchSize | API 地址、请求方法、请求头、批量大小 |

#### 11.9.3 Excel 导出示例

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Product"}
  ],
  "mutation": {
    "export": {
      "destination": "excel",
      "destinationConfig": {
        "url": "https://storage.example.com/export/products_report.xlsx",
        "sheetName": "Products",
        "append": false
      },
      "returns": {
        "fields": ["id", "name", "price", "category", "stock", "createdAt"]
      },
      "orders": [
        {"field": "category", "direction": "ASC"},
        {"field": "price", "direction": "DESC"}
      ],
      "maxResults": 5000
    }
  }
}
```

#### 11.9.4 JSON 导出示例

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Customer"}
  ],
  "mutation": {
    "export": {
      "destination": "json",
      "destinationConfig": {
        "url": "https://storage.example.com/export/customers.json",
        "format": "array",
        "indent": 2
      },
      "conditions": {
        "objectType": "Customer",
        "property": "status",
        "operator": "EQ",
        "values": ["active"]
      },
      "returns": {
        "fields": ["id", "name", "email", "phone", "createdAt"]
      },
      "maxResults": 10000
    }
  }
}
```

#### 11.9.5 API 导出示例

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"}
  ],
  "mutation": {
    "export": {
      "destination": "api",
      "destinationConfig": {
        "url": "https://api.example.com/orders/sync",
        "method": "POST",
        "headers": {
          "Authorization": "Bearer ${env.API_TOKEN}",
          "Content-Type": "application/json"
        },
        "batchSize": 100
      },
      "conditions": {
        "objectType": "Order",
        "property": "synced",
        "operator": "EQ",
        "values": [false]
      },
      "returns": {
        "fields": ["id", "orderNo", "customerId", "totalAmount", "items"]
      },
      "maxResults": 1000
    }
  }
}
```

### 11.10 批量关联导出

支持导出对象之间的关联关系：

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "options": {
    "returnData": true
  },
  "mutation": {
    "export": {
      "destination": "csv",
      "destinationConfig": {
        "url": "https://storage.example.com/export/order_items.csv"
      },
      "relationships": "items",
      "returns": {
        "fields": ["id", "orderNo"],
        "linkFields": ["quantity", "price"]
      }
    }
  }
}
```

### 11.11 响应格式

#### 11.11.1 批量操作响应

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "objectType": "Order",
        "by": {"id": "order_001"},
        "action": "created",
        "etag": "\"abc123\""
      },
      {
        "objectType": "Product",
        "by": {"id": "prod_001"},
        "action": "updated",
        "changedFields": ["price", "updatedAt"]
      }
    ],
    "summary": {
      "totalProcessed": 2,
      "totalCreated": 1,
      "totalUpdated": 1,
      "totalFailed": 0
    }
  },
  "metadata": {
    "executionTime": 150
  }
}
```

#### 11.11.2 导入响应

```json
{
  "success": true,
  "data": {
    "totalRows": 1000,
    "processedRows": 998,
    "skippedRows": 2,
    "failedRows": 0,
    "createdCount": 500,
    "updatedCount": 498,
    "errorLogUrl": null
  },
  "metadata": {
    "executionTime": 5000
  }
}
```

#### 11.11.3 导出响应

```json
{
  "success": true,
  "data": {
    "totalExported": 1000,
    "fileUrl": "https://storage.example.com/export/data_20240301.csv",
    "fileSize": 524288,
    "checksum": "md5:abc123..."
  },
  "metadata": {
    "executionTime": 3000
  }
}
```

### 11.12 BATCH 操作速查

| 场景 | 必填字段 | 可选字段 |
|------|----------|----------|
| 事务批量操作 | objects, mutation.batch, options.transaction: true | isolationLevel, timeoutMs |
| 非事务批量操作 | objects, mutation.batch | options.continueOnFailure |
| 批量创建 | objects, mutation.batch[].operation: "CREATE", mutation.batch[].data | by |
| 批量更新 | objects, mutation.batch[].by, mutation.batch[].set/unset/increment | - |
| 批量删除 | objects, mutation.batch[].by | - |
| 批量关联 | objects, links.create/update/delete | links.relationships |
| 数据导入 | objects, mutation.import.source, mutation.import.mapping | onConflict, batchSize |
| 数据导出 | objects, mutation.export.destination | conditions, returns, orders |

### 11.13 最佳实践

1. **事务控制**：
    - 相关联的操作使用 `transaction: true`
    - 独立操作使用 `transaction: false` 提高性能

2. **批量大小**：
    - 推荐 `batchSize: 100-1000`
    - 大数据量分批导入导出

3. **错误处理**：
    - 使用 `continueOnFailure: true` 处理部分失败
    - 配置 `skipErrors: true` 和 `errorLogUrl` 记录错误

4. **导入导出**：
    - 导入前先备份数据
    - 导出时指定明确的条件减少数据量

5. **性能优化**：
    - 使用索引字段作为查询条件
    - 避免导出过大数据集（建议分批）

---

## 12. 执行选项（options）

### 12.1 通用选项

```json
{
  "options": {
    "transaction": true,
    "timeoutMs": 30000,
    "isolationLevel": "READ_COMMITTED",
    "consistency": "strong",
    "returnAffectedCount": true,
    "returnData": true,
    "returnBeforeState": false
  }
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| transaction | boolean | false | 是否启用事务 |
| timeoutMs | integer | 30000 | 超时时间（毫秒） |
| isolationLevel | string | READ_COMMITTED | 隔离级别 |
| consistency | string | eventual | 一致性级别 |
| returnAffectedCount | boolean | true | 是否返回影响数量 |
| returnData | boolean | false | 是否返回数据 |
| returnBeforeState | boolean | false | 是否返回更新前状态 |

### 12.2 并发控制

```json
{
  "options": {
    "concurrency": {
      "ifMatch": "\"etag-abc123\"",
      "ifUnmodifiedSince": "2024-03-01T12:00:00Z",
      "forceUpdate": false
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| ifMatch | ETag 条件 |
| ifUnmodifiedSince | 时间戳条件 |
| forceUpdate | 强制更新，跳过检查 |

---

## 13. 表达式语法

### 13.1 表达式操作符

```json
{
  "expression": {
    "op": "add",
    "params": [
      {"field": "price"},
      {"value": 10}
    ]
  }
}
```

| 类别 | 操作符 | 说明 |
|------|--------|------|
| 算术 | add, sub, multiply, divide, mod | 四则运算 |
| 比较 | eq, neq, gt, gte, lt, lte | 比较运算 |
| 逻辑 | and, or, not | 逻辑运算 |
| 字符串 | concat, upper, lower, length | 字符串操作 |
| 条件 | case | 条件表达式 |
| 类型 | cast | 类型转换 |

### 13.2 内置函数

| 函数 | 说明 | 示例 |
|------|------|------|
| $now() | 当前时间戳 | `$now()` |
| $uuid() | 生成 UUID | `$uuid()` |
| $random(min, max) | 生成随机数 | `$random(100, 999)` |
| $currentUser() | 当前用户 | `$currentUser()` |

---

## 14. 完整示例

### 14.1 订单处理（复杂事务）

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Order"},
    {"objectType": "Product"}
  ],
  "options": {
    "transaction": true,
    "timeoutMs": 60000,
    "returnAffectedCount": true
  },
  "mutation": {
    "batch": [
      {
        "operation": "CREATE",
        "objectType": "Order",
        "by": {"orderNo": "ORD-20240301-001"},
        "data": {
          "customerId": "cust_001",
          "status": "pending",
          "createdAt": "$now()"
        }
      },
      {
        "operation": "UPDATE",
        "objectType": "Product",
        "by": {"id": "prod_001"},
        "set": {"status": "active"}
      },
      {
        "operation": "UPDATE",
        "objectType": "Product",
        "by": {"id": "prod_002"},
        "set": {"status": "active"}
      }
    ]
  },
  "links": {
    "relationships": "items",
    "create": [
      {
        "from": {"objectType": "Order", "by": {"orderNo": "ORD-20240301-001"}},
        "to": {"objectType": "Product", "by": {"id": "prod_001"}},
        "properties": {"quantity": 2, "price": 7999}
      },
      {
        "from": {"objectType": "Order", "by": {"orderNo": "ORD-20240301-001"}},
        "to": {"objectType": "Product", "by": {"id": "prod_002"}},
        "properties": {"quantity": 1, "price": 1999}
      }
    ]
  }
}
```

### 14.2 产品搜索聚合

```json
{
  "version": "1.0",
  "operation": "QUERY",
  "objects": [
    {"objectType": "Product"}
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"property": "status", "operator": "EQ", "values": ["active"]},
      {"property": "price", "operator": "GTE", "values": [100]},
      {"property": "name", "operator": "CONTAINS", "values": ["手机"]}
    ]
  },
  "returns": {
    "fields": ["id", "name", "price", "category", "status"],
    "computed": [
      {
        "alias": "discountedPrice",
        "expression": {
          "op": "multiply",
          "params": [
            {"field": "price"},
            {"op": "sub", "params": [{"value": 1}, {"field": "discountRate"}]}
          ]
        }
      }
    ]
  },
  "orders": [
    {"field": "price", "direction": "DESC"}
  ],
  "maxResults": 20
}
```

### 14.3 批量导入导出

```json
{
  "version": "1.0",
  "operation": "BATCH",
  "objects": [
    {"objectType": "Product"}
  ],
  "options": {
    "transaction": true
  },
  "mutation": {
    "import": {
      "source": "csv",
      "sourceConfig": {
        "url": "https://storage.example.com/data/products.csv",
        "delimiter": ",",
        "hasHeader": true
      },
      "mapping": {
        "id": {"column": "product_id"},
        "name": {"column": "product_name"},
        "price": {"column": "price", "transform": "number"},
        "category": {"column": "category"},
        "stock": {"column": "stock", "transform": "number"}
      },
      "onConflict": "upsert",
      "batchSize": 500
    }
  }
}
```

### 14.4 关联查询示例

```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "by": {"orderNo": "ORD-20240301-001"}
    }
  ],
  "relationships": "items",
  "conditions": {
    "objectType": "OrderItem",
    "property": "status",
    "operator": "EQ",
    "values": ["active"]
  },
  "returns": {
    "fields": ["id", "name", "price", "category"]
  },
  "orders": [
    {"field": "createdAt", "direction": "DESC"}
  ],
  "maxResults": 100
}
```

### 14.5 聚合统计示例

```json
{
  "version": "1.0",
  "operation": "AGGREGATE",
  "objects": [
    {"objectType": "Order"}
  ],
  "conditions": {
    "property": "createdAt",
    "operator": "GTE",
    "values": ["2024-01-01T00:00:00Z"]
  },
  "groupBy": [
    {"field": "status"}
  ],
  "aggregations": [
    {"field": "totalAmount", "function": "SUM", "alias": "amount"},
    {"field": "id", "function": "COUNT", "alias": "count"},
    {"field": "totalAmount", "function": "AVG", "alias": "avgAmount"},
    {"field": "totalAmount", "function": "MAX", "alias": "maxAmount"},
    {"field": "totalAmount", "function": "MIN", "alias": "minAmount"}
  ],
  "orders": [
    {"field": "amount", "direction": "DESC"}
  ],
  "maxResults": 100
}
```

---

## 15. Operation 类型总览

### 15.1 Operation 分类

OQL 定义了以下 Operation 类型：

| 分类 | Operation | 说明 | 适用场景 |
|------|-----------|------|----------|
| **查询类** | QUERY | 对象查询 | 读取对象列表和详情 |
| | AGGREGATE | 聚合计算 | 统计、分组聚合 |
| | LIST_LINKS | 关联列表 | 列出关联对象 |
| | GET_LINKED_OBJECT | 关联对象 | 获取特定关联对象 |
| **写操作类** | CREATE | 创建对象 | 新建单个或批量对象 |
| | UPDATE | 更新对象 | 修改对象属性 |
| | DELETE | 删除对象 | 删除对象（软/硬删除） |
| | UPSERT | 插入或更新 | 存在更新/不存在创建 |
| **批量类** | BATCH | 批量操作 | 组合多个写操作 |
|  | **SUBGRAPH** | **子图操作** | **批量多对象 + 多关联** | **复杂业务场景（见 v1.0 文档）** |

### 15.2 Operation 能力对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OQL Operation 能力矩阵                               │
├─────────────────┬───────────────────────────────────────────────────────────┤
│                 │                                                           │
│   单对象操作     │   CREATE / UPDATE / DELETE / UPSERT                       │
│   单对象查询     │   QUERY（单个对象）                                        │
│   列表查询      │   QUERY（列表） / AGGREGATE / LIST_LINKS                   │
│   关联查询      │   LIST_LINKS / GET_LINKED_OBJECT                           │
│   批量写操作    │   BATCH                                                   │
│   多对象+多关联  │   **ASSOCIATION_QUERY**（第 10 章）                        │
│                 │                                                           │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

### 15.3 与 Palantir SearchQL 对比

| 特性 | Palantir SearchQL | OQL v1.0 |
|------|-------------------|----------|
| 顶层结构 | 分散 | 统一 |
| 操作类型 | 查询为主 | 完整 CRUD |
| 字段投影 | select | select |
| 过滤条件 | where | filter |
| 关联查询 | links | links + query |
| 排序 | orderBy | orderBy |
| 数量限制 | pageToken | maxResults |
| 聚合 | aggregations | aggregation |
| Link 操作 | 不支持 | 支持（边上无属性） |
| 事务控制 | 不支持 | options.transaction |
| 并发控制 | ETag | concurrency |
| 批量操作 | 支持 | BATCH |
| 多对象关联 | 不支持 | ASSOCIATION_QUERY（v1.0） |
| 多数据源映射 | 不支持 | 支持 |
| 复合主键 | 不支持 | 支持 |
| 自定义扩展 | 不支持 | extensions |
| AI 友好度 | 一般 | 优化 |

---

## 16. DSL 翻译引擎转换示例

### 16.1 翻译引擎概述

DSL 翻译引擎负责将 OQL 转换为目标存储系统的查询语言：
- **关系型数据库** → 生成标准 SQL（MySQL、Gauss V3、PostgreSQL）
- **图数据库** → 生成 GQL（NebulaGraph）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DSL 翻译引擎架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────────────┐     ┌────────────────────┐  │
│  │   OQL DSL    │────▶│  DSL 翻译引擎         │────▶│  RDB SQL / GQL     │  │
│  │              │     │                      │     │                    │  │
│  │ {operation:  │     │  1. 解析DSL AST      │     │  SELECT * FROM     │  │
│  │  QUERY,      │     │  2. 属性→数据源映射  │     │  Product WHERE...  │  │
│  │  target:     │     │  3. 条件优化下推     │     │                    │  │
│  │  objectType: │     │  4. 生成目标语句      │     │  LOOKUP ON Product │  │
│  │  "Product",  │     │  5. 结果合并          │     │  WHERE...          │  │
│  │  ...}        │     │                      │     │                    │  │
│  └──────────────┘     └──────────────────────┘     └────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**支持的数据库**：
- MySQL 5.7 / 8.X（华为云版本）- 主业务数据
- Gauss V3（GDE版本）- 主业务数据（adc模型）
- PostgreSQL 15.X（华为云版本）- 资源、拓扑
- ClickHouse（GDE版本）- 日志、trace
- ElasticSearch（GDE版本/华为云版本）- 历史数据、日志、指标
- Carbon（GDE版本）- 性能数据
- NebulaGraph（GDE版本）- 资源、拓扑、知识
- Gauss V5（GDE版本）- 向量数据

### 16.2 数据源映射说明

#### 16.2.1 单数据源场景

所有属性存储在同一个数据源中：

```json
{
  "objectType": "Product",
  "attributes": {
    "id": {"source": "mysql", "table": "products", "column": "id"},
    "name": {"source": "mysql", "table": "products", "column": "name"},
    "price": {"source": "mysql", "table": "products", "column": "price"},
    "status": {"source": "mysql", "table": "products", "column": "status"}
  }
}
```

#### 16.2.2 多数据源场景

同一对象的不同属性映射到不同的物理数据源：

```json
{
  "objectType": "Order",
  "attributes": {
    "id": {"source": "mysql-5.7", "table": "orders", "column": "id"},
    "orderNo": {"source": "mysql-5.7", "table": "orders", "column": "order_no"},
    "customerId": {"source": "gauss-v3", "table": "customers", "column": "customer_id"},
    "amount": {"source": "postgresql-15", "table": "payments", "column": "amount"},
    "status": {"source": "postgresql-15", "table": "orders", "column": "status"},
    "shippingAddr": {"source": "elasticsearch", "index": "order_addresses", "field": "address"},
    "createdAt": {"source": "carbon", "metric": "order.created_at"}
  }
}
```

**多数据源查询流程**：
```
1. 并行从 MySQL 5.7、Gauss V3、PostgreSQL 15.X、ElasticSearch、Carbon 获取数据
2. 按主键关联结果
3. 合并为统一对象返回
```

---

### 16.3 QUERY 操作转换示例

#### 16.3.1 单数据源 - 简单查询

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "QUERY",
  "objects": [
    {"objectType": "Product"}
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"property": "status", "operator": "EQ", "values": ["active"]},
      {"property": "price", "operator": "GTE", "values": [1000]}
    ]
  },
  "returns": {
    "fields": ["id", "name", "price"]
  },
  "orders": [
    {"field": "price", "direction": "DESC"}
  ],
  "maxResults": 20
}
```

**转换为 RDB SQL**：
```sql
SELECT id, name, price
FROM products
WHERE status = 'active'
  AND price >= 1000
ORDER BY price DESC
LIMIT 20;
```

**转换为 GQL（NebulaGraph）**：

```gql
LOOKUP ON Product
WHERE Product.status == "active" AND Product.price >= 1000
YIELD Product.id AS id, Product.name AS name, Product.price AS price
ORDER BY Product.price DESC
LIMIT 0, 20;
```

---

#### 16.3.2 单数据源 - 复杂过滤查询

**OQL DSL**：

```json
{
  "version": "1.0",
  "operation": "QUERY",
  "objects": [
    {"objectType": "Order"}
  ],
  "conditions": {
    "relation": "AND",
    "children": [
      {"property": "status", "operator": "EQ", "values": ["completed"]},
      {"property": "createdAt", "operator": "GTE", "values": ["2024-01-01T00:00:00Z"]},
      {"property": "orderNo", "operator": "CONTAINS", "values": ["202403"]}
    ]
  },
  "returns": {
    "fields": ["id", "orderNo", "amount", "status", "createdAt"]
  },
  "orders": [
    {"field": "createdAt", "direction": "DESC"}
  ],
  "maxResults": 50
}
```

**转换为 RDB SQL**：
```sql
SELECT id, order_no, amount, status, created_at
FROM orders
WHERE status = 'completed'
  AND created_at >= '2024-01-01 00:00:00'
  AND order_no LIKE '%202403%'
ORDER BY created_at DESC
LIMIT 50;
```

**转换为 GQL（NebulaGraph）**：

```gql
LOOKUP ON Order
WHERE Order.status == "completed"
  AND Order.createdAt >= datetime('2024-01-01T00:00:00')
  AND Order.orderNo CONTAINS '202403'
YIELD Order.id AS id, Order.orderNo AS orderNo, Order.amount AS amount,
       Order.status AS status, Order.createdAt AS createdAt
ORDER BY Order.createdAt DESC
LIMIT 0, 50;
```

---

#### 16.3.3 多数据源 - 查询示例

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "QUERY",
  "objects": [
    {"objectType": "Order"}
  ],
  "conditions": {
    "property": "status",
    "operator": "EQ",
    "values": ["pending"]
  },
  "returns": {
    "fields": ["id", "orderNo", "amount", "status", "shippingAddr"]
  },
  "maxResults": 10
}
```

**数据源映射**：
- id, orderNo, status → MySQL 5.7/8.X (华为云版本) orders 表
- amount → PostgreSQL 15.X (华为云版本) payments 表
- shippingAddr → ElasticSearch (GDE版本) order_addresses 索引

**转换为 RDB SQL（MySQL 5.7）**：
```sql
SELECT id, order_no, status
FROM orders
WHERE status = 'pending'
LIMIT 10;
```

**转换为 RDB SQL（PostgreSQL 15.X）**：

```sql
SELECT order_id, SUM(amount) as amount
FROM payments
WHERE order_id IN (/* 主键列表 */)
GROUP BY order_id;
```

**转换为 ElasticSearch 查询**：

```json
GET /order_addresses/_search
{
  "query": {
    "terms": {
      "orderId": ["/* 主键列表 */"]
    }
  },
  "_source": ["shippingAddr"]
}
```

**结果合并**（翻译引擎内部处理）：

```json
{
  "data": [
    {
      "id": "order_001",
      "orderNo": "ORD-20240301-001",
      "amount": 199.99,
      "status": "pending",
      "shippingAddr": {"city": "北京", "detail": "xxx"}
    }
  ]
}
```

---

### 16.4 CREATE 操作转换示例

#### 16.4.1 单数据源 - 创建对象

**OQL DSL**：

```json
{
  "version": "1.0",
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "data": {
      "name": "iPhone 16",
      "price": 8999,
      "category": "electronics",
      "status": "active"
    }
  }
}
```

**转换为 RDB SQL（INSERT）**：

```sql
INSERT INTO products (id, name, price, category, status, created_at, updated_at)
VALUES ('prod_001', 'iPhone 16', 8999, 'electronics', 'active', NOW(), NOW());
```

**转换为 GQL（NebulaGraph）**：

```gql
INSERT VERTEX Product(id, name, price, category, status, createdAt, updatedAt)
VALUES "prod_001":("prod_001", "iPhone 16", 8999, "electronics", "active", now(), now());
```

**响应**：

```json
{
  "success": true,
  "data": {
    "created": [{
      "by": {"id": "prod_001"},
      "etag": "\"abc123\""
    }]
  }
}
```

---

#### 16.4.2 多数据源 - 创建对象

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Order",
      "byComposite": {"sourceSystem": "ERP", "orderId": "ORD-001"}
    }
  ],
  "mutation": {
    "data": {
      "customerId": "CUST-001",
      "amount": 19999,
      "status": "pending",
      "shippingAddr": {"city": "上海", "detail": "xxx"}
    }
  }
}
```

**转换为 RDB SQL（MySQL 5.7 - 订单基础信息）**：

```sql
INSERT INTO orders (source_system, order_id, customer_id, status, created_at)
VALUES ('ERP', 'ORD-001', 'CUST-001', 'pending', NOW());
```

**转换为 RDB SQL（PostgreSQL 15.X - 金额信息）**：

```sql
INSERT INTO payments (source_system, order_id, amount, created_at)
VALUES ('ERP', 'ORD-001', 19999, NOW());
```

**转换为 ElasticSearch（地址信息）**：

```json
PUT /order_addresses/_doc/ERP-ORD-001
{
  "sourceSystem": "ERP",
  "orderId": "ORD-001",
  "address": {"city": "上海", "detail": "xxx"},
  "createdAt": "2024-03-01T10:00:00Z"
}
```

---

### 16.5 UPDATE 操作转换示例

#### 16.5.1 单数据源 - 更新对象

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "set": {
      "price": 7999,
      "status": "active",
      "updatedAt": "$now()"
    },
    "unset": ["discount"]
  }
}
```

**转换为 RDB SQL（UPDATE）**：
```sql
UPDATE products
SET price = 7999,
    status = 'active',
    updated_at = NOW(),
    discount = NULL
WHERE id = 'prod_001';
```

**转换为 GQL（NebulaGraph）**：
```gql
UPDATE VERTEX ON Product "prod_001"
SET
    price = 7999,
    status = "active",
    updatedAt = now()
YIELD Product.id, Product.price, Product.status;
```

---

#### 16.5.2 复合主键 - 更新对象

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "OrderItem",
      "byComposite": {"sourceSystem": "ERP", "orderId": "ORD-001", "productId": "PROD-001"}
    }
  ],
  "mutation": {
    "set": {
      "quantity": 5,
      "updatedAt": "$now()"
    },
    "increment": {"version": 1}
  }
}
```

**转换为 RDB SQL**：
```sql
UPDATE order_items
SET quantity = 5,
    version = version + 1,
    updated_at = NOW()
WHERE source_system = 'ERP'
  AND order_id = 'ORD-001'
  AND product_id = 'PROD-001';
```

---

#### 16.5.3 批量条件更新

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "UPDATE",
  "objects": [
    {"objectType": "Product"}
  ],
  "conditions": {
    "property": "status",
    "operator": "EQ",
    "values": ["outdated"]
  },
  "mutation": {
    "set": {
      "status": "archived",
      "archivedAt": "$now()"
    }
  }
}
```

**转换为 RDB SQL**：
```sql
UPDATE products
SET status = 'archived',
    archived_at = NOW()
WHERE status = 'outdated';
```

---

### 16.6 DELETE 操作转换示例

#### 16.6.1 单数据源 - 删除对象

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Product",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "deleteMode": "soft"
  }
}
```

**转换为 RDB SQL（软删除）**：
```sql
UPDATE products
SET status = 'deleted',
    deleted_at = NOW(),
    deleted_by = CURRENT_USER()
WHERE id = 'prod_001';
```

**转换为 RDB SQL（硬删除）**：
```sql
DELETE FROM products WHERE id = 'prod_001';
```

**转换为 GQL（NebulaGraph 软删除）**：
```gql
UPDATE VERTEX ON Product "prod_001"
SET status = "deleted", deletedAt = now();
```

**转换为 GQL（NebulaGraph 硬删除）**：
```gql
DELETE VERTEX ON Product "prod_001";
```

---

#### 16.6.2 复合主键 - 删除对象

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "byComposite": {"sourceSystem": "ERP", "orderId": "ORD-001"}
    }
  ],
  "mutation": {
    "deleteMode": "hard"
  }
}
```

**转换为 RDB SQL**：
```sql
DELETE FROM orders
WHERE source_system = 'ERP'
  AND order_id = 'ORD-001';
```

---

#### 16.6.3 级联删除

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "by": {"id": "order_001"}
    }
  ],
  "mutation": {
    "deleteMode": "hard",
    "cascade": true,
    "cascadeLinks": ["items", "payments"]
  }
}
```

**转换为 RDB SQL**：
```sql
-- 删除订单
DELETE FROM orders WHERE id = 'order_001';

-- 级联删除订单项
DELETE FROM order_items WHERE order_id = 'order_001';

-- 级联删除支付记录
DELETE FROM payments WHERE order_id = 'order_001';
```

---

### 16.7 AGGREGATE 操作转换示例

#### 16.7.1 单数据源 - 分组聚合

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "AGGREGATE",
  "objects": [
    {"objectType": "Order"}
  ],
  "conditions": {
    "property": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "groupBy": [
    {"field": "category"}
  ],
  "aggregations": [
    {"field": "amount", "function": "SUM", "alias": "totalAmount"},
    {"field": "id", "function": "COUNT", "alias": "orderCount"},
    {"field": "amount", "function": "AVG", "alias": "avgAmount"}
  ]
}
```

**转换为 RDB SQL**：
```sql
SELECT
    category,
    SUM(amount) AS totalAmount,
    COUNT(id) AS orderCount,
    AVG(amount) AS avgAmount
FROM orders
WHERE status = 'completed'
GROUP BY category;
```

**转换为 GQL（NebulaGraph）**：

```gql
MATCH (o:Order)
WHERE o.status == "completed"
YIELD o.category AS category, o.amount AS amount
GROUP BY $-.category
YIELD
    $-.category AS category,
    SUM($-.amount) AS totalAmount,
    COUNT(*) AS orderCount,
    AVG($-.amount) AS avgAmount
ORDER BY $-.category;
```

---

#### 16.7.2 多数据源 - 全局聚合

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "AGGREGATE",
  "objects": [
    {"objectType": "Order"}
  ],
  "aggregations": [
    {"field": "amount", "function": "SUM", "alias": "totalSales"},
    {"field": "id", "function": "COUNT", "alias": "totalOrders"}
  ]
}
```

**转换为 RDB SQL（MySQL 5.7）**：
```sql
SELECT COUNT(*) AS totalOrders FROM orders;
```

**转换为 RDB SQL（PostgreSQL 15.X）**：
```sql
SELECT SUM(amount) AS totalSales FROM payments;
```

**结果合并（翻译引擎内部）**：
```json
{
  "data": [{
    "metrics": [
      {"name": "totalSales", "value": 1500000},
      {"name": "totalOrders", "value": 1200}
    ],
    "group": {}
  }]
}
```

---

### 16.8 UPSERT 操作转换示例

#### 16.8.1 单数据源 - 插入或更新

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Product",
      "by": {"id": "prod_001"}
    }
  ],
  "mutation": {
    "onCreate": {
      "name": "iPhone 16",
      "price": 8999,
      "category": "electronics"
    },
    "onUpdate": {
      "price": 7999,
      "updatedAt": "$now()"
    }
  }
}
```

**转换为 RDB SQL（MySQL 5.7）**：
```sql
INSERT INTO products (id, name, price, category, created_at, updated_at)
VALUES ('prod_001', 'iPhone 16', 8999, 'electronics', NOW(), NOW())
ON DUPLICATE KEY UPDATE
    price = 7999,
    updated_at = NOW();
```

**转换为 GQL（NebulaGraph UPSERT）**：
```gql
UPSERT VERTEX ON Product "prod_001"
SET
    name = "iPhone 16",
    price = 7999,
    category = "electronics",
    updatedAt = now();
```

---

### 16.9 LIST_LINKED_OBJECTS 操作转换示例

#### 16.9.1 关联对象查询

**OQL DSL**：
```json
{
  "version": "1.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [
    {
      "objectType": "Order",
      "by": {"id": "order_001"}
    }
  ],
  "relationships": "items",
  "returns": {
    "fields": ["id", "name", "price"]
  },
  "maxResults": 50
}
```

**转换为 RDB SQL**：

```sql
-- 先查询关联关系
SELECT target_object_key
FROM object_links
WHERE source_object_type = 'Order'
  AND source_object_key = 'order_001'
  AND link_type = 'items';

-- 再查询关联对象
SELECT p.id, p.name, p.price
FROM products p
WHERE p.id IN (/* 关联的主键列表 */);
```

**转换为 GQL（NebulaGraph）**：
```gql
GO FROM "order_001" OVER items
YIELD items._dst AS id
| LOOKUP ON Product WHERE Product.id == $-.id
YIELD Product.id AS id, Product.name AS name, Product.price AS price
LIMIT 50;
```

---

### 16.10 翻译规则速查表

| OQL 元素 | RDB SQL 映射 | GQL (NebulaGraph) |
|----------|--------------|-------------------|
| objects[].objectType | 表名 / FROM 子句 | 节点类型 / LOOKUP/GO |
| returns.fields | SELECT 列 | YIELD 属性 AS 别名 |
| conditions.EQ | WHERE field = value | WHERE field == value |
| conditions.GTE | WHERE field >= value | WHERE field >= value |
| conditions.LT | WHERE field < value | WHERE field < value |
| conditions.IN | WHERE field IN (...) | WHERE field IN [...] |
| conditions.relation: AND | WHERE cond1 AND cond2 | WHERE cond1 AND cond2 |
| conditions.relation: OR | WHERE cond1 OR cond2 | WHERE cond1 OR cond2 |
| conditions.CONTAINS | WHERE field LIKE '%val%' | WHERE field CONTAINS 'val' |
| orders | ORDER BY field ASC/DESC | ORDER BY field ASC/DESC |
| maxResults | LIMIT N | LIMIT 0, N |
| groupBy | GROUP BY field | GROUP BY field YIELD |
| aggregations | SUM/COUNT/AVG/MIN/MAX | SUM/COUNT/AVG/MIN/MAX |
| mutation.data | INSERT INTO ... | INSERT VERTEX Type() VALUES |
| mutation.set | UPDATE ... SET | UPDATE VERTEX ON Type() SET |
| mutation.deleteMode | DELETE FROM ... | DELETE VERTEX ON |

**操作符映射速查**：

| OQL 操作符 | SQL | NebulaGraph |
|-----------|-----|-------------|
| EQ | = | == |
| NE | <> | != |
| AND | AND | AND |
| OR | OR | OR |
| CONTAINS | LIKE %x% | CONTAINS 'x' |
| IN | IN (a,b,c) | IN [a,b,c] |

---

### 16.11 多数据源处理策略

| 场景 | 处理策略 |
|------|----------|
| **属性分散在多个数据源** | 并行查询 → 按主键关联 → 合并结果 |
| **跨数据源 JOIN** | 优先在数据源内完成 JOIN，不行则应用层处理 |
| **分布式事务** | 使用最终一致性或 Saga 模式 |
| **结果排序** | 各数据源返回 topN → 应用层合并排序 |
| **分页** | 各数据源返回更多数据 → 应用层分页 |

**示例：多数据源查询处理流程**：
```
1. 解析 OQL，获取查询条件和字段映射
2. 按数据源分组查询条件
3. 并行执行各数据源查询
4. 收集各数据源结果
5. 按主键关联结果
6. 应用层过滤（不支持下推的条件）
7. 排序和分页
8. 返回统一结果
```

---

## 17. 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-01 | 初始版本发布 |
| 1.0 | 2026-03-01 | 统一顶层结构，整合查询/增删改/Link操作 |
| 1.0 | 2026-03-01 | 增加关联查询：LIST_LINKS、GET_LINKED_OBJECT |
| 1.0 | 2026-03-01 | 独立子图操作文档，分离 SUBGRAPH 操作 |
| 1.0 | 2026-03-01 | 增加 Section 16：DSL翻译示例（QUERY/CREATE/UPDATE/DELETE/AGGREGATE/UPSERT/LIST_LINKED_OBJECTS → SQL/GQL转换，含单数据源和多数据源场景） |
| 1.0 | 2026-03-01 | 删除第9章 Link 操作；移除 Neo4j Cypher GQL 示例，仅保留 NebulaGraph GQL；刷新支持的数据库列表 |
| 1.0 | 2026-03-01 | 支持数据库列表：Nebula(GDE)、Gauss V3(GDE)、MySQL 5.7/8.X(华为云)、ClickHouse(GDE)、ElasticSearch(GDE/华为云)、Carbon(GDE)、PostgreSQL 15.X、Gauss V5(GDE) |
| 1.0 | 2026-03-01 | 增加 2.5 节：无过滤条件查询说明（可查询对象类型所有对象），补充 nextPageToken 和 data 数组响应格式 |
| 1.0 | 2026-03-03 | 增加关联查询（ASSOCIATION_QUERY）能力：批量多对象 + 多关联关系查询，补充 maxResults 参数说明，并增加时序属性查询（TIMESERIES_QUERY）说明 |
| 1.0 | 2026-03-03 | target 新增 version 字段标识对象模型版本；by 和 byComposite 改为 KV 形式；更新复合主键说明（1.4 节）；更新所有示例中的主键格式 |
| 1.0 | 2026-03-07 | 统一顶层为 `objects`（移除 `targets`）；新增跨对象条件查询（whereFrom）；支持同表多对象属性查询；新增 MULTI_OBJECT_QUERY 操作类型；移除分页语法，改为 `maxResults` 上限 100k；ASSOCIATION_QUERY 增强 conditions/returns/orders 等 DSL 参数定义，并新增 nGQL 对应关系与错误码说明 |

---

## 附录 A：DSL 文件清单

| 文件 | 版本 | 说明 |
|------|------|------|
| 本体对象操作语言(OQL)-DSL规范v1.1.md | 1.0 | 统一 DSL 规范（查询/增删改/关联操作） |
| **本体对象操作语言(OQL)-子图DSL规范v1.2.md** | **1.0** | **子图操作（SUBGRAPH）—— 批量多对象 + 多关联** |
| 本体对象操作服务-接口规范.md | 1.0 | REST API 接口说明 |
| 本体对象操作接口规范.json | 1.0 | OpenAPI 3.0 规范 |
| 本体对象操作接口-错误码设计.md | 1.0 | 错误码定义 |

> **说明**：
> - v1.0 将 SUBGRAPH 子图操作独立到单独文档，以保持主 DSL 规范的简洁性
> - v1.0 新增 ASSOCIATION_QUERY 关联查询操作，用于批量多对象及其关联关系的查询场景
> - v1.0 新增 MULTI_OBJECT_QUERY 多对象联合查询操作，支持同表多对象查询和跨对象条件查询（whereFrom）

## 附录 B：快速参考

### B.1 Operation 速查

| Operation | objects 必填 | query 必填 | linkQuery 必填 | associationQuery 必填 | mutation 必填 | 说明 |
|-----------|-------------|------------|----------------|-----------------------|---------------|------|
| QUERY | objectType | 是 | 否 | 否 | 否 | 对象查询 |
| **MULTI_OBJECT_QUERY** | **是（多 objectType）** | 是 | 否 | 否 | 否 | **多对象联合查询** |
| AGGREGATE | objectType | 是（filter） | 否 | 否 | 否 | 聚合计算 |
| LIST_LINKS | objectType, by | 否 | relationships | 否 | 否 | 关联列表查询 |
| GET_LINKED_OBJECT | objectType, by | 否 | relationships, linkedObjectKey | 否 | 否 | 关联对象查询 |
| **ASSOCIATION_QUERY** | objectType | 否 | 否 | **是** | 否 | **多对象关联查询** |
| CREATE | objectType | 否 | 否 | 否 | 是（data/batch） | 创建对象 |
| UPDATE | objectType | 否 | 否 | 否 | 是 | 更新对象 |
| DELETE | objectType | 否 |否 | 否 | 是 | 删除对象 |
| UPSERT | objectType | 否 | 否 | 否 | 是 | 插入或更新 |
| BATCH | 否 | 否 | 否 | 否 | 否（用 mutations） | 批量操作 |
| **SUBGRAPH** | 否 | 否 | 否 | 否 | 否（用 subgraph） | **子图操作（见 v1.0 文档）** |

> **ASSOCIATION_QUERY 操作说明**：v1.0 新增，v1.0 增强，支持多 `objects` + 多 `relationships` 查询，支持 bizRelType/structRelType 等本体模型字段，支持 returns 配置指定对象/关系字段用于 GQL 拼装，详见第 10 章。
> **SUBGRAPH 操作详情**：请参阅《本体对象操作语言(OQL)-子图DSL规范v1.2.md》，包含 objects、links、deletes 的批量操作设计。

### B.2 Filter 操作符速查

| 类别 | 操作符 |
|------|--------|
| 比较 | eq, neq, gt, gte, lt, lte, in, notIn, between |
| 字符串 | contains, startsWith, endsWith, like, isNull, exists |
| 逻辑 | and, or, not |

### B.3 Link Query 操作速查

| Operation | linkQuery 必填字段 | linkQuery 可选字段 |
|-----------|-------------------|-------------------|
| LIST_LINKS | relationships | select, filter, orderBy, pagination, direction |
| GET_LINKED_OBJECT | relationships, linkedObjectKey | select, concurrency |

### B.4 Mutation 操作速查

| Operation | 关键字段 |
|-----------|----------|
| CREATE | data.by, data.properties, batch[] |
| UPDATE | by, filter, set, unset, increment, arrayOps |
| DELETE | by, filter, deleteMode, cascade |
| UPSERT | by, matchOn, onCreate, onUpdate |

### B.5 API 对应关系

| Operation | DSL | REST API |
|-----------|-----|----------|
| QUERY | QUERY | POST /objects/list/{objectType} |
| QUERY | QUERY | POST /objects/query/{objectType}/{by} |
| AGGREGATE | AGGREGATE | POST /objects/aggregate/{objectType} |
| LIST_LINKS | LIST_LINKS | POST /objects/list/links/{objectType}/{by}/{linkType} |
| GET_LINKED_OBJECT | GET_LINKED_OBJECT | POST /objects/query/links/{objectType}/{by}/{linkType}/{linkedObjectKey} |
| **ASSOCIATION_QUERY** | **ASSOCIATION_QUERY** | **POST /objects/association/query** |
| CREATE | CREATE | POST /objects/create/{objectType} |
| UPDATE | UPDATE | POST /objects/update/{objectType} |
| DELETE | DELETE | POST /objects/delete/{objectType} |
| UPSERT | UPSERT | POST /objects/upsert/{objectType} |
| BATCH | BATCH | POST /objects/batch |
| **SUBGRAPH** | **SUBGRAPH** | **POST /objects/subgraph** |

> **ASSOCIATION_QUERY API**：详见第 10 章关联查询（ASSOCIATION_QUERY）规范。
> **SUBGRAPH API**：请参阅《本体对象操作语言(OQL)-子图DSL规范v1.2.md》了解详情。

---

## 附录 C：语法关键字详解

> **说明**：OQL v1.0 采用"顶层通用字段 + 操作专用块"结构设计，详见 [第2章统一顶层结构](#2-统一顶层结构)。本附录按关键字分类详细说明。

### C.1 顶层关键字（Top-Level Keywords）

#### C.1.1 核心字段

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| **version** | string | 是 | DSL 版本号，当前为 `1.0` |
| **operation** | string | 是 | 操作类型（QUERY / MULTI_OBJECT_QUERY / AGGREGATE / ASSOCIATION_QUERY / LIST_LINKED_OBJECTS / GET_LINKED_OBJECT / CREATE / UPDATE / DELETE / UPSERT / BATCH） |

#### C.1.2 统一对象定位（objects）

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| **objects** | array | 是 | 对象实例数组，定义查询的目标对象 |
| **objects[].objectType** | string | 是 | 对象类型标识符 |
| **objects[].alias** | string | 否 | 对象别名，用于后续引用 |
| **objects[].by** | object | 否 | 单主键定位，如 `{"id": "prod_001"}` |
| **objects[].byList** | array | 否 | 批量主键列表，如 `[{"id": "a"}, {"id": "b"}]` |
| **objects[].byComposite** | object | 否 | 复合主键，如 `{"sourceSystem": "ERP", "orderNo": "ORD"}` |
| **objects[].conditions** | object | 否 | 对象级别的过滤条件（历史语法，推荐使用顶层 conditions） |

#### C.1.3 统一条件与返回

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|:----:|------|
| **conditions** | object | 否 | 统一的条件表达式（二叉树结构） |
| **conditions.relation** | string | 否 | 逻辑关系：AND / OR |
| **conditions.children** | array | 否 | 条件子节点列表 |
| **returns** | array | 否 | 返回字段定义列表 |
| **orders** | array | 否 | 排序定义列表 |
| **maxResults** | integer | 否 | 最大返回数量，默认 100000 |
| **options** | object | 否 | 执行选项配置 |
| **extensions** | object | 否 | 业务自定义扩展机制 |

#### C.1.4 操作专用块速查

| 专用块 | 对应 operation | 说明 |
|--------|---------------|------|
| `query` | QUERY / MULTI_OBJECT_QUERY | 查询条件定义 |
| `aggregations` | AGGREGATE | 聚合计算定义 |
| `associationQuery` | ASSOCIATION_QUERY | 关联查询定义 |
| `linkQuery` | LIST_LINKED_OBJECTS / GET_LINKED_OBJECT | LinkType 查询定义 |
| `mutation` | CREATE / UPDATE / DELETE / UPSERT | 数据变更定义 |
| `mutations` | BATCH | 批量操作定义 |

---

### C.2 查询关键字（Query Keywords）

`query` 节点用于定义查询条件，支持以下子关键字：

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| **select** | object | 否 | 字段投影配置，定义返回哪些字段 |
| **select.fields** | array | 否 | 要返回的字段列表，如 `["id", "name", "price"]` |
| **select.computed** | array | 否 | 计算字段定义 |
| **select.exclude** | array | 否 | 要排除的字段列表 |
| **select.nested** | array | 否 | 嵌套对象字段投影 |
| **filter** | object | 否 | 过滤条件，支持逻辑组合 |
| **filter.and** | array | 否 | AND 逻辑组合 |
| **filter.or** | array | 否 | OR 逻辑组合 |
| **filter.not** | object | 否 | NOT 逻辑取反 |
| **orderBy** | array | 否 | 排序配置数组 |
| **orderBy.field** | string | 是（排序时） | 排序字段 |
| **orderBy.direction** | string | 是（排序时） | 排序方向：`ASC` 或 `DESC` |
| **orderBy.nullsFirst** | boolean | 否 | null 值是否排在前面 |
| **maxResults** | integer | 否 | 最大返回数量，默认 100000，最大 100000 |
| **includeTotal** | boolean | 否 | 是否返回总记录数 |
| **timeRange** | object | 否 | 时间范围过滤 |
| **timeRange.field** | string | 是 | 时间字段名 |
| **timeRange.from** | string | 否 | 开始时间（ISO 8601 格式） |
| **timeRange.to** | string | 否 | 结束时间（ISO 8601 格式） |
| **whereFrom** | object | 否 | 跨对象条件查询定义，MULTI_OBJECT_QUERY 操作使用 |
| **whereFrom.from** | string | 是（当 whereFrom 存在时） | 来源对象属性引用（格式：alias.field 或 objectType.field） |
| **whereFrom.to** | string | 是（当 whereFrom 存在时） | 目标对象过滤字段 |
| **whereFrom.operator** | string | 否 | 比较操作符，默认 eq，支持 eq/in/between 等 |

#### C.2.1 Filter 操作符

| 操作符 | 类型 | 适用类型 | 说明 |
|--------|------|----------|------|
| **eq** | object | 所有 | 等于，精确匹配 |
| **neq** | object | 所有 | 不等于 |
| **gt** | object | 数值/日期 | 大于 |
| **gte** | object | 数值/日期 | 大于或等于 |
| **lt** | object | 数值/日期 | 小于 |
| **lte** | object | 数值/日期 | 小于或等于 |
| **in** | object | 所有 | 在列表中 |
| **notIn** | object | 所有 | 不在列表中 |
| **between** | object | 数值/日期 | 区间范围 |
| **contains** | object | 字符串 | 包含子串 |
| **startsWith** | object | 字符串 | 前缀匹配 |
| **endsWith** | object | 字符串 | 后缀匹配 |
| **like** | object | 字符串 | LIKE 模式匹配 |
| **isNull** | object | 所有 | 是否为空 |
| **exists** | object | 所有 | 值是否存在 |

#### C.2.2 Computed Field（计算字段）

```json
{
  "select": {
    "computed": [
      {
        "alias": "discountedPrice",
        "expression": {
          "op": "multiply",
          "params": [
            {"field": "price"},
            {"op": "sub", "params": [{"value": 1}, {"field": "discountRate"}]}
          ]
        }
      }
    ]
  }
}
```

| 关键字 | 类型 | 说明 |
|--------|------|------|
| **alias** | string | 计算字段别名 |
| **expression** | object | 表达式定义 |
| **expression.op** | string | 操作符：add / sub / multiply / divide / mod / concat / upper / lower |
| **expression.params** | array | 参数列表，可包含 `field`（引用字段）或 `value`（字面值） |

---

### C.3 关联查询关键字（LinkQuery Keywords）

`linkQuery` 节点用于定义关联查询条件：

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| **relationships** | string | 是 | 关联类型标识符，如 `items`、`orders`、`owned` 等 |
| **linkedObjectKey** | string | GET_LINKED_OBJECT 必填 | 关联对象主键 |
| **select** | object | 否 | 字段投影配置 |
| **select.fields** | array | 否 | 要返回的关联对象字段 |
| **select.includeLinkProperties** | boolean | 否 | 是否包含关联属性，默认 false |
| **select.includeLinkType** | boolean | 否 | 是否包含关联类型信息，默认 false |
| **filter** | object | 否 | 过滤条件（对关联对象或其属性过滤） |
| **orderBy** | array | 否 | 排序配置 |
| **maxResults** | integer | 否 | 最大返回数量，默认 100000，最大 100000 |
| **direction** | string | 否 | 查询方向：`forward`（默认，正向）或 `reverse`（反向） |
| **concurrency** | object | 否 | 并发控制配置 |

---

### C.4 写入操作关键字（Mutation Keywords）

`mutation` 节点用于定义数据变更操作：

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| **data** | object | CREATE 必填 | 单对象创建数据 |
| **data.by** | object | 否 | 对象主键（KV 结构），若不指定则自动生成 |
| **data.properties** | object | 是 | 对象属性键值对 |
| **batch** | array | 否 | 批量操作数据数组 |
| **by** | object | UPDATE/DELETE/UPSERT 条件必填 | 指定操作对象的主键（KV 结构） |
| **filter** | object | UPDATE/DELETE 条件可选 | 过滤条件 |
| **set** | object | UPDATE 必填 | 要设置的属性 |
| **unset** | array | 否 | 要移除的字段列表 |
| **increment** | object | 否 | 数值字段递增/递减 |
| **arrayOps** | object | 否 | 数组操作（$push、$pop、$pull 等） |
| **deleteMode** | string | DELETE 可选 | 删除模式：`soft`（软删除，默认）或 `hard`（硬删除） |
| **cascade** | boolean | DELETE 可选 | 是否级联删除关联对象 |
| **matchOn** | array | UPSERT 可选 | 匹配字段列表 |
| **onCreate** | object | UPSERT 可选 | 不存在时创建的属性 |
| **onUpdate** | object | UPSERT 可选 | 存在时更新的属性 |

#### C.4.1 Array Operations（数组操作）

| 操作符 | 说明 | 示例 |
|--------|------|------|
| **$push** | 追加元素到数组 | `{"$push": ["item1", "item2"]}` |
| **$pushAll** | 批量追加 | `{"$pushAll": ["a", "b", "c"]}` |
| **$pop** | 移除末尾元素 | `{"$pop": 1}` |
| **$shift** | 移除开头元素 | `{"$shift": -1}` |
| **$pull** | 移除匹配元素 | `{"$pull": {"status": "expired"}}` |
| **$addToSet** | 添加去重 | `{"$addToSet": "newItem"}` |
| **$pullAll** | 批量移除 | `{"$pullAll": ["a", "b"]}` |

#### C.4.2 Expression Operators（表达式操作符）

| 类别 | 操作符 | 说明 | 示例 |
|------|--------|------|------|
| 算术 | add | 加法 | `{"add": ["$field", 10]}` |
| 算术 | sub | 减法 | `{"sub": ["$field", 5]}` |
| 算术 | multiply | 乘法 | `{"multiply": ["$field", 0.9]}` |
| 算术 | divide | 除法 | `{"divide": ["$field", 2]}` |
| 算术 | mod | 取模 | `{"mod": ["$field", 100]}` |
| 递增 | inc | 递增 | `{"inc": 1}` |
| 递减 | dec | 递减 | `{"dec": 1}` |
| 字符串 | concat | 拼接 | `{"concat": ["$field", "_v2"]}` |
| 字符串 | upper | 转大写 | `{"upper": "$field"}` |
| 字符串 | lower | 转小写 | `{"lower": "$field"}` |
| 字符串 | length | 获取长度 | `{"length": "$field"}` |
| 条件 | case | 条件分支 | 见下方示例 |

#### C.4.3 Case Expression（条件分支）

```json
{
  "set": {
    "level": {
      "$case": [
        {"when": {"gte": {"totalAmount": 1000}}, "then": {"level": "vip", "discountRate": 0.15}},
        {"when": {"gte": {"totalAmount": 500}}, "then": {"level": "silver", "discountRate": 0.05}},
        {"else": {"level": "normal", "discountRate": 0}}
      ]
    }
  }
}
```

---

### C.5 关联操作关键字（Link Keywords）

`links` 节点用于定义关联（Link）操作：

#### C.5.1 Link Operation Keywords

| 关键字 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| **create** | array | CREATE Link 必填 | 创建关联列表 |
| **create.relationships** | string | 是 | 关联类型标识符 |
| **create.from** | string | 是 | 源对象主键（发起关联方） |
| **create.to** | string | 是 | 目标对象主键（被关联方） |
| **create.properties** | object | 否 | 关联属性，如数量、价格等 |
| **update** | array | UPDATE Link 必填 | 更新关联列表 |
| **update.relationships** | string | 是 | 关联类型标识符 |
| **update.from** | string | 是 | 源对象主键 |
| **update.to** | string | 是 | 目标对象主键 |
| **update.set** | object | 是 | 要更新的关联属性 |
| **delete** | array | DELETE Link 必填 | 删除关联列表 |
| **delete.relationships** | string | 是 | 关联类型标识符 |
| **delete.from** | string | 是 | 源对象主键 |
| **delete.to** | string | 是 | 目标对象主键 |

---

### C.6 执行选项关键字（Options Keywords）

`options` 节点用于控制执行行为：

| 关键字 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| **transaction** | boolean | false | 是否启用事务 |
| **timeoutMs** | integer | 30000 | 超时时间（毫秒） |
| **isolationLevel** | string | READ_COMMITTED | 事务隔离级别 |
| **consistency** | string | eventual | 一致性级别 |
| **returnAffectedCount** | boolean | true | 是否返回影响数量 |
| **returnData** | boolean | false | 是否返回数据 |
| **returnBeforeState** | boolean | false | 是否返回更新前状态 |
| **continueOnFailure** | boolean | false | 失败时是否继续 |
| **validationMode** | string | strict | 验证模式：`strict`（严格）或 `relaxed`（宽松） |

#### C.6.1 Isolation Levels（隔离级别）

| 隔离级别 | 说明 |
|----------|------|
| READ_UNCOMMITTED | 读未提交，可能读到未提交数据 |
| READ_COMMITTED | 读已提交（默认） |
| REPEATABLE_READ | 可重复读 |
| SERIALIZABLE | 串行化，最高隔离级别 |

#### C.6.2 Concurrency Control（并发控制）

```json
{
  "options": {
    "concurrency": {
      "ifMatch": "\"etag-abc123\"",
      "ifUnmodifiedSince": "2024-03-01T12:00:00Z",
      "forceUpdate": false
    }
  }
}
```

| 关键字 | 类型 | 说明 |
|--------|------|------|
| **ifMatch** | string | ETag 条件，匹配才执行 |
| **ifUnmodifiedSince** | string | 时间戳条件，未修改才执行 |
| **forceUpdate** | boolean | 强制更新，跳过并发检查 |

---

### C.7 内置函数（Built-in Functions）

| 函数 | 说明 | 返回值类型 | 示例 |
|------|------|-----------|------|
| **$now()** | 当前时间戳 | datetime | `"createdAt": "$now()"` |
| **$uuid()** | 生成 UUID | string | `"id": "$uuid()"` |
| **$random(min, max)** | 生成随机数 | number | `"code": "$random(1000, 9999)"` |
| **$currentUser()** | 当前用户 ID | string | `"createdBy": "$currentUser()"` |
| **$currentTenant()** | 当前租户 ID | string | `"tenantId": "$currentTenant()"` |

---

### C.8 扩展机制关键字（Extensions Keywords）

`extensions` 节点用于业务自定义扩展：

```json
{
  "extensions": {
    "customField": "value",
    "businessRule": {
      "applyDiscount": true,
      "discountRate": 0.1
    },
    "audit": {
      "logLevel": "detailed"
    }
  }
}
```

| 关键字 | 类型 | 说明 |
|--------|------|------|
| **自定义键** | any | 业务可根据需要定义任意扩展字段 |
| 保留前缀 | - | 建议使用业务模块名作为前缀避免冲突 |

---

### C.9 关键字速查表

#### 按功能分类

| 功能 | 关键字 |
|------|--------|
| **版本控制** | version |
| **操作定义** | operation |
| **目标对象** | target, objectType, by |
| **查询条件** | query, select, filter, orderBy, pagination |
| **关联查询** | linkQuery, relationships, linkedObjectKey, direction |
| **数据变更** | mutation, data, properties, batch, set, unset, increment |
| **关联操作** | links, create, update, delete, relationships, from, to, properties |
| **执行控制** | options, transaction, timeoutMs, isolationLevel |
| **并发控制** | concurrency, ifMatch, ifUnmodifiedSince, forceUpdate |
| **过滤操作符** | eq, neq, gt, gte, lt, lte, in, notIn, between |
| **字符串操作符** | contains, startsWith, endsWith, like, isNull, exists |
| **逻辑操作符** | and, or, not |
| **表达式操作符** | add, sub, multiply, divide, inc, case |
| **数组操作** | $push, $pop, $pull, $addToSet |
| **内置函数** | $now(), $uuid(), $random(), $currentUser() |
| **扩展机制** | extensions |
| **引擎自动生成** | requestId（由引擎自动生成，不对用户暴露） |

#### 按必填性分类

| 必填 | 关键字 |
|------|--------|
| **顶层必填** | version, operation, objects[].objectType |
| **查询必填** | query（QUERY/AGGREGATE），linkQuery（LIST_LINKS/GET_LINKED_OBJECT） |
| **写入必填** | mutation（CREATE/UPDATE/DELETE/UPSERT） |
| **关联必填** | links（CREATE/UPDATE/DELETE Link） |

---

### C.10 关键字冲突注意事项

1. **保留关键字**：以下关键字为 DSL 保留，业务属性应避免使用：
    - `version`, `operation`, `target`, `query`, `linkQuery`, `mutation`, `links`, `options`, `extensions`, `mutations`
    - `objectType`, `by`, `properties`, `filter`, `select`, `orderBy`, `pagination`
    - 所有 Filter 操作符（eq, neq, gt 等）
    - 所有表达式操作符（add, sub, multiply 等）
    - 注意：`requestId` 由引擎自动生成，不属于用户可用的关键字

2. **命名规范**：
    - 建议使用 camelCase 命名法（如 `orderNo`, `createdAt`）
    - 对象属性名避免与 DSL 关键字冲突
    - 如必须使用冲突名称，请使用转义或咨询架构团队

3. **大小写敏感**：
    - 关键字大小写不敏感（eq 等价于 EQ / Eq）
    - 对象属性名大小写敏感（建议统一命名风格）
