# 本体对象操作语言（OQL）DSL 规范（优化版）

> 目标：面向 LLM/Agent 的高一致性 DSL 规范。OQL 只描述“做什么”，由翻译引擎映射为 SQL、nGQL 或其他物理执行语句。

## 1. 规范目标与边界

### 1.1 设计目标

- **统一结构**：查询、聚合、写入共享同一顶层骨架。
- **对象优先**：围绕本体对象与关系建模，不暴露底层表结构细节。
- **AI 友好**：字段语义稳定、低歧义、低冗余，便于生成与校验。
- **可扩展**：保留 `options`、`extensions` 作为平台扩展入口。
- **多源透明**：属性可映射到不同数据源，调用方只面向统一对象视图。

### 1.2 执行边界

- OQL 是**逻辑 DSL**，不是物理方言；不直接承诺 SQL/nGQL 细节。
- 跨源 JOIN、过滤下推、聚合下推由翻译引擎决定并优化。
- 建议默认幂等重试能力，写操作可结合事务策略执行。

## 2. 多数据源属性映射模型

对象属性允许独立映射到不同物理源。例如 `Order`：

- `orderNo` → MySQL
- `customerId` → GaussDB
- `amount/status` → PostgreSQL
- `metadata` → ElasticSearch
- `createdAt` → Carbon

翻译引擎职责：

1. 将 DSL 属性引用映射到物理字段。
2. 在可能情况下做过滤/聚合下推。
3. 需要时执行跨源拼接与结果整形，返回统一 JSON。

## 3. 统一 DSL 顶层结构

### 3.1 通用骨架

```json
{
  "version": "1.8.0",
  "operation": "QUERY | MULTI_OBJECT_QUERY | AGGREGATE | ASSOCIATION_QUERY | LIST_LINKED_OBJECTS | GET_LINKED_OBJECT | CREATE | UPDATE | DELETE | UPSERT | BATCH",
  "objects": [],
  "relationships": [],
  "conditions": {},
  "returns": [],
  "orders": [],
  "maxResults": 100000,

  "query": {},
  "aggregations": {},
  "associationQuery": {},
  "linkQuery": {},
  "mutation": {},

  "sourceQuery": [],
  "options": {},
  "extensions": {}
}
```

### 3.2 顶层字段定义

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `version` | string | 是 | DSL 版本，当前建议 `1.8.0` |
| `operation` | enum | 是 | 操作类型 |
| `objects` | array | 多数操作必填 | 目标对象与定位信息 |
| `relationships` | array | 关系类操作必填 | 关系类型定义 |
| `conditions` | object | 否 | 统一条件树 |
| `returns` | array | 查询类建议必填 | 返回字段投影 |
| `orders` | array | 否 | 排序定义 |
| `maxResults` | integer | 否 | 返回上限，默认/最大 100000 |
| `query`/`aggregations`/`associationQuery`/`linkQuery`/`mutation` | object | 按操作激活 | 操作专用块 |
| `sourceQuery` | array | 否 | 嵌套查询数据源 |
| `options` | object | 否 | 执行选项 |
| `extensions` | object | 否 | 业务扩展 |

### 3.3 操作与专用块激活矩阵（新增）

> 目的：减少 LLM/Agent 生成“字段存在但无效”的 DSL。

| operation | 必须字段 | 可选字段 | 必须激活专用块 |
|---|---|---|---|
| `QUERY` | `objects` | `conditions` `returns` `orders` `maxResults` `sourceQuery` | 无（`query`可选） |
| `MULTI_OBJECT_QUERY` | `objects` | `conditions` `returns` `orders` `maxResults` `sourceQuery` | 推荐 `query.whereFrom` |
| `AGGREGATE` | `objects` `returns` | `conditions` `sourceQuery` | `aggregations` 或 `returns.function` |
| `ASSOCIATION_QUERY` | `objects` `relationships` | `conditions` `returns` `orders` `maxResults` | `associationQuery` |
| `LIST_LINKED_OBJECTS` | `objects` `relationships` | `conditions` `returns` | `linkQuery`（可选） |
| `GET_LINKED_OBJECT` | `objects` `relationships` | `conditions` `returns` | `linkQuery.linkedObjectKey` |
| `CREATE` | `objects` | - | `mutation.data` |
| `UPDATE` | `objects` | `conditions` | `mutation.set` |
| `DELETE` | `objects` | `conditions` | `mutation` |
| `UPSERT` | `objects` | - | `mutation.set` + `mutation.createIfNotExists` |
| `BATCH` | - | `options` | `mutation.actions` |

### 3.4 objects（对象定位）

`objects[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `objectType` | string | 是 | 对象类型 |
| `alias` | string | 否 | 引用别名 |
| `by` | object | 否 | 单主键定位 |
| `byList` | array | 否 | 批量主键定位 |
| `byComposite` | object | 否 | 复合主键定位 |

示例（复合主键）：

```json
{
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "byComposite": {"sourceSystem": "ERP", "orderNo": "ORD-20240301-001"}
    }
  ]
}
```

### 3.5 conditions（统一条件树）

```json
{
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["active"]},
      {
        "relation": "OR",
        "children": [
          {"objectType": "Device", "property": "amount", "operator": "GTE", "values": [1000]},
          {"objectType": "Device", "property": "priority", "operator": "EQ", "values": ["P1"]}
        ]
      }
    ]
  }
}
```

规则：

- `conditions` 与 `objects[].by/byList/byComposite` 可组合；若冲突以校验器策略为准。
- 叶子节点使用 `objectType + property + operator + values`。

常用 `operator`（建议最小集合）：

- 比较：`EQ` `NEQ` `GT` `GTE` `LT` `LTE`
- 集合：`IN` `NOT_IN`
- 字符串：`CONTAINS` `STARTS_WITH` `ENDS_WITH`
- 空值：`IS_NULL` `IS_NOT_NULL`

### 3.6 returns 与 orders

```json
{
  "returns": [
    {"type": "object", "param": "o", "fields": ["id", "orderNo", "amount"]},
    {"type": "relationship", "param": "r", "fields": ["bizRelType"]}
  ],
  "orders": [
    {"param": "o", "property": "createdAt", "descending": true}
  ]
}
```

### 3.7 sourceQuery（嵌套查询）

- `sourceQuery[]` 与顶层结构同构，可递归嵌套。
- `sourceQuery[].outputAs` 必填，供外层引用。
- 适用于“先过滤/聚合，再作为外层数据源”的场景。
- 当启用 `sourceQuery` 时，建议避免与主查询 `objects[].by*` 同时表达相同语义，以免冲突。

关键示例（两层）：

```json
{
  "operation": "QUERY",
  "objects": [{"objectType": "FinalReport", "alias": "f"}],
  "sourceQuery": [
    {
      "outputAs": "order_sub",
      "operation": "QUERY",
      "objects": [{"objectType": "Order", "alias": "o"}],
      "conditions": {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
      "returns": [{"type": "object", "param": "o", "fields": ["id", "amount", "customerId"]}]
    }
  ],
  "returns": [{"type": "object", "param": "f", "fields": ["*"]}]
}
```

## 4. Operation 类型说明与差异化示例

### 4.1 QUERY（单对象/列表查询）

用途：单对象类型查询、列表检索、按条件过滤。

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
  "returns": [{"type": "object", "param": "o", "fields": ["id", "orderNo", "amount"]}],
  "orders": [{"param": "o", "property": "createdAt", "descending": true}],
  "maxResults": 10000
}
```

### 4.2 MULTI_OBJECT_QUERY（多对象联合查询）

用途：同表多对象、跨对象字段约束、跨对象关联过滤。

差异点：通过 `query.whereFrom` 指定跨对象字段映射。

```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "User", "alias": "u", "by": {"id": "user_001"}},
    {"objectType": "Community", "alias": "c"}
  ],
  "query": {
    "whereFrom": {"from": "u.id", "to": "c.ownerId", "operator": "eq"}
  },
  "returns": [{"type": "object", "param": "c", "fields": ["id", "name", "address"]}]
}
```

补充：`query.whereFrom` 字段建议

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `from` | string | 是 | 来源字段，格式 `alias.property` |
| `to` | string | 是 | 目标字段，格式 `alias.property` |
| `operator` | string | 否 | 连接比较操作，默认 `eq` |
| `joinType` | string | 否 | `INNER`/`LEFT`/`RIGHT`（默认 `INNER`） |

### 4.3 AGGREGATE（聚合）

用途：分组统计、指标计算。

```json
{
  "version": "1.8.0",
  "operation": "AGGREGATE",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
  "returns": [
    {"type": "object", "param": "o", "fields": ["region"], "function": "groupBy"},
    {"type": "object", "param": "o", "field": "amount", "function": "sum", "alias": "totalAmount"}
  ]
}
```

### 4.4 ASSOCIATION_QUERY（关系遍历查询）

用途：图关系多跳遍历、关系属性过滤。

```json
{
  "version": "1.8.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [{"objectType": "Device", "alias": "d", "by": {"id": "dev-001"}}],
  "relationships": [
    {
      "name": "connectedTo",
      "alias": "r",
      "sourceObjectType": "Device",
      "targetObjectType": "Device",
      "bizRelType": "connectedTo"
    }
  ],
  "associationQuery": {"action": "go", "maxDepth": 2},
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name"]},
    {"type": "relationship", "param": "r", "fields": ["bizRelType"]}
  ]
}
```

### 4.5 LIST_LINKED_OBJECTS（列出关联对象）

用途：按 LinkType 获取某对象的全部关联对象。

```json
{
  "version": "1.8.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [{"objectType": "Application", "alias": "a", "by": {"id": "app-001"}}],
  "relationships": [{"name": "deployedOn", "sourceObjectType": "Application", "targetObjectType": "Server"}],
  "returns": [{"type": "object", "param": "a", "fields": ["id"]}]
}
```

### 4.6 GET_LINKED_OBJECT（获取特定关联对象）

用途：按 LinkType + 目标 key 获取单个/特定关联对象。

```json
{
  "version": "1.8.0",
  "operation": "GET_LINKED_OBJECT",
  "objects": [{"objectType": "Application", "alias": "a", "by": {"id": "app-001"}}],
  "relationships": [{"name": "owner", "sourceObjectType": "Application", "targetObjectType": "User"}],
  "linkQuery": {"linkedObjectKey": {"id": "user-001"}},
  "returns": [{"type": "object", "param": "a", "fields": ["id", "name"]}]
}
```

### 4.7 CREATE（创建）

```json
{
  "version": "1.8.0",
  "operation": "CREATE",
  "objects": [{"objectType": "Product", "alias": "p"}],
  "mutation": {
    "data": {"properties": {"name": "iPhone 16", "price": 8999}}
  }
}
```

### 4.8 UPDATE（更新）

```json
{
  "version": "1.8.0",
  "operation": "UPDATE",
  "objects": [{"objectType": "Product", "alias": "p", "by": {"id": "prod_001"}}],
  "mutation": {"set": {"price": 7999, "updatedAt": "$now()"}}
}
```

### 4.9 DELETE（删除）

```json
{
  "version": "1.8.0",
  "operation": "DELETE",
  "objects": [{"objectType": "Order", "alias": "o", "byComposite": {"sourceSystem": "ERP", "orderNo": "ORD-001"}}],
  "mutation": {}
}
```

### 4.10 UPSERT（存在则更新，不存在则创建）

```json
{
  "version": "1.8.0",
  "operation": "UPSERT",
  "objects": [{"objectType": "Inventory", "alias": "i", "by": {"sku": "SKU-001"}}],
  "mutation": {
    "set": {"stock": 120},
    "createIfNotExists": {"properties": {"sku": "SKU-001", "stock": 120}}
  }
}
```

### 4.11 BATCH（批量复合操作）

用途：将多个写操作组合执行，可携带事务语义。

```json
{
  "version": "1.8.0",
  "operation": "BATCH",
  "mutation": {
    "transaction": true,
    "actions": [
      {
        "operation": "CREATE",
        "objects": [{"objectType": "Order", "alias": "o"}],
        "mutation": {"data": {"properties": {"id": "ord-001", "amount": 1200}}}
      },
      {
        "operation": "UPDATE",
        "objects": [{"objectType": "Inventory", "alias": "i", "by": {"sku": "SKU-001"}}],
        "mutation": {"set": {"stock": 119}}
      }
    ]
  }
}
```

## 5. 操作类型速查

| operation | 说明 | 典型专用块 |
|---|---|---|
| `QUERY` | 单对象/列表查询 | `query`（可选） |
| `MULTI_OBJECT_QUERY` | 多对象联合查询 | `query.whereFrom` |
| `AGGREGATE` | 聚合统计 | `aggregations` 或 `returns.function` |
| `ASSOCIATION_QUERY` | 图关系遍历 | `associationQuery` + `relationships` |
| `LIST_LINKED_OBJECTS` | 列出关联对象 | `linkQuery`（可选） |
| `GET_LINKED_OBJECT` | 获取特定关联对象 | `linkQuery.linkedObjectKey` |
| `CREATE` | 创建 | `mutation.data` |
| `UPDATE` | 更新 | `mutation.set` |
| `DELETE` | 删除 | `mutation` |
| `UPSERT` | 插入或更新 | `mutation.set/createIfNotExists` |
| `BATCH` | 批处理 | `mutation.actions` |

## 6. OQL → 物理执行映射（关键规则）

### 6.1 SQL 类引擎（MySQL/PostgreSQL/GaussDB）

- `QUERY + conditions` → `SELECT ... FROM ... WHERE ...`
- `MULTI_OBJECT_QUERY + whereFrom` → `JOIN + WHERE`
- `AGGREGATE` → `GROUP BY + 聚合函数`
- `orders` → `ORDER BY`
- `maxResults` → `LIMIT`

### 6.2 图引擎（nGQL 等）

- `ASSOCIATION_QUERY` → 图遍历（GO/MATCH）语义
- `relationships` 映射边类型
- `associationQuery.maxDepth` 映射 hop 限制

### 6.3 搜索/日志引擎（ElasticSearch/ClickHouse）

- `conditions` 映射 `must/should/filter` 或等价过滤表达式
- 聚合条件优先下推，失败时回退到上层汇总

## 7. 响应模型（统一建议）

```json
{
  "success": true,
  "data": [
    {
      "objectType": "Order",
      "rid": "ri.xxx",
      "properties": {"id": "order-001", "amount": 19999.0}
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

说明：

- `maxResults` 超限时建议返回 `metadata.truncated=true`。
- `rid` 为全局唯一对象资源标识（如平台支持）。

失败响应建议：

```json
{
  "success": false,
  "error": {
    "code": "OQL_VALIDATION_ERROR",
    "message": "alias 'c' not found in objects",
    "details": {"field": "returns[0].param", "expected": ["u", "o"]}
  },
  "trace": {"requestId": "req-xxx"}
}
```

## 8. 生成与校验建议（面向 LLM/Agent）

1. 始终先确定 `operation`，再补充对应专用块。
2. `objects[].alias` 应在 `returns/orders/query.whereFrom` 中保持一致引用。
3. 多对象场景优先显式写 `query.whereFrom`，减少隐式推断。
4. 仅保留必要字段，避免同时给出互斥或冲突配置。
5. 通过 schema 校验器执行：必填检查、类型检查、引用一致性检查。
6. 先生成“最小可执行 DSL”，再按需补充 `orders`、`options`、`extensions`。
7. 对写操作优先使用 `by/byComposite` 明确定位，避免仅依赖宽泛 `conditions`。

---

**版本说明**：本优化版在保持 11 种操作类型语义与关键示例的前提下，删除重复章节、合并相近示例并统一编号，适合作为后续 Claude Skill 的输入规范。
