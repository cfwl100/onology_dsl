# 本体对象操作语言（OQL）DSL 规范

---

# 阅读导航

- **第 1 章：设计原则、架构定位与多数据源映射**
- **第 2 章：统一顶层结构与通用字段**（`objects` / `relationships` / `conditions` / `returns` / `orders` / `sourceQuery`）
- **第 3 章：对象查询（QUERY）**
- **第 4 章：聚合查询（AGGREGATE）**
- **第 5 章：关联路径查询（ASSOCIATION_QUERY）**
- **第 6 章：一跳关联查询（LINK_QUERY）**
- **第 7 章：写操作**（`CREATE` / `UPDATE` / `DELETE` / `UPSERT` / `BATCH`）
- **第 8 章：错误码与校验规则**
- **附录 A：JSON Schema / EBNF 形式化定义**
- **附录 B：完整样例、物理查询转换示例与字段速查**

> **建议阅读顺序**：
> 先阅读第 1 章理解 OQL 的设计目标、适用边界与 OAC 转换架构；
> 再阅读第 2 章掌握统一结构；
> 最后按 operation 类型阅读对应章节。

------

# 1. 设计原则与架构

## 1.1 OQL 的定位

OQL（Ontology Query Language）是一种**面向本体对象模型的声明式逻辑查询与操作语言**。
它描述的是：

- 需要查询或操作哪些对象
- 这些对象之间有哪些逻辑关系
- 需要满足哪些条件
- 需要返回哪些字段
- 需要执行何种写入动作

OQL **不直接面向物理表、物理字段和具体数据库方言**。
它的执行依赖 OAC（Ontology Access）服务完成从 OQL 到真实物理查询语句或写入语句的转换。

因此，OQL 的职责是：

- 表达**逻辑意图**
- 保持对物理存储透明
- 为 AI Agent 和 OAC 转换引擎提供稳定、统一、可校验的中间表示

OAC 的职责是：

- 将 OQL 绑定到本体元数据与物理映射
- 生成逻辑执行计划
- 将逻辑计划下推为 SQL、nGQL 或其他物理查询语句
- 对多数据源查询进行拆分、编排、回表、聚合与结果装配

> **重要说明**：
> OQL 不是 SQL 的别名，也不是图查询语言的包装器。
> OQL 是**逻辑层 DSL**；SQL、nGQL 等仅是 OAC 在物理层的执行产物。

------

## 1.2 设计目标

OQL 的设计目标如下：

- **统一性**：不同操作共享统一的顶层结构与通用字段
- **对象驱动**：以对象、属性、关系为中心，而非以表、列、Join 为中心
- **AI 友好**：采用单一 canonical 写法，降低大模型生成歧义
- **可校验**：支持 JSON Schema、语义校验、引用校验与执行期校验
- **可编排**：支持单源下推、跨源拆分、中间结果集与 `sourceQuery`
- **可扩展**：允许通过 schema 与映射元数据扩展对象类型、属性与关系
- **企业级**：支持批处理、原子执行、可观测性、执行选项与错误码规范
- **多数据源透明**：对象属性来源对调用方透明，由 OAC 负责映射与装配

------

## 1.3 核心设计原则

| 原则               | 说明                                                   |
| ------------------ | ------------------------------------------------------ |
| **声明式**         | 只描述“查什么 / 改什么”，不描述“怎么执行”              |
| **对象中心**       | 所有请求围绕对象、属性、关系表达，而非围绕物理表表达   |
| **单一主写法**     | 同一语义只保留一种 canonical 结构，避免多套等价写法    |
| **引用显式化**     | 所有跨模块引用统一使用 alias，不依赖隐式推断           |
| **条件统一收口**   | 查询筛选、更新目标、删除目标统一通过 `conditions` 表达 |
| **逻辑与物理解耦** | OQL 不直接暴露表名、列名、库名，由 OAC 负责绑定与翻译  |
| **可组合**         | 支持 `sourceQuery` 作为中间结果集，支持复杂查询编排    |
| **优先下推**       | 能在单一物理源下推的过滤、排序、聚合，应优先下推       |
| **谨慎跨源**       | 跨源查询默认拆分执行，由 OAC 在中间层进行合并与装配    |
| **安全优先**       | 不允许高风险隐式写法；写操作必须显式声明范围或匹配键   |

------

## 1.4 面向 AI 与 OAC 的规范约束

OQL v1.0 采用 **canonical JSON** 作为唯一标准形态，并遵循以下约束：

1. **只保留唯一主写法**，不定义并行兼容语法
2. **对象只声明，不定位**；对象目标由 `conditions` 或 `matchBy` 决定
3. **所有跨模块引用统一使用 alias**
4. **未使用字段必须省略**；不允许 `null`、空对象、空数组占位
5. **普通查询统一使用 `QUERY`**；不单独定义 `MULTI_OBJECT_QUERY`
6. **多跳路径查询使用 `ASSOCIATION_QUERY`**
7. **一跳关联对象查询使用 `LINK_QUERY`**
8. **写操作统一使用 `mutation` 专用块**
9. **`UPDATE` / `DELETE` 必须显式声明 `scope`**
10. **`UPSERT` 必须显式声明 `matchBy`**

这些约束既服务于 AI 生成稳定性，也服务于 OAC 编译器的实现简化。

------

## 1.5 多数据源映射模型

### 1.5.1 基本思想

在本体模型中，**对象的每个属性都可以独立映射到不同的物理数据源**。
也就是说：

- 同一个对象的不同属性，可能来自不同数据库
- 不同对象，可能映射到同一个数据库
- 多个对象，甚至可能映射到同一个数据库的同一张表
- 对象之间的关系，既可能存在于关系表，也可能存在于图数据库边

因此，OQL 所面对的是**逻辑统一对象模型**，而不是单一物理库模型。

------

### 1.5.2 示例：对象属性跨源映射

以下示例说明一个逻辑对象 `Order` 的属性可分布在多个物理源中：

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        逻辑对象：Order                              │
├─────────────────────────────────────────────────────────────────────┤
│  id / orderNo        → MySQL.orders                                │
│  customerId          → Gauss.customer_order_ref                    │
│  amount              → PostgreSQL.payments                         │
│  status              → PostgreSQL.order_status                     │
│  createdAt           → Carbon.order_perf                           │
│  metadata            → ElasticSearch.order_history                 │
│                                                                     │
│  逻辑主键：["sourceSystem", "orderNo"]                              │
│  物理主键：由各源映射规则分别定义                                     │
└─────────────────────────────────────────────────────────────────────┘
```

这意味着同一个逻辑 `Order` 对象可能需要经过：

- 单源查询
- 多源并行查询
- 主键回查
- 中间层字段装配

才能形成最终结果。

------

### 1.5.3 支持的物理数据源（示例）

| 数据源            | 版本 / 形态         | 典型用途                           |
| ----------------- | ------------------- | ---------------------------------- |
| **NebulaGraph**   | GDE 版本            | 资源关系、拓扑、知识图谱、多跳关联 |
| **GaussDB V3**    | GDE 版本            | 主业务数据                         |
| **MySQL**         | 5.7 / 8.x           | 主业务数据、在线事务数据           |
| **PostgreSQL**    | 15.x                | 资源、结构化业务数据               |
| **ClickHouse**    | GDE 版本            | 日志、指标、明细分析               |
| **ElasticSearch** | GDE / 云版本        | 历史索引、检索型数据               |
| **Carbon / Hudi** | GDE 版本 / 后续演进 | 性能与时序数据                     |
| **GaussDB V5**    | GDE 版本            | 向量数据                           |

> **说明**：
> OQL 规范本身不绑定具体厂商版本；
> 数据源类型与版本信息通常由 OAC 的映射元数据管理。

------

## 1.6 阅读建议

阅读本规范时，建议先建立以下三个认知：

1. **OQL 描述的是逻辑对象操作，不是物理表操作**
2. **对象与属性的物理来源可以完全不同**
3. **OAC 的核心是编译与编排，不是简单字符串翻译**

理解以上三点后，再进入第 2 章统一结构，会更容易理解：

- 为什么 `objects` 只声明对象
- 为什么 `conditions` 统一承担筛选职责
- 为什么 `sourceQuery` 被设计为中间结果集
- 为什么 OQL 可以同时服务于 SQL 与图查询后端

---

# 2. 统一顶层结构

> **设计原则**：OQL DSL 采用**顶层通用字段 + 少量操作专用块**的统一结构设计。
>
> 1. **单一主写法**：同一语义只保留一种规范写法，不定义并行等价写法。
> 2. **对象只声明**：`objects` 仅用于声明参与本次操作的对象类型与别名，不承担实例定位职责。
> 3. **目标确定统一显式化**：查询筛选、更新目标、删除目标统一由 `conditions` 表达；`UPSERT` 的存在性判断由 `matchBy` 表达。。
> 4. **引用统一用 alias**：`conditions`、`returns`、`orders`、`relationships`、`linkQuery` 中的跨模块引用，统一使用 alias。
> 5. **未使用字段必须省略**：不允许输出 `null`、空对象、空数组作为占位。
> 6. **JSON 为唯一标准形态**：OQL DSL 的 canonical form 为 JSON；示例与执行入口均以 JSON 为准。

> **规范术语说明**：
>
> * **必须**：不满足即视为无效请求
> * **应**：推荐遵循；非特殊场景不应偏离
> * **可**：按场景选用

---

## 2.0 模块化阅读指引

| 模块        | 核心字段            | 作用                     | 适用操作                                                       |
| --------- | --------------- | ---------------------- | ---------------------------------------------------------- |
| 对象声明模块    | `objects`       | 声明参与本次操作的对象类型与别名       | 除 `BATCH` 外全部操作                                            |
| 关系路径模块    | `relationships` | 显式定义关系路径与别名            | `ASSOCIATION_QUERY`                                        |
| 条件模块      | `conditions`    | 统一定义过滤条件、目标确定与逻辑组合     | 查询、聚合、关联查询、更新、删除                                           |
| 投影模块      | `returns`       | 定义返回字段、分组字段、聚合指标       | `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `LINK_QUERY` |
| 排序模块      | `orders`        | 定义结果排序                 | 查询、聚合、关联查询、Link 查询                                         |
| 嵌套查询模块    | `sourceQuery`   | 用子查询结果作为当前层输入          | 查询、聚合、关联查询                                                 |
| Link 专用模块 | `linkQuery`     | 定义 Link 查询模式、方向和源/目标别名 | `LINK_QUERY`                                               |
| 写入模块      | `mutation`      | 定义创建、更新、删除、插入或更新、批处理   | `CREATE` / `UPDATE` / `DELETE` / `UPSERT` / `BATCH`        |

---

## 2.1 完整结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "<OPERATION>",

  "objects": [...],
  "relationships": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 1000,

  "sourceQuery": [...],

  "linkQuery": {...},
  "mutation": {...},

  "options": {...},
  "extensions": {...}
}
```

### 2.1.1 顶层字段顺序

为提升大模型生成稳定性，推荐固定以下顶层字段顺序：

```text
version
schemaRef
strict
operation
objects
relationships
conditions
returns
orders
maxResults
sourceQuery
linkQuery
mutation
options
extensions
```

> 建议生成顺序为：
>  `operation → objects → relationships/linkQuery → conditions → returns → orders → maxResults → sourceQuery → mutation`

### 2.1.2 Canonical 输出约束

1. 顶层必须包含 `version`、`schemaRef`、`operation`。
2. `strict` 缺省时默认视为 `true`。
3. 未使用字段必须省略；不得输出 `null`、`{}`、`[]` 作为占位。
4. 所有 alias 必须显式声明，不得依赖隐式默认值。
5. 所有字段名、对象类型名、关系类型名必须与 `schemaRef` 所指向的 schema 定义严格一致。
6. `returns` 不允许字符串数组简写；必须使用对象数组写法。
7. `FIELDS` 投影必须显式列出字段名；不允许使用 `*`。
8. `sourceQuery` 在 `strict=true` 时最大嵌套深度为 2。

---

## 2.2 完整语法结构元素说明

### 2.2.1 顶层字段

| 字段            | 类型          |   必填   | 说明                                                         |
| --------------- | ------------- | :------: | ------------------------------------------------------------ |
| `version`       | string        |    是    | DSL 版本。当前固定为 `1.0`                                   |
| `schemaRef`     | string        |    是    | 当前请求所绑定的 本体唯一schema 标识，对应 `ontologyid`      |
| `strict`        | boolean       |    否    | 是否启用严格校验。默认 `true`                                |
| `operation`     | enum          |    是    | 操作类型：`QUERY`、`AGGREGATE`、`ASSOCIATION_QUERY`、`LINK_QUERY`、`CREATE`、`UPDATE`、`DELETE`、`UPSERT`、`BATCH` |
| `objects`       | array<object> | 条件必填 | 参与对象声明数组。除 `BATCH` 外通常必填                      |
| `relationships` | array<object> | 条件必填 | 关系路径定义。仅 `ASSOCIATION_QUERY` 使用                    |
| `conditions`    | object        | 条件必填 | 统一条件表达式。查询可省略；`UPDATE` / `DELETE` 必填         |
| `returns`       | array<object> | 条件必填 | 返回字段、分组字段、聚合指标定义。查询类操作必填             |
| `orders`        | array<object> |    否    | 排序定义                                                     |
| `maxResults`    | integer       |    否    | 最大返回行数。默认 `1000`，最大 `100000`                     |
| `sourceQuery`   | array<object> |    否    | 子查询定义数组                                               |
| `linkQuery`     | object        | 条件必填 | `LINK_QUERY` 专用块                                          |
| `mutation`      | object        | 条件必填 | 写操作专用块                                                 |
| `options`       | object        |    否    | 执行选项                                                     |
| `extensions`    | object        |    否    | 扩展字段。非标准能力注入；无明确约定时应省略                 |

`schemaRef`：当前请求所绑定的本体 schema 标识。
 它用于确定本次请求可用的对象类型、关系类型、属性定义与物理映射规则。
 在具体实现中，`schemaRef` 可以对应 `ontologyId`、`schemaId` 或 `ontologyVersionId`，但在 OQL 语义层统一抽象为 `schemaRef`。



---

### 2.2.2 `objects`：统一对象声明

`objects` 只负责声明参与本次操作的对象类型与别名，不负责实例定位。

#### 字段定义

| 字段                     | 类型     |  必填 | 说明                                 |
| ---------------------- | ------ | :-: | ---------------------------------- |
| `objects[].objectType` | string |  是  | 对象类型标识符                            |
| `objects[].alias`      | string |  是  | 对象别名；必须在当前层级内唯一                    |
| `objects[].fromSource` | string |  否  | 绑定同层 `sourceQuery[].outputAs` 的结果集 |

#### 使用约束

1. `alias` 必须显式声明，推荐使用 `lower_snake_case`。
2. `fromSource` 仅可引用**同层** `sourceQuery[].outputAs`。
3. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 中，`objects` 长度必须为 `1`。
4. `LINK_QUERY` 中，`objects` 长度必须为 `2`，分别对应源对象与目标对象。
5. `BATCH` 顶层不使用 `objects`。

#### 示例

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

---

### 2.2.3 `relationships`：统一关系路径定义

`relationships` 用于 `ASSOCIATION_QUERY` 中显式声明关系路径。关系路径按数组顺序解释。

#### 字段定义

| 字段                                 | 类型     |  必填 | 说明              |
| ---------------------------------- | ------ | :-: | --------------- |
| `relationships[].relationshipType` | string |  是  | 关系类型标识符         |
| `relationships[].alias`            | string |  是  | 关系别名；必须在当前层级内唯一 |
| `relationships[].from`             | string |  是  | 源对象 alias       |
| `relationships[].to`               | string |  是  | 目标对象 alias      |

#### 使用约束

1. `from` / `to` 必须引用当前层 `objects[].alias`。
2. `relationships[].alias` 不得与任一 `objects[].alias` 重名。
3. 数组顺序即路径顺序；多跳关联按定义顺序执行。
4. `relationships` 仅用于 `ASSOCIATION_QUERY`；其他操作不得出现。

#### 示例

```json
{
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s"
    },
    {
      "relationshipType": "deployed_in",
      "alias": "r2",
      "from": "s",
      "to": "dc"
    }
  ]
}
```

---

### 2.2.4 `conditions`：统一条件表达式

`conditions` 采用**递归逻辑树**表达布尔条件。逻辑节点与叶子节点通过 `kind` 显式区分。

> 本节中的字段名均指对象 schema 中定义的逻辑字段名，不是物理表列名；物理列名绑定由 OAC 根据映射元数据完成。

#### 字段定义

| 字段                  | 类型          |   必填   | 说明                                                         |
| --------------------- | ------------- | :------: | ------------------------------------------------------------ |
| `conditions.kind`     | enum          |    是    | `GROUP` 或 `PREDICATE`                                       |
| `conditions.relation` | enum          | 条件必填 | `GROUP` 节点使用：`AND` / `OR` / `NOT`                       |
| `conditions.children` | array<object> | 条件必填 | `GROUP` 节点的子条件数组                                     |
| `conditions.ref`      | string        | 条件必填 | `PREDICATE` 节点引用的 alias，可为对象 alias 或关系 alias    |
| `conditions.field`    | string        | 条件必填 | 条件字段名                                                   |
| `conditions.operator` | enum          | 条件必填 | 比较操作符                                                   |
| `conditions.values`   | array<any>    | 条件必填 | `PREDICATE` 节点的比较值数组；对 `IS_NULL` / `IS_NOT_NULL` 不出现 |

#### 操作符定义

| 操作符                                            | `values` 取值规则 | 说明                              |
| ------------------------------------------------- | ----------------- | --------------------------------- |
| `EQ` / `NE`                                       | 恰好 1 个值       | 等于 / 不等于                     |
| `GT` / `GTE` / `LT` / `LTE`                       | 恰好 1 个值       | 大于 / 大于等于 / 小于 / 小于等于 |
| `IN` / `NOT_IN`                                   | 至少 1 个值       | 属于 / 不属于                     |
| `BETWEEN`                                         | 恰好 2 个值       | 区间                              |
| `LIKE` / `CONTAINS` / `STARTS_WITH` / `ENDS_WITH` | 恰好 1 个字符串值 | 字符串匹配                        |
| `IS_NULL` / `IS_NOT_NULL`                         | 不出现 `values`   | 空值判断                          |

#### 示例

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

---

### 2.2.5 `returns`：统一返回投影

`returns` 用于定义查询结果的投影方式，统一采用对象数组，不提供简写。

> 本节中的字段名均指对象 schema 中定义的逻辑字段名，不是物理表列名；物理列名绑定由 OAC 根据映射元数据完成。

#### 字段定义

| 字段                 | 类型          |   必填   | 说明                                                   |
| -------------------- | ------------- | :------: | ------------------------------------------------------ |
| `returns[].kind`     | enum          |    是    | `FIELDS` / `GROUP_BY` / `METRIC`                       |
| `returns[].ref`      | string        |    是    | 引用的 alias，可为对象 alias 或**关系 alias**          |
| `returns[].fields`   | array<string> | 条件必填 | `FIELDS` 使用，字段列表                                |
| `returns[].field`    | string        | 条件必填 | `GROUP_BY` / `METRIC` 使用，字段名                     |
| `returns[].function` | enum          | 条件必填 | `METRIC` 使用：`COUNT` / `SUM` / `AVG` / `MIN` / `MAX` |
| `returns[].alias`    | string        | 条件必填 | `GROUP_BY` / `METRIC` 使用，结果列名                   |

#### 使用约束

1. `FIELDS` 只能使用 `fields`，且字段必须显式列出。
2. `FIELDS.fields` 不允许出现 `*`。
3. `GROUP_BY` 与 `METRIC` 必须显式声明 `alias`。
4. `COUNT` 统计总行数时，`field` 可写为 `*`；除此之外，`field` 必须为显式字段名。

#### 示例

```json
{
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount", "status"]
    }
  ]
}
```

```json
{
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "o",
      "field": "region",
      "alias": "region"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "*",
      "function": "COUNT",
      "alias": "orderCount"
    }
  ]
}
```

---

### 2.2.6 `orders`：统一排序定义

> 本节中的字段名均指对象 schema 中定义的逻辑字段名，不是物理表列名；物理列名绑定由 OAC 根据映射元数据完成。

#### 字段定义

| 字段                   | 类型     |  必填 | 说明                                       |
| -------------------- | ------ | :-: | ---------------------------------------- |
| `orders[].ref`       | string |  是  | 排序所基于的 alias                             |
| `orders[].field`     | string |  是  | 排序字段；可为源字段，或当前结果集中已定义的 `returns[].alias` |
| `orders[].direction` | enum   |  是  | `ASC` / `DESC`                           |

> 当 `orders[].field` 引用聚合结果、分组别名或派生列时，应使用 `returns[].alias`；
>  当 `orders[].field` 引用原始对象字段时，应使用对象上的逻辑字段名。
>
> 例如：
>
> - `createdAt` 是对象字段
> - `totalAmount` 是 `METRIC.alias`

#### 示例

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

---

### 2.2.7 `sourceQuery`：嵌套查询定义

> `sourceQuery` 的语义是“定义当前层依赖的中间结果集”，而不是仅表示语法级子查询。
>  在 OAC 中，`sourceQuery` 可对应单源子查询、跨源逻辑子计划、或图查询前置结果集。

`sourceQuery` 允许在当前层中定义子查询，子查询结果可通过 `objects[].fromSource` 绑定为当前层输入。

#### 字段定义

| 字段                            | 类型            |  必填  | 说明                                                |
| ----------------------------- | ------------- | :--: | ------------------------------------------------- |
| `sourceQuery[].outputAs`      | string        |   是  | 子查询输出别名                                           |
| `sourceQuery[].operation`     | enum          |   是  | 子查询类型：`QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` |
| `sourceQuery[].objects`       | array<object> |   是  | 子查询对象声明                                           |
| `sourceQuery[].relationships` | array<object> | 条件必填 | 子查询为 `ASSOCIATION_QUERY` 时必填                      |
| `sourceQuery[].conditions`    | object        |   否  | 子查询条件                                             |
| `sourceQuery[].returns`       | array<object> |   是  | 子查询返回定义                                           |
| `sourceQuery[].orders`        | array<object> |   否  | 子查询排序                                             |
| `sourceQuery[].maxResults`    | integer       |   否  | 子查询最大返回数                                          |
| `sourceQuery[].sourceQuery`   | array<object> |   否  | 多层嵌套子查询                                           |

#### 使用约束

1. `outputAs` 在同层必须唯一。

2. `sourceQuery` 不允许引用外层 alias；即不支持相关子查询。

3. 在 `strict=true` 时，`sourceQuery` 最大嵌套深度为 `2`。

4. `sourceQuery` 只允许出现在查询类操作中；写操作中不得出现。

   > `sourceQuery` 仅用于生成可供外层消费的只读中间结果集，因此不支持写操作；
   >  `LINK_QUERY` 语义上属于一跳关系获取，通常应直接作为顶层查询使用，而不作为中间结果集定义。

---

### 2.2.8 `linkQuery`：Link 查询专用块

`LINK_QUERY` 用于通过一个关系类型，获取从源对象出发可达的目标对象。

#### 字段定义

| 字段                           | 类型     |  必填 | 说明                                                     |
| ---------------------------- | ------ | :-: | ------------------------------------------------------ |
| `linkQuery.mode`             | enum   |  是  | `LIST` / `ONE`                                         |
| `linkQuery.relationshipType` | string |  是  | Link 对应的关系类型                                           |
| `linkQuery.sourceRef`        | string |  是  | 源对象 alias                                              |
| `linkQuery.targetRef`        | string |  是  | 目标对象 alias                                             |
| `linkQuery.direction`        | enum   |  否  | `OUTBOUND` / `INBOUND` / `BIDIRECTIONAL`，默认 `OUTBOUND` |

#### 使用约束

1. `LINK_QUERY` 顶层 `objects` 必须声明且仅声明 2 个对象。
2. `sourceRef` / `targetRef` 必须引用 `objects[].alias`。
3. `mode = ONE` 时，结果必须恰好 1 条；否则返回错误。
4. `LINK_QUERY` 不使用 `relationships`。

---

### 2.2.9 `mutation`：写操作专用块

#### 字段定义

| 字段                         | 类型            |  必填  | 说明                                    |
| -------------------------- | ------------- | :--: | ------------------------------------- |
| `mutation.scope`           | enum          | 条件必填 | `UPDATE` / `DELETE` 使用：`ONE` / `MANY` |
| `mutation.data`            | object        | 条件必填 | `CREATE` / `UPSERT` 使用                |
| `mutation.data.properties` | object        | 条件必填 | 待创建或待插入/更新的属性键值                       |
| `mutation.set`             | object        | 条件必填 | `UPDATE` 使用，待更新字段键值                   |
| `mutation.matchBy`         | array<string> | 条件必填 | `UPSERT` 使用；用于判定是否已存在                 |
| `mutation.atomic`          | boolean       | 条件必填 | `BATCH` 使用；是否原子执行                     |
| `mutation.items`           | array<object> | 条件必填 | `BATCH` 使用；批处理子请求数组                   |

> ```
> BATCH.items[]` 仅允许 `CREATE` / `UPDATE` / `DELETE` / `UPSERT
> ```

#### 使用约束

1. `CREATE`：必须包含 `mutation.data.properties`；不得出现 `conditions`。
2. `UPDATE`：必须包含 `conditions`、`mutation.scope`、`mutation.set`。
3. `DELETE`：必须包含 `conditions`、`mutation.scope`。
4. `UPSERT`：必须包含 `mutation.matchBy` 与 `mutation.data.properties`；不得出现 `conditions`。
5. `BATCH`：必须包含 `mutation.atomic` 与非空 `mutation.items`。
6. `BATCH` 中的 `items[]` 使用与顶层相同的 canonical 结构，但不再包含 `version`、`schemaRef`、`strict`；这些值继承外层。
7. `BATCH` 的子项不得再使用 `BATCH`，即不允许嵌套批处理。

---

### 2.2.10 `options` 与 `extensions`

#### `options`

| 字段                       | 类型      |  必填 | 说明          |
| ------------------------ | ------- | :-: | ----------- |
| `options.timeoutMs`      | integer |  否  | 请求超时时间（毫秒）  |
| `options.dryRun`         | boolean |  否  | 是否只做校验不实际执行 |
| `options.returnMetadata` | boolean |  否  | 是否返回执行元数据   |

#### `extensions`

`extensions` 为保留扩展区，非存在明确契约时应省略。
在 `strict=true` 场景下，执行器可拒绝未约定的扩展字段。

---

### 2.2.11 值表达式

写入值除支持标量、数组外，还支持函数表达式对象。推荐写法如下：

```json
{
  "$fn": "now"
}
```

带参数的函数表达式：

```json
{
  "$fn": "coalesce",
  "args": ["customerName", "unknown"]
}
```

#### 使用约束

1. 函数表达式主要用于 `mutation.data.properties` 与 `mutation.set`。
2. `conditions.values` 应使用普通字面量值，不应使用函数表达式。

---

## 2.3 `conditions` - 统一条件表达式

`conditions` 统一表达查询筛选、更新目标与删除目标。
其结构为递归逻辑树，而非自由拼装对象。

### 2.3.1 叶子条件示例

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

### 2.3.2 组合条件示例

```json
{
  "conditions": {
    "kind": "GROUP",
    "relation": "OR",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "d",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      },
      {
        "kind": "GROUP",
        "relation": "AND",
        "children": [
          {
            "kind": "PREDICATE",
            "ref": "d",
            "field": "status",
            "operator": "EQ",
            "values": ["warning"]
          },
          {
            "kind": "PREDICATE",
            "ref": "d",
            "field": "alertLevel",
            "operator": "LTE",
            "values": [2]
          }
        ]
      }
    ]
  }
}
```

---

## 2.4 `returns` - 返回字段投影与聚合

### 2.4.1 普通投影

```json
{
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "p",
      "fields": ["id", "name", "price"]
    }
  ]
}
```

### 2.4.2 聚合投影

```json
{
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "o",
      "field": "region",
      "alias": "region"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    }
  ]
}
```

---

## 2.5 `orders` - 排序定义

```json
{
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    },
    {
      "ref": "o",
      "field": "orderNo",
      "direction": "ASC"
    }
  ]
}
```

---

## 2.6 `sourceQuery` - 嵌套查询

### 2.6.1 基本规则

1. `sourceQuery` 的结果通过 `outputAs` 暴露给当前层。
2. 当前层通过 `objects[].fromSource` 显式绑定子查询结果。
3. 外层对象如何从子查询获取数据，必须显式声明，不允许隐式推断。
4. `sourceQuery` 不支持引用外层 alias。

### 2.6.2 示例：单层嵌套查询

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
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
          "fields": ["id", "customerId", "region", "amount"]
        }
      ],
      "maxResults": 5000
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "co",
      "fields": ["id", "customerId", "region", "amount"]
    }
  ],
  "orders": [
    {
      "ref": "co",
      "field": "amount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

---

## 2.7 Operation 类型速查表

| 类型                  | 说明             | 专用字段 / 特征                                        | 使用场景       |
| ------------------- | -------------- | ------------------------------------------------ | ---------- |
| `QUERY`             | 单对象或多对象查询      | `objects` + `conditions` + `returns`             | 列表查询、联合查询  |
| `AGGREGATE`         | 分组与聚合          | `returns.kind = GROUP_BY / METRIC`               | 统计、分组汇总    |
| `ASSOCIATION_QUERY` | 显式关系路径查询       | `relationships`                                  | 多跳关联、图路径查询 |
| `LINK_QUERY`        | 基于单一关系类型获取关联对象 | `linkQuery`                                      | 一跳关联对象获取   |
| `CREATE`            | 创建单个对象         | `mutation.data.properties`                       | 新建对象       |
| `UPDATE`            | 更新对象           | `conditions` + `mutation.scope` + `mutation.set` | 单条或批量修改    |
| `DELETE`            | 删除对象           | `conditions` + `mutation.scope`                  | 单条或批量删除    |
| `UPSERT`            | 插入或更新          | `mutation.matchBy` + `mutation.data.properties`  | 依据唯一键插入或更新 |
| `BATCH`             | 批量执行多个子请求      | `mutation.atomic` + `mutation.items`             | 组合事务、批处理   |

---

## 2.8 选择操作类型的决策树

```text
开始
  │
  ├─ 需要读取数据？
  │     │
  │     ├─ 需要显式关系路径或多跳查询？
  │     │     └─ ASSOCIATION_QUERY
  │     │
  │     ├─ 需要通过单一关系类型获取关联对象？
  │     │     └─ LINK_QUERY
  │     │
  │     ├─ 需要统计、分组或聚合？
  │     │     └─ AGGREGATE
  │     │
  │     └─ 普通对象查询
  │           └─ QUERY
  │
  └─ 需要修改数据？
        │
        ├─ 新建单个对象 → CREATE
        ├─ 按条件修改 → UPDATE
        ├─ 按条件删除 → DELETE
        ├─ 按匹配键存在则更新否则创建 → UPSERT
        └─ 组合多个操作 → BATCH
```

---

## 2.9 统一结构模板速查

### 2.9.1 QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "FIELDS", "ref": "x", "fields": ["id", "name"] }
  ],
  "orders": [
    { "ref": "x", "field": "createdAt", "direction": "DESC" }
  ],
  "maxResults": 1000
}
```

### 2.9.2 AGGREGATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "GROUP_BY", "ref": "x", "field": "category", "alias": "category" },
    { "kind": "METRIC", "ref": "x", "field": "amount", "function": "SUM", "alias": "totalAmount" }
  ],
  "orders": [
    { "ref": "x", "field": "totalAmount", "direction": "DESC" }
  ],
  "maxResults": 1000
}
```

### 2.9.3 ASSOCIATION_QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    { "objectType": "A", "alias": "a" },
    { "objectType": "B", "alias": "b" }
  ],
  "relationships": [
    { "relationshipType": "rel_ab", "alias": "r1", "from": "a", "to": "b" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "FIELDS", "ref": "a", "fields": ["id", "name"] },
    { "kind": "FIELDS", "ref": "b", "fields": ["id", "name"] }
  ],
  "maxResults": 1000
}
```

### 2.9.4 LINK_QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    { "objectType": "A", "alias": "a" },
    { "objectType": "B", "alias": "b" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "FIELDS", "ref": "b", "fields": ["id", "name"] }
  ],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "rel_ab",
    "sourceRef": "a",
    "targetRef": "b",
    "direction": "OUTBOUND"
  },
  "maxResults": 1000
}
```

### 2.9.5 CREATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "mutation": {
    "data": {
      "properties": {
        "name": "value"
      }
    }
  }
}
```

### 2.9.6 UPDATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "mutation": {
    "scope": "ONE",
    "set": {
      "name": "newValue"
    }
  }
}
```

### 2.9.7 DELETE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "DELETE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "mutation": {
    "scope": "ONE"
  }
}
```

### 2.9.8 UPSERT 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPSERT",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "mutation": {
    "matchBy": ["key1", "key2"],
    "data": {
      "properties": {
        "key1": "v1",
        "key2": "v2",
        "name": "value"
      }
    }
  }
}
```

### 2.9.9 BATCH 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
        "objects": [
          { "objectType": "X", "alias": "x" }
        ],
        "conditions": { "...": "..." },
        "mutation": {
          "scope": "ONE",
          "set": {
            "status": "done"
          }
        }
      }
    ]
  }
}
```

---

## 2.10 请求示例

### 2.10.1 查询请求

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
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
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount", "status", "customerName", "createdAt"]
    }
  ],
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    }
  ],
  "maxResults": 10000
}
```

### 2.10.2 无过滤条件查询（查询全部对象）

```json
{
  "version": "1.0",
  "schemaRef": "iam@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "User",
      "alias": "u"
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "u",
      "fields": ["id", "firstName", "lastName"]
    }
  ],
  "maxResults": 1000
}
```

> **说明**：
>
> * 省略 `conditions` 表示不限制过滤条件。
> * 实际返回仍受 `maxResults` 控制。

### 2.10.3 聚合请求

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
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
      "ref": "o",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "*",
      "function": "COUNT",
      "alias": "orderCount"
    }
  ],
  "orders": [
    {
      "ref": "o",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

### 2.10.4 关联查询请求（多跳路径）

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    },
    {
      "objectType": "Server",
      "alias": "s"
    },
    {
      "objectType": "DataCenter",
      "alias": "dc"
    }
  ],
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s"
    },
    {
      "relationshipType": "deployed_in",
      "alias": "r2",
      "from": "s",
      "to": "dc"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "d",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      },
      {
        "kind": "PREDICATE",
        "ref": "dc",
        "field": "region",
        "operator": "EQ",
        "values": ["华东"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["id", "name", "status"]
    },
    {
      "kind": "FIELDS",
      "ref": "s",
      "fields": ["id", "hostname"]
    },
    {
      "kind": "FIELDS",
      "ref": "dc",
      "fields": ["id", "name", "region"]
    }
  ],
  "maxResults": 5000
}
```

### 2.10.5 Link 查询请求

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "LINK_QUERY",
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
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "orderNo",
    "operator": "EQ",
    "values": ["ORD-20240301-001"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "i",
      "fields": ["id", "invoiceNo", "amount", "status"]
    }
  ],
  "linkQuery": {
    "mode": "ONE",
    "relationshipType": "has_invoice",
    "sourceRef": "o",
    "targetRef": "i",
    "direction": "OUTBOUND"
  },
  "maxResults": 1
}
```

### 2.10.6 创建请求

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
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
        "price": 8999,
        "category": "phone",
        "createdAt": {
          "$fn": "now"
        }
      }
    }
  }
}
```

### 2.10.7 更新请求

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
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
      "price": 7999,
      "updatedAt": {
        "$fn": "now"
      }
    }
  }
}
```

### 2.10.8 删除请求

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
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
    "values": ["ORD-20240301-001"]
  },
  "mutation": {
    "scope": "ONE"
  }
}
```

### 2.10.9 插入或更新请求

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
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
        "orderNo": "ORD-20240301-001",
        "status": "shipped",
        "amount": 19999,
        "shippedAt": {
          "$fn": "now"
        }
      }
    }
  }
}
```

### 2.10.10 批处理请求

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
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
          "values": ["ORD-20240301-001"]
        },
        "mutation": {
          "scope": "ONE",
          "set": {
            "status": "paid",
            "paidAt": {
              "$fn": "now"
            }
          }
        }
      },
      {
        "operation": "CREATE",
        "objects": [
          {
            "objectType": "Invoice",
            "alias": "i"
          }
        ],
        "mutation": {
          "data": {
            "properties": {
              "invoiceNo": "INV-20240301-001",
              "orderNo": "ORD-20240301-001",
              "amount": 19999
            }
          }
        }
      }
    ]
  }
}
```

---

## 2.11 统一校验约束

以下约束适用于 OQL v1.0 的 canonical form：

1. `version`、`schemaRef`、`operation` 必须出现。
2. `objects[].alias` 必须在当前层级唯一。
3. `relationships[].alias` 必须在当前层级唯一，且不得与对象 alias 重名。
4. 所有 `ref` / `from` / `to` / `sourceRef` / `targetRef` 必须引用当前层已声明 alias。
5. `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `LINK_QUERY` 必须包含非空 `returns`。
6. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 顶层不得出现 `returns`、`orders`、`maxResults`、`sourceQuery`。
7. `UPDATE` / `DELETE` 必须包含 `conditions`；`CREATE` / `UPSERT` 不得包含 `conditions`。
8. `UPSERT` 必须声明 `mutation.matchBy`，且 `matchBy` 中字段必须同时出现在 `mutation.data.properties` 中。
9. `FIELDS.fields` 必须显式列出字段，且不允许 `*`。
10. `METRIC.function = COUNT` 时可使用 `field = "*"；其他函数不得使用 "*"。
11. `orders[].direction` 仅允许 `ASC` / `DESC`。
12. `maxResults` 取值范围为 `1` 到 `100000`。
13. `sourceQuery` 在 `strict=true` 时最大嵌套深度为 `2`。
14. `sourceQuery` 不允许引用外层 alias。
15. `BATCH.mutation.items` 必须非空，且子项 `operation` 不得为 `BATCH`。
16. `LINK_QUERY.mode = ONE` 时，若匹配结果不是恰好一条，应返回错误而非自动截断。
17. `strict=true` 时，执行器应拒绝未知字段、空对象、空数组与非法枚举值。
18. `extensions` 只有在调用方与执行器事先约定时才可使用。

---

## 2.12 响应格式

### 2.12.1 统一响应结构

```json
{
  "success": true,
  "operation": "<OPERATION>",
  "data": [...],
  "metadata": {
    "returnedCount": 0,
    "totalCount": 0,
    "truncated": false,
    "affectedCount": 0
  },
  "trace": {
    "executionTimeMs": 0,
    "requestId": "req_xxx"
  },
  "errors": [...]
}
```

### 2.12.2 响应字段说明

| 字段                       | 类型      | 说明                   |
| ------------------------ | ------- | -------------------- |
| `success`                | boolean | 是否执行成功               |
| `operation`              | string  | 本次执行的操作类型            |
| `data`                   | array   | 查询结果集；写操作通常可省略       |
| `metadata.returnedCount` | integer | 实际返回的结果行数，适用于查询类操作   |
| `metadata.totalCount`    | integer | 符合条件的总行数，可选          |
| `metadata.truncated`     | boolean | 是否因 `maxResults` 被截断 |
| `metadata.affectedCount` | integer | 受影响记录数，适用于写操作        |
| `trace.executionTimeMs`  | integer | 执行耗时（毫秒）             |
| `trace.requestId`        | string  | 请求标识，可选              |
| `errors`                 | array   | 失败时返回的错误列表           |

### 2.12.3 查询响应示例

对于 `FIELDS` 投影，结果行按 `ref` 分组返回：

```json
{
  "success": true,
  "operation": "QUERY",
  "data": [
    {
      "o": {
        "id": "order-001",
        "orderNo": "ORD-20240301-001",
        "amount": 1500,
        "status": "completed",
        "customerName": "张三",
        "createdAt": "2024-03-01T10:30:00Z"
      }
    }
  ],
  "metadata": {
    "returnedCount": 1,
    "totalCount": 156,
    "truncated": false
  },
  "trace": {
    "executionTimeMs": 25,
    "requestId": "req_001"
  }
}
```

### 2.12.4 聚合响应示例

对于 `GROUP_BY` / `METRIC`，结果行使用 `alias` 作为列名：

```json
{
  "success": true,
  "operation": "AGGREGATE",
  "data": [
    {
      "region": "华东",
      "totalAmount": 3500,
      "orderCount": 2
    },
    {
      "region": "华北",
      "totalAmount": 2200,
      "orderCount": 1
    }
  ],
  "metadata": {
    "returnedCount": 2,
    "totalCount": 2,
    "truncated": false
  },
  "trace": {
    "executionTimeMs": 18,
    "requestId": "req_002"
  }
}
```

### 2.12.5 写操作响应示例

```json
{
  "success": true,
  "operation": "UPDATE",
  "metadata": {
    "affectedCount": 1
  },
  "trace": {
    "executionTimeMs": 12,
    "requestId": "req_003"
  }
}
```

### 2.12.6 错误响应示例

```json
{
  "success": false,
  "operation": "LINK_QUERY",
  "errors": [
    {
      "code": "INVALID_RESULT_SIZE",
      "message": "linkQuery.mode = ONE requires exactly one result, but got 2."
    }
  ],
  "trace": {
    "executionTimeMs": 6,
    "requestId": "req_004"
  }
}
```

---

下面给出可直接续接在第 2 章后的**第 3～第 7 章正式规范文本**。
风格、术语、字段写法与上一版第 2 章保持一致，采用同一套 canonical 规则。

---

## 2.13 禁止事项

1. 不得使用未定义字段
2. 不得输出 `null` / `{}` / `[]` 占位
3. 不得使用字符串数组形式的 `returns`
4. 不得使用 `FIELDS.fields = ["*"]`
5. 不得在 `objects` 中表达对象定位
6. 不得在写操作中使用 `sourceQuery`
7. 不得在 `UPSERT` 中使用 `conditions`



# 3. QUERY - 对象查询

`QUERY` 用于执行单对象或多对象的数据查询。
其核心能力包括：

* 声明一个或多个参与对象
* 通过 `conditions` 统一表达筛选条件
* 通过 `returns` 定义返回字段
* 通过 `orders` 定义排序
* 通过 `sourceQuery` 引入子查询结果作为输入

> **说明**：
> `QUERY` 既可用于单对象查询，也可用于多对象联合查询；规范中不再单独定义 `MULTI_OBJECT_QUERY`。

---

## 3.1 适用场景

`QUERY` 适用于以下场景：

1. 查询某一对象类型的列表或明细
2. 在多个对象之间进行联合过滤与联合返回
3. 从子查询结果集中继续查询
4. 对普通对象记录做字段投影、排序和限制返回数量

不适用于以下场景：

1. 需要分组或聚合统计时，应使用 `AGGREGATE`
2. 需要显式定义关系路径时，应使用 `ASSOCIATION_QUERY`
3. 需要基于单一 LinkType 获取关联对象时，应使用 `LINK_QUERY`
4. 需要写入数据时，应使用第 7 章定义的写操作

---

## 3.2 结构定义

### 3.2.1 QUERY 顶层结构

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 1000,
  "sourceQuery": [...]
}
```

---

## 3.3 字段要求

| 字段            | 类型            |  必填 | 说明             |
| ------------- | ------------- | :-: | -------------- |
| `objects`     | array<object> |  是  | 参与查询的对象声明      |
| `conditions`  | object        |  否  | 查询条件；省略表示无过滤条件 |
| `returns`     | array<object> |  是  | 返回字段定义         |
| `orders`      | array<object> |  否  | 排序定义           |
| `maxResults`  | integer       |  否  | 最大返回行数         |
| `sourceQuery` | array<object> |  否  | 子查询定义          |

---

## 3.4 使用约束

1. `operation` 必须固定为 `QUERY`。
2. `objects` 必须非空。
3. `returns` 必须非空，且仅允许使用 `FIELDS`。
4. `QUERY` 中不得出现 `relationships`。
5. `QUERY` 中不得出现 `linkQuery`。
6. `QUERY` 中不得出现 `mutation`。
7. 省略 `conditions` 时，表示不加过滤条件。
8. 当 `objects` 长度大于 `1` 时，所有对象之间的联合语义必须通过 `conditions` 明确表达，不得依赖隐式连接。
9. 若某对象来自子查询结果，必须通过 `objects[].fromSource` 显式绑定。
10. `orders[].field` 可以是源字段，也可以是当前结果集中已返回字段；若排序字段未在返回集中，执行器可按实现决定是否支持。

---

## 3.5 单对象查询

单对象查询是最常见的 `QUERY` 形式。
此时 `objects` 中通常只声明一个对象别名，`conditions`、`returns`、`orders` 均围绕该对象展开。

### 3.5.1 示例：带过滤条件的单对象查询

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
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
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount", "status", "customerName", "createdAt"]
    }
  ],
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    }
  ],
  "maxResults": 10000
}
```

### 3.5.2 示例：无过滤条件查询全部对象

```json
{
  "version": "1.0",
  "schemaRef": "iam@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "User",
      "alias": "u"
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "u",
      "fields": ["id", "firstName", "lastName", "email"]
    }
  ],
  "orders": [
    {
      "ref": "u",
      "field": "lastName",
      "direction": "ASC"
    }
  ],
  "maxResults": 1000
}
```

---

## 3.6 多对象联合查询

`QUERY` 支持在同一请求中声明多个对象。
此时，联合过滤逻辑必须通过 `conditions` 显式表达。

> **注意**：
> 本规范不定义隐式 join。若多对象之间存在关联关系且需要路径语义，应优先使用 `ASSOCIATION_QUERY`。

### 3.6.1 示例：两个对象的联合筛选查询

```json
{
  "version": "1.0",
  "schemaRef": "crm@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    },
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "c",
        "field": "region",
        "operator": "EQ",
        "values": ["华东"]
      },
      {
        "kind": "PREDICATE",
        "ref": "o",
        "field": "status",
        "operator": "EQ",
        "values": ["completed"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "c",
      "fields": ["id", "name", "region"]
    },
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount", "status"]
    }
  ],
  "maxResults": 5000
}
```

---

## 3.7 sourceQuery 与 QUERY 组合使用

`QUERY` 可通过 `sourceQuery` 将子查询结果作为本层输入。
子查询结果必须通过 `outputAs` 暴露，并由本层 `objects[].fromSource` 绑定。

### 3.7.1 示例：从子查询结果继续查询

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
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
          "fields": ["id", "customerId", "region", "amount", "createdAt"]
        }
      ],
      "maxResults": 5000
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "co",
      "fields": ["id", "customerId", "region", "amount", "createdAt"]
    }
  ],
  "orders": [
    {
      "ref": "co",
      "field": "amount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

---

## 3.8 QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "FIELDS", "ref": "x", "fields": ["id", "name"] }
  ],
  "orders": [
    { "ref": "x", "field": "createdAt", "direction": "DESC" }
  ],
  "maxResults": 1000
}
```

---

# 4. AGGREGATE - 聚合查询

`AGGREGATE` 用于执行分组、统计与汇总计算。
其与 `QUERY` 的主要区别在于：`returns` 中允许使用 `GROUP_BY` 与 `METRIC`。

---

## 4.1 适用场景

`AGGREGATE` 适用于以下场景：

1. 按一个或多个维度分组统计
2. 对数值字段进行汇总、平均、最大值、最小值等计算
3. 对满足条件的对象记录进行行数统计
4. 基于子查询结果继续聚合

---

## 4.2 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 1000,
  "sourceQuery": [...]
}
```

---

## 4.3 字段要求

| 字段            | 类型            |  必填 | 说明          |
| ------------- | ------------- | :-: | ----------- |
| `objects`     | array<object> |  是  | 参与聚合的对象声明   |
| `conditions`  | object        |  否  | 聚合前过滤条件     |
| `returns`     | array<object> |  是  | 分组字段与聚合指标定义 |
| `orders`      | array<object> |  否  | 排序定义        |
| `maxResults`  | integer       |  否  | 最大返回分组数     |
| `sourceQuery` | array<object> |  否  | 子查询定义       |

---

## 4.4 使用约束

1. `operation` 必须固定为 `AGGREGATE`。
2. `returns` 必须非空。
3. `returns` 中至少包含一个 `METRIC`。
4. `returns` 中可包含零个、一个或多个 `GROUP_BY`。
5. `AGGREGATE` 中不得出现 `relationships`。
6. `AGGREGATE` 中不得出现 `linkQuery`。
7. `AGGREGATE` 中不得出现 `mutation`。
8. `returns.kind = FIELDS` 在 `AGGREGATE` 中不允许出现。
9. `orders[].field` 推荐引用 `returns[].alias`，尤其在按聚合结果排序时。
10. 当不存在 `GROUP_BY` 时，整个结果集视为单一分组，通常返回一行结果。

---

## 4.5 示例：按地区统计订单金额与数量

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
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
      "ref": "o",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "*",
      "function": "COUNT",
      "alias": "orderCount"
    }
  ],
  "orders": [
    {
      "ref": "o",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

---

## 4.6 示例：不分组的总量聚合

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
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
        "field": "createdAt",
        "operator": "GTE",
        "values": ["2026-01-01T00:00:00Z"]
      }
    ]
  },
  "returns": [
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "*",
      "function": "COUNT",
      "alias": "orderCount"
    },
    {
      "kind": "METRIC",
      "ref": "o",
      "field": "amount",
      "function": "AVG",
      "alias": "avgAmount"
    }
  ],
  "maxResults": 1
}
```

---

## 4.7 sourceQuery 与 AGGREGATE 组合使用

### 4.7.1 示例：先筛选订单，再对结果聚合

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
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
          "fields": ["id", "region", "amount"]
        }
      ],
      "maxResults": 10000
    }
  ],
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "co",
      "field": "region",
      "alias": "region"
    },
    {
      "kind": "METRIC",
      "ref": "co",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    }
  ],
  "orders": [
    {
      "ref": "co",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

---

## 4.8 AGGREGATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "GROUP_BY", "ref": "x", "field": "category", "alias": "category" },
    { "kind": "METRIC", "ref": "x", "field": "amount", "function": "SUM", "alias": "totalAmount" }
  ],
  "orders": [
    { "ref": "x", "field": "totalAmount", "direction": "DESC" }
  ],
  "maxResults": 1000
}
```

---

# 5. ASSOCIATION_QUERY - 显式关系路径查询

`ASSOCIATION_QUERY` 用于沿显式定义的关系路径执行对象关联查询。
其适用于**多跳关联、图路径遍历、路径两端对象联合返回**等场景。

---

## 5.1 适用场景

`ASSOCIATION_QUERY` 适用于以下场景：

1. 从一个对象经一跳或多跳关系找到其他对象
2. 需要显式声明路径上的关系类型
3. 需要同时返回路径上的对象与关系字段
4. 需要对路径起点、终点或中间节点进行联合筛选

不适用于以下场景：

1. 仅需要通过单一关系类型获取一跳目标对象时，应优先使用 `LINK_QUERY`
2. 不涉及路径语义的普通查询，应使用 `QUERY`
3. 仅做聚合统计时，应使用 `AGGREGATE`

---

## 5.2 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [...],
  "relationships": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 1000,
  "sourceQuery": [...]
}
```

---

## 5.3 字段要求

| 字段              | 类型            |  必填 | 说明             |
| --------------- | ------------- | :-: | -------------- |
| `objects`       | array<object> |  是  | 路径中参与的对象声明     |
| `relationships` | array<object> |  是  | 关系路径定义         |
| `conditions`    | object        |  否  | 对路径中对象或关系的过滤条件 |
| `returns`       | array<object> |  是  | 返回定义           |
| `orders`        | array<object> |  否  | 排序定义           |
| `maxResults`    | integer       |  否  | 最大返回路径数        |
| `sourceQuery`   | array<object> |  否  | 子查询定义          |

---

## 5.4 使用约束

1. `operation` 必须固定为 `ASSOCIATION_QUERY`。
2. `objects` 必须非空。
3. `relationships` 必须非空。
4. 每个 `relationships[i].from` 和 `relationships[i].to` 必须引用已声明对象 alias。
5. 多跳路径按 `relationships` 数组顺序解释。
6. `returns` 必须非空。
7. `returns` 中允许使用 `FIELDS`，引用对象 alias 或关系 alias。
8. `ASSOCIATION_QUERY` 中不得出现 `linkQuery`。
9. `ASSOCIATION_QUERY` 中不得出现 `mutation`。
10. 需要从子查询结果出发进行路径查询时，可使用 `sourceQuery + objects[].fromSource`。

---

## 5.5 示例：设备到数据中心的多跳路径查询

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    },
    {
      "objectType": "Server",
      "alias": "s"
    },
    {
      "objectType": "DataCenter",
      "alias": "dc"
    }
  ],
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s"
    },
    {
      "relationshipType": "deployed_in",
      "alias": "r2",
      "from": "s",
      "to": "dc"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "d",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      },
      {
        "kind": "PREDICATE",
        "ref": "dc",
        "field": "region",
        "operator": "EQ",
        "values": ["华东"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["id", "name", "status"]
    },
    {
      "kind": "FIELDS",
      "ref": "s",
      "fields": ["id", "hostname"]
    },
    {
      "kind": "FIELDS",
      "ref": "dc",
      "fields": ["id", "name", "region"]
    },
    {
      "kind": "FIELDS",
      "ref": "r1",
      "fields": ["relationshipType"]
    },
    {
      "kind": "FIELDS",
      "ref": "r2",
      "fields": ["relationshipType"]
    }
  ],
  "maxResults": 5000
}
```

---

## 5.6 示例：单跳关系查询

```json
{
  "version": "1.0",
  "schemaRef": "org@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Employee",
      "alias": "e"
    },
    {
      "objectType": "Department",
      "alias": "d"
    }
  ],
  "relationships": [
    {
      "relationshipType": "works_in",
      "alias": "r",
      "from": "e",
      "to": "d"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "d",
    "field": "name",
    "operator": "EQ",
    "values": ["研发部"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "e",
      "fields": ["id", "name", "employeeNo"]
    },
    {
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["id", "name"]
    }
  ],
  "orders": [
    {
      "ref": "e",
      "field": "employeeNo",
      "direction": "ASC"
    }
  ],
  "maxResults": 1000
}
```

---

## 5.7 ASSOCIATION_QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    { "objectType": "A", "alias": "a" },
    { "objectType": "B", "alias": "b" }
  ],
  "relationships": [
    { "relationshipType": "rel_ab", "alias": "r1", "from": "a", "to": "b" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "FIELDS", "ref": "a", "fields": ["id", "name"] },
    { "kind": "FIELDS", "ref": "b", "fields": ["id", "name"] },
    {
      "kind": "FIELDS",
      "ref": "r1",
      "fields": ["relationshipType"]
    }
  ],
  "maxResults": 1000
}
```

---

# 6. LINK_QUERY - 一跳关联对象查询

`LINK_QUERY` 用于基于单一关系类型，从一个源对象获取一跳关联的目标对象。
它适合“通过某个 LinkType 找到关联对象”的简洁场景。

---

## 6.1 适用场景

`LINK_QUERY` 适用于以下场景：

1. 从源对象出发，通过一个关系类型获取所有关联对象
2. 从源对象出发，通过一个关系类型获取唯一关联对象
3. 需要指定方向（入向、出向、双向）的一跳查询

当需要显式多跳路径时，应改用 `ASSOCIATION_QUERY`。

---

## 6.2 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [...],
  "conditions": {...},
  "returns": [...],
  "orders": [...],
  "maxResults": 1000,
  "linkQuery": {...}
}
```

---

## 6.3 字段要求

| 字段           | 类型            |  必填 | 说明                  |
| ------------ | ------------- | :-: | ------------------- |
| `objects`    | array<object> |  是  | 必须声明 2 个对象：源对象与目标对象 |
| `conditions` | object        |  是  | 用于确定源对象             |
| `returns`    | array<object> |  是  | 返回定义，通常面向目标对象       |
| `orders`     | array<object> |  否  | 排序定义                |
| `maxResults` | integer       |  否  | 最大返回数量              |
| `linkQuery`  | object        |  是  | Link 查询专用参数         |

---

## 6.4 使用约束

1. `operation` 必须固定为 `LINK_QUERY`。
2. `objects` 必须且仅能声明 2 个对象。
3. `conditions` 必须用于确定源对象；若 `sourceRef` 对应多条对象，执行器应按实现决定是否允许。
4. `linkQuery.sourceRef` 与 `linkQuery.targetRef` 必须引用已声明对象 alias。
5. `linkQuery.mode` 仅允许 `LIST` 或 `ONE`。
6. 当 `mode = ONE` 时，结果必须恰好一条；否则返回错误。
7. `LINK_QUERY` 中不得出现 `relationships`。
8. `LINK_QUERY` 中不得出现 `mutation`。

---

## 6.5 示例：获取订单关联的唯一发票

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "LINK_QUERY",
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
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "orderNo",
    "operator": "EQ",
    "values": ["ORD-20240301-001"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "i",
      "fields": ["id", "invoiceNo", "amount", "status"]
    }
  ],
  "linkQuery": {
    "mode": "ONE",
    "relationshipType": "has_invoice",
    "sourceRef": "o",
    "targetRef": "i",
    "direction": "OUTBOUND"
  },
  "maxResults": 1
}
```

---

## 6.6 示例：获取用户关联的全部设备

```json
{
  "version": "1.0",
  "schemaRef": "asset@1.0",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {
      "objectType": "User",
      "alias": "u"
    },
    {
      "objectType": "Device",
      "alias": "d"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "u",
    "field": "id",
    "operator": "EQ",
    "values": ["user_001"]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["id", "name", "deviceType", "status"]
    }
  ],
  "orders": [
    {
      "ref": "d",
      "field": "name",
      "direction": "ASC"
    }
  ],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "owns_device",
    "sourceRef": "u",
    "targetRef": "d",
    "direction": "OUTBOUND"
  },
  "maxResults": 1000
}
```

---

## 6.7 LINK_QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    { "objectType": "A", "alias": "a" },
    { "objectType": "B", "alias": "b" }
  ],
  "conditions": { "...": "..." },
  "returns": [
    { "kind": "FIELDS", "ref": "b", "fields": ["id", "name"] }
  ],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "rel_ab",
    "sourceRef": "a",
    "targetRef": "b",
    "direction": "OUTBOUND"
  },
  "maxResults": 1000
}
```

---

# 7. 写操作：CREATE / UPDATE / DELETE / UPSERT / BATCH

本章定义 OQL 的写入操作。
写操作统一使用 `mutation` 专用块，采用单一 canonical 写法。

---

## 7.1 设计原则

1. **对象只声明，不定位**：写操作中的目标对象由 `objects` 声明类型，由 `conditions` 或 `matchBy` 决定目标。
2. **更新与删除显式声明作用范围**：`UPDATE` 与 `DELETE` 必须通过 `mutation.scope` 标识是修改单条还是多条。
3. **UPSERT 使用匹配键**：`UPSERT` 必须通过 `mutation.matchBy` 明确存在性判断逻辑。
4. **批处理复用主语法**：`BATCH` 中每个子项继续使用相同 canonical 结构。

---

## 7.2 CREATE - 创建对象

`CREATE` 用于创建单个对象实例。

### 7.2.1 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "CREATE",
  "objects": [...],
  "mutation": {
    "data": {
      "properties": {...}
    }
  }
}
```

### 7.2.2 使用约束

1. `objects` 必须且仅能声明 1 个对象。
2. `mutation.data.properties` 必须非空。
3. `CREATE` 不得出现 `conditions`。
4. `CREATE` 不得出现 `returns`、`orders`、`maxResults`、`sourceQuery`、`relationships`、`linkQuery`。

### 7.2.3 示例

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
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
        "price": 8999,
        "category": "phone",
        "createdAt": {
          "$fn": "now"
        }
      }
    }
  }
}
```

---

## 7.3 UPDATE - 更新对象

`UPDATE` 用于按条件更新一个或多个对象。

### 7.3.1 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [...],
  "conditions": {...},
  "mutation": {
    "scope": "ONE",
    "set": {...}
  }
}
```

### 7.3.2 使用约束

1. `objects` 必须且仅能声明 1 个对象。
2. `conditions` 必须存在。
3. `mutation.scope` 必须为 `ONE` 或 `MANY`。
4. `mutation.set` 必须非空。
5. 当 `scope = ONE` 时，若条件匹配多条对象，执行器必须返回错误。
6. `UPDATE` 不得出现 `returns`、`orders`、`maxResults`、`sourceQuery`、`relationships`、`linkQuery`。

### 7.3.3 示例：单条更新

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
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
      "price": 7999,
      "updatedAt": {
        "$fn": "now"
      }
    }
  }
}
```

### 7.3.4 示例：批量更新

```json
{
  "version": "1.0",
  "schemaRef": "asset@1.0",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Device",
      "alias": "d"
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "d",
    "field": "status",
    "operator": "EQ",
    "values": ["warning"]
  },
  "mutation": {
    "scope": "MANY",
    "set": {
      "alertLevel": 2,
      "updatedAt": {
        "$fn": "now"
      }
    }
  }
}
```

---

## 7.4 DELETE - 删除对象

`DELETE` 用于按条件删除一个或多个对象。

### 7.4.1 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "DELETE",
  "objects": [...],
  "conditions": {...},
  "mutation": {
    "scope": "ONE"
  }
}
```

### 7.4.2 使用约束

1. `objects` 必须且仅能声明 1 个对象。
2. `conditions` 必须存在。
3. `mutation.scope` 必须为 `ONE` 或 `MANY`。
4. 当 `scope = ONE` 时，若条件匹配多条对象，执行器必须返回错误。
5. `DELETE` 不得出现 `mutation.set` 或 `mutation.data`。
6. `DELETE` 不得出现 `returns`、`orders`、`maxResults`、`sourceQuery`、`relationships`、`linkQuery`。

### 7.4.3 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
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
    "values": ["ORD-20240301-001"]
  },
  "mutation": {
    "scope": "ONE"
  }
}
```

---

## 7.5 UPSERT - 插入或更新对象

`UPSERT` 用于“存在则更新，不存在则创建”的写入场景。
其存在性判断由 `mutation.matchBy` 指定。

### 7.5.1 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPSERT",
  "objects": [...],
  "mutation": {
    "matchBy": [...],
    "data": {
      "properties": {...}
    }
  }
}
```

### 7.5.2 使用约束

1. `objects` 必须且仅能声明 1 个对象。
2. `mutation.matchBy` 必须非空。
3. `mutation.data.properties` 必须非空。
4. `matchBy` 中列出的字段必须全部出现在 `data.properties` 中。
5. `UPSERT` 不得出现 `conditions`。
6. `UPSERT` 不得出现 `returns`、`orders`、`maxResults`、`sourceQuery`、`relationships`、`linkQuery`。

### 7.5.3 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
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
        "orderNo": "ORD-20240301-001",
        "status": "shipped",
        "amount": 19999,
        "shippedAt": {
          "$fn": "now"
        }
      }
    }
  }
}
```

---

## 7.6 BATCH - 批处理

`BATCH` 用于在一次请求中组合多个子操作。
其子项继续复用本规范的 canonical 结构。

### 7.6.1 结构定义

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [...]
  }
}
```

### 7.6.2 使用约束

1. 顶层 `operation` 必须固定为 `BATCH`。
2. 顶层不得出现 `objects`、`conditions`、`returns`、`orders`、`maxResults`、`relationships`、`linkQuery`、`sourceQuery`。
3. `mutation.atomic` 必须显式声明。
4. `mutation.items` 必须非空。
5. `items[]` 的每一项必须是一个合法的非 `BATCH` 子请求。
6. 子请求不再包含 `version`、`schemaRef`、`strict`；这些值继承外层。
7. 不允许嵌套 `BATCH`。

### 7.6.3 示例

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
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
          "values": ["ORD-20240301-001"]
        },
        "mutation": {
          "scope": "ONE",
          "set": {
            "status": "paid",
            "paidAt": {
              "$fn": "now"
            }
          }
        }
      },
      {
        "operation": "CREATE",
        "objects": [
          {
            "objectType": "Invoice",
            "alias": "i"
          }
        ],
        "mutation": {
          "data": {
            "properties": {
              "invoiceNo": "INV-20240301-001",
              "orderNo": "ORD-20240301-001",
              "amount": 19999
            }
          }
        }
      }
    ]
  }
}
```

---

## 7.7 写操作模板速查

### CREATE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "mutation": {
    "data": {
      "properties": {
        "name": "value"
      }
    }
  }
}
```

### UPDATE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "mutation": {
    "scope": "ONE",
    "set": {
      "name": "newValue"
    }
  }
}
```

### DELETE

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "DELETE",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "conditions": { "...": "..." },
  "mutation": {
    "scope": "ONE"
  }
}
```

### UPSERT

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPSERT",
  "objects": [
    { "objectType": "X", "alias": "x" }
  ],
  "mutation": {
    "matchBy": ["key1", "key2"],
    "data": {
      "properties": {
        "key1": "v1",
        "key2": "v2",
        "name": "value"
      }
    }
  }
}
```

### BATCH

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "CREATE",
        "objects": [
          { "objectType": "X", "alias": "x" }
        ],
        "mutation": {
          "data": {
            "properties": {
              "name": "value"
            }
          }
        }
      }
    ]
  }
}
```



---

# 8. 错误码与校验规则

本章定义 OQL DSL 的错误分类、错误码、校验阶段与标准错误响应结构。
其目标是：

1. 为调用方提供可预测、可处理的错误语义
2. 为大模型提供明确的失败边界，避免“猜测式修正”
3. 为执行器提供统一的校验与报错规范

---

## 8.1 错误处理原则

1. **先校验，后执行**：请求在进入执行阶段前，必须完成语法校验与语义校验。
2. **错误优先返回**：当请求不满足规范时，执行器必须返回错误，不得猜测用户意图并自动修正。
3. **错误信息结构化**：错误必须以标准错误对象返回，不得只返回自由文本。
4. **同一错误码表示同一类问题**：错误码语义必须稳定，不得同码多义。
5. **可校验错误优先前置**：凡可在请求接收阶段发现的问题，应在执行前报出。
6. **`strict=true` 时从严校验**：未知字段、空占位、非法枚举值、结构漂移均应直接报错。

---

## 8.2 校验阶段

OQL 请求的校验分为四个阶段：

### 8.2.1 第一阶段：结构校验（Structural Validation）

用于验证 JSON 结构是否满足 DSL 的基本形态，包括：

* 顶层字段是否合法
* 必填字段是否存在
* 字段类型是否正确
* 枚举值是否合法
* 判别结构是否满足 `kind` / `operation` / 专用块约束

若本阶段失败，必须返回 `VALIDATION_ERROR` 类错误。

---

### 8.2.2 第二阶段：引用校验（Reference Validation）

用于验证 DSL 内部引用是否一致，包括：

* `ref` 是否指向已声明 alias
* `from` / `to` 是否指向合法对象 alias
* `sourceRef` / `targetRef` 是否合法
* `fromSource` 是否引用当前层已定义的 `sourceQuery[].outputAs`
* `orders[].field` 若引用返回别名，是否存在对应 `returns[].alias`

若本阶段失败，必须返回 `REFERENCE_ERROR` 类错误。

---

### 8.2.3 第三阶段：语义校验（Semantic Validation）

用于验证请求的操作语义是否成立，包括：

* `operation` 与专用块是否匹配
* `QUERY` 是否错误包含 `mutation`
* `UPDATE` 是否缺少 `conditions`
* `UPSERT.matchBy` 字段是否出现在 `data.properties`
* `AGGREGATE` 是否至少包含一个 `METRIC`
* `LINK_QUERY.mode = ONE` 是否满足唯一性要求
* `scope = ONE` 的写操作是否匹配唯一对象

若本阶段失败，必须返回 `SEMANTIC_ERROR` 类错误。

---

### 8.2.4 第四阶段：执行期校验（Execution-time Validation）

用于验证请求在数据执行阶段是否成立，包括：

* 查询结果集大小是否满足 `ONE`
* 唯一约束是否冲突
* 目标对象是否不存在
* 写入字段类型是否与 schema 不匹配
* 外部依赖、存储层、事务、超时等运行期失败

若本阶段失败，必须返回 `EXECUTION_ERROR` 类错误。

---

## 8.3 标准错误响应结构

当请求失败时，执行器必须返回如下结构：

```json id="thxkzq"
{
  "success": false,
  "operation": "<OPERATION>",
  "errors": [
    {
      "code": "INVALID_FIELD",
      "category": "VALIDATION_ERROR",
      "message": "Unknown top-level field: query",
      "path": "$.query",
      "details": {
        "expected": [
          "version",
          "schemaRef",
          "strict",
          "operation",
          "objects",
          "relationships",
          "conditions",
          "returns",
          "orders",
          "maxResults",
          "sourceQuery",
          "linkQuery",
          "mutation",
          "options",
          "extensions"
        ],
        "actual": "query"
      }
    }
  ],
  "trace": {
    "executionTimeMs": 3,
    "requestId": "req_1001"
  }
}
```

---

## 8.4 错误对象字段定义

| 字段                  | 类型     |  必填 | 说明                |
| ------------------- | ------ | :-: | ----------------- |
| `errors[].code`     | string |  是  | 错误码               |
| `errors[].category` | enum   |  是  | 错误分类              |
| `errors[].message`  | string |  是  | 人类可读错误信息          |
| `errors[].path`     | string |  否  | 指向出错字段的 JSON Path |
| `errors[].details`  | object |  否  | 机器可处理的附加信息        |

### 8.4.1 `category` 枚举

| 值                  | 说明                             |
| ------------------ | ------------------------------ |
| `VALIDATION_ERROR` | 结构、类型、枚举、必填项错误                 |
| `REFERENCE_ERROR`  | alias、source、field alias 等引用错误 |
| `SEMANTIC_ERROR`   | 请求含义不成立或不符合操作规则                |
| `EXECUTION_ERROR`  | 执行阶段失败                         |
| `INTERNAL_ERROR`   | 执行器内部异常                        |

---

## 8.5 错误码定义

以下错误码为 OQL v1.0 规范保留错误码。
执行器应优先复用，不应任意自定义近义错误码。

---

### 8.5.1 结构校验错误（VALIDATION_ERROR）

| 错误码                        | 说明                         |
| -------------------------- | -------------------------- |
| `MISSING_REQUIRED_FIELD`   | 缺少必填字段                     |
| `INVALID_FIELD`            | 出现未知字段或不允许字段               |
| `INVALID_FIELD_TYPE`       | 字段类型错误                     |
| `INVALID_ENUM_VALUE`       | 枚举值非法                      |
| `EMPTY_OBJECT_NOT_ALLOWED` | 不允许出现空对象                   |
| `EMPTY_ARRAY_NOT_ALLOWED`  | 不允许出现空数组                   |
| `NULL_NOT_ALLOWED`         | 不允许出现 `null`               |
| `INVALID_TOP_LEVEL_ORDER`  | 顶层字段顺序不符合推荐顺序（仅作提示或严格模式错误） |
| `INVALID_KIND_COMBINATION` | 判别结构字段组合非法                 |
| `MAX_NESTING_EXCEEDED`     | `sourceQuery` 嵌套层数超限       |
| `INVALID_OPERATOR_VALUES`  | 操作符与 `values` 个数不匹配        |
| `INVALID_MAX_RESULTS`      | `maxResults` 取值非法          |

#### 示例：缺少必填字段

```json id="oe0tks"
{
  "success": false,
  "operation": "QUERY",
  "errors": [
    {
      "code": "MISSING_REQUIRED_FIELD",
      "category": "VALIDATION_ERROR",
      "message": "Missing required field: returns",
      "path": "$.returns"
    }
  ]
}
```

#### 示例：判别结构非法

```json id="dkn4ma"
{
  "success": false,
  "operation": "QUERY",
  "errors": [
    {
      "code": "INVALID_KIND_COMBINATION",
      "category": "VALIDATION_ERROR",
      "message": "PREDICATE node must contain ref, field, operator and values, and must not contain children.",
      "path": "$.conditions"
    }
  ]
}
```

---

### 8.5.2 引用校验错误（REFERENCE_ERROR）

| 错误码                             | 说明                                     |
| ------------------------------- | -------------------------------------- |
| `UNDECLARED_ALIAS`              | 引用了未声明 alias                           |
| `DUPLICATE_ALIAS`               | alias 重复声明                             |
| `INVALID_SOURCE_REFERENCE`      | `fromSource` 或 `outputAs` 引用非法         |
| `INVALID_RELATION_ENDPOINT`     | `relationships.from` / `to` 非法         |
| `INVALID_LINK_REFERENCE`        | `linkQuery.sourceRef` / `targetRef` 非法 |
| `INVALID_RETURN_REFERENCE`      | `returns.ref` 非法                       |
| `INVALID_ORDER_REFERENCE`       | `orders.ref` 非法                        |
| `INVALID_ORDER_FIELD_REFERENCE` | `orders.field` 引用了不存在的结果别名或非法字段        |

#### 示例：alias 未声明

```json id="i7n0tg"
{
  "success": false,
  "operation": "AGGREGATE",
  "errors": [
    {
      "code": "UNDECLARED_ALIAS",
      "category": "REFERENCE_ERROR",
      "message": "Reference alias 'x' is not declared in current scope.",
      "path": "$.returns[0].ref",
      "details": {
        "actual": "x"
      }
    }
  ]
}
```

---

### 8.5.3 语义校验错误（SEMANTIC_ERROR）

| 错误码                        | 说明                                   |
| -------------------------- | ------------------------------------ |
| `INVALID_OPERATION_BLOCK`  | operation 与专用块不匹配                    |
| `INVALID_OPERATION_FIELD`  | 当前 operation 不允许出现某字段                |
| `INVALID_OBJECT_COUNT`     | 当前 operation 的 `objects` 数量非法        |
| `MISSING_CONDITIONS`       | 当前 operation 必须提供 `conditions`       |
| `CONDITIONS_NOT_ALLOWED`   | 当前 operation 不允许提供 `conditions`      |
| `INVALID_RETURNS_KIND`     | 当前 operation 不允许某类 `returns.kind`    |
| `MISSING_METRIC`           | `AGGREGATE` 缺少 `METRIC`              |
| `INVALID_SCOPE`            | `scope` 值不合法或与操作不匹配                  |
| `INVALID_MATCH_BY`         | `matchBy` 非法                         |
| `MATCH_BY_FIELD_MISSING`   | `matchBy` 字段未出现在 `data.properties` 中 |
| `BATCH_ITEM_INVALID`       | `BATCH` 子项非法                         |
| `NESTED_BATCH_NOT_ALLOWED` | 不允许嵌套 `BATCH`                        |
| `SOURCE_QUERY_NOT_ALLOWED` | 当前 operation 不允许 `sourceQuery`       |
| `RETURNS_REQUIRED`         | 查询类操作缺少 `returns`                    |

#### 示例：UPDATE 缺少 conditions

```json id="lfsdnw"
{
  "success": false,
  "operation": "UPDATE",
  "errors": [
    {
      "code": "MISSING_CONDITIONS",
      "category": "SEMANTIC_ERROR",
      "message": "UPDATE requires conditions.",
      "path": "$.conditions"
    }
  ]
}
```

#### 示例：UPSERT 的 matchBy 非法

```json id="xn3lto"
{
  "success": false,
  "operation": "UPSERT",
  "errors": [
    {
      "code": "MATCH_BY_FIELD_MISSING",
      "category": "SEMANTIC_ERROR",
      "message": "All fields in matchBy must appear in mutation.data.properties.",
      "path": "$.mutation.matchBy",
      "details": {
        "missingFields": ["orderNo"]
      }
    }
  ]
}
```

---

### 8.5.4 执行期错误（EXECUTION_ERROR）

| 错误码                             | 说明                |
| ------------------------------- | ----------------- |
| `OBJECT_NOT_FOUND`              | 目标对象不存在           |
| `NON_UNIQUE_RESULT`             | 期望唯一结果却匹配多条       |
| `NO_RESULT`                     | 期望唯一结果却没有匹配       |
| `RESULT_SIZE_MISMATCH`          | 结果数量不满足操作要求       |
| `UNIQUE_CONSTRAINT_VIOLATION`   | 唯一约束冲突            |
| `FIELD_TYPE_MISMATCH`           | 字段值类型与 schema 不匹配 |
| `FIELD_NOT_DEFINED`             | 字段在 schema 中不存在   |
| `OBJECT_TYPE_NOT_DEFINED`       | 对象类型在 schema 中不存在 |
| `RELATIONSHIP_TYPE_NOT_DEFINED` | 关系类型在 schema 中不存在 |
| `WRITE_CONFLICT`                | 并发写冲突             |
| `TRANSACTION_ABORTED`           | 事务失败              |
| `TIMEOUT`                       | 执行超时              |
| `PERMISSION_DENIED`             | 权限不足              |
| `BACKEND_UNAVAILABLE`           | 后端不可用             |

#### 示例：scope = ONE 但匹配多条

```json id="a5xiok"
{
  "success": false,
  "operation": "DELETE",
  "errors": [
    {
      "code": "NON_UNIQUE_RESULT",
      "category": "EXECUTION_ERROR",
      "message": "DELETE with scope=ONE matched 3 objects.",
      "path": "$.mutation.scope",
      "details": {
        "scope": "ONE",
        "matchedCount": 3
      }
    }
  ]
}
```

#### 示例：LINK_QUERY mode = ONE 但无结果

```json id="3npl7d"
{
  "success": false,
  "operation": "LINK_QUERY",
  "errors": [
    {
      "code": "NO_RESULT",
      "category": "EXECUTION_ERROR",
      "message": "linkQuery.mode = ONE requires exactly one result, but got 0.",
      "path": "$.linkQuery.mode"
    }
  ]
}
```

---

### 8.5.5 内部错误（INTERNAL_ERROR）

| 错误码                   | 说明          |
| --------------------- | ----------- |
| `INTERNAL_ERROR`      | 未分类内部错误     |
| `SERIALIZATION_ERROR` | 序列化或反序列化失败  |
| `SCHEMA_LOAD_FAILED`  | schema 加载失败 |
| `PLANNER_ERROR`       | 执行计划生成失败    |

#### 示例

```json id="f0i7of"
{
  "success": false,
  "operation": "QUERY",
  "errors": [
    {
      "code": "SCHEMA_LOAD_FAILED",
      "category": "INTERNAL_ERROR",
      "message": "Failed to load schema: sales@1.0"
    }
  ]
}
```

---

## 8.6 严格模式校验规则

当 `strict = true` 时，执行器必须启用以下附加规则：

1. 拒绝未知字段
2. 拒绝 `null`
3. 拒绝空对象 `{}`
4. 拒绝空数组 `[]`
5. 拒绝未使用但仍输出的专用块
6. 拒绝字符串数组形式的 `returns` 简写
7. 拒绝 `FIELDS.fields = ["*"]`
8. 拒绝不在 schema 中定义的对象类型、关系类型、字段名
9. 拒绝超出规范嵌套深度的 `sourceQuery`
10. 可将顶层字段顺序错误视为 `INVALID_TOP_LEVEL_ORDER`

---

## 8.7 建议的校验顺序

执行器应按如下顺序校验请求：

1. 顶层结构与字段类型
2. operation 与专用块合法性
3. `objects` / `relationships` / `sourceQuery` 的基础结构
4. alias 与内部引用
5. `conditions` / `returns` / `orders` 的判别结构
6. operation 特定语义约束
7. schema 对象类型、关系类型、字段合法性
8. 执行阶段唯一性、存在性、事务性校验

> **说明**：
> 若同一请求包含多个错误，执行器可选择：
>
> * 返回首个错误；或
> * 返回同阶段内多个错误
>
> 但不应混合返回跨阶段的大量错误，避免噪音。

---

## 8.8 面向大模型的错误响应建议

为便于大模型自动修正 DSL，建议在 `details` 中尽可能提供：

* `expected`
* `actual`
* `allowedValues`
* `missingFields`
* `matchedCount`
* `requiredKind`
* `declaredAliases`

例如：

```json id="9marwj"
{
  "success": false,
  "operation": "QUERY",
  "errors": [
    {
      "code": "INVALID_ENUM_VALUE",
      "category": "VALIDATION_ERROR",
      "message": "Invalid value for orders[0].direction.",
      "path": "$.orders[0].direction",
      "details": {
        "expected": ["ASC", "DESC"],
        "actual": "DOWN"
      }
    }
  ]
}
```

---

# 附录 A：JSON Schema / EBNF 形式化定义

本附录提供 OQL v1.0 canonical form 的两种形式化描述：

1. **JSON Schema（简化规范版）**：用于工程校验、约束解码、结构验证
2. **EBNF（抽象语法版）**：用于阅读、编译器实现与文档说明

> **说明**：
> 以下 JSON Schema 为规范参考实现，不要求所有执行器逐字采用，但应保证等价约束。
> 若工程实现中采用 Pydantic、Avro、Protocol Buffers 或其他形式化工具，其约束效果应与本附录等价。

---

## A.1 JSON Schema（简化规范版）

下面给出一版适合文档展示的简化 JSON Schema。
其目标是清晰表达主约束，而非穷尽实现细节。

```json id="k4saih"
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/oql/v1.0/schema.json",
  "title": "OQL Canonical DSL v1.0",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "schemaRef", "operation"],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0"
    },
    "schemaRef": {
      "type": "string",
      "minLength": 1
    },
    "strict": {
      "type": "boolean",
      "default": true
    },
    "operation": {
      "type": "string",
      "enum": [
        "QUERY",
        "AGGREGATE",
        "ASSOCIATION_QUERY",
        "LINK_QUERY",
        "CREATE",
        "UPDATE",
        "DELETE",
        "UPSERT",
        "BATCH"
      ]
    },
    "objects": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/objectDecl" }
    },
    "relationships": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/relationshipDecl" }
    },
    "conditions": {
      "$ref": "#/$defs/conditionNode"
    },
    "returns": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/returnNode" }
    },
    "orders": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/orderNode" }
    },
    "maxResults": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100000
    },
    "sourceQuery": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/sourceQueryNode" }
    },
    "linkQuery": {
      "$ref": "#/$defs/linkQueryNode"
    },
    "mutation": {
      "$ref": "#/$defs/mutationNode"
    },
    "options": {
      "$ref": "#/$defs/optionsNode"
    },
    "extensions": {
      "type": "object"
    }
  },
  "$defs": {
    "objectDecl": {
      "type": "object",
      "additionalProperties": false,
      "required": ["objectType", "alias"],
      "properties": {
        "objectType": {
          "type": "string",
          "minLength": 1
        },
        "alias": {
          "type": "string",
          "minLength": 1
        },
        "fromSource": {
          "type": "string",
          "minLength": 1
        }
      }
    },

    "relationshipDecl": {
      "type": "object",
      "additionalProperties": false,
      "required": ["relationshipType", "alias", "from", "to"],
      "properties": {
        "relationshipType": {
          "type": "string",
          "minLength": 1
        },
        "alias": {
          "type": "string",
          "minLength": 1
        },
        "from": {
          "type": "string",
          "minLength": 1
        },
        "to": {
          "type": "string",
          "minLength": 1
        }
      }
    },

    "conditionNode": {
      "oneOf": [
        { "$ref": "#/$defs/conditionGroup" },
        { "$ref": "#/$defs/conditionPredicate" }
      ]
    },

    "conditionGroup": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "relation", "children"],
      "properties": {
        "kind": {
          "type": "string",
          "const": "GROUP"
        },
        "relation": {
          "type": "string",
          "enum": ["AND", "OR", "NOT"]
        },
        "children": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/conditionNode" }
        }
      }
    },

    "conditionPredicate": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "ref", "field", "operator"],
      "properties": {
        "kind": {
          "type": "string",
          "const": "PREDICATE"
        },
        "ref": {
          "type": "string",
          "minLength": 1
        },
        "field": {
          "type": "string",
          "minLength": 1
        },
        "operator": {
          "type": "string",
          "enum": [
            "EQ", "NE", "GT", "GTE", "LT", "LTE",
            "IN", "NOT_IN", "BETWEEN",
            "LIKE", "CONTAINS", "STARTS_WITH", "ENDS_WITH",
            "IS_NULL", "IS_NOT_NULL"
          ]
        },
        "values": {
          "type": "array",
          "items": {}
        }
      }
    },

    "returnNode": {
      "oneOf": [
        { "$ref": "#/$defs/returnFields" },
        { "$ref": "#/$defs/returnGroupBy" },
        { "$ref": "#/$defs/returnMetric" }
      ]
    },

    "returnFields": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "ref", "fields"],
      "properties": {
        "kind": {
          "type": "string",
          "const": "FIELDS"
        },
        "ref": {
          "type": "string",
          "minLength": 1
        },
        "fields": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string",
            "minLength": 1
          }
        }
      }
    },

    "returnGroupBy": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "ref", "field", "alias"],
      "properties": {
        "kind": {
          "type": "string",
          "const": "GROUP_BY"
        },
        "ref": {
          "type": "string",
          "minLength": 1
        },
        "field": {
          "type": "string",
          "minLength": 1
        },
        "alias": {
          "type": "string",
          "minLength": 1
        }
      }
    },

    "returnMetric": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "ref", "field", "function", "alias"],
      "properties": {
        "kind": {
          "type": "string",
          "const": "METRIC"
        },
        "ref": {
          "type": "string",
          "minLength": 1
        },
        "field": {
          "type": "string",
          "minLength": 1
        },
        "function": {
          "type": "string",
          "enum": ["COUNT", "SUM", "AVG", "MIN", "MAX"]
        },
        "alias": {
          "type": "string",
          "minLength": 1
        }
      }
    },

    "orderNode": {
      "type": "object",
      "additionalProperties": false,
      "required": ["ref", "field", "direction"],
      "properties": {
        "ref": {
          "type": "string",
          "minLength": 1
        },
        "field": {
          "type": "string",
          "minLength": 1
        },
        "direction": {
          "type": "string",
          "enum": ["ASC", "DESC"]
        }
      }
    },

    "sourceQueryNode": {
      "type": "object",
      "additionalProperties": false,
      "required": ["outputAs", "operation", "objects", "returns"],
      "properties": {
        "outputAs": {
          "type": "string",
          "minLength": 1
        },
        "operation": {
          "type": "string",
          "enum": ["QUERY", "AGGREGATE", "ASSOCIATION_QUERY"]
        },
        "objects": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/objectDecl" }
        },
        "relationships": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/relationshipDecl" }
        },
        "conditions": {
          "$ref": "#/$defs/conditionNode"
        },
        "returns": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/returnNode" }
        },
        "orders": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/orderNode" }
        },
        "maxResults": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100000
        },
        "sourceQuery": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/sourceQueryNode" }
        }
      }
    },

    "linkQueryNode": {
      "type": "object",
      "additionalProperties": false,
      "required": ["mode", "relationshipType", "sourceRef", "targetRef"],
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["LIST", "ONE"]
        },
        "relationshipType": {
          "type": "string",
          "minLength": 1
        },
        "sourceRef": {
          "type": "string",
          "minLength": 1
        },
        "targetRef": {
          "type": "string",
          "minLength": 1
        },
        "direction": {
          "type": "string",
          "enum": ["OUTBOUND", "INBOUND", "BIDIRECTIONAL"]
        }
      }
    },

    "functionExpr": {
      "type": "object",
      "additionalProperties": false,
      "required": ["$fn"],
      "properties": {
        "$fn": {
          "type": "string",
          "minLength": 1
        },
        "args": {
          "type": "array",
          "items": {}
        }
      }
    },

    "valueExpr": {
      "oneOf": [
        { "type": "string" },
        { "type": "number" },
        { "type": "integer" },
        { "type": "boolean" },
        {
          "type": "array",
          "items": {}
        },
        { "$ref": "#/$defs/functionExpr" }
      ]
    },

    "propertiesMap": {
      "type": "object",
      "additionalProperties": { "$ref": "#/$defs/valueExpr" }
    },

    "mutationCreate": {
      "type": "object",
      "additionalProperties": false,
      "required": ["data"],
      "properties": {
        "data": {
          "type": "object",
          "additionalProperties": false,
          "required": ["properties"],
          "properties": {
            "properties": { "$ref": "#/$defs/propertiesMap" }
          }
        }
      }
    },

    "mutationUpdate": {
      "type": "object",
      "additionalProperties": false,
      "required": ["scope", "set"],
      "properties": {
        "scope": {
          "type": "string",
          "enum": ["ONE", "MANY"]
        },
        "set": {
          "$ref": "#/$defs/propertiesMap"
        }
      }
    },

    "mutationDelete": {
      "type": "object",
      "additionalProperties": false,
      "required": ["scope"],
      "properties": {
        "scope": {
          "type": "string",
          "enum": ["ONE", "MANY"]
        }
      }
    },

    "mutationUpsert": {
      "type": "object",
      "additionalProperties": false,
      "required": ["matchBy", "data"],
      "properties": {
        "matchBy": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "data": {
          "type": "object",
          "additionalProperties": false,
          "required": ["properties"],
          "properties": {
            "properties": { "$ref": "#/$defs/propertiesMap" }
          }
        }
      }
    },

    "batchItem": {
      "type": "object",
      "additionalProperties": false,
      "required": ["operation"],
      "properties": {
        "operation": {
          "type": "string",
          "enum": [
            "CREATE",
            "UPDATE",
            "DELETE",
            "UPSERT",
            "QUERY",
            "AGGREGATE",
            "ASSOCIATION_QUERY",
            "LINK_QUERY"
          ]
        },
        "objects": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/objectDecl" }
        },
        "relationships": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/relationshipDecl" }
        },
        "conditions": {
          "$ref": "#/$defs/conditionNode"
        },
        "returns": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/returnNode" }
        },
        "orders": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/orderNode" }
        },
        "maxResults": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100000
        },
        "linkQuery": {
          "$ref": "#/$defs/linkQueryNode"
        },
        "mutation": {
          "oneOf": [
            { "$ref": "#/$defs/mutationCreate" },
            { "$ref": "#/$defs/mutationUpdate" },
            { "$ref": "#/$defs/mutationDelete" },
            { "$ref": "#/$defs/mutationUpsert" }
          ]
        }
      }
    },

    "mutationBatch": {
      "type": "object",
      "additionalProperties": false,
      "required": ["atomic", "items"],
      "properties": {
        "atomic": {
          "type": "boolean"
        },
        "items": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/batchItem" }
        }
      }
    },

    "mutationNode": {
      "oneOf": [
        { "$ref": "#/$defs/mutationCreate" },
        { "$ref": "#/$defs/mutationUpdate" },
        { "$ref": "#/$defs/mutationDelete" },
        { "$ref": "#/$defs/mutationUpsert" },
        { "$ref": "#/$defs/mutationBatch" }
      ]
    },

    "optionsNode": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "timeoutMs": {
          "type": "integer",
          "minimum": 1
        },
        "dryRun": {
          "type": "boolean"
        },
        "returnMetadata": {
          "type": "boolean"
        }
      }
    }
  }
}
```

---

## A.2 JSON Schema 的操作级约束说明

由于 JSON Schema 难以完整表达所有跨字段语义，以下约束应由执行器或更高层校验器补充实现：

1. `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `LINK_QUERY` 必须包含 `returns`
2. `CREATE` / `UPSERT` 不允许 `conditions`
3. `UPDATE` / `DELETE` 必须包含 `conditions`
4. `QUERY` 的 `returns.kind` 只能为 `FIELDS`
5. `AGGREGATE` 必须至少包含一个 `METRIC`
6. `ASSOCIATION_QUERY` 必须包含 `relationships`
7. `LINK_QUERY` 必须包含 `linkQuery` 且 `objects.length = 2`
8. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 顶层 `objects.length = 1`
9. `BATCH` 顶层不得出现 `objects` / `conditions` / `returns` / `orders` / `relationships` / `linkQuery` / `sourceQuery`
10. `sourceQuery` 最大嵌套深度为 2（在 `strict=true` 时）
11. `matchBy` 中字段必须出现在 `mutation.data.properties` 中
12. 所有 alias 引用必须在当前层有效
13. `scope = ONE` 与 `linkQuery.mode = ONE` 的唯一性，需要在执行期校验

---

## A.3 EBNF（抽象语法定义）

以下 EBNF 用于表达 OQL 的抽象语法结构。
其中 JSON 细节被抽象为语法节点，而非逐字符定义。

```text id="n2n78y"
OQLDocument
  = QueryDoc
  | AggregateDoc
  | AssociationQueryDoc
  | LinkQueryDoc
  | CreateDoc
  | UpdateDoc
  | DeleteDoc
  | UpsertDoc
  | BatchDoc
  ;

CommonHeader
  = "version" ":" "1.0"
    "," "schemaRef" ":" String
    [ "," "strict" ":" Boolean ]
  ;

QueryDoc
  = "{"
      CommonHeader
      "," "operation" ":" "QUERY"
      "," "objects" ":" ObjectDeclList
      [ "," "conditions" ":" ConditionNode ]
      "," "returns" ":" ReturnFieldsList
      [ "," "orders" ":" OrderList ]
      [ "," "maxResults" ":" Integer ]
      [ "," "sourceQuery" ":" SourceQueryList ]
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

AggregateDoc
  = "{"
      CommonHeader
      "," "operation" ":" "AGGREGATE"
      "," "objects" ":" ObjectDeclList
      [ "," "conditions" ":" ConditionNode ]
      "," "returns" ":" ReturnAggregateList
      [ "," "orders" ":" OrderList ]
      [ "," "maxResults" ":" Integer ]
      [ "," "sourceQuery" ":" SourceQueryList ]
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

AssociationQueryDoc
  = "{"
      CommonHeader
      "," "operation" ":" "ASSOCIATION_QUERY"
      "," "objects" ":" ObjectDeclList
      "," "relationships" ":" RelationshipDeclList
      [ "," "conditions" ":" ConditionNode ]
      "," "returns" ":" ReturnFieldsList
      [ "," "orders" ":" OrderList ]
      [ "," "maxResults" ":" Integer ]
      [ "," "sourceQuery" ":" SourceQueryList ]
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

LinkQueryDoc
  = "{"
      CommonHeader
      "," "operation" ":" "LINK_QUERY"
      "," "objects" ":" ObjectDeclList
      "," "conditions" ":" ConditionNode
      "," "returns" ":" ReturnFieldsList
      "," "linkQuery" ":" LinkQueryBlock
      [ "," "orders" ":" OrderList ]
      [ "," "maxResults" ":" Integer ]
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

CreateDoc
  = "{"
      CommonHeader
      "," "operation" ":" "CREATE"
      "," "objects" ":" SingleObjectDeclList
      "," "mutation" ":" CreateMutation
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

UpdateDoc
  = "{"
      CommonHeader
      "," "operation" ":" "UPDATE"
      "," "objects" ":" SingleObjectDeclList
      "," "conditions" ":" ConditionNode
      "," "mutation" ":" UpdateMutation
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

DeleteDoc
  = "{"
      CommonHeader
      "," "operation" ":" "DELETE"
      "," "objects" ":" SingleObjectDeclList
      "," "conditions" ":" ConditionNode
      "," "mutation" ":" DeleteMutation
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

UpsertDoc
  = "{"
      CommonHeader
      "," "operation" ":" "UPSERT"
      "," "objects" ":" SingleObjectDeclList
      "," "mutation" ":" UpsertMutation
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

BatchDoc
  = "{"
      CommonHeader
      "," "operation" ":" "BATCH"
      "," "mutation" ":" BatchMutation
      [ "," "options" ":" Options ]
      [ "," "extensions" ":" Object ]
    "}"
  ;

ObjectDeclList = "[" ObjectDecl { "," ObjectDecl } "]" ;
SingleObjectDeclList = "[" ObjectDecl "]" ;

ObjectDecl
  = "{"
      "objectType" ":" String
      "," "alias" ":" String
      [ "," "fromSource" ":" String ]
    "}"
  ;

RelationshipDeclList = "[" RelationshipDecl { "," RelationshipDecl } "]" ;

RelationshipDecl
  = "{"
      "relationshipType" ":" String
      "," "alias" ":" String
      "," "from" ":" String
      "," "to" ":" String
    "}"
  ;

ConditionNode = ConditionGroup | ConditionPredicate ;

ConditionGroup
  = "{"
      "kind" ":" "GROUP"
      "," "relation" ":" ("AND" | "OR" | "NOT")
      "," "children" ":" "[" ConditionNode { "," ConditionNode } "]"
    "}"
  ;

ConditionPredicate
  = "{"
      "kind" ":" "PREDICATE"
      "," "ref" ":" String
      "," "field" ":" String
      "," "operator" ":" Operator
      [ "," "values" ":" "[" Value { "," Value } "]" ]
    "}"
  ;

Operator
  = "EQ" | "NE" | "GT" | "GTE" | "LT" | "LTE"
  | "IN" | "NOT_IN" | "BETWEEN"
  | "LIKE" | "CONTAINS" | "STARTS_WITH" | "ENDS_WITH"
  | "IS_NULL" | "IS_NOT_NULL"
  ;

ReturnFieldsList = "[" ReturnFields { "," ReturnFields } "]" ;
ReturnAggregateList = "[" (ReturnGroupBy | ReturnMetric) { "," (ReturnGroupBy | ReturnMetric) } "]" ;

ReturnFields
  = "{"
      "kind" ":" "FIELDS"
      "," "ref" ":" String
      "," "fields" ":" "[" String { "," String } "]"
    "}"
  ;

ReturnGroupBy
  = "{"
      "kind" ":" "GROUP_BY"
      "," "ref" ":" String
      "," "field" ":" String
      "," "alias" ":" String
    "}"
  ;

ReturnMetric
  = "{"
      "kind" ":" "METRIC"
      "," "ref" ":" String
      "," "field" ":" String
      "," "function" ":" MetricFunction
      "," "alias" ":" String
    "}"
  ;

MetricFunction = "COUNT" | "SUM" | "AVG" | "MIN" | "MAX" ;

OrderList = "[" OrderNode { "," OrderNode } "]" ;

OrderNode
  = "{"
      "ref" ":" String
      "," "field" ":" String
      "," "direction" ":" ("ASC" | "DESC")
    "}"
  ;

SourceQueryList = "[" SourceQueryNode { "," SourceQueryNode } "]" ;

SourceQueryNode
  = "{"
      "outputAs" ":" String
      "," "operation" ":" ("QUERY" | "AGGREGATE" | "ASSOCIATION_QUERY")
      "," "objects" ":" ObjectDeclList
      [ "," "relationships" ":" RelationshipDeclList ]
      [ "," "conditions" ":" ConditionNode ]
      "," "returns" ":" (ReturnFieldsList | ReturnAggregateList)
      [ "," "orders" ":" OrderList ]
      [ "," "maxResults" ":" Integer ]
      [ "," "sourceQuery" ":" SourceQueryList ]
    "}"
  ;

LinkQueryBlock
  = "{"
      "mode" ":" ("LIST" | "ONE")
      "," "relationshipType" ":" String
      "," "sourceRef" ":" String
      "," "targetRef" ":" String
      [ "," "direction" ":" ("OUTBOUND" | "INBOUND" | "BIDIRECTIONAL") ]
    "}"
  ;

CreateMutation
  = "{"
      "data" ":" DataBlock
    "}"
  ;

UpdateMutation
  = "{"
      "scope" ":" ("ONE" | "MANY")
      "," "set" ":" PropertiesMap
    "}"
  ;

DeleteMutation
  = "{"
      "scope" ":" ("ONE" | "MANY")
    "}"
  ;

UpsertMutation
  = "{"
      "matchBy" ":" "[" String { "," String } "]"
      "," "data" ":" DataBlock
    "}"
  ;

BatchMutation
  = "{"
      "atomic" ":" Boolean
      "," "items" ":" "[" BatchItem { "," BatchItem } "]"
    "}"
  ;

BatchItem
  = QueryItem
  | AggregateItem
  | AssociationQueryItem
  | LinkQueryItem
  | CreateItem
  | UpdateItem
  | DeleteItem
  | UpsertItem
  ;

QueryItem = QueryDoc without CommonHeader ;
AggregateItem = AggregateDoc without CommonHeader ;
AssociationQueryItem = AssociationQueryDoc without CommonHeader ;
LinkQueryItem = LinkQueryDoc without CommonHeader ;
CreateItem = CreateDoc without CommonHeader ;
UpdateItem = UpdateDoc without CommonHeader ;
DeleteItem = DeleteDoc without CommonHeader ;
UpsertItem = UpsertDoc without CommonHeader ;

DataBlock
  = "{"
      "properties" ":" PropertiesMap
    "}"
  ;

PropertiesMap
  = "{" [ PropertyEntry { "," PropertyEntry } ] "}" ;

PropertyEntry
  = String ":" ValueExpr
  ;

ValueExpr
  = Value
  | FunctionExpr
  ;

FunctionExpr
  = "{"
      "$fn" ":" String
      [ "," "args" ":" "[" Value { "," Value } "]" ]
    "}"
  ;

Options
  = "{"
      [ "timeoutMs" ":" Integer ]
      [ "," "dryRun" ":" Boolean ]
      [ "," "returnMetadata" ":" Boolean ]
    "}"
  ;

Value = String | Number | Boolean | Object | Array ;
String = JSON string ;
Integer = JSON integer ;
Number = JSON number ;
Boolean = "true" | "false" ;
Object = JSON object ;
Array = JSON array ;
```

---

## A.4 EBNF 补充语义约束

以下约束无法完全通过 EBNF 表达，应由实现补充：

1. alias 在当前层必须唯一
2. `ref` / `from` / `to` / `sourceRef` / `targetRef` 必须引用当前层合法 alias
3. `fromSource` 必须引用当前层合法 `outputAs`
4. `QUERY` 的 `returns` 只能为 `FIELDS`
5. `AGGREGATE` 必须至少出现一个 `METRIC`
6. `ASSOCIATION_QUERY` 必须出现 `relationships`
7. `LINK_QUERY` 顶层 `objects` 必须且仅能有 2 个
8. `CREATE` / `UPDATE` / `DELETE` / `UPSERT` 顶层 `objects` 必须且仅能有 1 个
9. `BATCH` 不允许嵌套 `BATCH`
10. `sourceQuery` 最大嵌套深度在 `strict=true` 时为 2
11. `FIELDS.fields` 中不允许出现 `*`
12. `COUNT` 允许 `field="*"`，其他聚合函数不允许
13. **identity source**：决定对象唯一身份的物理源
    - **primary source**：对象默认主读/主写物理源
    - **pushdown**：将逻辑条件下推到物理源
    - **fallback / degraded**：无法完全下推时的退化执行
    - **sourceQuery**：逻辑中间结果集

---

## A.5 面向大模型的形式化使用建议

为提升大模型生成准确率，建议在推理与生成系统中采用以下策略：

1. 使用本附录 JSON Schema 作为约束解码的目标模式
2. 将 `operation` 作为首要判别字段，先决定顶层文档分支
3. 在生成 `conditions` 与 `returns` 时，先生成 `kind`，再生成对应字段
4. 在生成 `BATCH.items[]` 时，强制每个子项先生成 `operation`
5. 在 `strict=true` 时，将未知字段直接视为硬错误，不做容错修复
6. 结合第 8 章错误码，让模型在修正失败请求时只改动相关路径字段，而不是重写整份 DSL

---
