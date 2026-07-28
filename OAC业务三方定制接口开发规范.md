# OAC 业务三方定制接口开发规范

> **文档版本**：1.0  
> **发布日期**：2026-07  
> **OQL 协议版本**：1.0  
> **Binding 协议版本**：1.0  
> **适用范围**：业务/三方数据访问服务对接 OAC 平台，实现 OQL 到物理查询（SQL、GQL、TQL 等）的转换与执行  
> **核心原则**：OQL 表达查询语义，Binding 表达物理映射；两者独立传输、独立演进

---

## 1. 目的与边界

本规范定义 OAC 平台与业务/三方数据访问服务之间的本体访问接口契约，指导业务方实现标准接口，完成以下处理：

1. 接收 OAC 下发的精简 OQL；
2. 接收与本次操作相关的最小 Runtime Binding；
3. 将本体对象、属性和关系翻译为物理 SQL、GQL、TQL 等查询；
4. 参数化执行物理查询；
5. 将物理结果组装为统一的本体对象和关系结果。

### 1.1 核心流程

```text
Agent / 上层应用
      │ 标准 OQL 1.0
      ▼
OAC 平台
      │ 从 OMS 查询完整 Canonical Binding
      │ 校验 OQL
      │ 选择唯一有效 Binding
      │ 按本次操作裁剪为 Runtime Binding
      ▼
业务三方服务（POST /ontology-access/v1/execute）
      │ 入参1：精简 OQL 1.0
      │ 入参2：Runtime Binding 1.0
      │ OQL + Binding → SQL/GQL/TQL
      │ 参数化执行
      │ 统一结果组装
      ▼
物理数据源
```

### 1.2 职责划分

| 组件 | 职责 |
|---|---|
| OAC 平台 | 接收标准 OQL、校验语义、从 OMS 获取完整 Binding、完成 Binding 唯一选择与裁剪、调用业务服务、汇总结果 |
| OMS | 管理本体模型、对象/关系绑定和完整 Catalog 资产信息，提供对象类型与关系类型 Binding 查询接口 |
| 业务三方服务 | 接收 OQL 与 Runtime Binding，实现物理查询翻译、参数化执行、结果组装和错误返回 |
| 物理数据源 | 提供关系型、图、时序、检索或多维数据访问能力 |

### 1.3 设计原则

1. **OQL 与 Binding 解耦**：OQL 不承载物理表、列、Tag、Edge 等标识。
2. **Runtime Binding 最小化**：仅下发本次执行所需的对象、属性、关系及 Catalog 资产闭包。
3. **对象与关系显式区分**：通过 `bindingKind` 区分 `OBJECT` 和 `RELATIONSHIP`。
4. **唯一 Binding**：OAC 下发前必须完成多 Binding 选择，业务侧不得依赖数组顺序猜测。
5. **物理标识受控**：物理标识只能来自 Binding，禁止从用户输入或 OQL values 构造。
6. **参数化执行**：条件值必须使用参数绑定，不得直接拼接。
7. **隐藏技术字段不泄露**：主键、Join 键、分区键等可参与执行，但未在 `returns` 中声明时不得返回。
8. **扩展字段受控**：1.0 基线之外的新增字段必须为可选字段；业务方反序列化时应忽略未知可选字段。
9. **结构化字段使用原生 JSON 类型**：数组、对象不得编码成 JSON 字符串。
10. **敏感配置不透传**：Binding 不携带数据库密码、Token、私钥等敏感连接信息。

---

## 2. 接口规范

### 2.1 接口端点

业务方必须提供：

| 端点 | 方法 | 用途 |
|---|---|---|
| `/ontology-access/v1/execute` | POST | 接收 OQL 与 Runtime Binding，执行本体访问操作 |

业务方可通过 OMS 模型注册接口登记服务地址，以覆盖平台默认地址。

### 2.2 请求头

| Header | 必填 | 说明 |
|---|:---:|---|
| `Content-Type` | 是 | 固定为 `multipart/form-data` |
| `X-Request-Id` | 是 | 全链路唯一请求标识 |
| `X-Tenant-Id` | 条件必填 | 多租户场景必填 |
| `X-Schema-Ref` | 是 | 本体模型标识，由 OAC 从原始 OQL 提取 |
| `X-OQL-Version` | 是 | 固定为 `1.0` |
| `X-Binding-Version` | 是 | 固定为 `1.0` |
| `X-Binding-Revision` | 否 | Binding 内容修订号，用于缓存失效和问题定位 |
| `X-Timeout-Ms` | 否 | 请求超时时间，单位毫秒 |
| `Idempotency-Key` | 写操作必填 | CREATE、UPDATE、DELETE、UPSERT 的幂等键 |

### 2.3 请求体

请求采用 `multipart/form-data`，包含两个独立 Part：

| Part | Content-Type | 说明 |
|---|---|---|
| `oql` | `application/json` | 精简 OQL 1.0，不包含 `schemaRef` 和 Binding |
| `binding` | `application/json` | 按 alias 组织的 Runtime Binding 1.0 |

```http
POST /ontology-access/v1/execute
Content-Type: multipart/form-data; boundary=----Boundary
X-Request-Id: 550e8400-e29b-41d4-a716-446655440000
X-Schema-Ref: fm-alarm-v1
X-OQL-Version: 1.0
X-Binding-Version: 1.0
X-Binding-Revision: 20260728-00015

------Boundary
Content-Disposition: form-data; name="oql"
Content-Type: application/json

{ "version": "1.0", "operation": "QUERY", "objects": [], "returns": [] }
------Boundary
Content-Disposition: form-data; name="binding"
Content-Type: application/json

{ "a": { "bindingKind": "OBJECT", "objectTypeContext": {}, "propertyBindings": [], "catalogContext": {} } }
------Boundary--
```

### 2.4 OQL 精简规则

| 原始信息 | 下发方式 |
|---|---|
| `schemaRef` | 移至 `X-Schema-Ref` |
| OQL 版本 | OQL 中保留 `version: "1.0"`，同时通过 `X-OQL-Version` 传递 |
| Binding | 独立放入 `binding` Part，不放入 `extensions` |
| 空 `extensions` | 默认省略 |
| 平台内部路由、缓存和鉴权信息 | 不进入 OQL |

### 2.5 鉴权

OAC 与业务服务位于 GDE 信任域时，服务证书统一使用 GDE 签发的二级根 CA。业务服务必须校验调用方身份，不得仅依赖网络可达性。

### 2.6 服务注册

```json
{
  "serviceId": "svc-alarm-access",
  "serviceName": "告警数据访问服务",
  "displayName": "Alarm Data Access Service",
  "endpoint": {
    "baseUrl": "https://alarm-access.example.com",
    "executePath": "/ontology-access/v1/execute"
  },
  "supportedOperations": [
    "QUERY",
    "AGGREGATE",
    "ASSOCIATION_QUERY",
    "CREATE",
    "UPDATE",
    "DELETE",
    "UPSERT"
  ],
  "supportedDatasourceTypes": [
    "MYSQL",
    "GAUSSDB",
    "NEBULAGRAPH"
  ],
  "maxLimit": 5000,
  "timeoutMs": 30000,
  "bindingVersions": ["1.0"],
  "oqlVersions": ["1.0"],
  "authentication": {
    "type": "MTLS",
    "certificateRef": "gde-ca-service-cert"
  }
}
```

### 2.7 Java Bean 实现要求

| 要求 | 说明 |
|---|---|
| 忽略未知字段 | Jackson 配置 `FAIL_ON_UNKNOWN_PROPERTIES = false` |
| 枚举安全 | 未识别枚举映射为 `UNKNOWN`，不得直接抛反序列化异常 |
| ConditionNode 多态 | 使用 `kind` 区分 `PREDICATE` 和 `GROUP` |
| 空值规范 | 空集合使用 `[]`；无值的可选对象或标量默认省略 |
| 结构化字段 | 数组、对象使用 JSON 原生类型，不使用 JSON 字符串 |
| 不可变模型 | 推荐 Java Record 或不可变 DTO |
| 敏感字段 | 不定义或接收明文密码、Token、私钥字段 |

推荐模型结构：

```text
model/
├── oql/
│   ├── OqlRequest.java
│   ├── OqlObject.java
│   ├── OqlRelationship.java
│   ├── ConditionNode.java
│   ├── PredicateCondition.java
│   ├── GroupCondition.java
│   └── ReturnItem.java
├── binding/
│   ├── BindingProjection.java
│   ├── ObjectTypeContext.java
│   ├── RelationshipContext.java
│   ├── ObjectBinding.java
│   ├── RelationBinding.java
│   ├── JoinKey.java
│   ├── PropertyBinding.java
│   ├── PhysicalBinding.java
│   └── CatalogContext.java
└── response/
    ├── OntologyAccessResponse.java
    ├── OntologyObject.java
    └── OntologyRelationship.java
```

---

## 3. 入参 1：OQL 1.0

### 3.1 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `version` | String | 是 | 固定为 `"1.0"` |
| `operation` | String | 是 | QUERY、AGGREGATE、ASSOCIATION_QUERY、CREATE、UPDATE、DELETE、UPSERT |
| `objects` | Array | 是 | 涉及的对象声明 |
| `relationships` | Array | 条件 | ASSOCIATION_QUERY 必填 |
| `conditions` | Object | 条件 | 查询过滤条件 |
| `returns` | Array | 查询类操作必填 | 返回字段、分组或指标 |
| `aggregateFilter` | Object | 否 | 聚合后过滤 |
| `orders` | Array | 否 | 排序 |
| `maxResults` | Object | 否 | `{ "limit": int, "offset": int }` |
| `sourceQuery` | Array | 否 | 前置子查询 |
| `mutation` | Object | 写操作必填 | 写操作定义 |
| `options` | Object | 否 | 受控扩展选项 |
| `extensions` | Object | 否 | 预留扩展，默认省略，不用于传递 Binding |

### 3.2 objects

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `objectType` | String | 是 | 本体对象类型名称 |
| `alias` | String | 是 | OQL 内唯一别名 |
| `fromSource` | String | 否 | 引用 `sourceQuery` 的输出 |

### 3.3 relationships

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `relationshipType` | String | 是 | 本体关系类型名称 |
| `alias` | String | 是 | 关系别名 |
| `from` | String | 是 | 源对象 alias |
| `to` | String | 是 | 目标对象 alias |
| `direction` | String | 是 | OUTBOUND、INBOUND、BIDIRECTIONAL |
| `mode` | String | 否 | ONE 或 LIST，默认 LIST |

### 3.4 conditions

#### PREDICATE

```json
{
  "kind": "PREDICATE",
  "ref": "a",
  "field": "severity",
  "operator": "EQ",
  "values": ["critical"]
}
```

| 字段 | 说明 |
|---|---|
| `kind` | 固定为 `PREDICATE` |
| `ref` | 对象或关系 alias |
| `field` | 本体属性名 |
| `operator` | EQ、NE、GT、GTE、LT、LTE、IN、NOT_IN、BETWEEN、LIKE、IS_NULL、IS_NOT_NULL |
| `values` | 条件值列表 |
| `left` | 字段间比较的左侧表达式，可选 |
| `subquery` | 子查询，可选 |

#### GROUP

```json
{
  "kind": "GROUP",
  "relation": "AND",
  "children": []
}
```

`relation` 支持 AND、OR、NOT。

### 3.5 returns

| 字段 | 说明 |
|---|---|
| `kind` | FIELDS、EXPR、FUNCTION、GROUP_BY、METRIC |
| `ref` | 对象或关系 alias |
| `fields` | FIELDS 类型的属性列表 |
| `field` | GROUP_BY、METRIC 等类型的单属性 |
| `function` | COUNT、SUM、AVG、MAX、MIN |
| `alias` | 结果别名 |

### 3.6 operation 约束

| operation | 必含 | 禁含 |
|---|---|---|
| QUERY | objects、returns | relationships、aggregateFilter、mutation |
| AGGREGATE | objects、returns | relationships、mutation |
| ASSOCIATION_QUERY | objects、relationships、returns | mutation |
| CREATE | objects、mutation | — |
| UPDATE | objects、mutation、conditions | — |
| DELETE | objects、mutation、conditions | — |
| UPSERT | objects、mutation | — |

---

## 4. 入参 2：Runtime Binding 1.0

### 4.1 Binding 来源

OAC 从 OMS 调用以下接口获取完整 Canonical Binding：

| 接口 | 路径 |
|---|---|
| 查询对象类型绑定 | `/api/v1/ontologies/{ontologyId}/object-types/{objectTypeId}/bindings/query` |
| 查询关系类型绑定 | `/api/v1/ontologies/{ontologyId}/relation-types/{relationTypeId}/bindings/query` |

OAC 必须在下发业务服务前完成：

1. 绑定合法性校验；
2. 多 Binding 唯一选择；
3. 本次操作所需属性计算；
4. Catalog 资产闭包裁剪；
5. 结构与类型校验；
6. 敏感信息剔除。

### 4.2 顶层结构

Binding 顶层 Key 为 OQL alias。

```json
{
  "a": {
    "bindingKind": "OBJECT",
    "objectTypeContext": {},
    "propertyBindings": [],
    "catalogContext": {}
  },
  "r1": {
    "bindingKind": "RELATIONSHIP",
    "relationshipContext": {},
    "relationBindings": [],
    "propertyBindings": [],
    "catalogContext": {}
  }
}
```

| 字段 | 必填条件 | 说明 |
|---|---|---|
| `bindingKind` | 是 | OBJECT 或 RELATIONSHIP |
| `objectTypeContext` | OBJECT 必填 | 对象上下文和对象级 Dataset 绑定 |
| `relationshipContext` | RELATIONSHIP 必填 | 关系上下文 |
| `relationBindings` | RELATIONSHIP 必填 | 关系的直接、桥接或图边映射 |
| `propertyBindings` | 是 | 本次执行所需属性映射 |
| `catalogContext` | 是 | 本次执行依赖的最小物理资产闭包 |

### 4.3 objectTypeContext

```json
{
  "objectTypeId": "obj_alarm",
  "name": "Alarm",
  "primaryKeys": ["alarmId"],
  "bindings": [
    {
      "assetId": "dataset_alarm",
      "role": "PRIMARY"
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `objectTypeId` | 是 | 本体对象类型 ID |
| `name` | 否 | 本体对象类型名称，便于诊断 |
| `primaryKeys` | 是 | 本体主键属性名数组 |
| `bindings` | 是 | 对象到物理 Dataset 的映射 |
| `bindings[].assetId` | 是 | 必须指向 `catalogContext.datasets` 中的 Dataset |
| `bindings[].role` | 是 | PRIMARY 或 EXTENSION |

约束：

- 每个对象必须且只能有一个 `PRIMARY` Dataset；
- 对象级 Binding 不承载字段 ID、表达式或时序字段；
- `description` 等展示信息默认不下发。

### 4.4 propertyBindings

```json
[
  {
    "propertyId": "prop_alarm_id",
    "propertyName": "alarmId",
    "dataType": "STRING",
    "bindings": [
      {
        "bindingId": "pb_001",
        "assetId": "field_alarm_id"
      }
    ]
  }
]
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `propertyId` | 是 | 本体属性 ID |
| `propertyName` | 是 | 本体属性名，翻译时的关键索引 |
| `dataType` | 是 | 本体逻辑数据类型 |
| `bindings` | 是 | 标准物理绑定；无绑定时为 `[]` |
| `bindings[].bindingId` | 否 | Binding 记录 ID，用于诊断 |
| `bindings[].assetId` | 条件 | 单物理字段映射，指向 Field |
| `bindings[].assetIds` | 条件 | 多物理字段映射，按表达式参数顺序排列 |
| `bindings[].expression` | 条件 | 多字段计算或类型转换表达式 |
| `bindings[].timeseriesFieldId` | 否 | 时序属性依赖的时间字段 ID |
| `bindings[].joinKeys` | 否 | 属性自身跨 Dataset 时的 Join 定义 |
| `bindings[].extendAttribute` | 否 | 仅允许白名单扩展，空对象默认省略 |

约束：

- `assetId` 与 `assetIds` 至少存在一个，且不得表达 Catalog 层级路径；
- Catalog 层级路径必须通过 `parentAssetId` 追溯；
- Runtime Binding 中每个属性必须只有一个有效 `PhysicalBinding`；
- 无法唯一选择时 OAC 返回 `BIND-AMBIGUOUS-001`；
- 业务侧不得按 `bindings[0]` 猜测优先级，只能在数组长度为 1 时使用。

### 4.5 relationshipContext

```json
{
  "relationTypeId": "rel_order_product",
  "name": "order_has_product",
  "sourceObjectTypeId": "obj_order",
  "targetObjectTypeId": "obj_product",
  "connectionType": "OBJECT_TO_OBJECT"
}
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `relationTypeId` | 是 | 关系类型 ID |
| `name` | 否 | 关系类型名称 |
| `sourceObjectTypeId` | 是 | 源对象类型 ID |
| `targetObjectTypeId` | 是 | 目标对象类型 ID |
| `connectionType` | 是 | OBJECT_TO_OBJECT 或 PROPERTY_TO_PROPERTY |
| `backingObjectTypeId` | 否 | 关系由中间对象承载时使用 |
| `junctionDatasetId` | 否 | 关系由桥接 Dataset 承载时使用 |

`junctionConfig`、`relationProperties` 等结构化信息不得使用 JSON 字符串；需要下发时必须分别使用 Object 和 Array。

### 4.6 relationBindings

#### 4.6.1 DIRECT：主外键直接关联

```json
[
  {
    "bindingMode": "DIRECT",
    "joinKeys": [
      {
        "sourceFieldId": "field_order_customer_id",
        "targetFieldId": "field_customer_id"
      }
    ]
  }
]
```

#### 4.6.2 JUNCTION：桥接表关联

```json
[
  {
    "bindingMode": "JUNCTION",
    "junctionDatasetId": "dataset_order_product",
    "sourceJoinKeys": [
      {
        "sourceFieldId": "field_order_id",
        "junctionFieldId": "field_junction_order_id"
      }
    ],
    "targetJoinKeys": [
      {
        "junctionFieldId": "field_junction_product_id",
        "targetFieldId": "field_product_id"
      }
    ]
  }
]
```

#### 4.6.3 BACKING_OBJECT：中间对象关联

```json
[
  {
    "bindingMode": "BACKING_OBJECT",
    "backingObjectTypeId": "obj_order_product",
    "junctionDatasetId": "dataset_order_product",
    "sourceJoinKeys": [],
    "targetJoinKeys": []
  }
]
```

#### 4.6.4 GRAPH_EDGE：图数据库边

```json
[
  {
    "bindingMode": "GRAPH_EDGE",
    "edgeDatasetId": "dataset_installed_on"
  }
]
```

约束：

- Runtime Binding 中每个关系 alias 只能保留一个有效 `relationBinding`；
- Join Key 必须通过 Field ID 引用，不直接携带用户输入的表名和列名；
- Join Key 引用的所有 Field 及其祖先资产必须包含在 `catalogContext` 中。

### 4.7 catalogContext

Catalog 统一使用以下层级：

```text
DataSource → Schema → Dataset → Field
```

统一通过 `parentAssetId` 表达父子关系，不使用层级专用父字段。

#### DataSource

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `id` | 是 | 数据源 ID |
| `datasourceType` | 是 | MYSQL、GAUSSDB、NEBULAGRAPH、ELASTICSEARCH、API、CUBE 等产品类型 |
| `queryDialect` | 否 | SQL、NGQL、TQL、ESDSL 等 |
| `connectionRef` | 否 | 业务侧安全配置引用，不是明文连接信息 |

不得下发密码、Token、私钥或完整敏感连接串。

#### Schema

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `id` | 是 | Schema ID |
| `parentAssetId` | 是 | 所属 DataSource ID |
| `name` | 是 | 物理 Schema、库或命名空间名称 |

#### Dataset

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `id` | 是 | Dataset ID |
| `parentAssetId` | 是 | 所属 Schema ID |
| `name` | 是 | 表、视图、Tag、Edge 或 Dimension 名称 |
| `storageType` | 是 | TABLE、VIEW、TAG、EDGE、DIMENSION |
| `storageLayout` | 否 | ROW、COLUMN 等物理布局 |
| `primaryKeys` | 否 | 物理主键字段名数组 |

#### Field

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `id` | 是 | Field ID |
| `parentAssetId` | 是 | 所属 Dataset ID |
| `name` | 是 | 物理字段或属性名称 |
| `dataType` | 是 | 物理数据类型 |
| `semanticRole` | 否 | PRIMARY_KEY、FOREIGN_KEY、DIMENSION、MEASURE、TIMESTAMP |
| `timeSeriesInfo` | 否 | 时序字段的格式、时间角色和粒度 |

### 4.8 Runtime Binding 最小字段集

| 区域 | 必须保留 | 条件保留 | 默认删除 |
|---|---|---|---|
| objectTypeContext | objectTypeId、primaryKeys、对象 Dataset Binding | name | description |
| propertyBindings | propertyId、propertyName、dataType、assetId/assetIds | expression、timeseriesFieldId、joinKeys | groupId、空 extendAttribute |
| relationshipContext | relationTypeId、source/target ID、connectionType | backingObjectTypeId、junctionDatasetId、name | description、展示名称 |
| relationBindings | bindingMode 和对应 Join/Edge 信息 | — | 无关关系映射 |
| DataSource | id、datasourceType | queryDialect、connectionRef | displayName、description、敏感连接配置 |
| Schema | id、parentAssetId、name | — | displayName、description |
| Dataset | id、parentAssetId、name、storageType | storageLayout、primaryKeys | displayName、description |
| Field | id、parentAssetId、name、dataType | semanticRole、timeSeriesInfo | displayName、description、sortOrder |

### 4.9 Binding 裁剪规则

OAC 必须按以下集合计算所需属性：

```text
RequiredProperties =
    OQL 显式引用属性
  ∪ 对象主键属性
  ∪ 关系 Join 属性
  ∪ 时序字段
  ∪ 分区键和路由字段
  ∪ expression 依赖字段
  ∪ 写操作 matchBy 属性
  ∪ 结果组装所需隐藏字段
```

其中 OQL 显式引用属性至少包括：

```text
conditions
returns
orders
aggregateFilter
mutation
sourceQuery
```

裁剪步骤：

1. **按 alias 裁剪**：只保留本次 OQL 引用的对象和关系 alias；
2. **补齐技术字段**：即使未在 `returns` 中出现，也必须补齐主键、Join 键、时序字段等；
3. **按属性裁剪**：只保留 `RequiredProperties` 对应的 `propertyBindings`；
4. **按关系裁剪**：只保留当前关系 alias 唯一选中的 `relationBinding`；
5. **Catalog 闭包裁剪**：保留所引用 Field、Dataset、Schema、DataSource 及完整祖先链；
6. **敏感字段剔除**：删除明文凭据和非白名单扩展；
7. **结构校验**：校验统一字段名称、JSON 类型和 `parentAssetId` 链；
8. **唯一性校验**：对象 PRIMARY Dataset、属性 Binding、关系 Binding 均必须唯一。

主键、Join 键等隐藏技术字段可加入物理 SELECT，但最终响应只输出 `returns` 显式声明的属性。

---

## 5. 响应规范

### 5.1 成功响应

```json
{
  "code": 20000,
  "message": "Success",
  "data": {
    "taskStatus": "SUCCESS",
    "objects": [
      {
        "rid": "Alarm-ALM-001",
        "objectType": "Alarm",
        "properties": {
          "alarmName": "CPU高温告警",
          "severity": "critical"
        }
      }
    ],
    "relationships": [],
    "metadata": {
      "totalCount": 1,
      "successTaskCount": 1,
      "failedTaskCount": 0
    },
    "trace": {
      "requestId": "req-001",
      "executionTime": 85
    }
  },
  "errors": []
}
```

### 5.2 失败响应

```json
{
  "code": 40010030201,
  "message": "validation failed",
  "data": {
    "taskStatus": "FAILED",
    "objects": [],
    "relationships": [],
    "metadata": {
      "totalCount": 0,
      "successTaskCount": 0,
      "failedTaskCount": 1
    },
    "trace": {
      "requestId": "req-001",
      "executionTime": 12
    }
  },
  "errors": [
    {
      "code": "BIND-PROP-001",
      "message": "property binding not found",
      "path": "$.binding.a.propertyBindings",
      "details": {}
    }
  ]
}
```

### 5.3 响应约束

| 约束 | 说明 |
|---|---|
| `objectType` | 返回本体对象类型，不得返回物理表名 |
| `properties` | Key 使用本体属性名或 OQL 结果 alias |
| `rid` | 必须由对象类型和主键值稳定生成，不得使用随机 UUID |
| `sourceId/targetId` | 必须引用已返回对象的 rid |
| 字段安全 | 隐藏技术字段不得泄露到 properties |
| 物理语句 | 默认不得返回原始 SQL、GQL、TQL |
| 错误信息 | 不得包含密码、Token、完整连接串 |

---

## 6. 开发指导

### 6.1 Controller

```java
@PostMapping("/execute")
public OntologyAccessResponse execute(
        @RequestHeader("X-Request-Id") String requestId,
        @RequestHeader(value = "X-Tenant-Id", required = false) String tenantId,
        @RequestHeader("X-Schema-Ref") String schemaRef,
        @RequestHeader("X-OQL-Version") String oqlVersion,
        @RequestHeader("X-Binding-Version") String bindingVersion,
        @RequestHeader(value = "X-Binding-Revision", required = false) String bindingRevision,
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @RequestPart("oql") String oqlJson,
        @RequestPart("binding") String bindingJson) {

    OqlRequest oql = JsonUtil.fromJson(oqlJson, OqlRequest.class);
    Map<String, BindingProjection> bindings =
        JsonUtil.fromJsonMap(bindingJson, BindingProjection.class);

    return service.execute(
        oql, bindings, requestId, tenantId, schemaRef,
        oqlVersion, bindingVersion, bindingRevision, idempotencyKey);
}
```

### 6.2 翻译器选择

`datasourceType` 表示具体产品类型，不能直接假设为 `rdb` 或 `graph`。建议使用注册表：

```java
Translator translator = translatorRegistry.get(datasource.datasourceType())
    .orElseThrow(() -> error(
        "TRANS-001",
        "unsupported datasourceType: " + datasource.datasourceType()));
```

示例映射：

```text
MYSQL         → SqlTranslator
GAUSSDB       → SqlTranslator
NEBULAGRAPH   → NgqlTranslator
ELASTICSEARCH → EsTranslator
```

### 6.3 对象主 Dataset 解析

物理 FROM、Tag 等入口必须来自 `objectTypeContext.bindings[role=PRIMARY]`，不得通过第一个返回属性反推。

```java
ObjectBinding primary = bp.objectTypeContext().bindings().stream()
    .filter(b -> "PRIMARY".equals(b.role()))
    .findFirst()
    .orElseThrow(() -> error("BIND-OBJ-001", "primary dataset missing"));

DatasetAsset dataset = findById(bp.catalogContext().datasets(), primary.assetId());
```

### 6.4 属性解析

```java
public ResolvedField resolveField(
        String alias,
        String propertyName,
        Map<String, BindingProjection> bindings) {

    BindingProjection bp = requireObjectBinding(alias, bindings);

    PropertyBinding property = bp.propertyBindings().stream()
        .filter(p -> p.propertyName().equals(propertyName))
        .findFirst()
        .orElseThrow(() -> error(
            "BIND-PROP-001", "property not found: " + alias + "." + propertyName));

    if (property.bindings().size() != 1) {
        throw error("BIND-AMBIGUOUS-001",
            "property binding must be unique: " + alias + "." + propertyName);
    }

    PhysicalBinding physical = property.bindings().getFirst();
    if (physical.assetId() == null) {
        throw error("BIND-PROP-001",
            "single field mapping requires assetId: " + alias + "." + propertyName);
    }

    CatalogContext catalog = bp.catalogContext();
    FieldAsset field = findById(catalog.fields(), physical.assetId());
    DatasetAsset dataset = findById(catalog.datasets(), field.parentAssetId());
    SchemaAsset schema = findById(catalog.schemas(), dataset.parentAssetId());
    DataSourceAsset dataSource =
        findById(catalog.dataSources(), schema.parentAssetId());

    return new ResolvedField(
        alias,
        propertyName,
        property.dataType(),
        dataSource.datasourceType(),
        schema.name(),
        dataset.name(),
        field.name());
}
```

### 6.5 关系解析

```java
BindingProjection relation = bindings.get(relationship.alias());

if (relation == null
        || !"RELATIONSHIP".equals(relation.bindingKind())
        || relation.relationBindings().size() != 1) {
    throw error("BIND-REL-001",
        "unique relationship binding required: " + relationship.alias());
}

RelationBinding physicalRelation = relation.relationBindings().getFirst();
```

关系型数据库根据 `DIRECT`、`JUNCTION`、`BACKING_OBJECT` 生成 Join；图数据库根据 `GRAPH_EDGE.edgeDatasetId` 解析 Edge 名称。

---

## 7. QUERY 翻译示例

### 7.1 输入 OQL

```json
{
  "version": "1.0",
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Alarm",
      "alias": "a"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "a",
        "field": "severity",
        "operator": "EQ",
        "values": ["critical"]
      },
      {
        "kind": "PREDICATE",
        "ref": "a",
        "field": "occurTime",
        "operator": "GTE",
        "values": ["2026-01-01T00:00:00Z"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "a",
      "fields": ["alarmName", "severity"]
    }
  ],
  "orders": [
    {
      "ref": "a",
      "field": "occurTime",
      "direction": "DESC"
    }
  ],
  "maxResults": {
    "limit": 100,
    "offset": 0
  }
}
```

虽然 `alarmId` 未在 `returns` 中声明，OAC 仍必须将其作为主键隐藏字段加入 Runtime Binding 和物理查询，用于生成稳定 rid。

### 7.2 Runtime Binding

```json
{
  "a": {
    "bindingKind": "OBJECT",
    "objectTypeContext": {
      "objectTypeId": "obj_alarm",
      "name": "Alarm",
      "primaryKeys": ["alarmId"],
      "bindings": [
        {
          "assetId": "dataset_alarm",
          "role": "PRIMARY"
        }
      ]
    },
    "propertyBindings": [
      {
        "propertyId": "prop_alarm_id",
        "propertyName": "alarmId",
        "dataType": "STRING",
        "bindings": [
          {
            "bindingId": "pb_001",
            "assetId": "field_alarm_id"
          }
        ]
      },
      {
        "propertyId": "prop_alarm_name",
        "propertyName": "alarmName",
        "dataType": "STRING",
        "bindings": [
          {
            "bindingId": "pb_002",
            "assetId": "field_alarm_name"
          }
        ]
      },
      {
        "propertyId": "prop_severity",
        "propertyName": "severity",
        "dataType": "STRING",
        "bindings": [
          {
            "bindingId": "pb_003",
            "assetId": "field_severity"
          }
        ]
      },
      {
        "propertyId": "prop_occur_time",
        "propertyName": "occurTime",
        "dataType": "TIMESTAMP",
        "bindings": [
          {
            "bindingId": "pb_004",
            "assetId": "field_occur_time"
          }
        ]
      }
    ],
    "catalogContext": {
      "dataSources": [
        {
          "id": "datasource_mysql",
          "datasourceType": "MYSQL",
          "queryDialect": "SQL",
          "connectionRef": "alarm-mysql-prod"
        }
      ],
      "schemas": [
        {
          "id": "schema_alarm",
          "parentAssetId": "datasource_mysql",
          "name": "fm_alarm_db"
        }
      ],
      "datasets": [
        {
          "id": "dataset_alarm",
          "parentAssetId": "schema_alarm",
          "name": "t_alarm",
          "storageType": "TABLE",
          "storageLayout": "ROW",
          "primaryKeys": ["alarm_id"]
        }
      ],
      "fields": [
        {
          "id": "field_alarm_id",
          "parentAssetId": "dataset_alarm",
          "name": "alarm_id",
          "dataType": "VARCHAR(64)",
          "semanticRole": "PRIMARY_KEY"
        },
        {
          "id": "field_alarm_name",
          "parentAssetId": "dataset_alarm",
          "name": "alarm_name",
          "dataType": "VARCHAR(128)"
        },
        {
          "id": "field_severity",
          "parentAssetId": "dataset_alarm",
          "name": "severity",
          "dataType": "VARCHAR(32)"
        },
        {
          "id": "field_occur_time",
          "parentAssetId": "dataset_alarm",
          "name": "occur_time",
          "dataType": "TIMESTAMP",
          "semanticRole": "TIMESTAMP"
        }
      ]
    }
  }
}
```

### 7.3 输出 SQL

```sql
SELECT
    a.alarm_id AS __pk_alarmId,
    a.alarm_name AS alarmName,
    a.severity AS severity
FROM fm_alarm_db.t_alarm a
WHERE a.severity = ?
  AND a.occur_time >= ?
ORDER BY a.occur_time DESC
LIMIT 100 OFFSET 0
```

参数：

```json
["critical", "2026-01-01T00:00:00Z"]
```

`__pk_alarmId` 仅用于生成 rid，不进入响应 `properties`。

---

## 8. 结果组装

### 8.1 rid 生成

```java
public String generateRid(
        String objectType,
        Map<String, Object> technicalValues,
        List<String> primaryKeys) {

    String key = primaryKeys.stream()
        .map(pk -> Objects.toString(technicalValues.get(pk), ""))
        .collect(Collectors.joining("|"));

    if (key.isBlank()) {
        throw error("RESULT-MAP-001", "primary key value missing");
    }

    return objectType + "-" + key;
}
```

禁止使用随机 UUID 替代稳定 rid。

### 8.2 返回字段过滤

结果组装分为两套映射：

1. `technicalValues`：包含主键、Join 键等隐藏字段，仅供 rid 和关系组装使用；
2. `properties`：只包含 OQL `returns` 显式声明的属性。

---

## 9. 安全规范

### 9.1 参数化查询

禁止：

```java
"WHERE severity = '" + value + "'"
```

必须：

```java
"WHERE severity = ?"
params.add(value);
```

### 9.2 物理标识符白名单

表名、列名、Schema、Tag、Edge 必须从 Runtime Binding 解析，不得来自：

- OQL `values`；
- 用户输入的动态字段名；
- URL 参数；
- `extensions` 中的任意字符串。

### 9.3 写操作安全

| 操作 | 必须检查 |
|---|---|
| CREATE | 必填属性、主键生成策略、幂等键 |
| UPDATE | conditions 非空、mutation.scope 存在、影响范围不超过阈值 |
| DELETE | conditions 非空、mutation.scope 存在、禁止无条件删除 |
| UPSERT | matchBy 属性存在且具有唯一 Binding |

### 9.4 连接信息

- Runtime Binding 只允许携带 `connectionRef`；
- 业务服务通过本地配置中心或密钥管理系统解析真实连接信息；
- 日志和错误信息中不得输出凭据或完整连接串。

---

## 10. 错误处理

| 错误码 | HTTP | 说明 |
|---|:---:|---|
| `OQL-VAL-001` | 400 | OQL 结构校验失败 |
| `OQL-REF-001` | 400 | alias 或属性引用不存在 |
| `OQL-OP-001` | 400 | operation 不支持 |
| `OQL-VERSION-001` | 400 | OQL 版本不支持 |
| `BIND-VERSION-001` | 400 | Binding 版本不支持 |
| `BIND-OBJ-001` | 400 | 对象 Binding 缺失或 PRIMARY Dataset 不唯一 |
| `BIND-PROP-001` | 400 | 属性 Binding 缺失 |
| `BIND-REL-001` | 400 | 关系 Binding 缺失 |
| `BIND-AMBIGUOUS-001` | 400 | 多 Binding 无法唯一选择 |
| `BIND-ASSET-001` | 400 | Catalog 资产闭包不完整 |
| `TRANS-001` | 500 | OQL 到物理查询转换失败 |
| `EXEC-001` | 500 | 物理查询执行失败 |
| `EXEC-TIMEOUT-001` | 504 | 查询超时 |
| `RESULT-MAP-001` | 500 | 结果映射失败 |
| `SEC-FIELD-001` | 403 | 访问未授权物理字段 |
| `WRITE-SCOPE-001` | 400 | 写操作范围不安全 |

JSONPath 示例：

```text
$.conditions.children[0].field
$.returns[1].fields[0]
$.binding.a.propertyBindings[2].bindings[0].assetId
$.binding.r1.relationBindings[0].joinKeys[0].sourceFieldId
```

---

## 11. 可观测性

每个请求至少记录：

```text
requestId=req-001
schemaRef=fm-alarm-v1
oqlVersion=1.0
bindingVersion=1.0
bindingRevision=20260728-00015
operation=QUERY
objectTypes=Alarm
datasourceType=MYSQL
dataset=t_alarm
translateMs=4
executeMs=85
assembleMs=3
objectCount=100
result=SUCCESS
```

日志不得记录 OQL 原始敏感值、数据库凭据或完整物理查询参数。

---

## 12. 测试规范

### 12.1 P0 契约测试

| 类别 | 场景 |
|---|---|
| OQL 反序列化 | QUERY、AGGREGATE、ASSOCIATION_QUERY、未知字段 |
| 条件多态 | PREDICATE、GROUP、AND/OR/NOT 嵌套 |
| 对象 Binding | 单 Dataset、PRIMARY 唯一、多 Dataset 扩展 |
| 属性 Binding | assetId、assetIds、表达式、无绑定 |
| 关系 Binding | DIRECT、JUNCTION、BACKING_OBJECT、GRAPH_EDGE |
| Catalog 闭包 | Field→Dataset→Schema→DataSource 完整追溯 |
| 裁剪 | returns 属性、主键隐藏字段、Join 键、时序字段 |
| 版本 | OQL 1.0、Binding 1.0、未知版本拒绝 |
| 唯一性 | 多属性 Binding、多关系 Binding 必须报错 |
| 结果组装 | 稳定 rid、隐藏字段不泄露 |

### 12.2 P1 测试

| 类别 | 场景 |
|---|---|
| 安全 | SQL 注入、标识符注入、敏感连接信息 |
| 写操作 | 幂等、范围限制、无条件删除拦截 |
| 性能 | 大属性对象裁剪、Catalog 去重、批量请求 |
| 扩展性 | 未知可选字段忽略、未知枚举安全处理 |

### 12.3 黄金语句

| ID | 场景 | 期望 |
|---|---|---|
| GOLD-SQL-001 | 单对象 QUERY | 参数化 SELECT + WHERE + LIMIT |
| GOLD-SQL-002 | 主键未返回 | SQL 包含隐藏主键，响应不泄露主键 |
| GOLD-SQL-003 | DIRECT 关系 | 按 sourceFieldId/targetFieldId 生成 JOIN |
| GOLD-SQL-004 | JUNCTION 关系 | 生成两段桥接 JOIN |
| GOLD-GQL-001 | GRAPH_EDGE | 使用 Binding 中的 Edge Dataset 生成图查询 |
| GOLD-WRITE-001 | UPDATE | 条件和影响范围校验通过后执行 |

---

## 13. 接入检查清单

### 接口

- [ ] 实现 `POST /ontology-access/v1/execute`
- [ ] 支持 `multipart/form-data`
- [ ] 校验 `X-OQL-Version: 1.0`
- [ ] 校验 `X-Binding-Version: 1.0`
- [ ] 在 OMS 注册 endpoint、操作类型和数据源类型

### Binding

- [ ] 支持 `bindingKind`
- [ ] 对象 PRIMARY Dataset 唯一
- [ ] 属性 Binding 唯一
- [ ] 关系 Binding 唯一
- [ ] 使用 `assetId/assetIds`
- [ ] 使用 `parentAssetId` 追溯 Catalog
- [ ] 主键、Join 键、时序字段已补齐
- [ ] 明文连接配置未透传

### 翻译

- [ ] FROM/Tag 来源于对象级 PRIMARY Dataset
- [ ] 物理标识只从 Binding 解析
- [ ] 查询值全部参数化
- [ ] datasourceType 通过 Translator Registry 选择翻译器
- [ ] 隐藏技术字段不进入响应

### 结果

- [ ] rid 稳定、可重复生成
- [ ] properties 只包含 returns 声明字段
- [ ] 关系 sourceId/targetId 引用有效 rid

### 测试

- [ ] P0 契约测试通过
- [ ] 黄金语句测试通过
- [ ] 注入防御测试通过
- [ ] 写操作安全测试通过
- [ ] 未知可选字段和未知枚举测试通过

---

## 14. 版本基线与演进约束

### 14.1 初始版本基线

本规范的 `1.0` 是 OAC 业务三方定制接口的首次正式版本，也是当前唯一有效基线：

- OQL 协议版本固定为 `1.0`；
- Runtime Binding 协议版本固定为 `1.0`；
- 不存在历史版本迁移、旧字段转换或双协议并行处理；
- OAC、OMS 和业务三方服务必须直接按照本规范 1.0 实现；
- 服务注册中的 `oqlVersions` 和 `bindingVersions` 当前只允许声明 `1.0`。

### 14.2 版本一致性校验

业务服务必须校验以下版本信息一致：

```text
OQL.version == X-OQL-Version == 1.0
X-Binding-Version == 1.0
```

校验规则：

1. 缺少版本 Header 时拒绝请求；
2. OQL Body 与 Header 版本不一致时返回 `OQL-VERSION-001`；
3. 不支持的 Binding 版本返回 `BIND-VERSION-001`；
4. 不允许自动降级、字段别名转换或隐式协议推断；
5. Binding 内容修订通过 `X-Binding-Revision` 标识，不改变协议版本。

### 14.3 后续版本演进原则

后续如需演进协议，应遵循以下规则：

- 在不改变既有字段语义的前提下，可增加可选字段或新增枚举值；
- 字段改名、字段类型变化、必填性变化或语义变化属于破坏性变更，必须发布新的主版本规范；
- 新版本必须通过服务注册显式声明支持范围；
- OAC 只能向业务服务下发双方均明确支持的版本；
- 不得在 1.0 报文中混入其他版本专属字段并依赖业务侧猜测处理。

### 14.4 未知字段和枚举处理

- 未知可选字段：忽略，并可记录 debug 日志；
- 未知必需语义：返回明确的结构或版本错误；
- 未知枚举：反序列化为 `UNKNOWN`，随后由业务能力校验决定是否拒绝；
- 不得因为新增展示性可选字段导致反序列化失败。

### 14.5 Binding 缓存

业务服务可使用以下组合缓存 Binding 解析结果：

```text
X-Schema-Ref
+ X-Binding-Version
+ X-Binding-Revision
+ alias
```

当 `X-Binding-Revision` 变化时，必须使对应旧缓存失效。

---

## 15. 完整请求示例

```http
POST /ontology-access/v1/execute
Content-Type: multipart/form-data
X-Request-Id: req-001
X-Tenant-Id: tenant-001
X-Schema-Ref: fm-alarm-v1
X-OQL-Version: 1.0
X-Binding-Version: 1.0
X-Binding-Revision: 20260728-00015
```

OQL 和 Binding 参见第 7 章示例。

---

## 16. 参考规范

| 规范 | 说明 |
|---|---|
| 数据模型对接本体知识平台规范 1.0 | OMS Canonical Binding 查询结构与建模对接方式 |
| 本体对象操作语言（OQL）DSL 规范 1.0 | OQL 完整语法 |
| OAC 业务三方定制接口开发规范 1.0 | OAC 到业务服务的 Runtime 接口契约 |
