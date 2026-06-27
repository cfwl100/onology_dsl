# 本体对象操作语言（OQL）DSL 规范 - 面向Agent

> 本文档定义面向 Agent / 大模型直接生成的 canonical OQL 规范。Agent 不再先生成中间简化语法，也不再依赖二次转换层；应直接输出可校验、可解释、可执行的 OQL JSON。
>
> 本文件由原《本体对象操作语言(OQL)-DSL规范v1.2-agent最终版.md》和《本体对象操作语言(OQL)-DSL规范v1.2-agent最终版-ID_NAME函数修订.md》合并形成。
>
> 本次合并已纳入 `ID(field)` / `NAME(field)` 返回字段类型指定函数修订：`ID` / `NAME` 不再使用旧的 `EXPR + expr.kind = FUNCTION + args` 写法，而统一使用 `returns.kind = "FUNCTION"`、`returns[].field = "ID(fieldName)" / "NAME(fieldName)"`。

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
11. **函数能力受控**：OQL 函数仅用于对象属性值的轻量转换、归一化、派生、过滤和返回字段语义标识；非核心函数必须通过 OAC 函数注册表扩展。
12. **ID / NAME 语义明确**：`ID` / `NAME` 只作为返回字段类型指定函数，不表示数据库函数调用，不改变字段原始值。

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
| `returns` | array | 条件必填 | 返回字段、表达式、字段类型指定函数、分组字段或聚合指标 |
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

### 3.3 `Expr`：表达式

表达式用于条件、返回派生列、函数型分组和写入值等位置，是 OQL 语义表达能力的一部分。

OQL 中的表达式函数 `FUNCTION` 定位为**受控函数表达式**，用于对象属性值的轻量转换、标准化、时间归一、派生和过滤。表达式函数不是数据库函数的直接映射，不允许把具体数据源方言函数直接暴露给 Agent。

#### 3.3.1 字段表达式

```json
{
  "kind": "FIELD",
  "ref": "o",
  "field": "amount"
}
```

#### 3.3.2 字面量表达式

```json
{
  "kind": "VALUE",
  "value": 100
}
```

#### 3.3.3 受控函数表达式

核心内置函数示例：

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

扩展函数示例：

```json
{
  "kind": "FUNCTION",
  "namespace": "custom",
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

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | :--: | --- |
| `kind` | enum | 是 | 固定为 `FUNCTION` |
| `namespace` | string | 否 | 函数命名空间。核心内置函数省略；扩展函数建议使用 `custom`、`domain`、`vendor` 等命名空间 |
| `name` | string | 是 | 函数名称。核心内置函数或已注册扩展函数 |
| `args` | array | 是 | 函数参数列表，元素必须为合法表达式或字面值 |

#### 3.3.4 核心内置表达式函数

OQL 默认只内置语义访问必要的核心表达式函数。核心函数必须具备可校验、可移植、可下推或可由 OAC 执行层解释的能力。

| 类型 | 核心函数 |
| --- | --- |
| 数值函数 | `ABS`、`ROUND`、`CEIL`、`FLOOR` |
| 字符串函数 | `LENGTH`、`LOWER`、`UPPER`、`TRIM`、`SUBSTRING`、`CONCAT` |
| 时间函数 | `NOW`、`DATE_TRUNC`、`YEAR`、`MONTH`、`DAY`、`HOUR`、`MINUTE`、`SECOND`、`DATE_ADD`、`DATE_SUB`、`DATEDIFF` |
| 空值处理 | `COALESCE`、`IFNULL` |

以下函数不作为核心内置函数默认开放，如确有需要，应通过扩展函数注册机制开放：

```text
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

以下函数不建议进入 OQL 函数体系：

```text
数据库方言函数
窗口函数
任意脚本函数
未治理的 UDF
随机函数
系统环境函数
关系遍历函数
聚合函数
```

聚合函数必须通过 `returns.kind = "METRIC"` 表达，不得通过表达式函数 `kind = "FUNCTION"` 表达。

错误示例：

```json
{
  "kind": "FUNCTION",
  "name": "AVG",
  "args": [
    {
      "kind": "FIELD",
      "ref": "ck",
      "field": "prbUsage"
    }
  ]
}
```

正确示例：

```json
{
  "kind": "METRIC",
  "function": "AVG",
  "ref": "ck",
  "field": "prbUsage",
  "alias": "avgPrbUsage"
}
```

#### 3.3.5 扩展函数注册机制

OAC 可以通过函数注册表开放扩展函数。扩展函数必须先注册、后使用；Agent 不得生成未注册函数。

建议函数注册信息至少包含：

| 字段 | 说明 |
| --- | --- |
| `namespace` | 函数命名空间，例如 `custom`、`domain`、`vendor` |
| `name` | 函数名称 |
| `description` | 函数语义说明 |
| `args` | 参数个数、参数类型、是否可为空 |
| `returnType` | 返回类型 |
| `deterministic` | 是否确定性函数 |
| `allowedIn` | 允许出现的位置，例如 `conditions.left`、`returns.expr`、`returns.groupByExpr`、`mutation.set` |
| `nullPolicy` | 空值处理策略 |
| `pushdownMappings` | 针对不同数据源的可选下推映射 |
| `fallback` | 不能下推时是否允许 OAC 执行层解释执行 |
| `owner` | 函数责任方 |
| `version` | 函数版本 |

扩展函数注册样例：

```json
{
  "namespace": "domain",
  "name": "NORMALIZE_CELL_ID",
  "description": "归一化小区标识格式",
  "args": [
    {
      "name": "cellId",
      "type": "string",
      "nullable": false
    }
  ],
  "returnType": "string",
  "deterministic": true,
  "allowedIn": [
    "conditions.left",
    "returns.expr"
  ],
  "nullPolicy": "RETURN_NULL_IF_ANY_ARG_NULL",
  "pushdownMappings": {
    "mysql": "NORMALIZE_CELL_ID({0})",
    "clickhouse": "normalizeCellId({0})"
  },
  "fallback": "OAC_EXECUTION",
  "owner": "telecom-domain-team",
  "version": "1.0"
}
```

扩展函数约束：

1. `namespace + name` 必须在 OAC 函数注册表中唯一。
2. 扩展函数不得直接暴露任意 SQL 片段、脚本代码或未治理 UDF。
3. 扩展函数必须声明参数类型、返回类型和允许出现的位置。
4. 扩展函数必须声明是否可以下推到具体数据源；不可下推时必须声明是否允许 OAC 执行层解释执行。
5. 扩展函数不得破坏本体对象、关系、属性的语义边界。
6. 复杂业务规则应优先沉淀为本体派生属性、指标模型、预聚合模型或领域服务，不应大量塞入 OQL 函数。

#### 3.3.6 表达式函数使用位置

表达式 `FUNCTION` 允许出现在以下位置：

1. `conditions.left`：用于函数过滤条件；
2. `returns.kind = "EXPR"` 的 `expr`：用于返回派生字段；
3. `returns.kind = "GROUP_BY"` 的 `expr`：用于函数型分组，例如时间桶；
4. `mutation.data.properties` 或 `mutation.set`：用于写操作动态值。

表达式 `FUNCTION` 不允许出现在以下位置：

1. `operation`；
2. `objectType`；
3. `alias`；
4. `relationshipType`；
5. `ref`；
6. 普通 `field`；
7. `metricAlias`；
8. `relationships.from` / `relationships.to`。

> 注意：`ID(field)` / `NAME(field)` 是返回字段类型指定函数，不属于本节表达式函数，不使用 `expr.kind = "FUNCTION" + args` 表达。

### 3.4 `conditions`：对象级条件树

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

表达式条件：

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

### 3.5 `returns`：返回定义

`returns` 用于定义查询结果中的字段、表达式、返回字段类型指定函数、分组字段或聚合指标。

#### 3.5.1 字段返回

```json
{
  "kind": "FIELDS",
  "ref": "o",
  "fields": ["id", "orderNo", "amount", "status"]
}
```

#### 3.5.2 派生表达式返回

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

#### 3.5.3 函数型分组字段

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

#### 3.5.4 普通分组字段

```json
{
  "kind": "GROUP_BY",
  "ref": "o",
  "field": "region",
  "alias": "region"
}
```

#### 3.5.5 聚合指标

```json
{
  "kind": "METRIC",
  "function": "COUNT",
  "ref": "o",
  "field": "*",
  "alias": "orderCount"
}
```

#### 3.5.6 `ID` / `NAME` 返回字段类型指定函数

`id(field)` 与 `name(field)` 函数用于 `returns` 中的字段类型指定，用于多维模型维度字段语义标注：

- `ID(field)` 表示字段 `field` 是多维模型中的“ID”维度。
- `NAME(field)` 表示字段 `field` 是多维模型中的“名称”维度。

该函数只用于返回字段类型指定，不表示数据库函数调用，不改变字段原始值。

标准格式：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

字段说明：

| 字段 | 必填 | 说明 |
|---|:--:|---|
| `kind` | 是 | 固定为 `FUNCTION`，表示返回字段类型指定函数。 |
| `ref` | 是 | 字段所属对象 alias。 |
| `field` | 是 | 使用 `ID(fieldName)` 或 `NAME(fieldName)` 表示多维模型维度语义。 |
| `alias` | 是 | 返回结果别名。名称维度建议使用 `_name` 后缀，ID 维度建议使用 `_id` 后缀或保留原字段名。 |

返回名称维度：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

返回 ID 维度：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "ID(release_cause)",
  "alias": "release_cause_id"
}
```

生成规则：

1. 用户表达“ID、标识、编号、编码、主键、唯一标识、id(field)”时，生成 `ID(field)`。
2. 用户表达“名称、名字、显示名、中文名、name(field)”时，生成 `NAME(field)`。
3. 用户自然语言或伪代码中的小写 `id()` / `name()`，生成 OQL 时统一规范化为大写 `ID()` / `NAME()`。
4. `ID()` / `NAME()` 只出现在 `returns[].field` 中。
5. `<fieldName>` 必须是当前 `ref` 对象下的字段名。
6. `alias` 必须显式填写。

禁止继续使用旧的 `EXPR + expr.kind = FUNCTION + args` 写法表达 `ID` / `NAME`。

错误示例：

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "name": "NAME",
    "args": [
      {
        "kind": "FIELD",
        "ref": "o",
        "field": "release_cause"
      }
    ]
  },
  "alias": "release_cause_name"
}
```

原因：`ID` / `NAME` 不是表达式函数，而是 `returns` 中的字段类型指定函数。

不得生成以下小写写法：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "name(release_cause)",
  "alias": "release_cause_name"
}
```

原因：函数名必须规范化为大写 `NAME`。

与聚合和条件的关系：

- `ID` / `NAME` 不用于 `conditions`。
- `ID` / `NAME` 不用于 `orders`。
- `ID` / `NAME` 不用于 `mutation`。
- `ID` / `NAME` 不表达聚合指标；聚合指标仍使用 `returns.kind = "METRIC"`。

#### 3.5.7 `returns` 约束

1. `QUERY`、`ASSOCIATION_QUERY` 允许 `FIELDS`、`EXPR` 和字段类型指定 `FUNCTION`。
2. `AGGREGATE` 只允许 `GROUP_BY` 和 `METRIC`。
3. `FIELDS.fields` 必须显式列出，不允许 `*`。
4. `EXPR`、`FUNCTION`、`GROUP_BY`、`METRIC` 必须声明 `alias`。
5. `COUNT` 允许 `field = "*"`，其他聚合函数不允许 `*`。
6. 聚合函数仅允许 `COUNT`、`SUM`、`AVG`、`MIN`、`MAX`。
7. `GROUP_BY` 必须使用 `ref + field` 或 `expr` 表达分组维度。
8. `ID` / `NAME` 字段类型指定函数必须使用 `returns.kind = "FUNCTION"`，不得使用 `returns.kind = "EXPR"`。

### 3.6 `aggregateFilter`：聚合结果过滤

#### 3.6.1 定位

`aggregateFilter` 用于对 `AGGREGATE` 操作中已经计算完成的聚合指标进行二次过滤。它表达的是“聚合后过滤”语义，等价于 SQL 中的 `HAVING`，但 OQL 不直接使用 `HAVING` 关键字，统一使用更贴近本体语义的 `aggregateFilter`。

#### 3.6.2 与 `conditions` 的区别

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

#### 3.6.3 基本结构

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

字段说明：

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

约束规则：

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

执行语义：

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

### 3.7 `orders`：排序定义

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

约束：

1. `direction` 只能为 `ASC` 或 `DESC`。
2. 普通查询排序可以使用 `ref + field`。
3. 聚合查询排序优先使用 `returns.alias`。
4. `ID` / `NAME` 不用于 `orders`。

### 3.8 `maxResults`：分页与数量限制

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

### 3.9 `sourceQuery`：中间结果查询

`sourceQuery` 用于把复杂逻辑拆分成多阶段查询，后续 `objects[].fromSource` 可以引用前序 `sourceQuery[].outputAs`。

约束：

1. `sourceQuery[].outputAs` 在当前层必须唯一。
2. `objects[].fromSource` 只能引用同层已声明的 `sourceQuery[].outputAs`。
3. 子查询不允许包含 `BATCH` operation。
4. 子查询层级建议不超过 2 层。

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

带 `ID` / `NAME` 返回字段类型指定的查询：

```json
{
  "version": "2.0",
  "schemaRef": "telecom-v1",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "ReleaseCauseKpi",
      "alias": "o"
    }
  ],
  "returns": [
    {
      "kind": "FUNCTION",
      "ref": "o",
      "field": "ID(release_cause)",
      "alias": "release_cause_id"
    },
    {
      "kind": "FUNCTION",
      "ref": "o",
      "field": "NAME(release_cause)",
      "alias": "release_cause_name"
    }
  ]
}
```

约束：

1. 必须包含 `objects` 与 `returns`。
2. 不得出现 `relationships`、`aggregateFilter`、`mutation`。
3. 多对象查询必须用 `conditions` 明确对象之间的关联条件。
4. 允许 `FIELDS`、`EXPR` 和字段类型指定 `FUNCTION`。

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

`AGGREGATE` 约束：

1. 必须包含 `objects` 与 `returns`。
2. `returns` 至少包含一个 `METRIC`。
3. `returns` 只允许 `GROUP_BY` 和 `METRIC`。
4. `aggregateFilter` 可选，但如果出现，只能引用 `METRIC.alias`。
5. 不得出现 `relationships`、`mutation`。
6. 聚合查询排序字段优先引用 `returns.alias`。
7. 聚合查询不建议返回过大结果集，必须通过 `maxResults.limit` 控制返回规模。
8. `ID` / `NAME` 不表达聚合指标。

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
7. 允许 `FIELDS`、`EXPR` 和字段类型指定 `FUNCTION`。

### 4.4 写操作

#### 4.4.1 `CREATE`

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

#### 4.4.2 `UPDATE`

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

#### 4.4.3 `DELETE`

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

#### 4.4.4 `UPSERT`

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
6. `ID` / `NAME` 不用于 `mutation`。

### 4.5 `BATCH`：批处理操作

`BATCH` 用于表达多个写操作或多个独立操作的批量执行。顶层 `BATCH` 不直接声明 `objects`，而是在 `items[]` 中分别声明子操作。

约束：

1. `BATCH.items` 必须非空。
2. `BATCH.items[]` 不允许继续嵌套 `BATCH`。
3. 每个子操作必须是合法 OQL operation。
4. 批处理的事务边界、失败策略、最大批量大小由 OAC 执行策略控制。
5. 批处理不得绕过单条 OQL 的结构校验和语义校验。

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
9. 如果需要轻量属性变换、时间归一、空值处理等表达能力，优先使用核心内置表达式函数；如需领域函数，必须使用已注册扩展函数。
10. 如果用户要求返回字段的 ID、标识、编号、编码、名称、名字、显示名、中文名等维度语义，使用 `returns.kind = "FUNCTION"` 与 `field = "ID(field)" / "NAME(field)"`。
11. 使用 canonical OQL 对象结构直接生成 JSON。
12. 省略所有未使用字段。
13. 调用 builder 做字段顺序和默认值稳定化。
14. 调用 validator 做结构与引用校验。
15. 仅当用户明确要求执行且请求校验通过时，才进入执行。

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
15. 表达式函数必须使用 `kind = "FUNCTION"` 结构，不得将函数调用退化为字符串拼接。
16. 不得生成未注册扩展函数。
17. 当用户要求返回字段的 ID、标识、编号、编码、名称或名字语义时，必须使用 `returns.kind = "FUNCTION"`、`field = "ID(field)" / "NAME(field)"`，不得使用旧的 `EXPR + expr.kind = FUNCTION + args` 写法。
18. 不得生成数据库方言函数、脚本函数、窗口函数、随机函数或系统环境函数。

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
9. 不允许出现 `linkQuery` 字段或 `LINK_QUERY` operation。

### 6.2 聚合过滤校验

1. `aggregateFilter` 只能用于 `AGGREGATE`。
2. `aggregateFilter.kind` 必须为 `METRIC_PREDICATE` 或 `GROUP`。
3. `METRIC_PREDICATE.metricAlias` 必须引用 `returns` 中的 `METRIC.alias`。
4. `aggregateFilter` 不得引用对象字段、关系字段或未声明 alias。
5. `GROUP.children` 必须非空。
6. `GROUP.relation = NOT` 时，`children` 必须且仅有一个。
7. 操作符与 `values` 个数必须匹配。
8. 不允许生成 `having` 字段。

### 6.3 表达式与函数校验

1. `FIELD.ref` 必须引用当前层已声明 alias。
2. 表达式 `FUNCTION.name` 必须为核心内置表达式函数或 OAC 函数注册表中的已注册扩展函数。
3. 表达式 `FUNCTION.namespace` 为空时，优先按核心内置函数解析；不为空时按 `namespace + name` 解析扩展函数。
4. 表达式 `FUNCTION.args` 必须满足核心函数定义或函数注册表声明的参数个数、参数类型和空值规则。
5. 表达式 `FUNCTION` 只能出现在规范允许的位置。
6. 聚合函数不得通过表达式 `kind = "FUNCTION"` 表达，必须通过 `returns.kind = "METRIC"` 表达。
7. 字段类型指定 `FUNCTION` 仅允许用于 `returns[]`，必须包含 `ref`、`field`、`alias`。
8. 字段类型指定 `FUNCTION.field` 只能使用 `ID(fieldName)` 或 `NAME(fieldName)`，函数名必须大写。
9. `ID(fieldName)` / `NAME(fieldName)` 的 `fieldName` 必须是当前 `ref` 对象下的字段名。
10. `ID` / `NAME` 不允许出现在 `conditions`、`orders`、`mutation`、`aggregateFilter` 中。
11. 扩展函数必须具备函数注册信息，包括参数类型、返回类型、允许位置、是否可下推和不可下推时的 fallback 策略。
12. 如果函数不可下推且 OAC 执行层不支持解释执行，应返回校验或执行计划错误。

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

函数相关错误建议使用：

```json
{
  "success": false,
  "errors": [
    {
      "code": "UNREGISTERED_FUNCTION",
      "message": "Function domain.NORMALIZE_CELL_ID is not registered in OAC function registry.",
      "path": "conditions.left",
      "details": {
        "namespace": "domain",
        "name": "NORMALIZE_CELL_ID"
      }
    }
  ]
}
```

`ID` / `NAME` 写法错误建议使用：

```json
{
  "success": false,
  "errors": [
    {
      "code": "INVALID_RETURN_FUNCTION",
      "message": "ID/NAME must be expressed as returns.kind=FUNCTION with field=ID(fieldName) or NAME(fieldName).",
      "path": "returns[0]",
      "details": {
        "allowed": ["ID(fieldName)", "NAME(fieldName)"]
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

### 8.2 QUERY with ID / NAME

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
      "kind": "FUNCTION",
      "ref": "o",
      "field": "ID(<FieldName>)",
      "alias": "<fieldName>_id"
    },
    {
      "kind": "FUNCTION",
      "ref": "o",
      "field": "NAME(<FieldName>)",
      "alias": "<fieldName>_name"
    }
  ]
}
```

### 8.3 AGGREGATE with aggregateFilter

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

### 8.4 UPDATE with FUNCTION

```json
{
  "version": "2.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "<ObjectType>",
      "alias": "o"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "id",
    "operator": "EQ",
    "values": ["id_001"]
  },
  "mutation": {
    "scope": "ONE",
    "set": {
      "updatedAt": {
        "kind": "FUNCTION",
        "name": "NOW",
        "args": []
      }
    }
  }
}
```

### 8.5 QUERY with extension FUNCTION

```json
{
  "version": "2.0",
  "schemaRef": "telecom-v1",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Cell",
      "alias": "c"
    }
  ],
  "returns": [
    {
      "kind": "EXPR",
      "expr": {
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
      },
      "alias": "normalizedCellId"
    }
  ]
}
```

---

## 9. 合并说明

本文件完成以下合并与覆盖：

1. 保留原 OQL v1.2 Agent 规范中的定位、顶层结构、对象声明、关系声明、条件树、返回定义、聚合过滤、排序、分页、操作类型、Agent 生成流程、校验规则和错误格式。
2. 合入 `ID` / `NAME` 函数修订内容。
3. 明确 `ID` / `NAME` 的标准写法为：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

4. 明确旧写法不再使用：

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "name": "NAME",
    "args": []
  },
  "alias": "release_cause_name"
}
```

5. 合并后仓库仅保留本文件作为面向 Agent 的 OQL DSL 规范入口。
