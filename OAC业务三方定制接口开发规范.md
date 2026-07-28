# OAC 业务三方定制接口开发规范

> **文档版本**：1.0  
> **发布日期**：2026-07  
> **OQL 语法来源**：《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》  
> **Binding 字段来源**：《数据模型对接本体知识平台规范_v1.0.md》第 5.6、5.7 节  
> **适用范围**：业务/三方数据访问服务对接 OAC，接收 canonical OQL 与对象/关系类型绑定信息，完成物理查询翻译、执行和结果组装

---

## 1. 规范目标

本规范只定义 OAC 与业务三方服务之间的传输接口，不重新定义 OQL，也不重新设计 Binding 数据模型。

必须遵循以下边界：

1. `oql` 的语法、字段、类型、必填性和操作约束，严格来源于《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》。
2. `bindings.objectTypes[]` 中的字段，严格来源于《数据模型对接本体知识平台规范_v1.0.md》第 5.6 节响应 `data`。
3. `bindings.relationTypes[]` 中的字段，严格来源于同一规范第 5.7 节响应 `data`。
4. 本规范只新增最外层传输包络字段 `oql`、`bindings`、`objectTypes`、`relationTypes`，用于组合两类既有数据。
5. Binding 包络内部禁止新增、改名、猜测或重新解释上游未定义字段。
6. OQL 必须原样传递，不删除 `schemaRef`，不改写 `version`，不增加另一套精简 OQL。
7. 未使用字段应省略；Binding 字段可以裁剪，但字段名、字段类型和字段语义不得改变。

### 1.1 核心流程

```text
Agent / 上层应用
      │ canonical OQL
      ▼
OAC
      │ 1. 按 OQL 规范校验
      │ 2. 按对象类型调用 5.6
      │ 3. 按关系类型调用 5.7
      │ 4. 按本次 OQL 引用裁剪字段和 Catalog 资产
      ▼
业务三方服务
      │ POST /ontology-access/v1/execute
      │ application/json
      │ { oql, bindings }
      ▼
物理查询翻译与执行
```

---

## 2. 接口定义

### 2.1 端点

```http
POST /ontology-access/v1/execute
Content-Type: application/json
```

### 2.2 请求头

| Header | 必填 | 说明 |
|---|:---:|---|
| `Content-Type` | 是 | 固定为 `application/json` |
| `X-Request-Id` | 是 | 全链路请求标识 |
| `X-Tenant-Id` | 条件必填 | 多租户场景必填 |
| `X-Timeout-Ms` | 否 | 本次执行超时时间，单位毫秒 |
| `Idempotency-Key` | 写操作必填 | `CREATE`、`UPDATE`、`DELETE`、`UPSERT` 的幂等键 |

以下信息已包含在 canonical OQL 或上游 Binding 中，不应在 Header 中重复定义：

- OQL 版本：使用 `oql.version`；
- 本体 Schema：使用 `oql.schemaRef`；
- OQL 严格模式：使用 `oql.strict`；
- Binding 版本：上游 Binding 规范当前未定义独立的报文版本字段，因此本接口不新增 `X-Binding-Version`。

### 2.3 请求体

```json
{
  "oql": {},
  "bindings": {
    "objectTypes": [],
    "relationTypes": []
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `oql` | object | 是 | 完整 canonical OQL，原样遵循 OQL 规范 |
| `bindings` | object | 是 | 本次 OQL 涉及的绑定信息传输包络 |
| `bindings.objectTypes` | array | 条件必填 | OQL 涉及对象类型时必填；每个元素严格对应 5.6 响应 `data` |
| `bindings.relationTypes` | array | 条件必填 | OQL 涉及关系类型时必填；每个元素严格对应 5.7 响应 `data` |

省略规则：

- OQL 未使用关系时，省略 `bindings.relationTypes`；
- 不输出 `null`、空对象或无意义空数组；
- `BATCH`、`sourceQuery` 中涉及的对象类型和关系类型，也应递归汇总到对应数组中；
- 同一对象类型或关系类型只传一份 Binding，业务服务按类型名称匹配，不按 alias 重复传输。

---

## 3. `oql` 参数定义

### 3.1 传递原则

`oql` 必须是《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》定义的 canonical OQL：

- 不删除 `schemaRef`；
- 不把 `schemaRef` 移入 Header；
- 不修改 `version`；
- 不新增 OAC 专用顶层字段；
- 不把 Binding 放入 `extensions`；
- 不输出未使用字段；
- 不允许 `linkQuery` 或 `LINK_QUERY`；
- 关系查询统一使用 `ASSOCIATION_QUERY + relationships`；
- 聚合后过滤统一使用 `aggregateFilter`。

### 3.2 顶层字段

下表严格对应 OQL 规范的顶层字段定义。

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `version` | string | 是 | OQL 协议版本；当前上游规范示例统一为 `"2.0"` |
| `schemaRef` | string | 是 | 本次请求绑定的本体 Schema 标识 |
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

> `BATCH` 在上游 OQL 规范中属于合法 operation，但其完整 `items[]` JSON 字段表尚未在顶层字段定义中展开。本接口不得自行补造 BATCH 子项字段；业务服务仅在已有统一实现和校验器时声明支持 BATCH。

### 3.3 对象与关系

`objects[]`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `objectType` | string | 是 | 本体对象类型名称 |
| `alias` | string | 是 | 当前层唯一对象别名 |
| `fromSource` | string | 否 | 引用同层 `sourceQuery[].outputAs` |

`relationships[]`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `relationshipType` | string | 是 | 本体关系类型名称 |
| `alias` | string | 是 | 当前层唯一关系别名 |
| `from` | string | 是 | 源对象 alias |
| `to` | string | 是 | 目标对象 alias |
| `direction` | string | 是 | `OUTBOUND` / `INBOUND` / `BIDIRECTIONAL` |
| `mode` | string | 否 | `ONE` / `LIST`，默认 `LIST` |

### 3.4 条件结构

字段条件：

```json
{
  "kind": "PREDICATE",
  "ref": "o",
  "field": "status",
  "operator": "EQ",
  "values": ["completed"]
}
```

表达式条件使用 `left`：

```json
{
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
```

逻辑组：

```json
{
  "kind": "GROUP",
  "relation": "AND",
  "children": [
    {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "status",
      "operator": "EQ",
      "values": ["completed"]
    }
  ]
}
```

条件操作符严格使用上游规范定义：

```text
EQ / NE / GT / GTE / LT / LTE
IN / NOT_IN / BETWEEN
LIKE / CONTAINS / STARTS_WITH / ENDS_WITH
IS_NULL / IS_NOT_NULL
IS_EMPTY / IS_NOT_EMPTY
EXISTS / NOT_EXISTS
```

### 3.5 返回结构

允许的 `returns.kind` 及结构：

| kind | 关键字段 | 使用范围 |
|---|---|---|
| `FIELDS` | `ref`、`fields` | QUERY、ASSOCIATION_QUERY |
| `EXPR` | `expr`、`alias` | QUERY、ASSOCIATION_QUERY |
| `FUNCTION` | `ref`、`field`、`alias` | `ID(field)` / `NAME(field)` 返回字段类型指定 |
| `GROUP_BY` | `ref + field` 或 `expr`、`alias` | AGGREGATE |
| `METRIC` | `function`、`ref`、`field`、`alias` | AGGREGATE |

聚合函数只允许：

```text
COUNT / SUM / AVG / MIN / MAX
```

`COUNT` 可以使用 `field = "*"`；其他聚合函数不得使用 `*`。

### 3.6 Operation 约束

| operation | 必须包含 | 不得包含 |
|---|---|---|
| `QUERY` | `objects`、`returns` | `relationships`、`aggregateFilter`、`mutation` |
| `AGGREGATE` | `objects`、`returns`，且至少一个 `METRIC` | `relationships`、`mutation` |
| `ASSOCIATION_QUERY` | `objects`、`relationships`、`returns` | `mutation` |
| `CREATE` | 单个 `objects`、`mutation.data.properties` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `UPDATE` | 单个 `objects`、`conditions`、`mutation.scope`、非空 `mutation.set` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `DELETE` | 单个 `objects`、`conditions`、`mutation.scope` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `UPSERT` | 单个 `objects`、`mutation.matchBy`、`mutation.data.properties` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `BATCH` | `items` | 顶层 `objects`；`items[]` 不得嵌套 BATCH |

---

## 4. `bindings` 传输包络

### 4.1 设计原则

`bindings` 只负责把 5.6、5.7 查询结果组织到同一次执行请求中：

```json
{
  "bindings": {
    "objectTypes": [],
    "relationTypes": []
  }
}
```

- `objectTypes[]` 的每个元素等于 5.6 响应中的 `data`；
- `relationTypes[]` 的每个元素等于 5.7 响应中的 `data`；
- 数组元素内部不增加类型标记，不增加 alias，不增加物理映射推断字段；
- 业务服务通过 `objectTypeContext.name` 匹配 `oql.objects[].objectType`；
- 业务服务通过 `relationshipContext.name` 匹配 `oql.relationships[].relationshipType`；
- 同一类型在 OQL 中出现多个 alias 时复用同一份类型 Binding。

### 4.2 严禁新增的 Binding 字段

以下字段不在 5.6、5.7 的 Binding 响应定义中，本接口禁止使用：

```text
bindingKind
relationBindings
bindingMode
role
selectedBindingId
field_ids
edgeDatasetId
sourceJoinKeys
targetJoinKeys
junctionFieldId
queryDialect
connectionRef
storageLayout
```

如果业务翻译所需信息无法从 5.6、5.7 的既有字段中得到，必须返回“Binding 信息不完整”，不得通过本规范猜测或补造字段。

---

## 5. `bindings.objectTypes[]`

### 5.1 元素结构

每个元素严格对应 5.6 响应 `data`：

```json
{
  "objectTypeContext": {},
  "propertyBindings": [],
  "catalogContext": {}
}
```

### 5.2 `objectTypeContext`

允许字段严格来源于 5.6：

| 字段 | 类型 | 说明 | 本接口处理 |
|---|---|---|---|
| `objectTypeId` | string | 对象类型 ID | 保留 |
| `name` | string | 对象类型名称 | 保留，用于匹配 OQL `objectType` |
| `description` | string | 对象类型描述 | 默认裁剪 |
| `primaryKeys` | array | 主键字段名称列表 | 保留 |
| `bindings` | array | 对象直接绑定信息，当前预留且暂为 `null` | 省略，不定义其内部结构 |

本接口不得为 `objectTypeContext.bindings` 补充 Dataset、role 或其他对象级映射字段。

### 5.3 `propertyBindings`

```json
{
  "propertyId": "prop_001",
  "propertyName": "order_id",
  "dataType": "BIGINT",
  "bindings": [
    {
      "assetId": "field_001"
    }
  ]
}
```

允许字段严格来源于 5.6：

| 字段 | 类型 | 说明 |
|---|---|---|
| `propertyId` | string | 属性 ID |
| `propertyName` | string | 属性名称 |
| `dataType` | string | 属性逻辑数据类型 |
| `bindings` | array | 该属性的绑定记录 |
| `bindings[].bindingId` | string | 绑定记录 ID |
| `bindings[].assetId` | string | 一对一绑定的数据资产 ID |
| `bindings[].groupId` | string | 多绑定分组 ID |
| `bindings[].assetIds` | array | 一对多绑定的数据资产 ID 列表 |
| `bindings[].expression` | string | 绑定表达式 |
| `bindings[].joinKeys` | string | Join 关联键 |
| `bindings[].timeseriesFieldId` | string | 时序字段 ID |
| `bindings[].extendAttribute` | object | 扩展属性 |

裁剪规则：

- 仅保留本次 OQL 实际使用的属性；
- 对象主键属性即使未出现在 `returns` 中，也应保留，以支持稳定对象标识和物理 Dataset 定位；
- `bindingId`、`groupId` 仅在执行选择或问题定位需要时保留；
- `null` 和空 `extendAttribute` 默认省略；
- 不将 `assetId` 改写成其他字段；
- 不把 `assetIds` 解释为 Catalog 祖先链；
- 不改变 `joinKeys`、`expression` 的字符串类型和内容。

### 5.4 Object Property 使用闭包

对象属性集合应由 OAC 从 canonical OQL 递归收集：

```text
conditions 中的 ref + field
conditions.left 中所有 FIELD 表达式
returns.FIELDS.fields
returns.EXPR.expr 中所有 FIELD 表达式
returns.FUNCTION.field 中 ID(...) / NAME(...) 的内部字段
returns.GROUP_BY 的 ref + field 或 expr 中 FIELD
returns.METRIC 的 ref + field（field="*" 除外）
orders 中使用 ref + field 的排序字段
mutation.data.properties 的属性键
mutation.set 的属性键
mutation.matchBy 的属性名
sourceQuery 和 BATCH.items 中上述字段的递归并集
objectTypeContext.primaryKeys
```

同一对象类型被多个 alias 引用时，取该类型所有 alias 使用属性的并集。

---

## 6. `bindings.relationTypes[]`

### 6.1 元素结构

每个元素严格对应 5.7 响应 `data`：

```json
{
  "relationshipContext": {},
  "propertyBindings": [],
  "catalogContext": {}
}
```

### 6.2 `relationshipContext`

允许字段严格来源于 5.7：

| 字段 | 类型 | 说明 |
|---|---|---|
| `relationTypeId` | string | 关系类型 ID |
| `name` | string | 关系名称，用于匹配 OQL `relationshipType` |
| `description` | string | 关系描述，默认裁剪 |
| `sourceObjectTypeId` | string | 源对象类型 ID |
| `targetObjectTypeId` | string | 目标对象类型 ID |
| `connectionType` | string | `OBJECT_TO_OBJECT` / `PROPERTY_TO_PROPERTY` |
| `junctionDatasetId` | string | 关联数据集 ID |
| `backingObjectTypeId` | string | 支撑对象类型 ID |
| `junctionConfig` | string | 关联配置 |
| `relationProperties` | string | 关系属性配置 |
| `junctionDatasetName` | string | 关联数据集名称 |

处理约束：

- `relationTypeId`、`name`、`sourceObjectTypeId`、`targetObjectTypeId`、`connectionType` 保留；
- `junctionDatasetId`、`backingObjectTypeId`、`junctionConfig`、`relationProperties`、`junctionDatasetName` 按非空值条件保留；
- `junctionConfig`、`relationProperties` 在上游规范中定义为 string，本接口不得擅自改为 object 或 array；
- 本接口不得新增 DIRECT、JUNCTION、GRAPH_EDGE 等 `bindingMode` 字段。

### 6.3 关系属性 `propertyBindings`

关系属性使用与 5.6 完全相同的 `propertyBindings` 结构，不另建关系专用映射结构。

仅保留：

- OQL 中通过关系 alias 引用的条件字段；
- OQL 中通过关系 alias 返回的字段；
- 关系执行所必需且已由 5.7 返回的绑定信息。

如果关联执行所需结构没有在 `relationshipContext`、`propertyBindings[].bindings` 或 `catalogContext` 中定义，业务服务必须返回 Binding 不完整错误，不得推测 Join 字段或图 Edge 字段。

---

## 7. `catalogContext`

### 7.1 传递原则

`catalogContext` 严格来源于 5.6、5.7：

```text
DataSource → Schema → Dataset → Field
```

只保留本次执行引用资产及其祖先闭包：

1. 从 `assetId`、`assetIds`、`timeseriesFieldId`、`junctionDatasetId` 等已定义 ID 出发；
2. 保留对应 Field 或 Dataset；
3. 沿上游定义的父资产字段保留 Schema、DataSource；
4. 去重后传递；
5. 不重命名、不改类型、不补造物理信息。

### 7.2 DataSource

按照 5.6 的 CatalogContext 详细字段说明：

| 字段 | 类型 | 处理 |
|---|---|---|
| `id` | string | 保留 |
| `parentAssetId` | string | 按返回值保留，顶级数据源可为空 |
| `displayName` | string | 默认裁剪 |
| `connectionConfig` | object | 执行连接所需时保留 |

`connectionConfig` 内部仅使用上游规范定义的字段。业务服务不得要求本接口额外增加密码、Token、私钥等字段。

### 7.3 Schema

| 字段 | 类型 | 处理 |
|---|---|---|
| `id` | string | 保留 |
| `parentAssetId` | string | 保留 |
| `name` | string | 保留 |

### 7.4 Dataset

| 字段 | 类型 | 处理 |
|---|---|---|
| `id` | string | 保留 |
| `parentAssetId` | string | 保留 |
| `name` | string | 保留 |
| `storageType` | string | 保留：`Table` / `View` / `Tag` / `Edge` / `Dimension` |
| `primaryKeys` | string | 按上游定义保留 JSON 数组格式字符串，不改为 array |
| `extendAttribute` | object | 仅执行需要时保留 |

### 7.5 Field

| 字段 | 类型 | 处理 |
|---|---|---|
| `id` | string | 保留 |
| `parentAssetId` | string | 保留 |
| `name` | string | 保留 |
| `description` | string | 默认裁剪 |
| `dataType` | string | 保留 |
| `sortOrder` | string | 默认裁剪 |
| `semanticRole` | string | 执行需要时保留 |
| `technicalType` | string | 执行需要时保留 |
| `cubeContext` | object | 多维查询需要时保留 |
| `timeSeriesInfo` | object | 时序查询需要时保留 |
| `extendAttribute` | object | 执行需要时保留 |

### 7.6 上游示例与字段表冲突

《数据模型对接本体知识平台规范_v1.0.md》的 5.6、5.7 JSON 示例使用了 `datasourceId`、`schemaId`、`datasetId`，而同章节的 CatalogContext 详细字段表使用统一的 `parentAssetId`。

本接口不增加第三套命名，也不定义自动转换规则。为保证 DTO 和物理路径解析唯一，本规范采用同章节“CatalogContext 详细字段说明”中的 `parentAssetId` 作为接口字段定义。上游规范示例应同步修正。

---

## 8. Binding 裁剪算法

### 8.1 类型收集

递归遍历 OQL：

```text
ObjectTypes =
  当前层 objects[].objectType
  ∪ sourceQuery 中对象类型
  ∪ BATCH.items 中对象类型

RelationTypes =
  当前层 relationships[].relationshipType
  ∪ sourceQuery 中关系类型
  ∪ BATCH.items 中关系类型
```

去重后分别调用 5.6 和 5.7。

### 8.2 属性裁剪

对象类型：

- 保留 `objectTypeContext.objectTypeId/name/primaryKeys`；
- 省略预留且为空的 `objectTypeContext.bindings`；
- 保留 OQL 使用属性与主键属性对应的 `propertyBindings`。

关系类型：

- 保留必要的 `relationshipContext`；
- 保留 OQL 显式引用的关系属性；
- 对上游未明确结构的关系配置只做原值透传，不做语义改写。

### 8.3 Catalog 裁剪

保留以下资产的最小闭包：

```text
Binding 直接引用资产
+ 时序字段资产
+ junctionDatasetId 指向资产
+ 上述资产的 Dataset / Schema / DataSource 祖先
```

如果无法根据上游返回字段构造完整闭包，OAC 应在调用业务服务前返回 Binding 校验错误。

### 8.4 类型与内容保持

裁剪允许：

- 删除未使用字段；
- 删除 `null`；
- 删除空对象；
- 对数组去重。

裁剪禁止：

- 字段改名；
- 字段类型转换；
- 把字符串 JSON 转为 object/array；
- 新增推断字段；
- 把一个字段拆成多个新字段；
- 根据数据库类型补造方言信息。

---

## 9. 完整请求示例：普通查询

```json
{
  "oql": {
    "version": "2.0",
    "schemaRef": "sales-v1",
    "strict": true,
    "operation": "QUERY",
    "objects": [
      {
        "objectType": "OrderObject",
        "alias": "o"
      }
    ],
    "conditions": {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "order_id",
      "operator": "EQ",
      "values": [10001]
    },
    "returns": [
      {
        "kind": "FIELDS",
        "ref": "o",
        "fields": ["order_id"]
      }
    ],
    "maxResults": {
      "limit": 100,
      "offset": 0
    }
  },
  "bindings": {
    "objectTypes": [
      {
        "objectTypeContext": {
          "objectTypeId": "obj_001",
          "name": "OrderObject",
          "primaryKeys": ["order_id"]
        },
        "propertyBindings": [
          {
            "propertyId": "prop_001",
            "propertyName": "order_id",
            "dataType": "BIGINT",
            "bindings": [
              {
                "assetId": "field_001"
              }
            ]
          }
        ],
        "catalogContext": {
          "dataSources": [
            {
              "id": "ds_001",
              "connectionConfig": {
                "connectionType": "DataCube",
                "name": "sales_prod",
                "datasourceId": "datasourc_xxx",
                "datasourceType": "MYSQL",
                "modelType": "物理"
              }
            }
          ],
          "schemas": [
            {
              "id": "schema_001",
              "parentAssetId": "ds_001",
              "name": "sales_db"
            }
          ],
          "datasets": [
            {
              "id": "ds_table_001",
              "parentAssetId": "schema_001",
              "name": "t_orders",
              "storageType": "Table",
              "primaryKeys": "[\"order_id\"]"
            }
          ],
          "fields": [
            {
              "id": "field_001",
              "parentAssetId": "ds_table_001",
              "name": "order_id",
              "dataType": "BIGINT",
              "technicalType": "BIGINT"
            }
          ]
        }
      }
    ]
  }
}
```

---

## 10. 完整请求示例：关系查询

```json
{
  "oql": {
    "version": "2.0",
    "schemaRef": "sales-v1",
    "strict": true,
    "operation": "ASSOCIATION_QUERY",
    "objects": [
      {
        "objectType": "OrderObject",
        "alias": "o"
      },
      {
        "objectType": "ProductObject",
        "alias": "p"
      }
    ],
    "relationships": [
      {
        "relationshipType": "order_has_product",
        "alias": "r1",
        "from": "o",
        "to": "p",
        "direction": "OUTBOUND",
        "mode": "LIST"
      }
    ],
    "returns": [
      {
        "kind": "FIELDS",
        "ref": "r1",
        "fields": ["quantity"]
      }
    ]
  },
  "bindings": {
    "objectTypes": [
      {
        "objectTypeContext": {
          "objectTypeId": "obj_order",
          "name": "OrderObject",
          "primaryKeys": ["order_id"]
        },
        "propertyBindings": [
          {
            "propertyId": "prop_order_id",
            "propertyName": "order_id",
            "dataType": "BIGINT",
            "bindings": [
              {
                "assetId": "field_order_id"
              }
            ]
          }
        ],
        "catalogContext": {
          "dataSources": [
            {
              "id": "ds_001",
              "connectionConfig": {
                "connectionType": "DataCube",
                "name": "sales_prod",
                "datasourceId": "datasourc_xxx",
                "datasourceType": "MYSQL",
                "modelType": "物理"
              }
            }
          ],
          "schemas": [
            {
              "id": "schema_001",
              "parentAssetId": "ds_001",
              "name": "sales_db"
            }
          ],
          "datasets": [
            {
              "id": "ds_order",
              "parentAssetId": "schema_001",
              "name": "t_orders",
              "storageType": "Table",
              "primaryKeys": "[\"order_id\"]"
            }
          ],
          "fields": [
            {
              "id": "field_order_id",
              "parentAssetId": "ds_order",
              "name": "order_id",
              "dataType": "BIGINT",
              "technicalType": "BIGINT"
            }
          ]
        }
      },
      {
        "objectTypeContext": {
          "objectTypeId": "obj_product",
          "name": "ProductObject",
          "primaryKeys": ["product_id"]
        },
        "propertyBindings": [
          {
            "propertyId": "prop_product_id",
            "propertyName": "product_id",
            "dataType": "BIGINT",
            "bindings": [
              {
                "assetId": "field_product_id"
              }
            ]
          }
        ],
        "catalogContext": {
          "dataSources": [
            {
              "id": "ds_001",
              "connectionConfig": {
                "connectionType": "DataCube",
                "name": "sales_prod",
                "datasourceId": "datasourc_xxx",
                "datasourceType": "MYSQL",
                "modelType": "物理"
              }
            }
          ],
          "schemas": [
            {
              "id": "schema_001",
              "parentAssetId": "ds_001",
              "name": "sales_db"
            }
          ],
          "datasets": [
            {
              "id": "ds_product",
              "parentAssetId": "schema_001",
              "name": "t_products",
              "storageType": "Table",
              "primaryKeys": "[\"product_id\"]"
            }
          ],
          "fields": [
            {
              "id": "field_product_id",
              "parentAssetId": "ds_product",
              "name": "product_id",
              "dataType": "BIGINT",
              "technicalType": "BIGINT"
            }
          ]
        }
      }
    ],
    "relationTypes": [
      {
        "relationshipContext": {
          "relationTypeId": "rel_001",
          "name": "order_has_product",
          "sourceObjectTypeId": "obj_order",
          "targetObjectTypeId": "obj_product",
          "connectionType": "OBJECT_TO_OBJECT",
          "junctionDatasetId": "ds_junction",
          "backingObjectTypeId": "obj_junction",
          "junctionConfig": "{}",
          "relationProperties": "[]",
          "junctionDatasetName": "t_order_product"
        },
        "propertyBindings": [
          {
            "propertyId": "prop_junc_001",
            "propertyName": "quantity",
            "dataType": "INT",
            "bindings": [
              {
                "assetId": "field_qty"
              }
            ]
          }
        ],
        "catalogContext": {
          "dataSources": [
            {
              "id": "ds_001",
              "connectionConfig": {
                "connectionType": "DataCube",
                "name": "sales_prod",
                "datasourceId": "datasourc_xxx",
                "datasourceType": "MYSQL",
                "modelType": "物理"
              }
            }
          ],
          "schemas": [
            {
              "id": "schema_001",
              "parentAssetId": "ds_001",
              "name": "sales_db"
            }
          ],
          "datasets": [
            {
              "id": "ds_junction",
              "parentAssetId": "schema_001",
              "name": "t_order_product",
              "storageType": "Table"
            }
          ],
          "fields": [
            {
              "id": "field_qty",
              "parentAssetId": "ds_junction",
              "name": "quantity",
              "dataType": "INT",
              "technicalType": "INT"
            }
          ]
        }
      }
    ]
  }
}
```

> 示例只展示接口结构。实际关系执行如果还需要上游未明确描述的 Join 配置，必须由 5.7 返回并按原值传递；本规范不补造 Join 字段。

---

## 11. 业务服务实现建议

### 11.1 Java DTO

顶层 DTO 推荐保持简单：

```java
public record ExecuteRequest(
    JsonNode oql,
    BindingsEnvelope bindings
) {}

public record BindingsEnvelope(
    List<ObjectTypeBindingData> objectTypes,
    List<RelationTypeBindingData> relationTypes
) {}
```

其中：

- `ObjectTypeBindingData` 只定义 `objectTypeContext`、`propertyBindings`、`catalogContext`；
- `RelationTypeBindingData` 只定义 `relationshipContext`、`propertyBindings`、`catalogContext`；
- 内部字段名称和类型必须逐项复制 5.6、5.7；
- 不建立 `bindingKind`、`relationBindings` 等第二套模型。

### 11.2 OQL 处理

推荐两种实现方式：

1. 直接复用与《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》同步维护的 OQL DTO 和校验器；
2. 顶层先用 `JsonNode` 接收，再根据 `oql.version` 使用对应版本校验器反序列化。

不得根据本规范中的摘要表自行实现一套裁剪版 OQL Bean；摘要只用于接口开发者快速理解，完整语法始终以上游 OQL 规范为准。

### 11.3 Binding 索引

业务服务启动单次请求处理时，可构建只读索引：

```text
objectTypeContext.name       -> ObjectTypeBindingData
objectTypeContext.objectTypeId -> ObjectTypeBindingData
relationshipContext.name     -> RelationTypeBindingData
relationshipContext.relationTypeId -> RelationTypeBindingData
catalogContext.*[].id        -> Catalog Asset
propertyName                 -> PropertyBinding
```

索引属于业务服务内部实现，不改变传输 JSON。

---

## 12. 校验规则

### 12.1 OQL 校验

业务服务至少校验：

1. `oql.version` 为已支持版本；
2. `schemaRef` 非空；
3. `operation` 合法；
4. operation 所需字段完整；
5. 所有 alias 先声明后引用；
6. `objects[].objectType` 能唯一匹配 `bindings.objectTypes[].objectTypeContext.name`；
7. `relationships[].relationshipType` 能唯一匹配 `bindings.relationTypes[].relationshipContext.name`；
8. OQL 引用属性存在于对应 `propertyBindings.propertyName`；
9. `aggregateFilter`、表达式函数、ID/NAME 函数满足 OQL 规范；
10. OQL 不包含当前版本未知顶层字段。

### 12.2 Binding 校验

业务服务至少校验：

1. 对象类型和关系类型无重复；
2. `propertyBindings.propertyName` 在同一类型中唯一；
3. 每个使用中的属性至少有一个绑定记录；
4. `assetId`、`assetIds`、`timeseriesFieldId` 引用的 Catalog 资产存在；
5. Catalog 祖先链完整；
6. `connectionType`、`storageType`、数据类型使用上游返回值，不自行扩展枚举；
7. 未定义的关系配置不进行推断。

### 12.3 错误码

| 错误码 | HTTP | 说明 |
|---|:---:|---|
| `INVALID_REQUEST` | 400 | 顶层请求包络不合法 |
| `UNSUPPORTED_OQL_VERSION` | 400 | 不支持 `oql.version` |
| `UNSUPPORTED_OPERATION` | 400 | 业务服务不支持该 operation |
| `OQL_VALIDATION_ERROR` | 400 | OQL 不符合上游语法或操作约束 |
| `OBJECT_BINDING_NOT_FOUND` | 400 | 对象类型 Binding 缺失 |
| `RELATION_BINDING_NOT_FOUND` | 400 | 关系类型 Binding 缺失 |
| `PROPERTY_BINDING_NOT_FOUND` | 400 | 属性 Binding 缺失 |
| `BINDING_AMBIGUOUS` | 400 | 类型或属性 Binding 不唯一 |
| `CATALOG_ASSET_NOT_FOUND` | 400 | Catalog 引用资产不存在 |
| `BINDING_INCOMPLETE` | 400 | 上游 Binding 信息不足以生成物理查询 |
| `TRANSLATE_ERROR` | 500 | 物理查询翻译失败 |
| `EXECUTE_ERROR` | 500 | 物理查询执行失败 |
| `EXECUTE_TIMEOUT` | 504 | 物理执行超时 |

错误响应：

```json
{
  "success": false,
  "errors": [
    {
      "code": "PROPERTY_BINDING_NOT_FOUND",
      "message": "property binding not found: OrderObject.order_id",
      "path": "bindings.objectTypes[0].propertyBindings",
      "details": {
        "objectType": "OrderObject",
        "propertyName": "order_id"
      }
    }
  ]
}
```

---

## 13. 成功响应

```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "rid": "OrderObject-10001",
        "objectType": "OrderObject",
        "properties": {
          "order_id": 10001
        }
      }
    ],
    "relationships": []
  },
  "errors": []
}
```

响应约束：

- `objectType`、`relationshipType` 使用本体类型名称；
- `properties` Key 使用 OQL 属性名或显式返回 alias；
- 未在 `returns` 中请求的技术字段不得出现在 `properties`；
- `rid` 必须稳定、可重复生成；
- 默认不得返回原始 SQL、GQL、TQL 和敏感连接信息。

---

## 14. 平滑兼容与维护原则

### 14.1 单一事实来源

| 内容 | 唯一事实来源 |
|---|---|
| OQL 字段、类型、operation、校验规则 | 《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》 |
| 对象类型 Binding | 《数据模型对接本体知识平台规范_v1.0.md》5.6 |
| 关系类型 Binding | 《数据模型对接本体知识平台规范_v1.0.md》5.7 |
| OAC 传输包络和响应 | 本规范 |

本规范不复制上游未定义的内部结构。

### 14.2 兼容规则

1. `oql.version` 决定 OQL 语法版本，不再使用重复版本 Header。
2. Binding 当前没有独立版本字段，不新增私有 Binding 版本号。
3. 上游新增可选 Binding 字段时，业务 DTO 应允许未知字段，避免反序列化失败。
4. 业务逻辑只能使用已明确理解的字段；未知字段不参与物理查询生成。
5. OQL 顶层字段仍按对应 `oql.version` 严格校验，不能因 DTO 忽略未知字段而绕过语法检查。
6. 本接口 v1 的新增可选包络字段必须具备默认行为。
7. 传输包络发生破坏性变化时发布 `/ontology-access/v2/execute`，不得静默改变 v1 语义。
8. 上游 Binding 字段发生改名、类型或语义变化时，先更新上游规范，再更新本规范；不得由 OAC 文档先行猜测。

### 14.3 文档同步检查

每次更新本规范时必须执行：

```text
OQL 顶层字段 = OQL 上游规范
OQL operation 枚举 = OQL 上游规范
Object Binding 字段 ⊆ 5.6 响应字段
Relation Binding 字段 ⊆ 5.7 响应字段
Catalog 字段 ⊆ 5.6 CatalogContext 字段
请求示例中不得出现禁止新增的 Binding 字段
```

---

## 15. 当前上游规范待澄清项

以下问题来源于两份上游规范自身，本规范不通过新增字段解决：

1. 《数据模型对接本体知识平台规范_v1.0.md》文件名为 v1.0，但文档标题仍为 v0.94。
2. 5.6、5.7 JSON 示例的父级字段使用 `datasourceId`、`schemaId`、`datasetId`，详细字段表使用 `parentAssetId`。
3. `joinKeys` 定义为 string，但未描述字符串内部格式。
4. `junctionConfig`、`relationProperties` 定义为 string，但未给出稳定 Schema。
5. `objectTypeContext.bindings` 标记为预留且暂为 `null`，不能据此补造对象级 Dataset Binding。
6. OQL `BATCH` 描述引用 `items[]`，但顶层字段表未完整定义 `items` 字段结构。

在上游规范补充前：

- OAC 和业务服务只使用已经明确的字段；
- 未定义字符串配置按原值透传；
- 信息不足时返回 `BINDING_INCOMPLETE`；
- 禁止在本规范中提前定义替代字段。

---

## 16. 接入检查清单

### 请求包络

- [ ] 使用 `application/json`
- [ ] 请求体只有 `oql` 和 `bindings`
- [ ] OQL 保留 `version`、`schemaRef`、`strict`
- [ ] 不使用重复的 OQL/Binding 版本 Header
- [ ] `objectTypes[]` 元素严格来自 5.6 `data`
- [ ] `relationTypes[]` 元素严格来自 5.7 `data`

### OQL

- [ ] 使用当前 canonical OQL
- [ ] operation 和字段约束来自 OQL 上游规范
- [ ] 省略未使用字段
- [ ] 不使用 `linkQuery`、`LINK_QUERY`、`having`
- [ ] ID/NAME 使用 `returns.kind = "FUNCTION"`

### Binding

- [ ] 不存在 `bindingKind`
- [ ] 不存在 `relationBindings`
- [ ] 不存在 `bindingMode`
- [ ] 不存在 `field_ids`
- [ ] 不存在 `queryDialect`、`connectionRef`、`storageLayout`
- [ ] 不改变上游字段类型
- [ ] Catalog 只保留引用资产和祖先闭包
- [ ] 上游未定义内容不猜测

### 实现

- [ ] DTO 忽略新增可选 Binding 字段
- [ ] OQL 按 `oql.version` 严格校验
- [ ] 所有物理标识来自 Binding
- [ ] 所有查询值参数化
- [ ] Binding 不完整时明确报错
- [ ] 隐藏技术字段不泄露到响应
