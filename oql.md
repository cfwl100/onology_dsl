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
