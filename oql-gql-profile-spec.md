# OQL-GQL Profile 语法规范

> 本文档定义面向大模型、AI Agent、开发者和人工审阅的 GQL-like OQL 表层语法，并给出其到现有 Canonical JSON OQL 的转换规则。
>
> OQL-GQL Profile 不是完整 GQL/Cypher，也不是数据库方言。它是面向本体语义数据访问的受限图查询语法，用于表达对象、关系、属性层面的查询意图。OAC 在执行前必须将 OQL-GQL Profile 解析、绑定、归一化为 Canonical JSON OQL，再由 OAC 编译为 MySQL、GaussDB、ES、NebulaGraph、REST API 等具体物理访问方式。

---

## 1. 定位

### 1.1 设计目标

OQL-GQL Profile 的目标是提升大模型和 Agent 生成 OQL 的稳定性、可读性和可审查性。

它解决的问题：

1. Canonical JSON OQL 对机器友好，但对人和大模型较冗长；
2. 本体模型天然是对象、关系、属性组成的图结构 Schema，适合用 GQL-like 语法表达；
3. 大模型更容易稳定生成 `MATCH / WHERE / RETURN / LIMIT` 这类声明式语法；
4. OAC 仍需要结构化、可校验、可治理的 Canonical JSON OQL 作为内部执行 IR；
5. 因此需要一个表层语法到 Canonical JSON OQL 的标准转换规则。

### 1.2 三层架构

```text
自然语言问题
  -> 本体语义子图规划
  -> OQL-GQL Profile
  -> Canonical JSON OQL
  -> OAC 逻辑计划 / DAG 执行计划
  -> SQL / nGQL / ES DSL / REST API / 业务接口
```

分层职责：

| 层次 | 面向对象 | 职责 |
| --- | --- | --- |
| OQL-GQL Profile | 大模型、Agent、开发者 | 以简洁、可读方式表达语义查询意图 |
| Canonical JSON OQL | OAC 编译器、校验器、执行器 | 结构化校验、语义绑定、执行治理、物理编译 |
| Physical Query | MySQL、GaussDB、ES、NebulaGraph、REST API | 实际物理执行 |

### 1.3 基本原则

1. OQL-GQL Profile 只允许使用本体对象、关系、属性，不允许使用物理表名、物理列名、物理索引名；
2. OQL-GQL Profile 必须可以无损转换为 Canonical JSON OQL；
3. OQL-GQL Profile 不作为 OAC 唯一可信执行输入；
4. OAC 执行前必须完成语法解析、语义绑定、Schema 校验和 Canonical JSON OQL 归一化；
5. 如果无法转换为合法 Canonical JSON OQL，则必须拒绝执行；
6. 不支持跨源复杂联邦查询、大规模跨库 Join、跨源复杂聚合；
7. 一个对象的多个属性映射到多个数据库时，只允许 OAC 做轻量属性补齐和结果装配；
8. 大规模分析、报表、复杂联邦计算应下沉到数据平台、指标平台、预聚合模型或专用 Skill。

---

## 2. 支持的语法范围

### 2.1 支持语句

第一阶段支持以下语句：

```text
MATCH
WHERE
RETURN
GROUP BY
AGGREGATE FILTER
ORDER BY
LIMIT
OFFSET
```

语义说明：

| 子句 | 说明 | Canonical JSON OQL 对应结构 |
| --- | --- | --- |
| `MATCH` | 声明对象模式和关系路径 | `objects`、`relationships`、`operation` |
| `WHERE` | 对象级、明细级过滤条件 | `conditions` |
| `RETURN` | 返回字段、派生表达式、聚合指标 | `returns` |
| `GROUP BY` | 聚合维度 | `returns.kind = GROUP_BY` |
| `AGGREGATE FILTER` | 聚合后过滤 | `aggregateFilter` |
| `ORDER BY` | 排序 | `orders` |
| `LIMIT` | 返回上限 | `maxResults.limit` |
| `OFFSET` | 分页偏移 | `maxResults.offset` |

### 2.2 不支持语句

第一阶段不支持：

```text
CREATE
MERGE
SET
DELETE
DETACH DELETE
CALL
UNWIND
WITH
UNION
OPTIONAL MATCH
FOREACH
LOAD CSV
```

写操作仍优先使用 Canonical JSON OQL 表达，因为写操作需要 `actionPolicy`、`dryRun`、`requireConfirmation`、`auditReason`、`maxAffectedRows` 等安全治理字段。

### 2.3 禁止项

OQL-GQL Profile 禁止：

1. `RETURN *` 或 `RETURN alias.*`；
2. 使用物理字段名，如 `order_no`、`created_at`，除非它们本身就是本体属性名；
3. 使用数据库方言函数，如 `DATE_FORMAT`、`JSON_EXTRACT`、`arrayJoin`；
4. 使用窗口函数，如 `ROW_NUMBER`、`RANK`、`LAG`、`LEAD`；
5. 使用脚本函数、随机函数、系统环境函数；
6. 使用未注册扩展函数；
7. 通过函数动态生成对象类型、关系类型、属性名或 alias；
8. 无边界多跳路径，如 `[:trigger*]`；
9. 跨源复杂 Join、跨源复杂聚合、跨源复杂排序；
10. 将聚合指标 alias 写入 `WHERE`，聚合后过滤必须使用 `AGGREGATE FILTER`。

---

## 3. 词法与命名规范

### 3.1 对象、关系、属性命名

```text
ObjectType        ::= Identifier
RelationshipType  ::= Identifier
PropertyName      ::= Identifier
Alias             ::= Identifier
Identifier        ::= [A-Za-z_][A-Za-z0-9_]*
```

命名规则：

1. `ObjectType` 必须来自本体对象类型；
2. `RelationshipType` 必须来自本体关系类型，通常对应语义子图中关系的 `edges.properties.name`；
3. `PropertyName` 必须来自本体对象属性或关系属性；
4. `Alias` 在同一个查询中必须唯一；
5. 推荐使用小写短 alias，例如 `a`、`ne`、`sp`、`ck`；
6. 不允许在 alias、属性名、关系名中使用函数表达式。

### 3.2 字符串、数值、布尔值

```text
StringLiteral  ::= "..."
NumberLiteral  ::= 100 | 100.5
BooleanLiteral ::= true | false
NullLiteral    ::= null
```

字符串必须使用双引号。

### 3.3 时间间隔

动态时间条件中的时间间隔建议使用 ISO-8601 duration 字符串。

```text
P7D    表示 7 天
PT1H   表示 1 小时
PT30M  表示 30 分钟
```

示例：

```text
WHERE ck.collectTime >= DATE_SUB(NOW(), "P7D")
```

---

## 4. 语法定义

### 4.1 查询基本结构

```text
Query ::= MatchClause
          WhereClause?
          ReturnClause
          GroupByClause?
          AggregateFilterClause?
          OrderByClause?
          LimitClause?
          OffsetClause?
```

### 4.2 MATCH 子句

#### 单对象匹配

```text
MATCH (alias:ObjectType)
```

示例：

```text
MATCH (o:Order)
```

转换为：

```json
{
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ]
}
```

#### 一跳关系匹配

```text
MATCH (srcAlias:SourceObject)-[relAlias:RelationshipType]->(dstAlias:TargetObject)
MATCH (srcAlias:SourceObject)<-[relAlias:RelationshipType]-(dstAlias:TargetObject)
```

示例：

```text
MATCH (a:Alarm)-[r:happenOn]->(ne:Ne)
```

转换为：

```json
{
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Alarm",
      "alias": "a"
    },
    {
      "objectType": "Ne",
      "alias": "ne"
    }
  ],
  "relationships": [
    {
      "relationshipType": "happenOn",
      "alias": "r",
      "from": "a",
      "to": "ne",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ]
}
```

反向关系示例：

```text
MATCH (ne:Ne)<-[r:happenOn]-(a:Alarm)
```

推荐转换为：

```json
{
  "relationshipType": "happenOn",
  "alias": "r",
  "from": "a",
  "to": "ne",
  "direction": "OUTBOUND",
  "mode": "LIST"
}
```

说明：即使表层语法采用反向箭头，Canonical JSON OQL 中也应优先按本体关系定义方向归一化。

#### 多跳固定路径

```text
MATCH (a:A)-[r1:R1]->(b:B)-[r2:R2]->(c:C)
```

转换为多个 `relationships`，按路径顺序排列。

```json
{
  "relationships": [
    {
      "relationshipType": "R1",
      "alias": "r1",
      "from": "a",
      "to": "b",
      "direction": "OUTBOUND",
      "mode": "LIST"
    },
    {
      "relationshipType": "R2",
      "alias": "r2",
      "from": "b",
      "to": "c",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ]
}
```

#### 受控可变长度路径

第一阶段不建议在 OQL-GQL Profile 中开放完整 `*` 路径语法。若必须支持，必须带路径边界。

推荐语法：

```text
MATCH (a:Alarm)-[r:trigger {minDepth:1, maxDepth:3, maxPaths:1000}]->(b:Alarm)
```

转换为：

```json
{
  "relationshipType": "trigger",
  "alias": "r",
  "from": "a",
  "to": "b",
  "direction": "OUTBOUND",
  "mode": "LIST",
  "pathPolicy": {
    "minDepth": 1,
    "maxDepth": 3,
    "maxPaths": 1000,
    "cyclePolicy": "NO_REPEAT_VERTEX"
  }
}
```

禁止：

```text
MATCH (a:Alarm)-[:trigger*]->(b:Alarm)
```

---

### 4.3 WHERE 子句

```text
WHERE Predicate
Predicate ::= Comparison | Predicate AND Predicate | Predicate OR Predicate | NOT Predicate
Comparison ::= Expr Operator ValueOrExpr
```

支持操作符：

| OQL-GQL Profile | Canonical JSON OQL operator |
| --- | --- |
| `==` | `EQ` |
| `!=` | `NE` |
| `>` | `GT` |
| `>=` | `GTE` |
| `<` | `LT` |
| `<=` | `LTE` |
| `IN` | `IN` |
| `NOT IN` | `NOT_IN` |
| `LIKE` | `LIKE` |
| `IS NULL` | `IS_NULL` |
| `IS NOT NULL` | `IS_NOT_NULL` |
| `BETWEEN ... AND ...` | `BETWEEN` |

属性条件示例：

```text
WHERE o.status == "completed"
```

转换为：

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

组合条件示例：

```text
WHERE o.status == "completed" AND o.amount >= 1000
```

转换为：

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

函数左值示例：

```text
WHERE LENGTH(o.comment) > 100
```

转换为：

```json
{
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
}
```

动态时间条件示例：

```text
WHERE ck.collectTime >= DATE_SUB(NOW(), "P7D")
```

转换为：

```json
{
  "conditions": {
    "kind": "PREDICATE",
    "ref": "ck",
    "field": "collectTime",
    "operator": "GTE",
    "values": [
      {
        "kind": "FUNCTION",
        "name": "DATE_SUB",
        "args": [
          {
            "kind": "FUNCTION",
            "name": "NOW",
            "args": []
          },
          {
            "kind": "VALUE",
            "value": "P7D"
          }
        ]
      }
    ]
  }
}
```

---

### 4.4 RETURN 子句

```text
RETURN ReturnItem (, ReturnItem)*
ReturnItem ::= PropertyRef AS Alias
             | FunctionExpr AS Alias
             | AggregateExpr AS Alias
```

普通字段返回：

```text
RETURN o.id AS id, o.orderNo AS orderNo, o.amount AS amount
```

转换为：

```json
{
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount"]
    }
  ]
}
```

如果同一个 `RETURN` 中包含多个对象字段，需要按 `ref` 分组转换。

```text
RETURN a.alarmName AS alarmName, ne.neId AS neId
```

转换为：

```json
{
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "a",
      "fields": ["alarmName"]
    },
    {
      "kind": "FIELDS",
      "ref": "ne",
      "fields": ["neId"]
    }
  ]
}
```

派生表达式返回：

```text
RETURN ABS(o.deltaAmount) AS absDeltaAmount
```

转换为：

```json
{
  "returns": [
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
  ]
}
```

聚合指标返回：

```text
RETURN AVG(ck.prbUsage) AS avgPrbUsage, COUNT(*) AS sampleCount
```

转换为：

```json
{
  "returns": [
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
  ]
}
```

注意：聚合函数不转换为 `kind = FUNCTION`，必须转换为 `kind = METRIC`。

---

### 4.5 GROUP BY 子句

普通分组：

```text
GROUP BY ck.cellId
```

转换为：

```json
{
  "kind": "GROUP_BY",
  "ref": "ck",
  "field": "cellId",
  "alias": "cellId"
}
```

函数型分组：

```text
GROUP BY DATE_TRUNC("hour", ck.collectTime) AS collectHour
```

转换为：

```json
{
  "kind": "GROUP_BY",
  "expr": {
    "kind": "FUNCTION",
    "name": "DATE_TRUNC",
    "args": [
      {
        "kind": "VALUE",
        "value": "hour"
      },
      {
        "kind": "FIELD",
        "ref": "ck",
        "field": "collectTime"
      }
    ]
  },
  "alias": "collectHour"
}
```

如果 `RETURN` 中已经包含同样的分组表达式，可由转换器去重，Canonical JSON OQL 中只保留一个 `GROUP_BY` 项。

---

### 4.6 AGGREGATE FILTER 子句

`AGGREGATE FILTER` 表达聚合后过滤，对应 Canonical JSON OQL 的 `aggregateFilter`。

示例：

```text
AGGREGATE FILTER avgPrbUsage > 80 AND sampleCount >= 100
```

转换为：

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

禁止使用 `HAVING`。如果解析器兼容 `HAVING`，也必须归一化为 `aggregateFilter`，并给出规范提示。

---

### 4.7 ORDER BY 子句

```text
ORDER BY o.createdAt DESC
ORDER BY avgPrbUsage DESC
```

字段排序转换为：

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

聚合或返回 alias 排序转换为：

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

转换规则：

1. 如果排序项是 `alias.field`，转换为 `ref + field`；
2. 如果排序项是返回 alias 或 metric alias，转换为 `field`；
3. 聚合查询中优先按 `returns.alias` 排序。

---

### 4.8 LIMIT / OFFSET 子句

```text
LIMIT 1000
OFFSET 0
```

转换为：

```json
{
  "maxResults": {
    "limit": 1000,
    "offset": 0
  }
}
```

约束：

1. `LIMIT` 必须为正整数；
2. `OFFSET` 必须为非负整数；
3. 如果没有指定 `LIMIT`，转换器应使用默认值，例如 `1000`；
4. OAC 应配置全局硬上限，例如 `100000`；
5. 禁止无边界大查询。

---

## 5. Operation 推导规则

| OQL-GQL Profile 特征 | Canonical JSON OQL operation |
| --- | --- |
| `MATCH` 中只有单对象，且无聚合指标 | `QUERY` |
| `MATCH` 中包含关系路径，且无聚合指标 | `ASSOCIATION_QUERY` |
| `RETURN` 中包含聚合指标或存在 `GROUP BY` | `AGGREGATE` |
| 存在 `AGGREGATE FILTER` | `AGGREGATE` |

推导优先级：

1. 如果存在聚合指标、`GROUP BY` 或 `AGGREGATE FILTER`，operation = `AGGREGATE`；
2. 否则如果 `MATCH` 中存在关系路径，operation = `ASSOCIATION_QUERY`；
3. 否则 operation = `QUERY`。

---

## 6. 函数规则

### 6.1 核心函数白名单

| 类型 | 函数 |
| --- | --- |
| 数值函数 | `ABS`、`ROUND` |
| 字符串函数 | `LENGTH`、`LOWER`、`UPPER`、`TRIM`、`SUBSTRING` |
| 时间函数 | `NOW`、`DATE_TRUNC`、`YEAR`、`MONTH`、`DAY`、`HOUR`、`MINUTE`、`DATE_ADD`、`DATE_SUB`、`DATEDIFF` |
| 空值处理 | `COALESCE`、`IFNULL` |

### 6.2 非核心扩展函数

以下函数不作为核心函数默认开放，如需使用必须注册为扩展函数：

```text
CEIL
FLOOR
CONCAT
SECOND
DATE_FORMAT
REPLACE
LPAD
RPAD
IF
TO_STRING
TO_NUMBER
TO_DATE
TO_DATETIME
```

### 6.3 扩展函数语法

扩展函数建议使用命名空间前缀：

```text
domain.NORMALIZE_CELL_ID(c.cellId)
```

转换为：

```json
{
  "kind": "FUNCTION",
  "namespace": "domain",
  "name": "NORMALIZE_CELL_ID",
  "args": [
    {
      "kind": "FIELD",
      "ref": "c",
      "field": "cellId"
    }
  ]
}
```

约束：

1. 扩展函数必须先注册后使用；
2. 未注册扩展函数不得执行；
3. 扩展函数不得直接暴露任意 SQL 片段；
4. 扩展函数必须声明参数类型、返回类型、允许位置、下推映射和 fallback 策略。

---

## 7. 转换总规则

### 7.1 MATCH 到 objects / relationships

| GQL-like 元素 | Canonical JSON OQL |
| --- | --- |
| `(a:Alarm)` | `objects[].objectType = Alarm, alias = a` |
| `-[r:happenOn]->` | `relationships[].relationshipType = happenOn, alias = r, direction = OUTBOUND` |
| `<-[r:happenOn]-` | 按本体关系方向归一化，必要时 direction = INBOUND |

### 7.2 WHERE 到 conditions

| GQL-like 条件 | Canonical JSON OQL |
| --- | --- |
| `a.name == "x"` | `PREDICATE ref=a field=name operator=EQ values=["x"]` |
| `a.score >= 80` | `operator=GTE` |
| `a.name LIKE "abc"` | `operator=LIKE` |
| `a.id IN ["1", "2"]` | `operator=IN` |
| `a.time BETWEEN "t1" AND "t2"` | `operator=BETWEEN values=["t1", "t2"]` |
| `A AND B` | `GROUP relation=AND children=[A,B]` |
| `A OR B` | `GROUP relation=OR children=[A,B]` |
| `NOT A` | `GROUP relation=NOT children=[A]` |

### 7.3 RETURN 到 returns

| GQL-like 返回项 | Canonical JSON OQL |
| --- | --- |
| `a.name AS name` | `FIELDS ref=a fields=[name]` |
| `ABS(a.score) AS absScore` | `EXPR expr=FUNCTION ABS alias=absScore` |
| `COUNT(*) AS cnt` | `METRIC function=COUNT field=* alias=cnt` |
| `AVG(a.score) AS avgScore` | `METRIC function=AVG field=score alias=avgScore` |

### 7.4 GROUP BY 到 GROUP_BY returns

| GQL-like 分组 | Canonical JSON OQL |
| --- | --- |
| `GROUP BY a.type` | `GROUP_BY ref=a field=type alias=type` |
| `GROUP BY DATE_TRUNC("hour", a.time) AS hour` | `GROUP_BY expr=FUNCTION DATE_TRUNC alias=hour` |

### 7.5 AGGREGATE FILTER 到 aggregateFilter

| GQL-like 聚合过滤 | Canonical JSON OQL |
| --- | --- |
| `cnt > 10` | `METRIC_PREDICATE metricAlias=cnt operator=GT values=[10]` |
| `avgScore >= 80 AND cnt > 10` | `GROUP relation=AND children=[...]` |

---

## 8. 完整样例

### 8.1 普通对象查询

OQL-GQL Profile：

```text
MATCH (o:Order)
WHERE o.status == "completed"
RETURN
  o.id AS id,
  o.orderNo AS orderNo,
  o.amount AS amount,
  o.status AS status
ORDER BY o.createdAt DESC
LIMIT 1000
```

Canonical JSON OQL：

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
    "limit": 1000,
    "offset": 0
  }
}
```

### 8.2 对象关系查询

OQL-GQL Profile：

```text
MATCH (a:Alarm)-[r:happenOn]->(ne:Ne)
WHERE a.alarmName LIKE "LinkDown"
RETURN
  ne.neId AS neId,
  ne.name AS name
LIMIT 1000
```

Canonical JSON OQL：

```json
{
  "version": "2.0",
  "schemaRef": "telecom-v1",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Alarm",
      "alias": "a"
    },
    {
      "objectType": "Ne",
      "alias": "ne"
    }
  ],
  "relationships": [
    {
      "relationshipType": "happenOn",
      "alias": "r",
      "from": "a",
      "to": "ne",
      "direction": "OUTBOUND",
      "mode": "LIST"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "a",
    "field": "alarmName",
    "operator": "LIKE",
    "values": ["LinkDown"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "ne",
      "fields": ["neId", "name"]
    }
  ],
  "maxResults": {
    "limit": 1000,
    "offset": 0
  }
}
```

### 8.3 聚合查询

OQL-GQL Profile：

```text
MATCH (ck:CellKpi)
WHERE ck.collectTime >= DATE_SUB(NOW(), "PT1H")
RETURN
  ck.cellId AS cellId,
  AVG(ck.prbUsage) AS avgPrbUsage,
  COUNT(*) AS sampleCount
GROUP BY ck.cellId
AGGREGATE FILTER avgPrbUsage > 80 AND sampleCount >= 100
ORDER BY avgPrbUsage DESC
LIMIT 1000
```

Canonical JSON OQL：

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
    "kind": "PREDICATE",
    "ref": "ck",
    "field": "collectTime",
    "operator": "GTE",
    "values": [
      {
        "kind": "FUNCTION",
        "name": "DATE_SUB",
        "args": [
          {
            "kind": "FUNCTION",
            "name": "NOW",
            "args": []
          },
          {
            "kind": "VALUE",
            "value": "PT1H"
          }
        ]
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
    "limit": 1000,
    "offset": 0
  }
}
```

### 8.4 函数型分组

OQL-GQL Profile：

```text
MATCH (ck:CellKpi)
WHERE ck.collectTime >= DATE_SUB(NOW(), "P1D")
RETURN
  DATE_TRUNC("hour", ck.collectTime) AS collectHour,
  ck.cellId AS cellId,
  AVG(ck.prbUsage) AS avgPrbUsage
GROUP BY DATE_TRUNC("hour", ck.collectTime) AS collectHour, ck.cellId
ORDER BY collectHour ASC
LIMIT 1000
```

Canonical JSON OQL：

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
    "kind": "PREDICATE",
    "ref": "ck",
    "field": "collectTime",
    "operator": "GTE",
    "values": [
      {
        "kind": "FUNCTION",
        "name": "DATE_SUB",
        "args": [
          {
            "kind": "FUNCTION",
            "name": "NOW",
            "args": []
          },
          {
            "kind": "VALUE",
            "value": "P1D"
          }
        ]
      }
    ]
  },
  "returns": [
    {
      "kind": "GROUP_BY",
      "expr": {
        "kind": "FUNCTION",
        "name": "DATE_TRUNC",
        "args": [
          {
            "kind": "VALUE",
            "value": "hour"
          },
          {
            "kind": "FIELD",
            "ref": "ck",
            "field": "collectTime"
          }
        ]
      },
      "alias": "collectHour"
    },
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
    }
  ],
  "orders": [
    {
      "field": "collectHour",
      "direction": "ASC"
    }
  ],
  "maxResults": {
    "limit": 1000,
    "offset": 0
  }
}
```

---

## 9. 校验规则

### 9.1 语法校验

1. 必须包含 `MATCH` 和 `RETURN`；
2. `MATCH` 中对象 alias 必须唯一；
3. 所有属性引用必须是 `alias.property` 形式；
4. 所有 alias 必须来自 `MATCH`；
5. `RETURN` 字段必须显式指定；
6. `LIMIT` 必须是正整数；
7. 禁止 `RETURN *`。

### 9.2 语义校验

1. `ObjectType` 必须存在于本体 Schema；
2. `RelationshipType` 必须存在于本体 Schema；
3. `PropertyName` 必须属于对应对象或关系；
4. 关系方向必须与本体关系定义一致，或可被 OAC 明确支持反向遍历；
5. 聚合指标 alias 必须来自 `RETURN` 中的聚合项；
6. `AGGREGATE FILTER` 只能引用聚合指标 alias；
7. `WHERE` 不能引用聚合指标 alias；
8. 函数必须来自核心白名单或函数注册表。

### 9.3 执行保护校验

1. 查询必须有 `LIMIT` 或由转换器补默认 `LIMIT`；
2. 不允许无边界路径遍历；
3. 不允许大规模跨源联邦查询；
4. 不允许没有过滤条件的大规模对象查询；
5. OAC 可根据对象类型和数据源能力拒绝执行高风险查询；
6. 超过结果上限时应返回结构化错误。

---

## 10. 错误示例

### 10.1 返回所有字段

错误：

```text
MATCH (o:Order)
RETURN o.*
```

原因：OQL 禁止隐式返回所有字段。

正确：

```text
MATCH (o:Order)
RETURN o.id AS id, o.status AS status
LIMIT 1000
```

### 10.2 使用物理字段名

错误：

```text
MATCH (o:Order)
RETURN o.order_no AS orderNo
```

原因：`order_no` 是物理字段风格，除非本体属性就叫 `order_no`，否则禁止使用。

正确：

```text
MATCH (o:Order)
RETURN o.orderNo AS orderNo
```

### 10.3 使用数据库函数

错误：

```text
MATCH (o:Order)
WHERE DATE_FORMAT(o.createdAt, "%Y-%m-%d") == "2026-06-01"
RETURN o.id AS id
```

原因：`DATE_FORMAT` 不属于核心函数，不能作为数据库方言函数直接使用。

### 10.4 聚合指标写入 WHERE

错误：

```text
MATCH (ck:CellKpi)
RETURN ck.cellId AS cellId, AVG(ck.prbUsage) AS avgPrbUsage
GROUP BY ck.cellId
WHERE avgPrbUsage > 80
```

正确：

```text
MATCH (ck:CellKpi)
RETURN ck.cellId AS cellId, AVG(ck.prbUsage) AS avgPrbUsage
GROUP BY ck.cellId
AGGREGATE FILTER avgPrbUsage > 80
```

---

## 11. 推荐落地方式

### 11.1 面向大模型

大模型优先生成 OQL-GQL Profile，因为它更短、更接近自然语言、更适合人工审阅。

推荐生成流程：

```text
自然语言问题
  -> 识别 rootObject / targetObject / relationship / properties
  -> 生成 OQL-GQL Profile
  -> 解析并转换为 Canonical JSON OQL
  -> 校验
  -> 执行
```

### 11.2 面向 OAC

OAC 不应直接把 OQL-GQL Profile 作为唯一可信执行输入。执行前必须转换为 Canonical JSON OQL。

推荐执行流程：

```text
OQL-GQL Profile
  -> Parser
  -> AST
  -> Semantic Binder
  -> Canonical JSON OQL
  -> JSON Schema Validator
  -> OAC Compiler
  -> DAG Execution Plan
  -> Physical Query Execution
```

### 11.3 面向兼容性

1. 保留现有 Canonical JSON OQL；
2. 新增 OQL-GQL Profile 作为表层语法；
3. 两者必须能互相追踪，但以 Canonical JSON OQL 作为执行基准；
4. 新增语法能力时，应先扩展 Canonical JSON OQL，再扩展 OQL-GQL Profile；
5. OQL-GQL Profile 的任何语法都必须能转换为 Canonical JSON OQL。

---

## 12. 总结

OQL-GQL Profile 更适合大模型和 Agent 生成，也更适合人类阅读和调试；Canonical JSON OQL 更适合 OAC 内部校验、治理、编译和多源执行。

推荐方案：

```text
OQL-GQL Profile 作为大模型生成和人工审阅的表层语法；
Canonical JSON OQL 作为 OAC 唯一可信执行 IR；
OAC 负责将 Canonical JSON OQL 编译为 MySQL、GaussDB、ES、NebulaGraph、REST API 等物理访问方式。
```
