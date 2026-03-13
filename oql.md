# 本体对象操作语言（OQL）DSL 规范（优化版）

> 版本：`1.9.0`  
> 状态：`Draft`（用于统一 LLM/Agent 生成与执行引擎翻译）

---

## 1. 目标与范围

OQL 是面向**本体对象**的声明式 DSL。调用方描述“要什么”，执行引擎负责翻译为 SQL、nGQL 或其他物理操作。

### 1.1 设计目标

- **对象优先**：以 `objectType` 建模，不暴露底层表/边细节。
- **LLM 友好**：固定结构、低歧义、可校验。
- **多源透明**：同一对象属性可映射到不同数据源，调用方无感知。
- **可执行可观测**：支持 trace、错误定位、部分下推统计。

### 1.2 规范性关键词

- **MUST**：必须遵守。
- **SHOULD**：推荐遵守，特殊场景可例外。
- **MAY**：可选。

---

## 2. 顶层结构（统一）

```json
{
  "version": "1.9.0",
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

### 2.1 通用字段定义

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| version | string | 是 | DSL 版本，当前为 `1.9.0` |
| operation | enum | 是 | 操作类型 |
| objects | array | 条件必填 | 查询/变更目标对象 |
| relationships | array | 仅关联类必填 | 关系定义 |
| conditions | object | 否 | 统一条件表达式树 |
| returns | array | 查询类建议必填 | 返回投影 |
| orders | array | 否 | 排序定义 |
| maxResults | integer | 否 | 返回条数上限，默认 100000，最大 100000 |
| sourceQuery | array | 否 | 子查询数据源 |
| options/extensions | object | 否 | 扩展参数 |

### 2.2 operation 与字段激活矩阵

| operation | objects | conditions | returns | relationships | query | aggregations | associationQuery | linkQuery | mutation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| QUERY | 必填（objects 或 sourceQuery 至少其一） | 可选 | 建议 | - | 可选 | - | - | - | - |
| MULTI_OBJECT_QUERY | 必填（objects 或 sourceQuery 至少其一） | 可选 | 建议 | - | 可选（whereFrom） | - | - | - | - |
| AGGREGATE | 必填（objects 或 sourceQuery 至少其一） | 可选 | 必填 | - | - | 可选 | - | - | - |
| ASSOCIATION_QUERY | 必填 | 可选 | 建议 | 必填 | - | - | 必填 | - | - |
| LIST_LINKED_OBJECTS | 必填 | 可选 | 建议 | 必填 | - | - | - | 可选 | - |
| GET_LINKED_OBJECT | 必填 | 可选 | 建议 | 必填 | - | - | - | 必填 | - |
| CREATE/UPDATE/DELETE/UPSERT | 必填 | UPDATE/DELETE 可选 | - | - | - | - | - | - | 必填 |
| BATCH | 可选 | 可选 | - | - | - | - | - | - | 必填 |

> 规则：`objects` 与 `sourceQuery` **可并存**，但含义不同：  
> - `sourceQuery`：定义“数据来源”；  
> - `objects`：定义“语义对象与别名绑定”。  
> 若两者并存，`objects` MUST 至少包含外层返回中用到的 `alias`。

---

## 3. objects（对象定位）

```json
{
  "objectType": "Order",
  "alias": "o",
  "by": {"id": "order_001"},
  "byList": [{"id": "order_001"}, {"id": "order_002"}],
  "byComposite": {"sourceSystem": "ERP", "orderNo": "ORD-001"}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| objectType | string | 对象类型标识，MUST |
| alias | string | 对象别名，SHOULD（建议总是填写） |
| by | object | 单主键定位（仅单键） |
| byList | array<object> | 批量主键定位 |
| byComposite | object | 复合主键定位（仅复合键） |

### 3.1 定位互斥规则

同一个对象项内，`by` / `byList` / `byComposite` MUST 至多出现一个。

### 3.2 与 conditions 的关系

- 当使用 `by/byList/byComposite` 时，`conditions` MAY 继续补充非主键过滤。
- 若两者冲突（例如主键指定 A，conditions 指向 B），应返回 `OQL_VALIDATE_CONFLICT`。

---

## 4. conditions（统一条件表达式）

### 4.1 结构

```json
{
  "relation": "AND",
  "children": [
    {"param": "o", "property": "status", "operator": "EQ", "values": ["completed"]},
    {
      "relation": "OR",
      "children": [
        {"param": "o", "property": "amount", "operator": "GTE", "values": [1000]},
        {"param": "o", "property": "priority", "operator": "EQ", "values": ["P0"]}
      ]
    }
  ]
}
```

### 4.2 叶子节点规范

| 字段 | 必填 | 说明 |
|---|---:|---|
| param | 是 | 对象别名，MUST 对应 `objects[].alias` |
| property | 是 | 属性名 |
| operator | 是 | 操作符 |
| values | 否 | 操作数数组（`IS_NULL`/`IS_NOT_NULL` 可省略） |

> 说明：`conditions` 中统一使用 `param`，不再推荐 `objectType` 作为绑定字段。

### 4.3 操作符

`EQ, NE, GT, GTE, LT, LTE, IN, NOT_IN, CONTAINS, STARTS_WITH, ENDS_WITH, IS_NULL, IS_NOT_NULL`

### 4.4 空值语义

- `EQ null` 不合法，必须使用 `IS_NULL`。
- `NE null` 不合法，必须使用 `IS_NOT_NULL`。

---

## 5. returns / orders / relationships

### 5.1 returns

```json
[
  {"type": "object", "param": "o", "fields": ["id", "orderNo", "amount"]},
  {"type": "relationship", "param": "r", "fields": ["bizRelType"]}
]
```

### 5.2 orders（唯一写法）

```json
[
  {"param": "o", "property": "createdAt", "descending": true}
]
```

> 不再使用 `field/direction` 写法。

### 5.3 relationships（统一 array）

```json
[
  {
    "name": "connectedTo",
    "alias": "r",
    "sourceObjectType": "Device",
    "targetObjectType": "Device",
    "bizRelType": "connectedTo",
    "structRelType": "Association"
  }
]
```

---

## 6. sourceQuery（嵌套查询）

### 6.1 定义

`sourceQuery` 是子查询数组，子查询结果可通过 `outputAs` 供外层引用。

```json
{
  "sourceQuery": [
    {
      "outputAs": "order_sub",
      "operation": "QUERY",
      "objects": [{"objectType": "Order", "alias": "o"}],
      "conditions": {"param": "o", "property": "status", "operator": "EQ", "values": ["completed"]},
      "returns": [{"type": "object", "param": "o", "fields": ["id", "amount"]}]
    }
  ]
}
```

### 6.2 约束

- `sourceQuery[].outputAs` MUST 填写且同层唯一。
- `sourceQuery` MAY 递归嵌套。
- 外层 `returns/conditions/query.whereFrom` 引用子查询字段时，MUST 指向已声明别名。

---

## 7. MULTI_OBJECT_QUERY 专项（whereFrom）

```json
{
  "query": {
    "whereFrom": {
      "from": "u.id",
      "to": "c.ownerId",
      "operator": "eq",
      "joinType": "INNER"
    }
  }
}
```

| 字段 | 必填 | 说明 |
|---|---:|---|
| from | 是 | 来源字段，格式 `alias.property` |
| to | 是 | 目标字段，格式 `alias.property` |
| operator | 否 | 默认 `eq` |
| joinType | 否 | `INNER/LEFT/RIGHT`，默认 `INNER` |

执行语义：`whereFrom` 先形成对象关联，再叠加 `conditions` 过滤。

---

## 8. mutation（写操作）

### 8.1 CREATE

```json
{
  "operation": "CREATE",
  "objects": [{"objectType": "Product", "alias": "p"}],
  "mutation": {
    "data": {
      "properties": {"name": "iPhone 16", "price": 8999}
    }
  }
}
```

### 8.2 UPDATE

```json
{
  "operation": "UPDATE",
  "objects": [{"objectType": "Order", "alias": "o", "byComposite": {"sourceSystem": "ERP", "orderNo": "ORD-001"}}],
  "mutation": {
    "set": {"status": "shipped", "shippedAt": "$now()"}
  }
}
```

### 8.3 DELETE / UPSERT / BATCH

- DELETE：`mutation` 可为空对象。
- UPSERT：MUST 同时提供定位键与写入字段。
- BATCH：`mutation.actions` MUST 为有序数组，支持事务选项。

---

## 9. 多数据源翻译与执行边界

### 9.1 执行阶段

1. 解析（Parse）  
2. 校验（Validate）  
3. 逻辑计划（Logical Plan）  
4. 物理计划（Physical Plan）  
5. 执行与合并（Execute & Merge）

### 9.2 下推原则

- Filter/Projection SHOULD 优先下推。
- Aggregate/Sort/Join 在能力支持时下推，否则在合并层执行。
- 跨源 JOIN 若无法保证正确性/性能，MUST 返回 `OQL_TRANSLATE_CROSS_SOURCE_UNSUPPORTED`。

### 9.3 maxResults 语义

- 默认 100000，最大 100000。
- 多源场景采用“全局截断”：先汇总再按统一排序截断。
- 若发生截断，`metadata.truncated` MUST 为 `true`。

---

## 10. 响应与错误模型

### 10.1 成功响应

```json
{
  "success": true,
  "data": [
    {
      "objectType": "Order",
      "rid": "ri.xxx",
      "properties": {"id": "order_001", "amount": 199.0}
    }
  ],
  "metadata": {
    "totalCount": 1,
    "truncated": false,
    "sourcesUsed": ["MySQL", "Nebula"]
  },
  "trace": {
    "executionTimeMs": 25,
    "requestId": "req-123"
  }
}
```

### 10.2 错误响应

```json
{
  "success": false,
  "error": {
    "code": "OQL_VALIDATE_FIELD_NOT_FOUND",
    "message": "property 'amunt' not found",
    "path": "conditions.children[0].property",
    "details": {"candidates": ["amount"]}
  },
  "trace": {"requestId": "req-124"}
}
```

### 10.3 错误码分层

- `OQL_PARSE_*`：语法解析错误
- `OQL_VALIDATE_*`：语义/字段校验错误
- `OQL_TRANSLATE_*`：逻辑到物理计划翻译失败
- `OQL_EXEC_*`：执行期错误

---

## 11. 兼容性与废弃项

| 旧写法 | 状态 | 替代 |
|---|---|---|
| `orders[].field + direction` | Deprecated | `orders[].param + property + descending` |
| `conditions` 叶子用 `objectType` | Deprecated | 使用 `param` |
| `relationships: "L"`（字符串） | Illegal | 使用 `relationships: []` |
| `query.filter` | Illegal | 使用顶层 `conditions` |

---

## 12. LLM/Agent 生成建议（简版）

### Do
- 始终填写 `version/operation/objects[].alias`。
- 先生成最小可执行 DSL，再增量加 `conditions/orders/maxResults`。
- 提交前进行 schema 校验并修复。

### Don’t
- 不要混用废弃字段。
- 不要在同一对象中同时使用 `by` 和 `byComposite`。
- 不要在 `conditions` 中引用未声明 alias。

