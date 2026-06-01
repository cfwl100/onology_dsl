# 本体对象操作语言（OQL）DSL 规范 - 面向 Agent 统一版

> 本文档定义面向 Agent / 大模型直接生成的 canonical OQL 规范。Agent 不再先生成中间简化语法，也不再依赖二次转换层；应直接输出可校验、可解释、可执行的 OQL JSON。
>
> 对象关系查询统一使用 `ASSOCIATION_QUERY` 表达。一跳关系导航是关系路径长度为 1 的特例，也通过 `relationships` 表达。
>
> 聚合结果过滤统一使用 `aggregateFilter` 表达。`aggregateFilter` 语义等价于 SQL 中的 `HAVING`，但 OQL 不直接暴露数据库方言关键字。

---

## 1. 定位与设计原则

### 1.1 OQL 定位

OQL（Ontology Query Language）是面向本体对象模型的声明式逻辑查询与操作语言，用于表达：

- 查询或操作哪些本体对象；
- 对象之间有哪些逻辑关系；
- 需要满足哪些对象级、明细级筛选条件；
- 需要返回哪些字段、表达式、分组字段或聚合指标；
- 是否需要对聚合结果进行二次过滤；
- 需要执行哪些创建、更新、删除、存在则更新或批处理动作。

OQL 不直接面向物理表、物理列或数据库方言。执行时由 OAC（Ontology Access）负责根据本体模型、映射信息和数据源能力，完成绑定、校验、翻译、执行和结果装配。

### 1.2 面向 Agent 的核心原则

1. **直接生成 canonical OQL**：Agent 输出的 JSON 即为标准 OQL，不使用中间简化层。
2. **对象中心**：围绕 `objects`、`relationships`、`conditions`、`returns`、`aggregateFilter`、`mutation` 表达逻辑意图。
3. **命名字段优先**：所有关键语义通过字段名表达，避免依赖数组槽位位置。
4. **引用闭包**：所有 `ref`、`sourceRef`、`targetRef`、`from`、`to` 必须引用当前层已声明 alias。
5. **结构可校验**：生成后必须能通过结构校验、引用校验、操作约束校验和执行期语义校验。
6. **字段显式**：返回字段、排序字段、更新字段必须显式列出，不使用隐式 `*`，除 `COUNT` 指标允许 `field = "*"`。
7. **省略未使用字段**：不得输出 `null`、空对象或空数组占位。
8. **查询与写入分离**：查询类操作不得出现 `mutation`；写入类操作不得混入返回、排序或关系路径字段，除非本规范明确允许。
9. **关系查询统一入口**：对象关系、路径关联、一跳关系导航均使用 `ASSOCIATION_QUERY`。
10. **聚合过滤语义化**：聚合后过滤统一使用 `aggregateFilter`，不得使用 `having` 字段。

---

## 2. 顶层结构

### 2.1 标准结构

```json
{
  "version": "2.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [],
  "relationships": [],
  "conditions": {},
  "returns": [],
  "aggregateFilter": {},
  "orders": [],
  "maxResults": {
    "limit": 1000,
    "offset": 0
  },
  "sourceQuery": [],
  "mutation": {},
  "options": {},
  "extensions": {}
}
```

上面仅展示全部可能字段。实际生成时必须省略未使用字段。

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
aggregateFilter
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
| `version` | string | 是 | OQL 协议版本，统一使用当前规范版本 |
| `schemaRef` | string | 是 | 本次请求绑定的本体 schema 标识 |
| `strict` | boolean | 否 | 是否启用严格校验，默认 `true` |
| `operation` | enum | 是 | `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `CREATE` / `UPDATE` / `DELETE` / `UPSERT` / `BATCH` |
| `objects` | array | 条件必填 | 对象声明 |
| `relationships` | array | 条件必填 | 关系路径声明，仅 `ASSOCIATION_QUERY` 使用 |
| `conditions` | object | 条件必填 | 对象级、明细级条件树 |
| `returns` | array | 条件必填 | 返回字段、表达式、分组字段或聚合指标 |
| `aggregateFilter` | object | 否 | 聚合结果过滤，仅 `AGGREGATE` 使用 |
| `orders` | array | 否 | 排序定义 |
| `maxResults` | object | 否 | 最大返回数量与偏移量控制 |
| `sourceQuery` | array | 否 | 中间结果查询 |
| `mutation` | object | 条件必填 | 写操作参数块 |
| `options` | object | 否 | 执行选项 |
| `extensions` | object | 否 | 扩展字段，无明确约定时省略 |

---

## 3. 通用模块

### 3.1 `objects`：对象声明

`objects` 用于声明参与请求的本体对象类型和别名，不承担实例定位职责。

```json
{
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ]
}
```

使用中间结果作为对象来源：

```json
{
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ]
}
```

约束：

1. `alias` 在当前层必须唯一。
2. `fromSource` 只能引用同层 `sourceQuery[].outputAs`。
3. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 中 `objects` 必须且仅有一个对象。
4. `ASSOCIATION_QUERY` 中 `objects` 必须覆盖 `relationships[].from` / `relationships[].to` 引用到的全部对象 alias。
5. `BATCH` 顶层不得出现 `objects`。

### 3.2 `relationships`：关系路径声明

`relationships` 用于显式声明对象之间的关系路径，主要用于 `ASSOCIATION_QUERY`。一跳关系导航也通过 `relationships` 表达，此时数组中只有一条关系。

```json
{
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ]
}
```

约束：

1. `from` / `to` 必须引用当前层 `objects[].alias`。
2. 关系 alias 不得与对象 alias 冲突。
3. `relationships` 仅允许出现在 `ASSOCIATION_QUERY` 中。
4. `relationships` 至少包含一条关系。
5. 多跳路径关联按数组顺序表达路径。
6. `mode = ONE` 时，该关系扩展结果必须恰好一条，否则应返回错误。

### 3.3 `conditions`：对象级条件树

`conditions` 表达聚合前的对象级、明细级过滤条件，语义上对应 SQL 中的 `WHERE`。

字段条件：

```json
{
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "status",
    "operator": "EQ",
    "values": ["completed"]
  }
}
```

逻辑组：

```json
{
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
}
```

操作符包括：`EQ` / `NE` / `GT` / `GTE` / `LT` / `LTE` / `IN` / `NOT_IN` / `BETWEEN` / `LIKE` / `CONTAINS` / `STARTS_WITH` / `ENDS_WITH` / `IS_NULL` / `IS_NOT_NULL` / `IS_EMPTY` / `IS_NOT_EMPTY` / `EXISTS` / `NOT_EXISTS`。

约束：

1. `PREDICATE` 必须使用 `ref + field` 或 `left` 表达左值。
2. `ref` 必须引用当前层对象 alias 或关系 alias。
3. `BETWEEN` 的 `values` 必须恰好包含两个值。
4. `IS_NULL` / `IS_NOT_NULL` / `IS_EMPTY` / `IS_NOT_EMPTY` 不得包含 `values`。
5. `GROUP.relation = NOT` 时，`children` 必须且仅有一个子条件。
6. `GROUP.children` 必须非空。
7. `EXISTS` / `NOT_EXISTS` 不使用 `values`，使用 `subquery` 字段。
8. 子查询深度建议不超过 2 层。
9. 子查询不允许包含 `BATCH` operation。

### 3.4 `returns`：返回定义

`returns` 用于定义查询结果中的字段、表达式、分组字段或聚合指标。

字段返回：

```json
{
  "kind": "FIELDS",
  "ref": "o",
  "fields": ["id", "orderNo", "amount", "status"]
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

### 3.5 `aggregateFilter`：聚合结果过滤

#### 3.5.1 定位

`aggregateFilter` 用于对 `AGGREGATE` 操作中已经计算完成的聚合指标进行二次过滤。它表达的是“聚合后过滤”语义，等价于 SQL 中的 `HAVING`，但 OQL 不直接使用 `HAVING` 关键字，统一使用更贴近本体语义的 `aggregateFilter`。

#### 3.5.2 与 `conditions` 的区别

| 字段 | 过滤阶段 | 过滤对象 | 是否可引用聚合指标 | 类 SQL 对应语义 |
| --- | --- | --- | --- | --- |
| `conditions` | 聚合前 | 对象实例、明细记录、关系实例 | 不可以 | `WHERE` |
| `aggregateFilter` | 聚合后 | 分组结果、聚合指标 | 可以 | `HAVING` |

示例说明：

```text
查询最近一天平均 PRB 利用率大于 80% 的小区。
```

应表达为：

1. 时间范围放在 `conditions`；
2. `AVG(prbUsage)` 放在 `returns` 的 `METRIC`；
3. `AVG(prbUsage) > 80` 放在 `aggregateFilter`。

不能把 `AVG(prbUsage) > 80` 放在 `conditions` 中，因为 `conditions` 执行时聚合指标尚未产生。

#### 3.5.3 基本结构

单个聚合指标过滤：

```json
{
  "aggregateFilter": {
    "kind": "METRIC_PREDICATE",
    "metricAlias": "totalAmount",
    "operator": "GT",
    "values": [10000]
  }
}
```

多个聚合指标组合过滤：

```json
{
  "aggregateFilter": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "METRIC_PREDICATE",
        "metricAlias": "avgPrbUsage",
        "operator": "GT",
        "values": [80]
      },
      {
        "kind": "METRIC_PREDICATE",
        "metricAlias": "sampleCount",
        "operator": "GTE",
        "values": [100]
      }
    ]
  }
}
```

#### 3.5.4 字段说明

`METRIC_PREDICATE`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `kind` | enum | 是 | 固定为 `METRIC_PREDICATE` |
| `metricAlias` | string | 是 | 引用 `returns` 中 `kind = "METRIC"` 的 `alias` |
| `operator` | enum | 是 | 聚合指标比较操作符 |
| `values` | array | 条件必填 | 比较值数组 |

`GROUP`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `kind` | enum | 是 | 固定为 `GROUP` |
| `relation` | enum | 是 | `AND` / `OR` / `NOT` |
| `children` | array | 是 | 子聚合过滤条件 |

支持的操作符：`EQ` / `NE` / `GT` / `GTE` / `LT` / `LTE` / `BETWEEN` / `IN` / `NOT_IN` / `IS_NULL` / `IS_NOT_NULL`。

#### 3.5.5 约束规则

1. `aggregateFilter` 仅允许出现在 `operation = "AGGREGATE"` 中。
2. 使用 `aggregateFilter` 时，`returns` 必须至少包含一个 `METRIC`。
3. `aggregateFilter.metricAlias` 必须引用 `returns` 中 `kind = "METRIC"` 的 `alias`。
4. `aggregateFilter` 不得直接引用对象原始字段、关系字段或未声明 alias。
5. `aggregateFilter` 不得替代 `conditions`；对象级、明细级过滤必须继续放在 `conditions`。
6. `aggregateFilter.kind = "GROUP"` 时，`children` 必须非空。
7. `GROUP.relation = "NOT"` 时，`children` 必须且仅有一个子条件。
8. `EQ` / `NE` / `GT` / `GTE` / `LT` / `LTE` 必须有且仅有一个比较值。
9. `BETWEEN` 必须有且仅有两个比较值。
10. `IS_NULL` / `IS_NOT_NULL` 不得包含 `values`。
11. `aggregateFilter` 不建议包含子查询；如需复杂聚合后再查询，应优先使用 `sourceQuery` 拆分为多阶段查询。
12. `orders` 在聚合查询中优先引用 `returns.alias`，可以引用被 `aggregateFilter` 使用的指标 alias。

#### 3.5.6 执行语义

OAC 执行 `AGGREGATE` 时，应按如下逻辑处理：

```text
对象绑定 -> conditions 明细过滤 -> 分组计算 -> 聚合指标计算 -> aggregateFilter 聚合后过滤 -> orders 排序 -> maxResults 截断
```

映射到 SQL 类数据源时：

```text
conditions       -> WHERE
GROUP_BY returns -> GROUP BY
METRIC returns   -> 聚合函数
aggregateFilter  -> HAVING
orders           -> ORDER BY
maxResults       -> LIMIT / OFFSET
```

对于非 SQL 数据源：

1. 如果数据源支持聚合和聚合后过滤，应尽量下推；
2. 如果数据源不支持，应由 OAC 执行层完成聚合和过滤；
3. 如果需要拉取大量明细数据才能聚合，应进行数据量保护，例如时间范围限制、最大扫描量限制、异步任务或预聚合表。

### 3.6 `orders`：排序定义

```json
{
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    }
  ]
}
```

聚合查询中推荐按 `returns.alias` 排序：

```json
{
  "orders": [
    {
      "field": "avgPrbUsage",
      "direction": "DESC"
    }
  ]
}
```

### 3.7 `maxResults`：分页与数量限制

推荐统一使用对象结构：

```json
{
  "maxResults": {
    "limit": 10,
    "offset": 40
  }
}
```

约束：

1. `limit` 必须大于 0。
2. `offset` 必须大于等于 0。
3. 未指定时默认 `limit = 1000`，`offset = 0`。
4. 最大 `limit` 应由 OAC 配置控制，避免大结果集风险。

---

## 4. Operation 规范

### 4.1 `QUERY`：普通对象查询

```json
{
  "version": "2.0",
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
  "maxResults": {
    "limit": 100,
    "offset": 0
  }
}
```

约束：

1. 必须包含 `objects` 与 `returns`。
2. 不得出现 `relationships`、`aggregateFilter`、`mutation`。
3. 多对象查询必须用 `conditions` 明确对象之间的关联条件。

### 4.2 `AGGREGATE`：聚合查询

`AGGREGATE` 用于表达面向对象集合的分组统计、指标计算和聚合后过滤。

基础聚合示例：

```json
{
  "version": "2.0",
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

使用 `aggregateFilter` 的聚合查询：

```json
{
  "version": "2.0",
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
  ],
  "aggregateFilter": {
    "kind": "METRIC_PREDICATE",
    "metricAlias": "totalAmount",
    "operator": "GT",
    "values": [10000]
  },
  "orders": [
    {
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": {
    "limit": 100,
    "offset": 0
  }
}
```

电信 KPI 聚合示例：

```json
{
  "version": "2.0",
  "schemaRef": "telecom-kpi-v1",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "CellKpi",
      "alias": "ck"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "ck",
        "field": "collectTime",
        "operator": "GTE",
        "values": ["2026-06-01 00:00:00"]
      },
      {
        "kind": "PREDICATE",
        "ref": "ck",
        "field": "collectTime",
        "operator": "LT",
        "values": ["2026-06-02 00:00:00"]
      }
    ]
  },
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "ck",
      "field": "cellId",
      "alias": "cellId"
    },
    {
      "kind": "METRIC",
      "function": "AVG",
      "ref": "ck",
      "field": "prbUsage",
      "alias": "avgPrbUsage"
    },
    {
      "kind": "METRIC",
      "function": "COUNT",
      "ref": "ck",
      "field": "*",
      "alias": "sampleCount"
    }
  ],
  "aggregateFilter": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "METRIC_PREDICATE",
        "metricAlias": "avgPrbUsage",
        "operator": "GT",
        "values": [80]
      },
      {
        "kind": "METRIC_PREDICATE",
        "metricAlias": "sampleCount",
        "operator": "GTE",
        "values": [100]
      }
    ]
  },
  "orders": [
    {
      "field": "avgPrbUsage",
      "direction": "DESC"
    }
  ],
  "maxResults": {
    "limit": 100,
    "offset": 0
  }
}
```

错误示例：聚合指标不得放入 `conditions`。

```json
{
  "conditions": {
    "kind": "PREDICATE",
    "ref": "ck",
    "field": "avgPrbUsage",
    "operator": "GT",
    "values": [80]
  }
}
```

正确写法：

```json
{
  "aggregateFilter": {
    "kind": "METRIC_PREDICATE",
    "metricAlias": "avgPrbUsage",
    "operator": "GT",
    "values": [80]
  }
}
```

`AGGREGATE` 约束：

1. 必须包含 `objects` 与 `returns`。
2. `returns` 至少包含一个 `METRIC`。
3. `returns` 只允许 `GROUP_BY` 和 `METRIC`。
4. `aggregateFilter` 可选，但如果出现，只能引用 `METRIC.alias`。
5. 不得出现 `relationships`、`mutation`。
6. 聚合查询排序字段优先引用 `returns.alias`。
7. 聚合查询不建议返回过大结果集，必须通过 `maxResults.limit` 控制返回规模。

### 4.3 `ASSOCIATION_QUERY`：对象关系/路径关联查询

`ASSOCIATION_QUERY` 用于表达对象之间的关系查询，包括一跳关系导航、多跳路径关联、明确关系类型/方向/路径顺序的关联查询。

```json
{
  "version": "2.0",
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

约束：

1. 必须包含 `objects`、`relationships`、`returns`。
2. `relationships` 至少包含一条关系。
3. `relationships` 按路径顺序声明。
4. `relationships[].from` / `relationships[].to` 必须引用当前层 `objects[].alias`。
5. 不得出现 `mutation`。
6. 一跳关系导航必须使用 `ASSOCIATION_QUERY`。

### 4.4 写操作

#### CREATE

```json
{
  "version": "2.0",
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
        "price": 7999
      }
    }
  }
}
```

#### UPDATE

```json
{
  "version": "2.0",
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
      "price": 6999
    }
  }
}
```

#### DELETE

```json
{
  "version": "2.0",
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

#### UPSERT

```json
{
  "version": "2.0",
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

写操作约束：

1. `CREATE` 与 `UPSERT` 必须使用 `mutation.data.properties`。
2. `UPDATE` 必须包含 `conditions`、`mutation.scope` 与非空 `mutation.set`。
3. `DELETE` 必须包含 `conditions` 与 `mutation.scope`。
4. `UPSERT.matchBy` 必须非空，且其中每个字段都必须出现在 `data.properties` 中。
5. 写操作不得出现 `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery`，除非规范明确允许。

---

## 5. Agent 生成流程

1. 识别用户意图属于普通查询、聚合查询、对象关系/路径关联、创建、更新、删除、存在则更新或批处理。
2. 选择唯一 `operation`。
3. 明确 `schemaRef`。
4. 声明参与对象和 alias。
5. 根据 operation 填写必要模块。
6. 对于对象级过滤，生成 `conditions`。
7. 对于聚合查询，生成 `GROUP_BY` 和 `METRIC`。
8. 如果用户意图包含“聚合结果满足某条件”，生成 `aggregateFilter`。
9. 使用 canonical OQL 对象结构直接生成 JSON。
10. 省略所有未使用字段。
11. 调用 builder 做字段顺序和默认值稳定化。
12. 调用 validator 做结构与引用校验。
13. 仅当用户明确要求执行且请求校验通过时，才进入执行。

生成禁忌：

1. 不输出 Markdown 包装的 JSON。
2. 不输出注释。
3. 不输出 `null` 字段。
4. 不输出空数组或空对象占位。
5. 不使用位置元组表达对象、关系、条件、返回、排序或聚合过滤。
6. 不在查询操作中输出 `mutation`。
7. 不在写操作中输出 `returns` 或 `orders`。
8. 不跨 `sourceQuery` 层级引用 alias。
9. 不在 `BATCH.items[]` 中嵌套 `BATCH`。
10. 不伪造 schema 中不存在的对象、关系或字段。
11. 一跳关系导航必须生成 `ASSOCIATION_QUERY`。
12. 关系类型、方向和返回模式必须通过 `relationships` 表达。
13. 聚合指标过滤必须生成 `aggregateFilter`，不得生成 `having` 字段。
14. 聚合指标 alias 不得放入 `conditions`。

---

## 6. 校验规则摘要

### 6.1 通用校验

1. `version` 必须为当前规范版本。
2. `schemaRef` 必须非空。
3. `operation` 必须为合法枚举。
4. 顶层不得出现未知字段。
5. 所有 alias 必须先声明后引用。
6. 所有对象、关系、字段必须存在于绑定 schema。
7. 所有未使用字段必须省略。
8. 不允许出现 `having` 字段；聚合后过滤统一使用 `aggregateFilter`。

### 6.2 聚合过滤校验

1. `aggregateFilter` 只能用于 `AGGREGATE`。
2. `aggregateFilter.kind` 必须为 `METRIC_PREDICATE` 或 `GROUP`。
3. `METRIC_PREDICATE.metricAlias` 必须引用 `returns` 中的 `METRIC.alias`。
4. `aggregateFilter` 不得引用对象字段、关系字段或未声明 alias。
5. `GROUP.children` 必须非空。
6. `GROUP.relation = NOT` 时，`children` 必须且仅有一个。
7. 操作符与 `values` 个数必须匹配。
8. 不允许生成 `having` 字段。

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

---

## 8. 附录：最小操作模板

### 8.1 QUERY

```json
{
  "version": "2.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "<ObjectType>",
      "alias": "o"
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id"]
    }
  ]
}
```

### 8.2 AGGREGATE with aggregateFilter

```json
{
  "version": "2.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "<ObjectType>",
      "alias": "o"
    }
  ],
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "o",
      "field": "<GroupField>",
      "alias": "<GroupAlias>"
    },
    {
      "kind": "METRIC",
      "function": "COUNT",
      "ref": "o",
      "field": "*",
      "alias": "cnt"
    }
  ],
  "aggregateFilter": {
    "kind": "METRIC_PREDICATE",
    "metricAlias": "cnt",
    "operator": "GT",
    "values": [10]
  }
}
```
