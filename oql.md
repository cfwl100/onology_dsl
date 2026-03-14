# 本体对象操作语言（OQL）DSL 规范（精简优化版）

> 目标：形成面向 LLM / Agent 的**高一致性、低歧义、可扩展** DSL 规范。OQL 仅描述“做什么”，由翻译引擎映射到 SQL / nGQL / 其他执行语句。

---

## 1. 规范目标与边界

### 1.1 设计目标

1. **统一结构**：查询、聚合、关系查询、写入共享同一顶层骨架。  
2. **对象优先**：围绕本体对象与关系建模，屏蔽底层表/图存储细节。  
3. **AI 友好**：字段命名稳定、语义清晰、冗余最小，便于生成和校验。  
4. **可扩展**：通过 `options` / `extensions` 支持平台能力扩展。  
5. **多源透明**：属性可映射到多个数据源，调用方只面向统一对象视图。

### 1.2 执行边界

1. OQL 是**逻辑 DSL**，不绑定具体 SQL / nGQL 方言。  
2. 跨源 JOIN、过滤下推、聚合下推由翻译引擎决策。  
3. 写操作事务、重试、幂等等执行语义由执行层策略控制。

---

## 2. 多数据源属性映射模型

同一对象属性可分布在不同物理源。

以 `Order` 为例：
- `orderNo` → MySQL
- `customerId` → GaussDB
- `amount/status` → PostgreSQL
- `metadata` → ElasticSearch
- `createdAt` → Carbon

翻译引擎职责：
1. 属性引用 → 物理字段映射。  
2. 可下推场景下执行过滤/聚合下推。  
3. 必要时跨源拼接并返回统一 JSON。

---

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
| `version` | string | 是 | DSL 版本，建议 `1.8.0` |
| `operation` | enum | 是 | 操作类型 |
| `objects` | array | 多数操作必填 | 目标对象及定位信息 |
| `relationships` | array | 关系类操作必填 | 关系定义 |
| `conditions` | object | 否 | 统一条件树 |
| `returns` | array | 查询类建议必填 | 返回字段投影 |
| `orders` | array | 否 | 排序 |
| `maxResults` | integer | 否 | 返回上限，默认/最大 100000 |
| `query` / `aggregations` / `associationQuery` / `linkQuery` / `mutation` | object | 按操作激活 | 操作专用块 |
| `sourceQuery` | array | 否 | 嵌套子查询 |
| `options` | object | 否 | 执行选项 |
| `extensions` | object | 否 | 业务扩展 |

### 3.3 `objects[]`（对象定位）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `objectType` | string | 是 | 对象类型 |
| `alias` | string | 否 | 引用别名 |
| `by` | object | 否 | 单主键定位 |
| `byList` | array | 否 | 批量主键定位 |
| `byComposite` | object | 否 | 复合主键定位 |

差异示例（复合主键）：

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

### 3.4 `conditions`（统一条件树）

```json
{
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["active"]},
      {
        "relation": "OR",
        "children": [
          {"objectType": "Device", "property": "cpuUsage", "operator": "GTE", "values": [80]},
          {"objectType": "Device", "property": "priority", "operator": "EQ", "values": ["P1"]}
        ]
      }
    ]
  }
}
```

规则：
1. 叶子节点统一为 `objectType + property + operator + values`。  
2. `conditions` 可与 `objects[].by/byList/byComposite` 组合；冲突处理由校验器策略决定。  
3. 若需跨对象过滤，优先在 `MULTI_OBJECT_QUERY` 中通过 `query.whereFrom` 显式表达映射。

### 3.5 `returns` 与 `orders`

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

### 3.6 `sourceQuery`（嵌套查询）

1. `sourceQuery[]` 与顶层结构同构，可递归。  
2. `sourceQuery[].outputAs` 必填，供外层引用。  
3. 适用于“先过滤/聚合，再作为外层数据源”的场景。

差异示例（两层查询）：

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

---

## 4. 操作类型总览

| 操作 | 类别 | 典型用途 |
|---|---|---|
| `QUERY` | 查询 | 单对象过滤、列表检索 |
| `MULTI_OBJECT_QUERY` | 查询 | 多对象联合查询、跨对象字段约束 |
| `AGGREGATE` | 查询 | 分组统计、指标聚合 |
| `ASSOCIATION_QUERY` | 查询 | 图关系遍历、多跳查询 |
| `LIST_LINKED_OBJECTS` | 查询 | 列出某对象的关联对象集合 |
| `GET_LINKED_OBJECT` | 查询 | 获取某对象某关系下的唯一关联对象 |
| `CREATE` | 写入 | 新增对象 |
| `UPDATE` | 写入 | 条件更新对象 |
| `DELETE` | 写入 | 条件删除对象 |
| `UPSERT` | 写入 | 存在更新、不存在创建 |
| `BATCH` | 写入 | 多操作顺序执行（可选事务） |

---

## 5. 各操作类型说明与关键差异示例

### 5.1 `QUERY`

**用途**：单对象查询、过滤、排序、分页/限流。

```json
{
  "version": "1.8.0",
  "operation": "QUERY",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
  "returns": [{"type": "object", "param": "o", "fields": ["id", "orderNo", "amount"]}],
  "orders": [{"param": "o", "property": "createdAt", "descending": true}],
  "maxResults": 1000
}
```

### 5.2 `MULTI_OBJECT_QUERY`

**用途**：多对象联合过滤；强调对象间字段关联条件。  
**差异点**：使用 `query.whereFrom` 明确跨对象字段映射。

```json
{
  "version": "1.8.0",
  "operation": "MULTI_OBJECT_QUERY",
  "objects": [
    {"objectType": "Order", "alias": "o"},
    {"objectType": "Customer", "alias": "c"}
  ],
  "query": {
    "whereFrom": [
      {"left": "o.customerId", "operator": "EQ", "right": "c.id"}
    ]
  },
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
      {"objectType": "Customer", "property": "level", "operator": "IN", "values": ["VIP", "SVIP"]}
    ]
  },
  "returns": [
    {"type": "object", "param": "o", "fields": ["id", "orderNo", "amount"]},
    {"type": "object", "param": "c", "fields": ["id", "name", "level"]}
  ]
}
```

### 5.3 `AGGREGATE`

**用途**：计数、求和、均值、分组统计。  
**差异点**：聚合定义在 `aggregations` 中，输出字段建议显式别名。

```json
{
  "version": "1.8.0",
  "operation": "AGGREGATE",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["completed"]},
  "aggregations": {
    "groupBy": [{"param": "o", "property": "customerId"}],
    "metrics": [
      {"func": "COUNT", "param": "o", "property": "id", "as": "orderCount"},
      {"func": "SUM", "param": "o", "property": "amount", "as": "totalAmount"}
    ]
  },
  "returns": [
    {"type": "aggregation", "fields": ["customerId", "orderCount", "totalAmount"]}
  ]
}
```

### 5.4 `ASSOCIATION_QUERY`

**用途**：关系遍历、多跳查询、返回对象+关系属性。  
**差异点**：依赖 `relationships` 与 `associationQuery`。

```json
{
  "version": "1.8.0",
  "operation": "ASSOCIATION_QUERY",
  "objects": [{"objectType": "Device", "alias": "d", "byList": [{"id": "device_001"}, {"id": "device_002"}]}],
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
  "conditions": {"objectType": "Device", "property": "status", "operator": "EQ", "values": ["running"]},
  "returns": [
    {"type": "object", "param": "d", "fields": ["id", "name", "status"]},
    {"type": "relationship", "param": "conn", "fields": ["bizRelType", "structRelType"]}
  ],
  "associationQuery": {
    "action": "go",
    "steps": 2,
    "direction": "BIDIRECT"
  }
}
```

### 5.5 `LIST_LINKED_OBJECTS`

**用途**：列出某对象在指定关系下的关联对象集合。  
**差异点**：强调“列表返回”，通常需要 `linkQuery` 限定关系。

```json
{
  "version": "1.8.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [{"objectType": "Order", "alias": "o", "by": {"id": "order_001"}}],
  "linkQuery": {
    "relationship": "belongsTo",
    "targetObjectType": "Product"
  },
  "returns": [{"type": "object", "param": "target", "fields": ["id", "name", "sku"]}]
}
```

### 5.6 `GET_LINKED_OBJECT`

**用途**：获取某对象某关系下的单一关联对象。  
**差异点**：语义上期望 0/1 结果，通常用于一对一或多对一“主链接”。

```json
{
  "version": "1.8.0",
  "operation": "GET_LINKED_OBJECT",
  "objects": [{"objectType": "Order", "alias": "o", "by": {"id": "order_001"}}],
  "linkQuery": {
    "relationship": "placedBy",
    "targetObjectType": "Customer"
  },
  "returns": [{"type": "object", "param": "target", "fields": ["id", "name", "phone"]}]
}
```

### 5.7 `CREATE`

**用途**：新增对象。  
**差异点**：写入内容在 `mutation.values`。

```json
{
  "version": "1.8.0",
  "operation": "CREATE",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "mutation": {
    "values": {
      "orderNo": "ORD-20260301-001",
      "customerId": "cust_001",
      "amount": 199.9,
      "status": "created"
    }
  },
  "returns": [{"type": "object", "param": "o", "fields": ["id", "orderNo", "status"]}]
}
```

### 5.8 `UPDATE`

**用途**：按定位或条件更新。  
**差异点**：更新字段在 `mutation.set`。

```json
{
  "version": "1.8.0",
  "operation": "UPDATE",
  "objects": [{"objectType": "Order", "alias": "o", "by": {"id": "order_001"}}],
  "mutation": {
    "set": {
      "status": "completed",
      "completedAt": "2026-03-01T10:30:00Z"
    }
  }
}
```

### 5.9 `DELETE`

**用途**：按定位或条件删除对象。  
**差异点**：`mutation` 可为空，关键是 `objects` / `conditions` 定位。

```json
{
  "version": "1.8.0",
  "operation": "DELETE",
  "objects": [{"objectType": "Order", "alias": "o"}],
  "conditions": {
    "relation": "AND",
    "children": [
      {"objectType": "Order", "property": "status", "operator": "EQ", "values": ["cancelled"]},
      {"objectType": "Order", "property": "createdAt", "operator": "LT", "values": ["2025-01-01T00:00:00Z"]}
    ]
  }
}
```

### 5.10 `UPSERT`

**用途**：存在即更新，不存在即创建。  
**差异点**：同时包含匹配键与写入值。

```json
{
  "version": "1.8.0",
  "operation": "UPSERT",
  "objects": [{"objectType": "Inventory", "alias": "i"}],
  "mutation": {
    "matchBy": {"sku": "SKU-001", "warehouseId": "WH-01"},
    "set": {"stock": 128, "updatedAt": "2026-03-01T10:30:00Z"},
    "insert": {"sku": "SKU-001", "warehouseId": "WH-01", "stock": 128}
  }
}
```

### 5.11 `BATCH`

**用途**：多步骤组合执行（如先创建再更新关联对象）。  
**差异点**：通过子操作数组表达顺序和事务策略。

```json
{
  "version": "1.8.0",
  "operation": "BATCH",
  "mutation": {
    "transactional": true,
    "actions": [
      {
        "operation": "CREATE",
        "objects": [{"objectType": "Order", "alias": "o"}],
        "mutation": {"values": {"orderNo": "ORD-20260301-010", "customerId": "cust_010", "amount": 88.8}}
      },
      {
        "operation": "UPDATE",
        "objects": [{"objectType": "Customer", "alias": "c", "by": {"id": "cust_010"}}],
        "mutation": {"set": {"lastOrderNo": "ORD-20260301-010"}}
      }
    ]
  }
}
```

---

## 6. 条件与操作符建议

建议最小通用集合：
- 比较：`EQ` `NE` `GT` `GTE` `LT` `LTE`
- 集合：`IN` `NOT_IN`
- 字符串：`LIKE` `STARTS_WITH` `ENDS_WITH`
- 空值：`IS_NULL` `IS_NOT_NULL`
- 逻辑：`AND` `OR` `NOT`

约束建议：
1. `values` 与 `operator` 匹配（如 `IN` 必须数组）。  
2. 日期/时间统一 ISO-8601 字符串。  
3. 数值类型避免字符串化，降低翻译歧义。

---

## 7. 返回结果与错误语义建议

### 7.1 返回体建议

```json
{
  "success": true,
  "data": [],
  "meta": {
    "operation": "QUERY",
    "maxResults": 1000,
    "truncated": false
  }
}
```

### 7.2 错误建议

```json
{
  "success": false,
  "error": {
    "code": "OQL_VALIDATION_ERROR",
    "message": "invalid operator for property type",
    "details": {
      "path": "conditions.children[1]",
      "operator": "LIKE",
      "property": "amount"
    }
  }
}
```

---

## 8. LLM / Agent 生成约束清单

1. 先确定 `operation`，再填充对应专用块（`query` / `aggregations` / `mutation` 等）。  
2. 所有对象引用统一通过 `alias` + `param` 对齐。  
3. 查询类优先显式 `returns`，避免默认 `*`。  
4. 多对象联合查询必须显式声明对象间约束（优先 `query.whereFrom`）。  
5. 图关系查询必须同时声明 `relationships` 与 `associationQuery`。  
6. 写操作必须最小化字段：仅提交必需字段 + 业务关键字段。  
7. 复杂任务优先拆成 `BATCH` 子步骤，确保可解释性与可回放。

---

## 9. 版本与兼容性

1. 当前推荐版本：`1.8.0`。  
2. 新增字段应保持向后兼容：默认可忽略、不可破坏既有语义。  
3. 破坏性变更通过版本升级体现，并提供迁移映射规则。

