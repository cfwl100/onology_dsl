# OAC 业务三方定制接口开发规范

> **文档版本**：1.0  
> **发布日期**：2026-07  
> **三方 OQL 版本**：1.0  
> **OQL 语法来源**：《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》  
> **Binding 数据来源**：《数据模型对接本体知识平台规范_v1.0.md》全文，重点包括数据资产特征与组合规则、数据模型层级定义、资产查询接口以及对象/关系绑定查询接口  
> **适用范围**：业务或三方数据访问服务对接 OAC，接收精简 OQL 与执行所需 Binding，完成物理查询翻译、执行和结果组装

---

## 1. 规范目标与边界

本规范定义 OAC 到业务三方服务的执行接口，不重新设计本体模型、OQL 语义或数据资产模型。

### 1.1 单一事实来源

| 内容 | 事实来源 |
|---|---|
| OQL 的 operation、objects、relationships、conditions、returns、aggregateFilter、orders、maxResults、sourceQuery、mutation、options、extensions 及其语义 | 《本体对象操作语言（OQL）DSL 规范 - 面向Agent.md》 |
| 数据资产类型与目录组合方式 | 《数据模型对接本体知识平台规范_v1.0.md》第 1 章 |
| 数据模型层级、assetType、possibleChildDefines 和访问规范 | 同一规范第 5.1、5.4 节 |
| 通用资产标识、父子关系、platform、levelName、datasetType、isPrimaryKey、isNullable 等字段 | 同一规范第 5.5、6.1～6.4 节 |
| 对象类型 Binding 根结构和属性 Binding | 同一规范第 5.6 节 |
| 关系类型 Binding 根结构和关系上下文 | 同一规范第 5.7 节 |
| OAC 三方请求包络、字段裁剪和字段归一化规则 | 本规范 |

### 1.2 三方接口专用投影

OAC 接收并校验上游 OQL 后，生成面向三方执行服务的 OQL 投影：

1. `version` 固定为字符串 `"1.0"`；
2. 不传递 `strict`；
3. 不传递 `schemaRef`；
4. 其余 OQL 字段名称、结构和语义保持与 OQL 来源规范一致；
5. 未使用字段必须省略，不输出 `null`、空对象或无意义空数组。

Binding 采用“有来源的统一投影”：

1. 对象和关系 Binding 根结构分别来源于 5.6、5.7；
2. Catalog 资产字段同时审视第 1 章、第 5.1、5.4、5.5 和第 6 章；
3. 只对规范中已经出现的同义字段做确定性归一化；
4. 不新增上游规范从未定义的关系 Join、图 Edge 或 Binding 选择字段；
5. 不能从规范字段确定物理执行信息时，返回 Binding 不完整错误，不进行猜测。

### 1.3 核心流程

```text
Agent / 上层应用
      │ 上游 OQL
      ▼
OAC
      │ 1. 校验 OQL 语义
      │ 2. 生成 version=1.0 的三方 OQL 投影
      │ 3. 查询对象类型 Binding
      │ 4. 查询关系类型 Binding
      │ 5. 结合数据资产和层级规范归一化 Catalog
      │ 6. 按本次请求裁剪 Binding
      ▼
业务三方服务
      │ POST /ontology-access/v1/execute
      │ Content-Type: application/json
      │ { oql, bindings }
      ▼
物理查询翻译、执行与结果组装
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
| `X-Request-Id` | 是 | 全链路唯一请求标识 |
| `X-Tenant-Id` | 条件必填 | 多租户场景必填 |
| `X-Timeout-Ms` | 否 | 本次执行超时时间，单位毫秒 |
| `Idempotency-Key` | 写操作必填 | `CREATE`、`UPDATE`、`DELETE`、`UPSERT` 的幂等键 |

不增加 `X-OQL-Version`、`X-Binding-Version` 等重复版本 Header。三方 OQL 版本只由 `oql.version` 表达。

### 2.3 请求体

```json
{
  "oql": {
    "version": "1.0",
    "operation": "QUERY"
  },
  "bindings": {
    "objectTypes": []
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `oql` | object | 是 | 三方 OQL 1.0 投影 |
| `bindings` | object | 是 | 本次操作所需 Binding 包络 |
| `bindings.objectTypes` | array | 条件必填 | 本次 OQL 涉及对象类型时必填 |
| `bindings.relationTypes` | array | 条件必填 | 本次 OQL 涉及关系类型时必填 |

省略规则：

- 未使用关系时省略 `bindings.relationTypes`；
- 同一对象类型或关系类型只传一份 Binding，不按 alias 重复；
- `sourceQuery` 和 `BATCH.items` 内涉及的类型需要递归汇总；
- 包络内不增加 `bindingKind`、alias 或 Binding 选择结果字段。

---

## 3. 三方 OQL 1.0 参数定义

### 3.1 顶层字段

以下字段除 `version` 的固定值以及明确删除的 `strict`、`schemaRef` 外，均沿用 OQL 来源规范的字段结构和语义。

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `version` | string | 是 | 固定为 `"1.0"` |
| `operation` | enum | 是 | `QUERY` / `AGGREGATE` / `ASSOCIATION_QUERY` / `CREATE` / `UPDATE` / `DELETE` / `UPSERT` / `BATCH` |
| `objects` | array | 条件必填 | 对象声明；`BATCH` 顶层不使用 |
| `relationships` | array | 条件必填 | 关系路径，仅 `ASSOCIATION_QUERY` 使用 |
| `conditions` | object | 条件必填 | 对象级、明细级过滤条件树 |
| `returns` | array | 查询类操作必填 | 返回字段、表达式、字段类型指定函数、分组字段或聚合指标 |
| `aggregateFilter` | object | 否 | 聚合后过滤，仅 `AGGREGATE` 使用 |
| `orders` | array | 否 | 排序定义 |
| `maxResults` | object | 否 | 数量与偏移量控制 |
| `sourceQuery` | array | 否 | 中间结果查询 |
| `mutation` | object | 写操作条件必填 | 写操作参数块 |
| `items` | array | `BATCH` 必填 | 批处理子操作；子项不得继续嵌套 `BATCH` |
| `options` | object | 否 | 执行选项 |
| `extensions` | object | 否 | 已治理扩展；无明确约定时省略 |

禁止字段：

```text
strict
schemaRef
linkQuery
having
```

禁止 operation：

```text
LINK_QUERY
```

### 3.2 objects

```json
{
  "objectType": "Order",
  "alias": "o"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `objectType` | string | 是 | 本体对象类型名称 |
| `alias` | string | 是 | 当前层唯一对象别名 |
| `fromSource` | string | 否 | 引用同层 `sourceQuery[].outputAs` |

约束：

- `alias` 在当前层唯一；
- `CREATE`、`UPDATE`、`DELETE`、`UPSERT` 必须且只能声明一个对象；
- `ASSOCIATION_QUERY` 的对象声明必须覆盖全部关系端点；
- `BATCH` 顶层不声明 `objects`。

### 3.3 relationships

```json
{
  "relationshipType": "order_has_product",
  "alias": "r1",
  "from": "o",
  "to": "p",
  "direction": "OUTBOUND",
  "mode": "LIST"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `relationshipType` | string | 是 | 本体关系类型名称 |
| `alias` | string | 是 | 当前层唯一关系别名 |
| `from` | string | 是 | 源对象 alias |
| `to` | string | 是 | 目标对象 alias |
| `direction` | enum | 是 | `OUTBOUND` / `INBOUND` / `BIDIRECTIONAL` |
| `mode` | enum | 否 | `ONE` / `LIST`，默认 `LIST` |

关系查询统一使用 `ASSOCIATION_QUERY + relationships`。多跳路径按数组顺序表达。

### 3.4 Expr 表达式

字段表达式：

```json
{
  "kind": "FIELD",
  "ref": "o",
  "field": "amount"
}
```

字面量表达式：

```json
{
  "kind": "VALUE",
  "value": 100
}
```

受控函数表达式：

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

扩展函数可以增加 `namespace`，但必须先在 OAC 函数注册表登记。聚合函数不得使用 Expr `FUNCTION` 表达，必须使用 `returns.kind = "METRIC"`。

### 3.5 conditions

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

条件操作符：

```text
EQ / NE / GT / GTE / LT / LTE
IN / NOT_IN / BETWEEN
LIKE / CONTAINS / STARTS_WITH / ENDS_WITH
IS_NULL / IS_NOT_NULL
IS_EMPTY / IS_NOT_EMPTY
EXISTS / NOT_EXISTS
```

### 3.6 returns

字段返回：

```json
{
  "kind": "FIELDS",
  "ref": "o",
  "fields": ["orderNo", "amount"]
}
```

派生表达式：

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

普通分组：

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

ID/NAME 字段类型指定函数：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

约束：

- `QUERY`、`ASSOCIATION_QUERY` 允许 `FIELDS`、`EXPR`、字段类型指定 `FUNCTION`；
- `AGGREGATE` 只允许 `GROUP_BY`、`METRIC`；
- `FIELDS.fields` 不允许 `*`；
- `COUNT` 允许 `field = "*"`，其他聚合函数不允许；
- 聚合函数仅允许 `COUNT`、`SUM`、`AVG`、`MIN`、`MAX`；
- `EXPR`、`FUNCTION`、`GROUP_BY`、`METRIC` 必须声明 `alias`。

### 3.7 aggregateFilter、orders、maxResults

聚合过滤：

```json
{
  "kind": "METRIC_PREDICATE",
  "metricAlias": "orderCount",
  "operator": "GT",
  "values": [10]
}
```

`aggregateFilter` 仅用于 `AGGREGATE`，只能引用 `returns` 中已声明的 `METRIC.alias`。

排序：

```json
{
  "ref": "o",
  "field": "createdAt",
  "direction": "DESC"
}
```

聚合查询可以省略 `ref`，直接按返回 alias 排序。`direction` 仅允许 `ASC` 或 `DESC`。

分页：

```json
{
  "limit": 100,
  "offset": 0
}
```

`limit` 必须大于 0，`offset` 必须大于等于 0。

### 3.8 Operation 约束

| operation | 必须包含 | 不得包含 |
|---|---|---|
| `QUERY` | `objects`、`returns` | `relationships`、`aggregateFilter`、`mutation` |
| `AGGREGATE` | `objects`、`returns`，且至少一个 `METRIC` | `relationships`、`mutation` |
| `ASSOCIATION_QUERY` | `objects`、`relationships`、`returns` | `mutation` |
| `CREATE` | 单个 `objects`、`mutation.data.properties` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `UPDATE` | 单个 `objects`、`conditions`、`mutation.scope`、非空 `mutation.set` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `DELETE` | 单个 `objects`、`conditions`、`mutation.scope` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `UPSERT` | 单个 `objects`、非空 `mutation.matchBy`、`mutation.data.properties` | `returns`、`orders`、`relationships`、`aggregateFilter`、`sourceQuery` |
| `BATCH` | 非空 `items` | 顶层 `objects`；`items[]` 不得嵌套 `BATCH` |

---

## 4. Binding 包络与字段来源

### 4.1 包络结构

```json
{
  "bindings": {
    "objectTypes": [],
    "relationTypes": []
  }
}
```

- `objectTypes[]` 的根结构来源于对象类型绑定查询响应 `data`；
- `relationTypes[]` 的根结构来源于关系类型绑定查询响应 `data`；
- `catalogContext` 的资产字段同时参考数据资产特征、组合规则、层级定义、通用资产查询和 Binding 详细字段说明；
- 数组元素不增加 alias 或类型标记，业务服务通过上下文中的类型名称或 ID 建立索引。

### 4.2 禁止新增的内部字段

以下字段未在数据模型规范中定义，本接口禁止放入 Binding：

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

### 4.3 Catalog 字段归一化

数据模型规范的不同章节对同一资产语义使用了不同字段名。为给三方开发者提供单一、稳定的 DTO，本接口只对已经明确同义的字段做下列归一化：

| 数据模型规范中的来源字段 | 三方 Binding 输出字段 | 规则 |
|---|---|---|
| `id`、`assetId` | `id` | 保留原值 |
| `parentAssetId`、`parentId` | `parentAssetId` | 保留原值 |
| Schema 示例中的 `datasourceId` | `parentAssetId` | 仅用于 Schema 父级 |
| Dataset 示例中的 `schemaId` | `parentAssetId` | 仅用于 Dataset 父级 |
| Field 示例中的 `datasetId` | `parentAssetId` | 仅用于 Field 父级 |
| `storageType`、`datasetType` | `storageType` | 保留原值，如 `Table`、`Tag`、`Edge`、`View`、`Dimension` |
| JSON 字符串形式的 `extendAttribute` | `extendAttribute` object | 仅在字符串为合法 JSON object 时解析；否则返回 Binding 格式错误 |

除上表外，不进行字段改名、类型推断或语义转换。

---

## 5. objectTypes[]

### 5.1 元素结构

```json
{
  "objectTypeContext": {},
  "propertyBindings": [],
  "catalogContext": {}
}
```

### 5.2 objectTypeContext

| 字段 | 类型 | 必填 | 处理 |
|---|---|:---:|---|
| `objectTypeId` | string | 是 | 保留 |
| `name` | string | 是 | 保留，用于匹配 `oql.objects[].objectType` |
| `description` | string | 否 | 默认裁剪 |
| `primaryKeys` | array | 是 | 保留 |
| `bindings` | array | 否 | 当前规范标记为预留；为空时省略，不定义其内部结构 |

不得为 `objectTypeContext.bindings` 补造 Dataset、角色或其他对象级映射字段。

### 5.3 propertyBindings

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

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `propertyId` | string | 是 | 本体属性 ID |
| `propertyName` | string | 是 | 本体属性名称 |
| `dataType` | string | 是 | 属性逻辑数据类型 |
| `bindings` | array | 条件必填 | 属性绑定记录；无绑定时可以为空或省略 |
| `bindings[].bindingId` | string | 否 | 绑定记录 ID |
| `bindings[].assetId` | string | 条件 | 一对一资产绑定 |
| `bindings[].groupId` | string | 否 | 多绑定分组 ID |
| `bindings[].assetIds` | array | 条件 | 一对多资产绑定 |
| `bindings[].expression` | string | 否 | 绑定表达式 |
| `bindings[].joinKeys` | string | 否 | Join 关联键，内部格式按上游原值使用 |
| `bindings[].timeseriesFieldId` | string | 否 | 时序字段 ID |
| `bindings[].extendAttribute` | object | 否 | 扩展属性 |

处理规则：

- 只保留本次 OQL 使用的属性以及 `primaryKeys` 对应属性；
- `null`、空扩展对象和非执行必需的诊断字段默认裁剪；
- `assetIds` 是资产 ID 列表，不解释为目录祖先链；
- `expression`、`joinKeys` 不解析为自定义新结构。

---

## 6. relationTypes[]

### 6.1 元素结构

```json
{
  "relationshipContext": {},
  "propertyBindings": [],
  "catalogContext": {}
}
```

### 6.2 relationshipContext

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `relationTypeId` | string | 是 | 关系类型 ID |
| `name` | string | 是 | 关系类型名称，用于匹配 `oql.relationships[].relationshipType` |
| `description` | string | 否 | 关系描述，默认裁剪 |
| `sourceObjectTypeId` | string | 是 | 源对象类型 ID |
| `targetObjectTypeId` | string | 是 | 目标对象类型 ID |
| `connectionType` | string | 是 | `OBJECT_TO_OBJECT` / `PROPERTY_TO_PROPERTY` |
| `junctionDatasetId` | string | 否 | 关联数据集 ID |
| `backingObjectTypeId` | string | 否 | 支撑对象类型 ID |
| `junctionConfig` | string | 否 | 关联配置，按原值传递 |
| `relationProperties` | string | 否 | 关系属性配置，按原值传递 |
| `junctionDatasetName` | string | 否 | 关联数据集名称 |

关系属性继续使用与对象属性相同的 `propertyBindings` 结构，不新增关系专用 Binding 模型。

如果物理关联所需的 Join 或 Edge 信息不能从上述字段、属性 Binding 或 Catalog 中确定，必须返回 `BINDING_INCOMPLETE`。

---

## 7. catalogContext

### 7.1 目录层级语义

数据模型规范明确支持灵活组合：

```text
datasource → dataset → field
datasource → schema → dataset → field
datasource → schema → schema → dataset → field
```

因此业务服务不得假设：

- Schema 一定存在；
- Schema 只有一层；
- Dataset 的父级一定是 Schema；
- Catalog 永远是固定四层。

统一使用 `parentAssetId` 沿父链解析：

- 无 Schema 模式：Dataset 的 `parentAssetId` 指向 DataSource；
- 标准模式：Dataset 的 `parentAssetId` 指向 Schema；
- 多级隔离模式：Schema 的 `parentAssetId` 可以指向另一个 Schema。

`levelName` 来源于层级定义和资产查询接口，在多级 Schema 或业务自定义层级中可以条件保留，辅助定位具体层级语义。

### 7.2 catalogContext 结构

```json
{
  "dataSources": [],
  "schemas": [],
  "datasets": [],
  "fields": []
}
```

数组按实际目录组合使用：无 Schema 模式可以省略 `schemas`。

### 7.3 DataSource

| 字段 | 类型 | 必填 | 来源与处理 |
|---|---|:---:|---|
| `id` | string | 是 | 由 `id` 或 `assetId` 归一化 |
| `name` | string | 条件 | 规范示例和数据源查询接口定义；执行需要时保留 |
| `displayName` | string | 否 | 默认裁剪 |
| `datasourceType` | string | 条件 | Binding 示例或 `connectionConfig` 中定义；执行选择数据源适配器时保留 |
| `parentAssetId` | string | 否 | 顶级数据源通常省略 |
| `levelName` | string | 否 | 多层模型定位需要时保留 |
| `connectionConfig` | object | 条件 | 执行连接需要时保留 |
| `description` | string | 否 | 默认裁剪 |
| `extendAttribute` | object | 否 | 由对象或合法 JSON 字符串归一化；执行需要时保留 |

`connectionConfig` 已定义字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `connectionType` | string | `DataCube` / `ADCDataModel` |
| `name` | string | DataCube 数据源名称 |
| `datasourceId` | string | DataCube 数据源 ID |
| `datasourceType` | string | 数据源类型 |
| `modelType` | string | 模型类型 |

不在 Binding 中增加密码、Token、私钥等新字段。

### 7.4 Schema

| 字段 | 类型 | 必填 | 来源与处理 |
|---|---|:---:|---|
| `id` | string | 是 | 由 `id` 或 `assetId` 归一化 |
| `parentAssetId` | string | 是 | 由 `parentAssetId`、`parentId` 或 Schema 示例的 `datasourceId` 归一化 |
| `name` | string | 是 | 保留 |
| `levelName` | string | 否 | 多级 Schema 时建议保留 |
| `displayName` | string | 否 | 默认裁剪 |
| `description` | string | 否 | 默认裁剪 |

### 7.5 Dataset

| 字段 | 类型 | 必填 | 来源与处理 |
|---|---|:---:|---|
| `id` | string | 是 | 由 `id` 或 `assetId` 归一化 |
| `parentAssetId` | string | 是 | 由 `parentAssetId`、`parentId` 或 Dataset 示例的 `schemaId` 归一化 |
| `name` | string | 是 | 保留 |
| `storageType` | string | 是 | 由 `storageType` 或 `datasetType` 归一化 |
| `levelName` | string | 否 | 自定义 dataset 层级需要时保留 |
| `primaryKeys` | string | 否 | 保留上游 JSON 数组格式字符串 |
| `displayName` | string | 否 | 默认裁剪 |
| `description` | string | 否 | 默认裁剪 |
| `extendAttribute` | object | 否 | 由对象或合法 JSON 字符串归一化 |

已出现的存储类型包括：

```text
Table / View / Tag / Edge / Dimension
```

### 7.6 Field

| 字段 | 类型 | 必填 | 来源与处理 |
|---|---|:---:|---|
| `id` | string | 是 | 由 `id` 或 `assetId` 归一化 |
| `parentAssetId` | string | 是 | 由 `parentAssetId`、`parentId` 或 Field 示例的 `datasetId` 归一化 |
| `name` | string | 是 | 保留 |
| `dataType` | string | 是 | 保留 |
| `levelName` | string | 否 | 字段层级名称，如 column、property |
| `description` | string | 否 | 默认裁剪 |
| `sortOrder` | string | 否 | 默认裁剪 |
| `semanticRole` | string | 否 | `DIMENSION` / `MEASURE` / `TIMESTAMP` |
| `technicalType` | string | 否 | 物理字段类型，执行需要时保留 |
| `cubeContext` | object | 否 | 多维模型需要时保留 |
| `timeSeriesInfo` | object | 否 | 时序模型需要时保留 |
| `isPrimaryKey` | boolean | 否 | 来源于字段查询接口 |
| `isNullable` | boolean | 否 | 来源于字段查询接口 |
| `extendAttribute` | object | 否 | 由对象或合法 JSON 字符串归一化 |

`cubeContext` 已定义字段：

```text
attributeId / type / name / levelId / levelName
```

`timeSeriesInfo` 已定义字段：

```text
timeRole / format / timeValueType / interval
```

---

## 8. Binding 裁剪与完整性规则

### 8.1 类型收集

递归收集：

```text
ObjectTypes =
  objects[].objectType
  ∪ sourceQuery 中对象类型
  ∪ BATCH.items 中对象类型

RelationTypes =
  relationships[].relationshipType
  ∪ sourceQuery 中关系类型
  ∪ BATCH.items 中关系类型
```

去重后查询对应 Binding。

### 8.2 属性使用闭包

每个类型保留下列属性的并集：

```text
conditions 中 ref + field
conditions.left 中所有 FIELD
returns.FIELDS.fields
returns.EXPR.expr 中所有 FIELD
returns.FUNCTION.field 内 ID(...) / NAME(...) 的字段
returns.GROUP_BY 的 field 或 expr 中所有 FIELD
returns.METRIC.field（* 除外）
orders 中 ref + field
mutation.data.properties 的属性键
mutation.set 的属性键
mutation.matchBy
sourceQuery / BATCH.items 的递归字段
objectTypeContext.primaryKeys
```

### 8.3 Catalog 资产闭包

从以下 ID 出发：

```text
assetId
assetIds[]
timeseriesFieldId
junctionDatasetId
```

保留：

1. 直接引用的 Field 或 Dataset；
2. 通过 `parentAssetId` 可达的全部父资产；
3. 多级 Schema 的完整父链；
4. 执行所需 DataSource 连接配置；
5. 多维或时序执行所需 `cubeContext`、`timeSeriesInfo`。

### 8.4 允许和禁止的处理

允许：

- 删除未使用字段；
- 删除 `null`、空对象和无意义空数组；
- 按第 4.3 节归一化已明确同义的字段；
- 对资产和类型数组去重；
- 将规范明确为 JSON 字符串的 `extendAttribute` 解析为 object。

禁止：

- 新增上游没有的物理字段；
- 推断 Join Key、Edge、表名或列名；
- 把 `assetIds` 当作祖先链；
- 自行解释 `joinKeys`、`junctionConfig`、`relationProperties` 的内部 Schema；
- 根据数据源类型补造数据库方言字段；
- 缺少 Binding 时静默降级。

---

## 9. 完整请求示例：普通查询

```json
{
  "oql": {
    "version": "1.0",
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
              "name": "mysql_prod",
              "datasourceType": "MYSQL",
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
              "name": "sales_db",
              "levelName": "project"
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
              "technicalType": "BIGINT",
              "isPrimaryKey": true,
              "isNullable": false
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
    "version": "1.0",
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
              "name": "mysql_prod",
              "datasourceType": "MYSQL"
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
              "storageType": "Table"
            }
          ],
          "fields": [
            {
              "id": "field_order_id",
              "parentAssetId": "ds_order",
              "name": "order_id",
              "dataType": "BIGINT"
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
              "name": "mysql_prod",
              "datasourceType": "MYSQL"
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
              "storageType": "Table"
            }
          ],
          "fields": [
            {
              "id": "field_product_id",
              "parentAssetId": "ds_product",
              "name": "product_id",
              "dataType": "BIGINT"
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
              "name": "mysql_prod",
              "datasourceType": "MYSQL"
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
              "dataType": "INT"
            }
          ]
        }
      }
    ]
  }
}
```

> 关系执行所需的 Join 或 Edge 信息必须来自 `relationshipContext`、关系属性 Binding 或 Catalog。信息不足时不得自行补造。

---

## 11. 业务服务实现建议

### 11.1 DTO 分层

```java
public record ExecuteRequest(
    ThirdPartyOql oql,
    BindingsEnvelope bindings
) {}

public record ThirdPartyOql(
    String version,
    String operation,
    JsonNode objects,
    JsonNode relationships,
    JsonNode conditions,
    JsonNode returns,
    JsonNode aggregateFilter,
    JsonNode orders,
    JsonNode maxResults,
    JsonNode sourceQuery,
    JsonNode mutation,
    JsonNode items,
    JsonNode options,
    JsonNode extensions
) {}

public record BindingsEnvelope(
    List<ObjectTypeBindingData> objectTypes,
    List<RelationTypeBindingData> relationTypes
) {}
```

建议：

- OQL 可复用来源规范对应 DTO；
- 顶层明确不定义 `strict`、`schemaRef`；
- Binding DTO 使用本规范归一化后的 Catalog 字段；
- `joinKeys`、`junctionConfig`、`relationProperties` 使用 String；
- `extendAttribute` 使用 JSON object；
- DTO 忽略未来新增的可选 Binding 字段；
- OQL 顶层未知字段仍应按版本规则拒绝。

### 11.2 请求内索引

业务服务可构建只读索引：

```text
objectTypeContext.name          -> ObjectTypeBindingData
objectTypeContext.objectTypeId  -> ObjectTypeBindingData
relationshipContext.name        -> RelationTypeBindingData
relationshipContext.relationTypeId -> RelationTypeBindingData
catalogContext.*[].id           -> Catalog Asset
propertyName                    -> PropertyBinding
```

索引只是内部实现，不改变传输 JSON。

### 11.3 物理翻译要求

- 物理标识只能来自 Binding；
- 条件值必须参数化；
- 不得把 OQL 值当作表名、列名、Tag 或 Edge；
- 无 Schema 和多级 Schema 均通过 `parentAssetId` 链处理；
- 未请求的技术字段不得出现在业务返回属性中。

---

## 12. 校验与错误处理

### 12.1 OQL 校验

1. `version` 必须等于 `"1.0"`；
2. 顶层不得出现 `strict`、`schemaRef`、`linkQuery`、`having`；
3. `operation` 必须合法；
4. operation 所需字段必须完整；
5. alias 必须先声明后引用；
6. 对象、关系和属性必须能匹配 Binding；
7. 函数、聚合和聚合后过滤必须符合 OQL 来源规范；
8. 未使用字段必须省略。

### 12.2 Binding 校验

1. 对象类型和关系类型不能重复；
2. 类型名称与 ID 必须能够唯一建立索引；
3. 使用中的属性必须存在至少一条有效 Binding；
4. `assetId`、`assetIds`、`timeseriesFieldId`、`junctionDatasetId` 引用资产必须存在；
5. Catalog 父链必须完整，且支持无 Schema 和多级 Schema；
6. 字段归一化只能使用第 4.3 节映射；
7. `extendAttribute` 字符串必须是合法 JSON object 才能归一化；
8. 未定义关系配置不得推断。

### 12.3 错误码

| 错误码 | HTTP | 说明 |
|---|:---:|---|
| `INVALID_REQUEST` | 400 | 请求包络不合法 |
| `UNSUPPORTED_OQL_VERSION` | 400 | `oql.version` 不是 `1.0` |
| `UNSUPPORTED_OPERATION` | 400 | operation 不支持 |
| `OQL_VALIDATION_ERROR` | 400 | OQL 结构或语义不合法 |
| `OBJECT_BINDING_NOT_FOUND` | 400 | 对象 Binding 缺失 |
| `RELATION_BINDING_NOT_FOUND` | 400 | 关系 Binding 缺失 |
| `PROPERTY_BINDING_NOT_FOUND` | 400 | 属性 Binding 缺失 |
| `BINDING_AMBIGUOUS` | 400 | Binding 无法唯一确定 |
| `CATALOG_ASSET_NOT_FOUND` | 400 | Catalog 引用资产不存在 |
| `CATALOG_NORMALIZE_ERROR` | 400 | 已记录的同义字段无法归一化或值冲突 |
| `BINDING_FORMAT_ERROR` | 400 | Binding 字段类型或 JSON 字符串格式错误 |
| `BINDING_INCOMPLETE` | 400 | Binding 信息不足以生成物理查询 |
| `TRANSLATE_ERROR` | 500 | 物理查询翻译失败 |
| `EXECUTE_ERROR` | 500 | 物理执行失败 |
| `EXECUTE_TIMEOUT` | 504 | 物理执行超时 |

错误响应：

```json
{
  "success": false,
  "errors": [
    {
      "code": "CATALOG_NORMALIZE_ERROR",
      "message": "conflicting parent asset identifiers",
      "path": "bindings.objectTypes[0].catalogContext.datasets[0]",
      "details": {
        "id": "ds_table_001"
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

- 类型名称使用本体对象或关系名称；
- `properties` Key 使用 OQL 属性名或返回 alias；
- 未请求的主键、Join Key 等技术字段不得进入 `properties`；
- 对象 `rid` 必须稳定、可重复；
- 默认不返回原始物理查询和连接配置。

---

## 14. 平滑兼容与维护

### 14.1 版本规则

1. 当前三方 OQL 唯一版本为 `1.0`；
2. `version` 只在 OQL Body 中出现一次；
3. `strict` 和 `schemaRef` 不属于三方接口参数；
4. 新增可选 Binding 字段时，旧 DTO 必须能够忽略；
5. 新增可选包络字段必须具有默认行为；
6. 修改字段名称、类型、必填性或语义属于破坏性变更，必须发布新的主版本接口；
7. 上游规范变化必须先更新字段来源矩阵和契约测试，再修改三方接口。

### 14.2 Binding 兼容规则

- 根结构保持 `objectTypeContext/propertyBindings/catalogContext` 或 `relationshipContext/propertyBindings/catalogContext`；
- Catalog 对外只使用归一化字段 `id`、`parentAssetId`、`storageType`；
- 上游若继续返回已记录的同义字段，由 OAC 统一归一化，业务服务无需维护多套 Bean；
- 未列入归一化矩阵的新字段名不得自动映射；
- 同一资产同时出现多个同义字段且值不一致时，返回 `CATALOG_NORMALIZE_ERROR`；
- `joinKeys`、`junctionConfig`、`relationProperties` 保持不透明字符串，直到上游规范正式定义其结构。

### 14.3 文档同步检查

每次更新本规范必须检查：

```text
三方 OQL version = 1.0
三方 OQL 顶层字段不包含 strict/schemaRef
OQL operation 和嵌套语义来自 OQL 来源规范
对象 Binding 根字段来自对象 Binding 查询规范
关系 Binding 根字段来自关系 Binding 查询规范
Catalog 归一化字段均能在数据模型规范其他章节找到明确来源
请求示例中禁止 Binding 字段出现次数 = 0
JSON 示例全部可解析
```

---

## 15. 接入检查清单

### 请求与 OQL

- [ ] 使用 `POST /ontology-access/v1/execute`
- [ ] 使用 `application/json`
- [ ] 请求体只包含 `oql`、`bindings`
- [ ] `oql.version` 固定为 `1.0`
- [ ] OQL 不包含 `strict`
- [ ] OQL 不包含 `schemaRef`
- [ ] operation 和嵌套结构来源于 OQL 规范
- [ ] 未使用字段已省略

### Binding

- [ ] `objectTypes[]` 根结构来自对象 Binding 查询
- [ ] `relationTypes[]` 根结构来自关系 Binding 查询
- [ ] Catalog 支持无 Schema 和多级 Schema
- [ ] 只使用第 4.3 节同义字段归一化
- [ ] 不存在 `bindingKind`、`relationBindings`、`bindingMode`
- [ ] 不存在 `field_ids`、`queryDialect`、`connectionRef`、`storageLayout`
- [ ] `joinKeys`、`junctionConfig`、`relationProperties` 未被擅自解析
- [ ] Binding 不完整时明确报错

### 实现

- [ ] 所有物理标识来自 Binding
- [ ] 所有查询值参数化
- [ ] DTO 忽略新增可选 Binding 字段
- [ ] OQL 顶层未知字段按 1.0 规则拒绝
- [ ] 隐藏技术字段不泄露到响应
