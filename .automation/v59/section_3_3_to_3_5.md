## 3.3 统一 REST API 规范

OAG 对外接口统一使用 Namespace：

```text
/v1/onto-retrieval/{ontologyId}
```

不再新增 `/v1/ontologies/{ontologyId}/...` 或 `/instance-evidence/import-jobs/...` 风格接口。

本章接口按 **OpenAPI 3.0.3** 规范定义。所有 URI、Path/Header/Query 参数、Request Body、HTTP Status Code 和 Response Schema 都必须能够直接映射为 OpenAPI `paths / parameters / requestBody / responses / components.schemas`。

### 3.3.1 公共协议约束

#### Content-Type

```http
Content-Type: application/json
Accept: application/json
```

MinIO 文件导入接口自身仍使用 JSON 注册文件，不通过 `multipart/form-data` 直接上传大文件；CSV 先由 DataSync 上传到双方约定的 MinIO Bucket，再调用 `file-import`。

#### 公共 Path 参数

**表 1  OntologyPath 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `ontologyId` | String | 是 | - | `in: path`，`required: true`，`maxLength: 256` | 本体唯一 ID；必须与 URI 中的目标本体一致 |

#### 公共 Header 参数

**表 2  OAGCommonHeaders 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `x-gde-tenant-id` | String | 是 | - | `in: header`，`required: true`，`maxLength: 256` | 租户 ID；OAG 按租户隔离本体和任务 |
| `Content-Type` | String | POST 请求是 | `application/json` | `application/json` | 请求体编码类型 |
| `Accept` | String | 否 | `application/json` | `application/json` | 响应类型 |

#### 公共 HTTP 状态码

| HTTP 状态码 | 场景 | Response Schema |
|:--|:--|:--|
| `200 OK` | 同步查询成功 | 对应接口 Success Response |
| `202 Accepted` | 异步导入、重试或取消请求已接受 | `AsyncTaskAcceptedResponse` / `TaskOperationAcceptedResponse` |
| `400 Bad Request` | Path/Header/Body/Query 参数校验失败 | `ValidationErrorResponse` |
| `404 Not Found` | Ontology、Task 或同步校验的资源不存在 | `BusinessErrorResponse` |
| `409 Conflict` | 幂等键冲突、任务状态不允许当前操作 | `BusinessErrorResponse` |
| `413 Payload Too Large` | REST Batch 超过 `maxRecordsPerRequest` 或 Body 限制 | `BusinessErrorResponse` |
| `429 Too Many Requests` | 导入任务或接口触发限流 | `BusinessErrorResponse` |
| `500 Internal Server Error` | OAG 内部未预期异常 | `BusinessErrorResponse` |
| `503 Service Unavailable` | GaussDB、Embedding、GaussVector、OpenSearch、MinIO 等依赖暂不可用 | `BusinessErrorResponse` |

> 对异步导入接口，`202 Accepted` 仅表示任务已成功写入 GaussDB 并进入执行队列，不表示数据已经完成 Embedding、双写或发布。

#### 幂等规则

`requestId` 是调用方生成的业务幂等键，最大长度 256。OAG 使用：

```text
ontologyId + requestId
```

作为任务级幂等约束：

```text
相同 ontologyId + requestId + 相同请求语义
  → 返回原 taskId，不重复创建任务

相同 ontologyId + requestId + 不同 dataType/importMode/数据内容
  → HTTP 409 IDEMPOTENCY_CONFLICT
```

---

### 3.3.2 语义子图检索接口

#### 典型场景

Agent、Skill 或上层业务根据自然语言问题获取与问题相关的 ObjectType、Property、Enum Value、Instance Value、Relation、Function/Action 等检索结果和本体子图。

#### 接口功能

执行 Query Understanding、6 路混合召回、Weighted RRF、LLM 精排和本体子图生成。该接口只负责语义检索与子图返回，不承担索引数据导入。

#### 调用方法

POST

#### URI

```text
/v1/onto-retrieval/{ontologyId}/subgraph/semantic-search
```

对应 Spring 接口：

```java
@PostMapping("/v1/onto-retrieval/{ontologyId}/subgraph/semantic-search")
```

#### 请求参数

除表 1、表 2 的公共 Path/Header 参数外，请求 Body 使用 `SemanticSearchRequest`。

**表 3  SemanticSearchRequest 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `query` | String | 是 | - | `minLength: 1` | 自然语言业务问题或 Planning 层整理后的语义检索问题 |
| `similarityThreshold` | Number(float) | 否 | `0.6` | `minimum: 0`，`maximum: 1` | Dense 相似度阈值；Exact 命中不受该阈值过滤 |
| `includeFunctions` | Integer | 否 | `1` | `enum: [0,1]` | 是否返回 Function，1 返回，0 不返回 |
| `includeActions` | Integer | 否 | `0` | `enum: [0,1]` | 是否返回 Action，1 返回，0 不返回 |
| `seedRetrievalMode` | String | 否 | `vector` | 当前支持值以服务配置为准 | 种子节点检索模式 |
| `topK` | Integer | 否 | `3` | `minimum: 1` | 种子节点候选 TopK |
| `graphExpansionStrategy` | String | 否 | `minimal` | `enum: [minimal,khop,component]` | 子图扩展策略 |
| `hopLimit` | Integer | 否 | `3` | `minimum: 1` | `khop` 策略下的最大扩散深度 |

#### 请求示例

```json
{
  "query": "查询正式用户的 Mobile Number",
  "similarityThreshold": 0.6,
  "includeFunctions": 1,
  "includeActions": 0,
  "seedRetrievalMode": "vector",
  "topK": 3,
  "graphExpansionStrategy": "minimal",
  "hopLimit": 3
}
```

#### 返回参数

成功响应沿用后续第 5、6 章定义的最终检索与子图结构。OpenAPI 中 `result` 至少声明为 Object，内部字段包括 `retrievalResults / seedNodes / nodes / edges / semanticExtensions / capabilityExtensions / metadata`，具体字段以第 5、6 章为准。

**表 4  SemanticSearchResponse 参数列表（HTTP 200）**

| 参数名称 | 类型 | 说明 |
|:--|:--|:--|
| `result` | Object | 最终语义检索结果与本体子图 |

#### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/subgraph/semantic-search:
  post:
    operationId: semanticSearchSubgraph
    summary: 本体语义子图检索
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TenantId'
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/SemanticSearchRequest'
    responses:
      '200':
        description: 检索成功
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SemanticSearchResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
      '503': { $ref: '#/components/responses/ServiceUnavailable' }
```

---

### 3.3.3 索引导入与任务接口清单

| 场景 | Method | URI | OpenAPI operationId | 说明 |
|---|---|---|---|---|
| REST 批量导入 | POST | `/v1/onto-retrieval/{ontologyId}/index-data/batch-import` | `batchImportIndexData` | Body 直接提交 Enum/Instance records |
| MinIO 文件导入 | POST | `/v1/onto-retrieval/{ontologyId}/index-data/file-import` | `importIndexDataFromMinio` | 注册已经上传到 MinIO 的 CSV 文件 |
| 查询任务 | GET | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}` | `getIndexTask` | 查询持久化任务状态和进度 |
| 重试任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry` | `retryIndexTask` | 对失败任务重新执行 |
| 取消任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel` | `cancelIndexTask` | 请求取消未完成任务 |
| 查询错误 | GET | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors` | `listIndexTaskErrors` | 分页查询任务记录级错误 |

所有导入接口采用异步任务模型：

```text
提交请求 → 同步基础参数校验 → GaussDB 创建/复用 T_OAG_INDEX_TASK → HTTP 202 + taskId → 后台执行
```

统一数据类型：`METADATA_ENUM`、`INSTANCE_VALUE`；统一导入模式：`FULL_REPLACE`、`INCREMENTAL`；统一记录操作：`UPSERT`、`DELETE`。

---

## 3.4 REST 批量导入接口

REST Batch Import 是 MinIO 文件导入的补充，主要面向动态枚举值实时/准实时增加、删除或修订，以及少量/中等规模实例值增量。超大数据不应通过 HTTP JSON Body 替代 MinIO 文件通道。`maxRecordsPerRequest` 为 OAG 工程配置，建议默认从 1000 条起步并通过压测调整。

### 3.4.1 接口定义

#### 典型场景

业务系统动态增加/删除枚举值，或 DataSync/业务应用需要实时、准实时导入少量实例列值，不希望先生成 MinIO 文件。

#### 接口功能

接收 `METADATA_ENUM` 或 `INSTANCE_VALUE` 批量记录，完成同步协议校验并创建异步索引任务。后台统一执行本体映射校验、Normalize、Dedup、Embedding、GaussVector/OpenSearch 双写、Verify 和 Publish。

#### 调用方法

POST

#### URI

```text
/v1/onto-retrieval/{ontologyId}/index-data/batch-import
```

对应 Spring 接口：

```java
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-data/batch-import")
```

#### 请求参数

**表 5  IndexBatchImportRequest 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `requestId` | String | 是 | - | `minLength: 1`，`maxLength: 256` | 调用方幂等键 |
| `dataType` | String | 是 | - | `enum: [METADATA_ENUM, INSTANCE_VALUE]` | 指定本批记录类型，禁止一个请求混合两类数据 |
| `importMode` | String | 是 | - | `enum: [FULL_REPLACE, INCREMENTAL]` | 全量替换或增量导入 |
| `records` | Array[MetadataEnumRecord] / Array[InstanceValueRecord] | 是 | - | `minItems: 1`；最大条数由 `maxRecordsPerRequest` 配置 | 记录类型必须与 `dataType` 一致 |

`records` 是 OpenAPI `oneOf` 语义：

```text
dataType = METADATA_ENUM
  → records[] 必须满足 MetadataEnumRecord

dataType = INSTANCE_VALUE
  → records[] 必须满足 InstanceValueRecord
```

OAG 不接受调用方提交 `vector`；物理 `type` 由 `dataType` 推导：`METADATA_ENUM → ENUM_VALUE`，`INSTANCE_VALUE → INSTANCE_VALUE`。

##### METADATA_ENUM 记录

> **字段名严格与第 2.8 节一致：使用 `propertyId`，不是 `propertyid`。字段名大小写敏感。**

**表 6  MetadataEnumRecord 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `propertyId` | String | 是 | - | `maxLength: 512` | 引用该 Enum 的 Property.id |
| `objectTypeId` | String | 否 | - | `maxLength: 256` | Property 所属 ObjectType.id；如传入必须与本体映射一致 |
| `value` | String | 是 | - | `maxLength: 4096` | 真实枚举值；用于唯一键和向量内容 |
| `name` | String | 否 | - | `maxLength: 4096` | Enum Value name |
| `display_zh` | String | 否 | - | `maxLength: 512` | 中文 display |
| `display_en` | String | 否 | - | `maxLength: 512` | 英文 display |
| `display_lang_1` | String | 否 | - | `maxLength: 512` | ontology 级额外语言槽位 1 display |
| `display_lang_2` | String | 否 | - | `maxLength: 512` | ontology 级额外语言槽位 2 display |
| `description_zh` | String | 否 | - | - | 中文 description |
| `description_en` | String | 否 | - | - | 英文 description |
| `description_lang_1` | String | 否 | - | - | 额外语言槽位 1 description |
| `description_lang_2` | String | 否 | - | - | 额外语言槽位 2 description |
| `synonyms` | Map[String, Array[String]] | 否 | `{}` | `maxProperties: 3` | 当前 Enum Value 的多语言同义词；语言 key 最多 3 个 |
| `op` | String | 否 | `UPSERT` | `enum: [UPSERT, DELETE]` | 增量操作；`FULL_REPLACE` 默认只使用 `UPSERT` |

枚举唯一业务键：

```text
objectTypeId + propertyId + normalized(value)
```

如果 `objectTypeId` 未传，OAG 可以根据 `propertyId` 的本体归属补齐；若调用方传入，则必须校验与 OMS 本体映射一致，不一致返回 `OBJECT_TYPE_MISMATCH`。

##### INSTANCE_VALUE 记录

> **字段名严格与第 2.10 节一致：使用 `propertyid`。该字段与第 2.8 的 `propertyId` 大小写不同，当前协议保持与既有物理模型一致。**

**表 7  InstanceValueRecord 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `propertyid` | String | 是 | - | `maxLength: 512` | 所属 Property.id |
| `objectTypeId` | String | 否 | - | `maxLength: 256` | Property 所属 ObjectType.id；如传入必须与本体映射一致 |
| `value` | String | 是 | - | `maxLength: 4096` | 去重后的真实 Instance Value；EmbeddingInput 严格为 `{value}` |
| `language` | String | 否 | `und` | BCP 47 / `und` | 导入协议扩展字段，只用于 Analyzer/观测 Hint，不改变第 2.10 的向量表核心字段 |
| `op` | String | 否 | `UPSERT` | `enum: [UPSERT, DELETE]` | 增量操作；`FULL_REPLACE` 默认只使用 `UPSERT` |

实例唯一业务键：

```text
objectTypeId + propertyid + normalized(value)
```

#### 请求示例：动态枚举

```json
{
  "requestId": "req-enum-20260816-000001",
  "dataType": "METADATA_ENUM",
  "importMode": "INCREMENTAL",
  "records": [
    {
      "propertyId": "prop:ont:vehicle:sp:bodyColor",
      "objectTypeId": "obj:ont:vehicle:Vehicle",
      "value": "red",
      "name": "red",
      "display_zh": "红色",
      "display_en": "Red",
      "display_lang_1": "Rojo",
      "description_zh": "红色",
      "description_en": "Red color",
      "description_lang_1": "Color rojo",
      "synonyms": {
        "zh": ["红", "赤色"],
        "en": ["Red"],
        "es": ["Rojo"]
      },
      "op": "UPSERT"
    }
  ]
}
```

#### 请求示例：实例列值

```json
{
  "requestId": "req-instance-20260816-000001",
  "dataType": "INSTANCE_VALUE",
  "importMode": "INCREMENTAL",
  "records": [
    {
      "propertyid": "prop:subscriber:subLevel",
      "objectTypeId": "obj:subscriber:Subscriber",
      "value": "VIP",
      "language": "und",
      "op": "UPSERT"
    }
  ]
}
```

#### 返回参数

**表 8  AsyncTaskAcceptedResponse 参数列表（HTTP 202）**

| 参数名称 | 类型 | 说明 | 示例 |
|:--|:--|:--|:--|
| `ontologyId` | String | 本体 ID | `dtmi.ontology.xxx.1` |
| `taskId` | String | GaussDB 持久化任务 ID | `idx-task-20260816-000001` |
| `requestId` | String | 调用幂等键 | `req-enum-20260816-000001` |
| `dataType` | String | `METADATA_ENUM` / `INSTANCE_VALUE` | `METADATA_ENUM` |
| `sourceType` | String | 固定 `REST` | `REST` |
| `status` | Integer | 任务状态：0 构建中，1 成功，2 失败，3 已取消 | `0` |
| `stage` | String | 当前阶段，任务创建时通常为 `CREATED` | `CREATED` |

#### 响应示例

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "taskId": "idx-task-20260816-000001",
  "requestId": "req-enum-20260816-000001",
  "dataType": "METADATA_ENUM",
  "sourceType": "REST",
  "status": 0,
  "stage": "CREATED"
}
```

#### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-data/batch-import:
  post:
    operationId: batchImportIndexData
    summary: REST 批量导入枚举值或实例列值
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TenantId'
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/IndexBatchImportRequest'
          examples:
            metadataEnum:
              $ref: '#/components/examples/MetadataEnumBatchImportExample'
            instanceValue:
              $ref: '#/components/examples/InstanceValueBatchImportExample'
    responses:
      '202':
        description: 导入任务已创建或命中幂等任务
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AsyncTaskAcceptedResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '409': { $ref: '#/components/responses/Conflict' }
      '413': { $ref: '#/components/responses/PayloadTooLarge' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
      '503': { $ref: '#/components/responses/ServiceUnavailable' }
```

---

## 3.5 MinIO CSV 文件导入接口

对于百万/千万级实例值及大规模枚举数据，默认使用 MinIO 文件通道：

```text
DataSync → 生成 CSV → S3 putObject 到双方约定 Bucket → POST file-import
         → OAG 创建任务 → S3 getObject 流式读取
         → Normalize/Dedup/Embedding/Bulk Write/Verify/Publish
```

### 3.5.1 接口定义

#### 典型场景

DataSync 定期或按事件生成大规模枚举/实例列值文件，数据量不适合通过 HTTP JSON Body 直接提交，需要使用 MinIO 进行解耦、流式消费和失败重试。

#### 接口功能

注册已经上传到 MinIO 的一个或多个 UTF-8 CSV 对象。接口同步校验请求结构和基础资源信息，创建持久化异步任务；后台按文件流式读取并进入与 REST Batch 相同的 Import Pipeline。

#### 调用方法

POST

#### URI

```text
/v1/onto-retrieval/{ontologyId}/index-data/file-import
```

对应 Spring 接口：

```java
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-data/file-import")
```

#### 请求参数

**表 9  IndexFileImportRequest 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `requestId` | String | 是 | - | `minLength: 1`，`maxLength: 256` | 调用方幂等键 |
| `dataType` | String | 是 | - | `enum: [METADATA_ENUM, INSTANCE_VALUE]` | 当前文件批次的数据类型 |
| `importMode` | String | 是 | - | `enum: [FULL_REPLACE, INCREMENTAL]` | 全量替换或增量导入 |
| `files` | Array[MinioCsvFile] | 是 | - | `minItems: 1` | 待导入的 MinIO CSV 对象列表 |

**表 10  MinioCsvFile 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `bucket` | String | 是 | - | `minLength: 3`，`maxLength: 63` | 双方部署时约定并加入 OAG allowlist 的 MinIO Bucket |
| `objectKey` | String | 是 | - | `minLength: 1`，`maxLength: 1024` | CSV 对象 Key；任务完成前不得覆盖同一 Key |
| `fileFormat` | String | 否 | `CSV` | `enum: [CSV]` | 当前只支持 CSV |
| `encoding` | String | 否 | `UTF-8` | `enum: [UTF-8]` | 当前只支持 UTF-8 |
| `hasHeader` | Boolean | 否 | `true` | 当前必须为 `true` | CSV 第一行为 Header |
| `rowCount` | Integer(int64) | 否 | - | `minimum: 0` | DataSync 侧统计的预期记录数；OAG 用于校验/观测 |
| `size` | Integer(int64) | 否 | - | `minimum: 0` | 预期文件字节数；OAG 可通过 `headObject` 二次校验 |
| `sha256` | String | 是 | - | `pattern: ^[A-Fa-f0-9]{64}$` | 文件 SHA-256；用于不可变校验和 Chunk 稳定标识 |

MinIO 的 `endpoint / accessKey / secretKey` 属于部署配置，不属于业务 API 参数，禁止通过 `file-import` Body 传输。

#### 请求示例

```json
{
  "requestId": "datasync-20260816-000001",
  "dataType": "INSTANCE_VALUE",
  "importMode": "FULL_REPLACE",
  "files": [
    {
      "bucket": "oag-retrieval-import",
      "objectKey": "onto-retrieval/tenant-a/dtmi.ontology.xxx.1/INSTANCE_VALUE/datasync-20260816-000001/part-00000.csv",
      "fileFormat": "CSV",
      "encoding": "UTF-8",
      "hasHeader": true,
      "rowCount": 1200000,
      "size": 183421234,
      "sha256": "7c222fb2927d828af22f592134e8932480637c0d4d7b31a7d7e6c80b7f5506ab"
    }
  ]
}
```

#### 返回参数

复用表 8 `AsyncTaskAcceptedResponse`，其中：

```text
sourceType = MINIO
status     = 0
stage      = CREATED
```

#### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "taskId": "idx-task-20260816-000101",
  "requestId": "datasync-20260816-000001",
  "dataType": "INSTANCE_VALUE",
  "sourceType": "MINIO",
  "status": 0,
  "stage": "CREATED"
}
```

#### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-data/file-import:
  post:
    operationId: importIndexDataFromMinio
    summary: 从 MinIO CSV 导入枚举值或实例列值
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TenantId'
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/IndexFileImportRequest'
    responses:
      '202':
        description: 文件导入任务已创建或命中幂等任务
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AsyncTaskAcceptedResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '409': { $ref: '#/components/responses/Conflict' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
      '503': { $ref: '#/components/responses/ServiceUnavailable' }
```

### 3.5.2 同步校验与异步校验边界

接口返回 `202` 前至少完成：

```text
ontologyId / tenant 基础校验
requestId 幂等校验
dataType / importMode Schema 校验
files 非空
bucket allowlist 校验
objectKey 格式校验
sha256 格式校验
T_OAG_INDEX_TASK 持久化成功
```

MinIO 对象存在性、size/checksum、CSV Header、逐行 Schema、Ontology Mapping 等校验可以在后台任务阶段执行；如果后台校验失败，任务进入 `STATUS=2` 并通过任务查询/错误查询接口返回详细错误。实现如果选择在 `202` 前执行 `headObject`，则对象不存在可以同步返回 `404 MINIO_OBJECT_NOT_FOUND`，但不得因此把百万级 CSV 内容同步加载到 API 线程。

---
