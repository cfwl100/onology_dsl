# OAC 业务三方定制接口开发规范

> **文档版本**：1.0
> **发布日期**：2026-07
> **OQL 基线版本**：2.0
> **适用范围**：业务/三方数据访问服务对接 OAC 平台，实现 OQL 到物理查询（SQL/GQL/TQL 等）转换的接口开发
> **核心原则**：接口参数格式由 RESTful 规范约定，业务方自行实现 Java Bean 和翻译逻辑

---

## 1. 目的

本规范定义 OAC 平台与业务/三方数据访问服务之间的**本体访问接口契约**，指导业务方实现标准接口，完成 OQL 到物理查询的转换。

### 1.1 核心流程

```text
Agent / 上层应用
      │ 标准 OQL
      ▼
OAC 平台
      │ 从 OMS 获取完整 Binding
      │ 校验 OQL 结构
      │ 按 OQL 实际引用裁剪 Binding
      ▼
业务三方服务（POST /ontology-access/v1/execute）
      │ 入参1: 精简 OQL（去除了 schemaRef）
      │ 入参2: 裁剪后的 Binding 映射
      │ 业务自定义：OQL → 物理 SQL/GQL/TQL
      │ 参数化执行物理查询
      │ 组装统一响应格式
      ▼
物理数据源（MySQL/GaussDB/NebulaGraph/...）
```

### 1.2 职责划分

| 组件 | 职责 |
|------|------|
| **OAC 平台** | 接收标准 OQL → 校验 → 裁剪 Binding → 下发（精简 OQL + 最小 Binding）两个独立参数 → 汇总结果 |
| **OMS** | 管理本体模型及完整 Binding 信息 |
| **业务三方服务** | 按本规范定义接口 → 自建 Java Bean 接收参数 → 实现 OQL 到物理查询的翻译逻辑 → 执行查询 → 返回统一响应 |

### 1.3 设计原则

1. **OQL 与 Binding 解耦**：OQL 和 Binding 作为两个独立入参传递，各自独立演进
2. **OQL 精简**：OQL 仅保留查询语义核心字段，去除 `schemaRef` 等平台内部字段
3. **接口优先**：参数格式通过 RESTful 接口规范约定，业务方直接据此实现 Java Bean
4. **不修改 OQL 语法**：不新增顶层字段、operation、kind、条件操作符
5. **不增加第二套查询 DSL**：不定义新的对外 JSON 查询协议
6. **Binding 最小化**：OAC 只传递本次执行必要的对象、属性、关系和 Catalog 信息
7. **物理标识受控**：物理表名、列名、Tag、Edge 只能来自 Binding
8. **参数化执行**：OQL 中的值不得直接拼接到物理查询语句

---

## 2. 接口规范

### 2.1 接口端点

业务方**必须**提供以下端点：

| 端点 | 方法 | 用途 | 说明 |
|------|------|------|------|
| `/ontology-access/v1/execute` | POST | 执行本体查询 | 核心接口，接收 OQL + Binding，返回查询结果 |
注：可以通过OMS的模型注册接口注册服务名和短点信息，覆盖默认的URL

### 2.2 请求格式

#### 2.2.1 请求头

| Header | 必填 | 说明 |
|--------|:---:|------|
| `Content-Type` | 是 | `multipart/form-data` |
| `X-Request-Id` | 是 | 全链路唯一请求标识（UUID） |
| `X-Tenant-Id` | 条件必填 | 多租户场景的租户标识 |
| `X-Schema-Ref` | 是 | 本体模型标识，如 `"fm-alarm-v1"`，由 OAC 从原始 OQL 中提取后通过 Header 传递 |
| `X-Binding-Version` | 是 | Binding 协议版本，如 `"v0.94"` |
| `X-Timeout-Ms` | 否 | 请求超时，单位毫秒 |
| `Idempotency-Key` | 写操作必填 | 幂等键，用于 CREATE/UPDATE/DELETE/UPSERT |

#### 2.2.2 请求体

采用 `multipart/form-data` 格式，包含两个独立 Part：

| Part 名称 | Content-Type | 说明 |
|-----------|-------------|------|
| `oql` | `application/json` | **入参 1**：精简 OQL 结构。去除 `schemaRef` 等平台内部字段，仅保留查询语义核心字段。完整结构见 §3 |
| `binding` | `application/json` | **入参 2**：Binding 物理映射。按 OQL 中的 alias 组织，Key 为对象/关系 alias，Value 为裁剪后的 Binding 投影。完整结构见 §4 |

```http
POST /ontology-access/v1/execute
Content-Type: multipart/form-data; boundary=----Boundary
X-Request-Id: 550e8400-e29b-41d4-a716-446655440000
X-Schema-Ref: fm-alarm-v1
X-Binding-Version: v0.94

------Boundary
Content-Disposition: form-data; name="oql"
Content-Type: application/json

{ "version": "2.0", "operation": "QUERY", "objects": [...], ... }
------Boundary
Content-Disposition: form-data; name="binding"
Content-Type: application/json

{ "a": { "objectTypeContext": {...}, "propertyBindings": [...], "catalogContext": {...} } }
------Boundary--
```

#### 2.2.3 字段精简说明

| 原 OQL 字段 | 处理方式 | 说明 |
|-------------|---------|------|
| `schemaRef` | 移至 Header `X-Schema-Ref` | 平台内部路由信息，无需进入 OQL 语义层 |
| `extensions` | 保留为空对象 | 预留未来扩展，当前不承载数据 |

### 2.3 接口鉴权

OAC 调用业务服务时需携带鉴权信息。业务方可根据自身环境选择鉴权方式：
当前属于GDE信任域内，认证的证书统一使用GDE签发的二级根CA。

### 2.5 接口注册

业务服务在 OMS 建模平台注册时，需声明以下信息：

```json
{
  "serviceId": "svc-alarm-access",
  "serviceName": "告警数据访问服务",
  "displayName": "Alarm Data Access Service",
  "endpoint": {
    "baseUrl": "https://alarm-access.example.com", //服务名
    "executePath": "/ontology-access/v1/execute"
  },
  "supportedOperations": ["QUERY", "AGGREGATE", "ASSOCIATION_QUERY", "CREATE", "UPDATE", "DELETE"],
  "supportedDatasourceTypes": ["rdb"],
  "maxLimit": 5000,
  "timeoutMs": 30000,
  "bindingVersions": ["v0.94"],
  "oqlVersions": ["2.0"],
  "authentication": {
    "type": "HMAC",
    "publicKeyRef": "key-001"
  }
}
```

### 2.6 接口实现要求

#### 2.6.1 Java Bean 自建

业务方根据本规范定义的参数 JSON schema（§3 入参1、§4 入参2）自行实现 Java Bean 类。推荐使用 **Java Record**（不可变、简洁）或 **Lombok @Data**。

**自建 Bean 的基本要求**：

| 要求 | 说明 |
|------|------|
| JSON 库兼容 | 支持 Jackson 或 Fastjson2 反序列化 |
| 忽略未知字段 | 配置 `FAIL_ON_UNKNOWN_PROPERTIES = false`，保证前向兼容 |
| ConditionNode 多态 | 使用 `@JsonTypeInfo` + `@JsonSubTypes` 正确区分 PREDICATE/GROUP |
| 枚举安全 | 使用字符串序列化，`valueOf` 失败时不应抛异常 |
| null 值处理 | 未使用字段不参与序列化 |

#### 2.6.2 推荐工程结构

```text
ontology-access-adapter/
├── controller/
│   └── OntologyAccessController.java   ← 接收 OQL + Binding，调用 Service
├── model/                             ← 业务方自行定义（参照本规范 §3、§4）
│   ├── oql/
│   │   ├── OqlRequest.java            ← OQL 顶层结构
│   │   ├── OqlObject.java
│   │   ├── OqlRelationship.java
│   │   ├── ConditionNode.java         ← sealed interface，多态根类型
│   │   ├── PredicateCondition.java
│   │   ├── GroupCondition.java
│   │   ├── ReturnItem.java
│   │   └── ...                         ← see §3 完整字段表
│   ├── binding/
│   │   ├── BindingProjection.java     ← Binding 投影
│   │   ├── ObjectTypeContext.java
│   │   ├── PropertyBinding.java
│   │   ├── CatalogContext.java
│   │   └── ...                         ← see §4 完整字段表
│   └── response/
│       ├── OntologyAccessResponse.java
│       ├── OntologyAccessData.java
│       ├── OntologyObject.java
│       └── OntologyRelationship.java
├── service/
│   └── OntologyAccessService.java      ← 编排：校验 → 映射 → 翻译 → 执行
├── translator/
│   ├── SqlTranslator.java              ← OQL → SQL 翻译器
│   ├── GqlTranslator.java              ← OQL → GQL 翻译器
│   └── ConditionTranslator.java        ← 条件翻译辅助
├── executor/
│   ├── PhysicalQuery.java              ← 内部物理查询对象
│   └── DataSourceExecutor.java         ← 数据源执行器
├── assembler/
│   ├── ObjectResultAssembler.java      ← 物理结果 → 本体对象
│   ├── RelationshipResultAssembler.java
│   └── RidGenerator.java               ← 稳定 rid 生成器
└── error/
    ├── OntologyAccessException.java    ← 统一异常类
    └── GlobalExceptionHandler.java     ← 异常 → 统一响应
```

---

## 3. 入参 1：OQL 结构定义

### 3.1 顶层字段

| 字段 | 类型 | 必填 | 说明                                                                             |
|------|------|:---:|--------------------------------------------------------------------------------|
| `version` | String | 是 | OQL 规范版本，当前 `"1.0"`                                                            |
| `operation` | String | 是 | 操作类型：QUERY / AGGREGATE / ASSOCIATION_QUERY / CREATE / UPDATE / DELETE / UPSERT |
| `objects` | Array\<Object\> | 是 | 查询涉及的对象声明                                                                      |
| `relationships` | Array\<Relationship\> | 条件 | 关系路径（ASSOCIATION_QUERY 必填，QUERY 禁止）                                            |
| `conditions` | Object | 条件 | 过滤条件（PREDICATE / GROUP）                                                        |
| `returns` | Array\<ReturnItem\> | 是 | 返回字段声明                                                                         |
| `aggregateFilter` | Object | 否 | 聚合后过滤（仅 AGGREGATE）                                                             |
| `orders` | Array\<OrderItem\> | 否 | 排序声明                                                                           |
| `maxResults` | Object | 否 | 分页：`{ "limit": int, "offset": int }`                                           |
| `sourceQuery` | Array\<OqlRequest\> | 否 | 前置子查询（递归结构）                                                                    |
| `linkQuery` | Object | 否 | 单跳关系查询（LINK_QUERY 操作使用）                                                        |
| `mutation` | Object | 条件 | 变更定义（写操作必填）                                                                    |
| `options` | Object | 否 | 扩展选项                                                                           |
| `extensions` | Object | 否 | 扩展字段（保留，当前接口不用于传递 Binding）                                                     |

> **精简说明**：OQL 已去除 `schemaRef`（改为 Header `X-Schema-Ref`）。Binding 独立作为入参 2 传递，不由 extensions 承载。

### 3.2 objects 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `objectType` | String | 是 | 本体对象类型名，如 `"Alarm"`、`"Order"` |
| `alias` | String | 是 | 对象别名，用于 OQL 内引用，如 `"a"`、`"o"` |
| `fromSource` | String | 否 | 来自 sourceQuery 结果时，引用其 `outputAs` |

### 3.3 relationships 结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `relationshipType` | String | 是 | 本体关系类型名，如 `"hasPort"` |
| `alias` | String | 是 | 关系别名，如 `"r1"` |
| `from` | String | 是 | 起始对象 alias |
| `to` | String | 是 | 目标对象 alias |
| `direction` | String | 是 | OUTBOUND / INBOUND / BIDIRECTIONAL |
| `mode` | String | 否 | ONE / LIST（默认 LIST） |

### 3.4 conditions 结构

#### PREDICATE（叶子条件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | String | 固定 `"PREDICATE"` |
| `ref` | String | 对象 alias |
| `field` | String | 本体属性名 |
| `operator` | String | 操作符 |
| `values` | Array | 条件值列表 |
| `left` | Object | 左侧表达式（可选，字段间比较时使用） |
| `subquery` | Object | 子查询（可选） |

**操作符表**：

| 操作符 | 含义 | values 要求 |
|--------|------|-----------|
| `EQ` | 等于 | 1 个值 |
| `NE` | 不等于 | 1 个值 |
| `GT` / `GTE` | 大于 / 大于等于 | 1 个值 |
| `LT` / `LTE` | 小于 / 小于等于 | 1 个值 |
| `IN` / `NOT_IN` | 在列表中 / 不在 | 多个值 |
| `BETWEEN` | 在范围内 | 2 个值 [min, max] |
| `LIKE` | 模糊匹配 | 1 个值 |
| `IS_NULL` / `IS_NOT_NULL` | 为空 / 不为空 | 0 个值 |

#### GROUP（组合条件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | String | 固定 `"GROUP"` |
| `relation` | String | AND / OR / NOT |
| `children` | Array\<ConditionNode\> | 子条件列表 |

### 3.5 returns 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | String | FIELDS / EXPR / FUNCTION / GROUP_BY / METRIC |
| `ref` | String | 对象 alias |
| `fields` | Array\<String\> | 属性名列表（FIELDS 类型） |
| `field` | String | 单个属性名（GROUP_BY / METRIC 类型） |
| `function` | String | 聚合函数（METRIC 类型）：COUNT / SUM / AVG / MAX / MIN |
| `alias` | String | 结果别名 |

### 3.6 操作类型约束

| operation | 必含 | 禁含 |
|-----------|------|------|
| QUERY | objects, returns | relationships, aggregateFilter, mutation |
| AGGREGATE | objects, returns(GROUP_BY+METRIC) | relationships, mutation |
| ASSOCIATION_QUERY | objects, relationships, returns | mutation |
| CREATE | objects, mutation | — |
| UPDATE | objects, mutation(scope+set), conditions | — |
| DELETE | objects, mutation(scope), conditions | — |
| UPSERT | objects, mutation(matchBy+data) | — |

---

## 4. 入参 2：Binding 结构定义

Binding 定义了 OQL 中本体元素到物理数据源的映射信息，作为独立入参传递，按 alias 组织。主要使用如下的接口查询模型绑定信息：

| 接口名称           | 方法   | 路径                                                                               | 功能              |
| -------------- | ---- | -------------------------------------------------------------------------------- | --------------- |
| **查询对象类型绑定信息** | GET  | `/api/v1/ontologies/{ontologyId}/object-types/{objectTypeId}/bindings/query`     | 查询对象类型的数据模型绑定详情 |
| **查询关系类型绑定信息** | GET  | `/api/v1/ontologies/{ontologyId}/relation-types/{relationTypeId}/bindings/query` | 查询关系类型的数据模型绑定详情 |

### 4.1 顶层结构

```json
{
  "<alias>": {
    "objectTypeContext": { ... },
    "propertyBindings": [ ... ],
    "catalogContext": { ... }
  }
}
```

Key 为 OQL 中对象的 `alias`（如 `"a"`）或关系的 `alias`（如 `"r1"`），Value 为该 alias 对应的裁剪 Binding。

### 4.2 objectTypeContext

```json
{
  "objectTypeId": "obj_alarm",
  "name": "Alarm",
  "description": "告警对象",
  "primaryKeys": ["alarmId"],
  "bindings": [
    {
      "assetId": "资产id",
      "assetIds": ["资产id_1", "资产id_2"],
      "field_ids": ["字段id_1", "字段id_2"],
      "expression": null,
      "joinKeys": null,
      "timeseriesFieldId": null,
      "extendAttribute": {}
    }
  ]
}
```

### 4.3 propertyBindings

```json
[
  {
    "propertyId": "prop_alarm_id",
    "propertyName": "alarmId",
    "dataType": "STRING",
    "bindings": [
      {
        "bindingId": "pb_001",
        "assetId": "资产id",
        "groupId": "default",
        "assetIds": ["资产id"],
        "field_ids": ["字段id"],
        "expression": null,
        "joinKeys": null,
        "timeseriesFieldId": null,
        "extendAttribute": {}
      }
    ]
  }
]
```

| 字段 | 说明 |
|------|------|
| `propertyName` | **本体属性名**——翻译逻辑中查找映射的关键标识 |
| `dataType` | STRING / INT / LONG / DOUBLE / DATETIME / BOOLEAN |
| `bindings[].field_ids` | 映射到的物理字段 ID |
| `bindings[].assetIds` | 关联的资产 ID 链 |
| `bindings[].groupId` | 多绑定分组标识 |
| `bindings[].expression` | 字段转换表达式 |

> 属性未绑定物理模型时 `bindings` 为空数组，仅返回元信息。

### 4.4 catalogContext

四级嵌套结构，沿 `parentAssetId` 链追溯物理路径：

```text
DataSource（数据源）→ Schema（模式/库）→ Dataset（表/Tag/Edge）→ Field（列/属性）
```

**DataSource**：

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `parentAssetId` | 父资产 ID |
| `displayName` | 显示名称 |
| `datasourceType` | rdb / graph / es / api / cube |

**Schema**：

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `parentAssetId` | 父资产 ID（指向上级 DataSource） |
| `name` | Schema 名称，如 `"fm_alarm_db"` |

**Dataset**：

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `parentAssetId` | 父资产 ID（指向上级 Schema） |
| `name` | 表名/Tag名/Edge名，如 `"t_alarm"` |
| `storageType` | ROW / COLUMN / GRAPH_TAG / GRAPH_EDGE |
| `primaryKeys` | 主键字段名 |

**Field**：

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `parentAssetId` | 父资产 ID（指向上级 Dataset） |
| `name` | 物理列名/属性名，如 `"alarm_id"` |
| `dataType` | 物理数据类型，如 `"VARCHAR(64)"` |
| `semanticRole` | 语义角色：PRIMARY_KEY / FOREIGN_KEY / DIMENSION / MEASURE |

### 4.5 Binding 裁剪规则

OAC 下发前已完成裁剪，业务侧收到的 Binding：

1. **按 alias 裁剪**：只包含 OQL 实际引用的对象和关系 alias
2. **按引用裁剪**：`propertyBindings` 只包含 conditions/returns/orders/mutation 引用的属性
3. **Catalog 最小化**：`catalogContext` 只包含本次执行依赖的资产
4. **多 Binding 已筛选**：OAC 一般已完成选择，业务侧按 `bindings[0]` 取映射即可

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
        "rid": "Alarm-1",
        "objectType": "Alarm",
        "properties": {
          "alarmId": "ALM-001",
          "alarmName": "CPU高温告警",
          "severity": "critical"
        }
      }
    ],
    "relationships": [
      {
        "rid": "Alarm-1->Server-1",
        "relationshipType": "generated_by",
        "sourceId": "Alarm-1",
        "targetId": "Server-1",
        "properties": {}
      }
    ],
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
    "metadata": { "totalCount": 0, "successTaskCount": 0, "failedTaskCount": 1 },
    "trace": { "requestId": "req-001", "executionTime": 12 }
  },
  "errors": [
    {
      "code": "OQL-VAL-001",
      "message": "property 'foo' does not exist on alias 'a'",
      "path": "$.conditions.children[0].field",
      "details": {}
    }
  ]
}
```

### 5.3 响应约束

| 约束 | 说明 |
|------|------|
| objectType | 返回本体对象类型名，**不得返回物理表名** |
| properties key | 使用本体属性名或 OQL 显式 alias |
| rid | **必须稳定、可重复生成**（由主键值生成，不能用随机 UUID） |
| sourceId / targetId | 必须关联到对象的 rid |
| 字段安全 | 未在 returns 中请求的物理字段**不得泄露** |
| 物理语句 | 默认**不得**返回原始 SQL/GQL/TQL |

---

## 6. 开发指导

### 6.1 Controller 实现

接口接收两个独立参数：

```java
@RestController
@RequestMapping("/ontology-access/v1")
public class OntologyAccessController {

    private final OntologyAccessService service;

    public OntologyAccessController(OntologyAccessService service) {
        this.service = service;
    }

    @PostMapping("/execute")
    public OntologyAccessResponse execute(
            @RequestHeader("X-Request-Id") String requestId,
            @RequestHeader(value = "X-Tenant-Id", required = false) String tenantId,
            @RequestHeader(value = "X-Schema-Ref", required = false) String schemaRef,
            @RequestHeader("X-Binding-Version") String bindingVersion,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @RequestPart("oql") String oqlJson,
            @RequestPart("binding") String bindingJson) {

        long start = System.currentTimeMillis();

        try {
            // 反序列化：使用业务方自建的 Java Bean
            OqlRequest oql = JsonUtil.fromJson(oqlJson, OqlRequest.class);
            Map<String, BindingProjection> bindings =
                JsonUtil.fromJsonMap(bindingJson, BindingProjection.class);

            OntologyAccessData data = service.execute(
                oql, bindings, requestId, tenantId, schemaRef,
                bindingVersion, idempotencyKey);

            return buildSuccessResponse(data, requestId, start);
        } catch (OntologyAccessException ex) {
            return buildFailureResponse(ex, requestId, start);
        }
    }
}
```

### 6.2 Service 编排实现

```java
@Service
public class OntologyAccessService {

    private final SqlTranslator sqlTranslator;     // 业务自定义
    private final GqlTranslator gqlTranslator;     // 业务自定义
    private final DataSourceExecutor executor;

    public OntologyAccessData execute(
            OqlRequest oql,
            Map<String, BindingProjection> bindings,
            String requestId, String tenantId,
            String schemaRef, String bindingVersion,
            String idempotencyKey) {

        // === 1. OQL 校验 ===
        validateOql(oql);

        // === 2. Binding 完备性校验 ===
        validateBinding(oql, bindings);

        // === 3. 确定数据源类型 → 选择翻译器 ===
        BindingProjection firstBinding = bindings.get(
            oql.objects().getFirst().alias());
        String dsType = firstBinding.catalogContext()
            .dataSources().getFirst().datasourceType();

        PhysicalQuery physicalQuery;
        if ("rdb".equals(dsType)) {
            physicalQuery = sqlTranslator.translate(oql, bindings);
        } else if ("graph".equals(dsType)) {
            physicalQuery = gqlTranslator.translate(oql, bindings);
        } else {
            throw error("TRANS-001", "Unsupported datasource: " + dsType);
        }

        // === 4. 参数化执行 ===
        ExecutionResult result = executor.execute(physicalQuery);

        // === 5. 组装结果 ===
        return assembleResult(oql, bindings, result);
    }
}
```

### 6.3 属性到物理字段的解析（推荐模式）

这是翻译过程中最核心的操作。推荐业务方实现一个轻量解析工具：

```java
/**
 * 沿 catalogContext 的 parentAssetId 链，将 fieldId 解析为完整的物理路径。
 * 这是业务方自建的工具方法，非平台 SDK 提供。
 */
public record ResolvedField(
    String objectAlias,
    String propertyName,
    String dataType,
    String datasourceType,      // "rdb" | "graph" | ...
    String physicalSchema,      // "fm_alarm_db"
    String physicalTable,       // "t_alarm"
    String physicalColumn       // "alarm_id"
) {}

public ResolvedField resolveField(
        String objectAlias, String propertyName,
        Map<String, BindingProjection> bindings) {

    BindingProjection bp = bindings.get(objectAlias);
    if (bp == null) throw error("BIND-OBJ-001", "alias not found: " + objectAlias);

    PropertyBinding pb = bp.propertyBindings().stream()
        .filter(p -> p.propertyName().equals(propertyName))
        .findFirst()
        .orElseThrow(() -> error("BIND-PROP-001",
            "property not found: " + objectAlias + "." + propertyName));

    PhysicalBinding phys = pb.bindings().getFirst(); // OAC 已筛选多绑定
    String fieldId = phys.field_ids().getFirst();

    // 沿 parentAssetId 链追溯：Field → Dataset → Schema → DataSource
    CatalogContext catalog = bp.catalogContext();
    FieldAsset field = findById(catalog.fields(), fieldId);
    DatasetAsset dataset = findById(catalog.datasets(), field.parentAssetId());
    SchemaAsset schema = findById(catalog.schemas(), dataset.parentAssetId());
    DataSourceAsset ds = findById(catalog.dataSources(), schema.parentAssetId());

    return new ResolvedField(objectAlias, propertyName, pb.dataType(),
        ds.datasourceType(), schema.name(), dataset.name(), field.name());
}
```

> 此模式屏蔽了 catalogContext 四级嵌套的遍历复杂度，将"属性→物理字段"映射变成一行调用。**推荐但非强制**——业务方可自行设计等价实现。

---

## 7. OQL 到物理 SQL 翻译范例

### 7.1 QUERY 翻译

**输入 OQL**（精简结构）：

```json
{
  "version": "2.0",
  "operation": "QUERY",
  "objects": [{ "objectType": "Alarm", "alias": "a" }],
  "conditions": {
    "kind": "GROUP", "relation": "AND",
    "children": [
      { "kind": "PREDICATE", "ref": "a", "field": "severity", "operator": "EQ", "values": ["critical"] },
      { "kind": "PREDICATE", "ref": "a", "field": "occurTime", "operator": "GTE", "values": ["2026-01-01T00:00:00Z"] }
    ]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "a", "fields": ["alarmId", "alarmName", "severity"] }
  ],
  "orders": [{ "ref": "a", "field": "occurTime", "direction": "DESC" }],
  "maxResults": { "limit": 100, "offset": 0 }
}
```

**翻译逻辑**：

```java
public PhysicalQuery translate(OqlRequest oql, Map<String, BindingProjection> bindings) {
    OqlObject obj = oql.objects().getFirst();
    String alias = obj.alias();
    List<Object> params = new ArrayList<>();

    // SELECT
    StringBuilder sql = new StringBuilder("SELECT ");
    for (ReturnItem item : oql.returns()) {
        if (item.kind().equals("FIELDS")) {
            for (String prop : item.fields()) {
                ResolvedField f = resolveField(alias, prop, bindings);
                sql.append(quote(f.physicalColumn()))
                   .append(" AS ").append(quote(prop)).append(", ");
            }
        }
    }
    sql.setLength(sql.length() - 2); // 去掉末尾 ", "

    // FROM
    ResolvedField first = resolveField(alias, oql.returns().getFirst().fields().getFirst(), bindings);
    sql.append(" FROM ").append(quote(first.physicalSchema()))
       .append(".").append(quote(first.physicalTable()))
       .append(" ").append(alias);

    // WHERE
    if (oql.conditions() != null) {
        sql.append(" WHERE ").append(buildCondition(oql.conditions(), bindings, params));
    }

    // ORDER BY + LIMIT
    if (!oql.orders().isEmpty()) {
        OrderItem o = oql.orders().getFirst();
        ResolvedField f = resolveField(o.ref(), o.field(), bindings);
        sql.append(" ORDER BY ").append(quote(f.physicalColumn())).append(" ").append(o.direction());
    }
    sql.append(" LIMIT ").append(oql.maxResults().limit());

    return new PhysicalQuery(sql.toString(), params,
        first.datasourceType(), first.physicalSchema());
}
```

**输出 SQL**：

```sql
SELECT alarm_id AS alarmId, alarm_name AS alarmName, severity AS severity
FROM fm_alarm_db.t_alarm a
WHERE (a.severity = ? AND a.occur_time >= ?)
ORDER BY a.occur_time DESC
LIMIT 100
```

**参数**：`["critical", "2026-01-01T00:00:00Z"]`

### 7.2 条件翻译

```java
public String buildCondition(ConditionNode node,
        Map<String, BindingProjection> bindings, List<Object> params) {

    if (node instanceof PredicateCondition pred) {
        ResolvedField f = resolveField(pred.ref(), pred.field(), bindings);
        String col = pred.ref() + "." + quote(f.physicalColumn());

        return switch (pred.operator()) {
            case "EQ"      -> { params.add(pred.values().getFirst()); yield col + " = ?"; }
            case "NE"      -> { params.add(pred.values().getFirst()); yield col + " <> ?"; }
            case "IN"      -> buildIn(col, pred.values(), params);
            case "LIKE"    -> { params.add(pred.values().getFirst()); yield col + " LIKE ?"; }
            case "IS_NULL" -> col + " IS NULL";
            default        -> col + " " + pred.operator() + " ?";
        };
    }

    if (node instanceof GroupCondition group) {
        String join = " " + group.relation() + " ";
        return group.children().stream()
            .map(c -> "(" + buildCondition(c, bindings, params) + ")")
            .collect(Collectors.joining(join));
    }

    throw error("TRANS-001", "Unknown condition type");
}
```

### 7.3 AGGREGATE 翻译

- `conditions` → WHERE（聚合前过滤）
- `returns[kind=GROUP_BY]` → GROUP BY
- `returns[kind=METRIC]` → COUNT / SUM / AVG / MAX / MIN
- `aggregateFilter` → HAVING（聚合后过滤）

### 7.4 ASSOCIATION_QUERY 翻译

**关系型数据库**（基于 joinKeys）：

```java
// 从 Binding 中获取关系 alias 的 joinKeys
BindingProjection relBinding = bindings.get(relationship.alias());
JoinKey jk = relBinding.getJoinKeys().getFirst();

sql.append(" LEFT JOIN ").append(quote(jk.targetTable()))
   .append(" ").append(toAlias)
   .append(" ON ").append(fromAlias).append(".").append(quote(jk.sourceColumn()))
   .append(" = ").append(toAlias).append(".").append(quote(jk.targetColumn()));
```

**图数据库**（NebulaGraph nGQL）：

```java
// MATCH (d:Device)-[r1:installed_on]->(s:Server)
String gql = String.format("MATCH (%s:%s)-[:%s]->(%s:%s)",
    fromAlias, getTag(fromAlias, bindings),
    relationship.relationshipType(),
    toAlias, getTag(toAlias, bindings));
```

### 7.5 写操作翻译

- **CREATE**：使用 `mutation.data.properties` 生成 INSERT
- **UPDATE**：检查 `conditions` 和 `mutation.scope` 存在
- **UPSERT**：基于 `matchBy` 字段判断存在性

---

## 8. 结果组装

### 8.1 对象组装

```java
public OntologyObject assembleObject(OqlObject obj,
        Map<String, Object> row, List<ReturnItem> returns,
        Map<String, BindingProjection> bindings) {

    Map<String, Object> properties = new LinkedHashMap<>();
    for (ReturnItem item : returns) {
        if (item.ref().equals(obj.alias()) && "FIELDS".equals(item.kind())) {
            for (String prop : item.fields()) {
                properties.put(prop, row.get(prop)); // 本体属性名作为 key
            }
        }
    }

    BindingProjection bp = bindings.get(obj.alias());
    String rid = generateRid(obj.objectType(), properties,
        bp.objectTypeContext().primaryKeys());

    return new OntologyObject(rid, obj.objectType(), properties);
}
```

### 8.2 rid 生成

```java
public String generateRid(String objectType,
        Map<String, Object> properties, List<String> primaryKeys) {
    String key = primaryKeys.stream()
        .map(pk -> String.valueOf(properties.get(pk)))
        .collect(Collectors.joining("|"));
    return objectType + "-" + key;
}
```

> **禁止**使用随机 UUID 代替可重复 rid。

---

## 9. 安全规范

### 9.1 参数化查询（强制）

❌ `"WHERE severity = '" + value + "'"`
✅ `"WHERE severity = ?"` + `params.add(value)`

### 9.2 物理标识符白名单（强制）

物理表名、列名**只能从 Binding 解析获得**，不得从 OQL 中直接读取、拼接用户输入或使用 OQL values 作为标识符。

### 9.3 写操作安全检查

| 操作 | 检查项 |
|------|--------|
| UPDATE | conditions 非空 + mutation.scope 存在 + mutation.set 非空 + 影响范围 ≤ 阈值 |
| DELETE | conditions 非空 + mutation.scope 存在 + **禁止无条件删除** |
| UPSERT | matchBy 字段必须有 Binding 映射 |

---

## 10. 错误处理

### 10.1 错误码

| 错误码 | HTTP | 说明 |
|--------|:---:|------|
| `OQL-VAL-001` | 400 | OQL 结构校验失败 |
| `OQL-REF-001` | 400 | alias 或字段引用不存在 |
| `OQL-OP-001` | 400 | operation 不支持 |
| `BIND-OBJ-001` | 400 | 对象 Binding 缺失 |
| `BIND-PROP-001` | 400 | 属性 Binding 缺失 |
| `BIND-REL-001` | 400 | 关系 Binding 缺失 |
| `BIND-ASSET-001` | 400 | Catalog 资产闭包不完整 |
| `TRANS-001` | 500 | OQL 到物理查询转换失败 |
| `EXEC-001` | 500 | 物理查询执行失败 |
| `EXEC-TIMEOUT-001` | 504 | 查询超时 |
| `RESULT-MAP-001` | 500 | 结果映射失败 |
| `SEC-FIELD-001` | 403 | 访问未授权物理字段 |
| `WRITE-SCOPE-001` | 400 | 写操作范围不安全 |

### 10.2 错误路径格式（JSONPath）

```text
$.conditions.children[0].field
$.returns[1].fields[0]
$.binding.a.propertyBindings[2].bindings[0].field_ids[0]
```

---

## 11. 可观测性

每个请求至少记录：

```text
requestId=req-001 schemaRef=fm-alarm-v1 operation=QUERY
objectTypes=Alarm datasourceType=rdb dataset=t_alarm
translateMs=4 executeMs=85 assembleMs=3
objectCount=100 result=SUCCESS
```

---

## 12. 测试规范

### 12.1 测试覆盖清单

| 类别 | 场景 | 优先级 |
|------|------|:---:|
| OQL 反序列化 | 标准 QUERY、含 sourceQuery、含未知字段 | P0 |
| 条件多态 | PREDICATE、GROUP(AND/OR/NOT)、嵌套 | P0 |
| Binding 反序列化 | 四级结构、属性未绑定 | P0 |
| 校验 | version/operation/ref/maxResults | P0 |
| 条件翻译 | 12 种操作符 + AND/OR/NOT 嵌套 | P0 |
| 返回类型 | FIELDS、GROUP_BY、METRIC | P0 |
| 安全 | SQL 注入字符、参数绑定 | P1 |
| 写操作 | 幂等、范围检查 | P1 |

### 12.2 黄金语句测试

每类数据源维护输入-期望对照表：

| ID | 输入 OQL | 输入 Binding | 期望物理语句 | 期望参数 |
|----|---------|-------------|-------------|---------|
| GOLD-SQL-001 | QUERY 单表过滤 | 单对象 Binding | `SELECT ... FROM t_alarm WHERE severity = ? LIMIT 100` | `["critical"]` |
| GOLD-SQL-002 | AGGREGATE 分组 | 单对象 Binding | `SELECT region, SUM(amount) ... GROUP BY region` | `[]` |
| GOLD-GQL-001 | ASSOCIATION 单跳 | 关系图 Binding | `MATCH (e:Employee)-[:works_in]->(d:Department) ...` | `["E1002"]` |

### 12.3 契约测试

```text
标准 OQL + 完整 Binding
        ↓ OAC 裁剪 + 拆分
入参1: 精简 OQL
入参2: 最小 Binding
        ↓ 业务服务处理
参数化 SQL/GQL/TQL
        ↓ Mock 执行 + 组装
统一对象结果
```

---

## 13. 接入检查清单

### 接口定义

- [ ] 实现 `POST /ontology-access/v1/execute`
- [ ] 在 OMS 注册服务信息（endpoint、支持的操作/数据源类型）
- [ ] 鉴权方式已配置

### 参数实现

- [ ] OQL 和 Binding 作为两个独立入参接收
- [ ] 自建 Java Bean 与规范字段 1:1 对应
- [ ] JSON 反序列化配置忽略未知字段
- [ ] ConditionNode 多态反序列化正确
- [ ] 未增加 OQL 顶层字段、operation 或操作符

### 翻译实现

- [ ] 属性→物理字段解析沿 `parentAssetId` 链正确追溯
- [ ] **所有查询值使用参数化绑定（`?` 占位符）**
- [ ] 物理表名、列名只从 Binding 获取
- [ ] rid 稳定、可重复生成

### 安全

- [ ] 写操作检查条件和影响范围
- [ ] 限制 maxResults 上限
- [ ] 敏感信息不写入日志

### 测试

- [ ] 所有条件操作符覆盖
- [ ] 所有 returns 类型覆盖
- [ ] SQL 注入防御测试
- [ ] 契约测试（与 OAC 共同维护）
- [ ] 黄金语句测试

---

## 14. 兼容性

| 维度 | 策略 |
|------|------|
| OQL 版本 | OAC 不下发业务不支持的版本；当前 OQL 2.0 |
| Binding 版本 | 通过 `X-Binding-Version` Header 传递 |
| 前向兼容 | Bean 反序列化配置忽略未知字段，新增可选字段不破坏旧版 |
| 业务自建 Bean | 规范字段变更时，业务方按新 JSON schema 更新 Bean 定义 |

---

## 15. 附录：完整请求示例

### HTTP 请求

```http
POST /ontology-access/v1/execute
Content-Type: multipart/form-data
X-Request-Id: req-001
X-Tenant-Id: tenant-001
X-Schema-Ref: fm-alarm-v1
X-Binding-Version: v0.94
```

### 入参 1：OQL

```json
{
  "version": "2.0",
  "operation": "QUERY",
  "objects": [{ "objectType": "Alarm", "alias": "a" }],
  "conditions": {
    "kind": "GROUP", "relation": "AND",
    "children": [
      { "kind": "PREDICATE", "ref": "a", "field": "severity", "operator": "EQ", "values": ["critical"] },
      { "kind": "PREDICATE", "ref": "a", "field": "occurTime", "operator": "GTE", "values": ["2026-01-01T00:00:00Z"] }
    ]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "a", "fields": ["alarmId", "alarmName", "severity", "resourceId"] }
  ],
  "orders": [{ "ref": "a", "field": "occurTime", "direction": "DESC" }],
  "maxResults": { "limit": 100, "offset": 0 }
}
```

### 入参 2：Binding

```json
{
  "a": {
    "objectTypeContext": {
      "objectTypeId": "obj_alarm", "name": "Alarm", "primaryKeys": ["alarmId"],
      "bindings": [{
        "assetId": "asset_fm_alarm",
        "assetIds": ["asset_fm_mysql", "asset_fm_schema", "asset_fm_alarm"],
        "field_ids": ["field_alarm_id", "field_alarm_name", "field_severity", "field_resource_id", "field_occur_time"]
      }]
    },
    "propertyBindings": [
      { "propertyId": "prop_alarm_id", "propertyName": "alarmId", "dataType": "STRING",
        "bindings": [{ "bindingId": "pb_001", "assetId": "asset_fm_alarm", "groupId": "default",
          "assetIds": ["asset_fm_alarm"], "field_ids": ["field_alarm_id"] }] },
      { "propertyId": "prop_alarm_name", "propertyName": "alarmName", "dataType": "STRING",
        "bindings": [{ "bindingId": "pb_002", "assetId": "asset_fm_alarm", "groupId": "default",
          "assetIds": ["asset_fm_alarm"], "field_ids": ["field_alarm_name"] }] },
      { "propertyId": "prop_severity", "propertyName": "severity", "dataType": "STRING",
        "bindings": [{ "bindingId": "pb_003", "assetId": "asset_fm_alarm", "groupId": "default",
          "assetIds": ["asset_fm_alarm"], "field_ids": ["field_severity"] }] },
      { "propertyId": "prop_resource_id", "propertyName": "resourceId", "dataType": "STRING",
        "bindings": [{ "bindingId": "pb_004", "assetId": "asset_fm_alarm", "groupId": "default",
          "assetIds": ["asset_fm_alarm"], "field_ids": ["field_resource_id"] }] },
      { "propertyId": "prop_occur_time", "propertyName": "occurTime", "dataType": "DATETIME",
        "bindings": [{ "bindingId": "pb_005", "assetId": "asset_fm_alarm", "groupId": "default",
          "assetIds": ["asset_fm_alarm"], "field_ids": ["field_occur_time"] }] }
    ],
    "catalogContext": {
      "dataSources": [
        { "id": "asset_fm_mysql", "parentAssetId": "", "displayName": "FM MySQL", "datasourceType": "rdb" }
      ],
      "schemas": [
        { "id": "asset_fm_schema", "parentAssetId": "asset_fm_mysql", "name": "fm_alarm_db" }
      ],
      "datasets": [
        { "id": "asset_fm_alarm", "parentAssetId": "asset_fm_schema", "name": "t_alarm", "storageType": "ROW", "primaryKeys": "alarm_id" }
      ],
      "fields": [
        { "id": "field_alarm_id", "parentAssetId": "asset_fm_alarm", "name": "alarm_id", "dataType": "VARCHAR(64)" },
        { "id": "field_alarm_name", "parentAssetId": "asset_fm_alarm", "name": "alarm_name", "dataType": "VARCHAR(128)" },
        { "id": "field_severity", "parentAssetId": "asset_fm_alarm", "name": "severity", "dataType": "VARCHAR(32)" },
        { "id": "field_resource_id", "parentAssetId": "asset_fm_alarm", "name": "resource_id", "dataType": "VARCHAR(64)" },
        { "id": "field_occur_time", "parentAssetId": "asset_fm_alarm", "name": "occur_time", "dataType": "DATETIME" }
      ]
    }
  }
}
```

### 翻译输出

```sql
SELECT alarm_id AS alarmId, alarm_name AS alarmName, severity AS severity, resource_id AS resourceId
FROM fm_alarm_db.t_alarm a
WHERE (a.severity = ? AND a.occur_time >= ?)
ORDER BY a.occur_time DESC
LIMIT 100
```

参数：`["critical", "2026-01-01T00:00:00Z"]`

---

## 参考规范

| 规范 | 说明 |
|------|------|
| OAC 业务本体访问接口规范 | OAC→业务服务接口契约 |
| 数据模型对接本体知识平台规范 v0.94 | Binding 数据结构和建模对接方式 |
| 本体对象操作语言（OQL）DSL 规范 | OQL 语法完整定义 |
