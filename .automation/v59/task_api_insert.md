### 3.8.4 索引任务管理接口详细定义

任务管理接口统一以 GaussDB `T_OAG_INDEX_TASK` 为事实来源，不以内存线程/Future 状态作为权威结果。

#### 3.8.4.1 查询索引任务

##### 典型场景

调用方提交 REST Batch 或 MinIO File Import 后，根据 `taskId` 轮询任务当前阶段、进度、结果和最后错误摘要。

##### 接口功能

查询指定本体下的索引任务状态。接口必须同时校验 `ontologyId + taskId + tenant` 归属，禁止跨租户/跨本体读取任务。

##### 调用方法

GET

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}
```

##### 请求参数

**表 11  GetIndexTask 参数列表**

| 参数名称 | 类型 | 参数位置 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|:--|
| `ontologyId` | String | Path | 是 | - | `maxLength: 256` | 本体 ID |
| `taskId` | String | Path | 是 | - | `maxLength: 256` | 索引任务 ID |
| `x-gde-tenant-id` | String | Header | 是 | - | `maxLength: 256` | 租户 ID |

##### 返回参数

**表 12  IndexTaskResponse 参数列表（HTTP 200）**

| 参数名称 | 类型 | 说明 |
|:--|:--|:--|
| `tenantId` | String | 租户 ID |
| `ontologyId` | String | 本体 ID |
| `taskId` | String | 任务 ID |
| `requestId` | String | 调用幂等键 |
| `dataType` | String | `SEED_NODE / METADATA_ENUM / INSTANCE_VALUE` |
| `sourceType` | String | `OMS / REST / MINIO` |
| `importMode` | String | `FULL_REPLACE / INCREMENTAL`；OMS 内部任务可为空 |
| `status` | Integer | 0 构建中；1 成功；2 失败；3 已取消 |
| `stage` | String | 当前执行阶段 |
| `totalCount` | Integer(int64) | 总记录数；未知时可为空 |
| `successCount` | Integer(int64) | 成功处理数 |
| `failedCount` | Integer(int64) | 失败记录数 |
| `skippedCount` | Integer(int64) | 去重/过滤记录数 |
| `retryCount` | Integer | 已执行重试次数 |
| `errorCode` | String | 任务最后错误码；非失败状态可为空 |
| `errorMessage` | String | 最后错误摘要；非失败状态可为空 |
| `createTime` | String(date-time) | 创建时间 |
| `startTime` | String(date-time) | 实际开始时间 |
| `updateTime` | String(date-time) | 最近更新时间 |
| `completionTime` | String(date-time) | 完成时间；未结束可为空 |

##### 响应示例

```json
{
  "tenantId": "tenant-a",
  "ontologyId": "dtmi.ontology.xxx.1",
  "taskId": "idx-task-20260816-000001",
  "requestId": "req-enum-20260816-000001",
  "dataType": "METADATA_ENUM",
  "sourceType": "REST",
  "importMode": "INCREMENTAL",
  "status": 0,
  "stage": "EMBEDDING",
  "totalCount": 1000,
  "successCount": 640,
  "failedCount": 2,
  "skippedCount": 8,
  "retryCount": 0,
  "errorCode": null,
  "errorMessage": null,
  "createTime": "2026-08-16T22:10:00+08:00",
  "startTime": "2026-08-16T22:10:01+08:00",
  "updateTime": "2026-08-16T22:10:08+08:00",
  "completionTime": null
}
```

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}:
  get:
    operationId: getIndexTask
    summary: 查询索引任务
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TaskId'
      - $ref: '#/components/parameters/TenantId'
    responses:
      '200':
        description: 查询成功
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IndexTaskResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '500': { $ref: '#/components/responses/InternalError' }
```

---

#### 3.8.4.2 重试索引任务

##### 典型场景

索引任务因 MinIO、Embedding、GaussVector、OpenSearch 或 Verify 等临时故障失败后，调用方希望从持久化 Source/Checkpoint 重试，而不是重新提交整批业务数据。

##### 接口功能

对 `STATUS=2` 的失败任务发起重试。OAG 复用原 `taskId`、`requestId`、输入 Source 和 Checkpoint，增加 `RETRY_COUNT` 并重新进入执行队列，不创建重复业务任务。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry
```

##### 请求参数

无 Request Body。Path/Header 参数复用表 11。

##### 前置条件

```text
任务存在
AND tenant/ontology 归属一致
AND STATUS = 2（FAILED）
AND 原始 REST Payload 或 MinIO Source/Checkpoint 仍可恢复
```

否则返回 `409 TASK_STATE_CONFLICT` 或相应资源错误。

##### 返回参数

**表 13  TaskOperationAcceptedResponse 参数列表（HTTP 202）**

| 参数名称 | 类型 | 说明 | 示例 |
|:--|:--|:--|:--|
| `ontologyId` | String | 本体 ID | `dtmi.ontology.xxx.1` |
| `taskId` | String | 原任务 ID | `idx-task-20260816-000001` |
| `operation` | String | 当前接受的任务操作 | `RETRY` |
| `accepted` | Boolean | 是否已接受 | `true` |
| `status` | Integer | 接受后任务状态，通常重新进入 0 | `0` |
| `stage` | String | 接受后的阶段 | `CREATED` |

##### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "taskId": "idx-task-20260816-000001",
  "operation": "RETRY",
  "accepted": true,
  "status": 0,
  "stage": "CREATED"
}
```

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry:
  post:
    operationId: retryIndexTask
    summary: 重试失败的索引任务
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TaskId'
      - $ref: '#/components/parameters/TenantId'
    responses:
      '202':
        description: 重试请求已接受
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskOperationAcceptedResponse'
      '404': { $ref: '#/components/responses/NotFound' }
      '409': { $ref: '#/components/responses/Conflict' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
      '503': { $ref: '#/components/responses/ServiceUnavailable' }
```

---

#### 3.8.4.3 取消索引任务

##### 典型场景

调用方发现导入数据错误、提交范围错误或需要停止长时间运行的文件导入任务。

##### 接口功能

请求取消尚未进入终态的索引任务。接口返回 `202` 代表取消请求已接受，不代表 Worker 已立即停止；Worker 在安全检查点停止后将任务更新为 `STATUS=3`。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel
```

##### 请求参数

无 Request Body。Path/Header 参数复用表 11。

##### 前置条件

只有 `STATUS=0` 的未完成任务允许取消；`STATUS=1/2/3` 返回 `409 TASK_STATE_CONFLICT`。

##### 返回参数

复用表 13 `TaskOperationAcceptedResponse`，其中 `operation=CANCEL`。

##### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "taskId": "idx-task-20260816-000001",
  "operation": "CANCEL",
  "accepted": true,
  "status": 0,
  "stage": "CANCEL_REQUESTED"
}
```

`CANCEL_REQUESTED` 作为取消请求已接收的瞬态阶段；Worker 安全停止后更新为 `STATUS=3`。

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel:
  post:
    operationId: cancelIndexTask
    summary: 取消索引任务
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TaskId'
      - $ref: '#/components/parameters/TenantId'
    responses:
      '202':
        description: 取消请求已接受
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskOperationAcceptedResponse'
      '404': { $ref: '#/components/responses/NotFound' }
      '409': { $ref: '#/components/responses/Conflict' }
      '500': { $ref: '#/components/responses/InternalError' }
```

---

#### 3.8.4.4 查询索引任务错误

##### 典型场景

批量或文件导入存在部分记录失败，需要定位具体 `recordIndex / objectKey / rowNumber / Property / value` 的错误原因。

##### 接口功能

分页查询任务记录级错误。百万级错误不得整体塞入 `T_OAG_INDEX_TASK.ERROR_MESSAGE` 或一次性返回。

##### 调用方法

GET

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors
```

##### 请求参数

**表 14  ListIndexTaskErrors 参数列表**

| 参数名称 | 类型 | 参数位置 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|:--|
| `ontologyId` | String | Path | 是 | - | `maxLength: 256` | 本体 ID |
| `taskId` | String | Path | 是 | - | `maxLength: 256` | 任务 ID |
| `x-gde-tenant-id` | String | Header | 是 | - | `maxLength: 256` | 租户 ID |
| `page` | Integer | Query | 否 | `0` | `minimum: 0` | 页码，从 0 开始 |
| `pageSize` | Integer | Query | 否 | `100` | `minimum: 1`，`maximum: 1000` | 每页条数 |

**表 15  IndexTaskErrorItem 参数列表**

| 参数名称 | 类型 | 说明 |
|:--|:--|:--|
| `recordIndex` | Integer(int64) | REST records[] 下标；文件导入可为空 |
| `objectKey` | String | MinIO Object Key；REST 导入可为空 |
| `rowNumber` | Integer(int64) | CSV 行号；REST 导入可为空 |
| `propertyId` | String | 统一错误输出中的 Property.id；从 Enum `propertyId` 或 Instance `propertyid` 规范化得到 |
| `objectTypeId` | String | ObjectType.id |
| `value` | String | 必要时脱敏/截断后的业务值 |
| `errorCode` | String | 记录级错误码 |
| `errorMessage` | String | 记录级错误信息 |

**表 16  IndexTaskErrorPage 参数列表（HTTP 200）**

| 参数名称 | 类型 | 说明 |
|:--|:--|:--|
| `taskId` | String | 任务 ID |
| `page` | Integer | 当前页码 |
| `pageSize` | Integer | 当前页大小 |
| `total` | Integer(int64) | 错误总数 |
| `items` | Array[IndexTaskErrorItem] | 当前页错误明细 |

##### 响应示例

```json
{
  "taskId": "idx-task-20260816-000001",
  "page": 0,
  "pageSize": 100,
  "total": 2,
  "items": [
    {
      "recordIndex": 8,
      "objectKey": null,
      "rowNumber": null,
      "propertyId": "prop:ont:vehicle:sp:bodyColor",
      "objectTypeId": "obj:ont:vehicle:Vehicle",
      "value": "red",
      "errorCode": "OBJECT_TYPE_MISMATCH",
      "errorMessage": "objectTypeId does not match the Property owner"
    }
  ]
}
```

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors:
  get:
    operationId: listIndexTaskErrors
    summary: 分页查询索引任务记录级错误
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TaskId'
      - $ref: '#/components/parameters/TenantId'
      - name: page
        in: query
        required: false
        schema: { type: integer, minimum: 0, default: 0 }
      - name: pageSize
        in: query
        required: false
        schema: { type: integer, minimum: 1, maximum: 1000, default: 100 }
    responses:
      '200':
        description: 查询成功
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IndexTaskErrorPage'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '500': { $ref: '#/components/responses/InternalError' }
```

---

### 3.8.5 OpenAPI 3.0.3 公共 Components 定义

以下 Components 与 3.3～3.8 的 Path 定义组合后，可以直接形成 OpenAPI 3.0.3 契约。工程实现可以将这些定义拆到独立 `openapi.yaml`，设计文档保留同名 Schema 作为接口评审基线。

```yaml
openapi: 3.0.3
info:
  title: OAG Onto Retrieval API
  version: 1.0.0

components:
  parameters:
    OntologyId:
      name: ontologyId
      in: path
      required: true
      schema:
        type: string
        maxLength: 256
    TaskId:
      name: taskId
      in: path
      required: true
      schema:
        type: string
        maxLength: 256
    TenantId:
      name: x-gde-tenant-id
      in: header
      required: true
      schema:
        type: string
        maxLength: 256

  schemas:
    SemanticSearchRequest:
      type: object
      required: [query]
      properties:
        query:
          type: string
          minLength: 1
        similarityThreshold:
          type: number
          format: float
          minimum: 0
          maximum: 1
          default: 0.6
        includeFunctions:
          type: integer
          enum: [0, 1]
          default: 1
        includeActions:
          type: integer
          enum: [0, 1]
          default: 0
        seedRetrievalMode:
          type: string
          default: vector
        topK:
          type: integer
          minimum: 1
          default: 3
        graphExpansionStrategy:
          type: string
          enum: [minimal, khop, component]
          default: minimal
        hopLimit:
          type: integer
          minimum: 1
          default: 3

    SemanticSearchResponse:
      type: object
      required: [result]
      properties:
        result:
          type: object
          additionalProperties: true

    MetadataEnumRecord:
      type: object
      required: [propertyId, value]
      properties:
        propertyId: { type: string, maxLength: 512 }
        objectTypeId: { type: string, maxLength: 256 }
        value: { type: string, maxLength: 4096 }
        name: { type: string, maxLength: 4096 }
        display_zh: { type: string, maxLength: 512 }
        display_en: { type: string, maxLength: 512 }
        display_lang_1: { type: string, maxLength: 512 }
        display_lang_2: { type: string, maxLength: 512 }
        description_zh: { type: string }
        description_en: { type: string }
        description_lang_1: { type: string }
        description_lang_2: { type: string }
        synonyms:
          type: object
          maxProperties: 3
          additionalProperties:
            type: array
            items: { type: string }
        op:
          type: string
          enum: [UPSERT, DELETE]
          default: UPSERT
      additionalProperties: false

    InstanceValueRecord:
      type: object
      required: [propertyid, value]
      properties:
        propertyid: { type: string, maxLength: 512 }
        objectTypeId: { type: string, maxLength: 256 }
        value: { type: string, maxLength: 4096 }
        language: { type: string, default: und }
        op:
          type: string
          enum: [UPSERT, DELETE]
          default: UPSERT
      additionalProperties: false

    MetadataEnumBatchImportRequest:
      type: object
      required: [requestId, dataType, importMode, records]
      properties:
        requestId: { type: string, minLength: 1, maxLength: 256 }
        dataType: { type: string, enum: [METADATA_ENUM] }
        importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL] }
        records:
          type: array
          minItems: 1
          items: { $ref: '#/components/schemas/MetadataEnumRecord' }
      additionalProperties: false

    InstanceValueBatchImportRequest:
      type: object
      required: [requestId, dataType, importMode, records]
      properties:
        requestId: { type: string, minLength: 1, maxLength: 256 }
        dataType: { type: string, enum: [INSTANCE_VALUE] }
        importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL] }
        records:
          type: array
          minItems: 1
          items: { $ref: '#/components/schemas/InstanceValueRecord' }
      additionalProperties: false

    IndexBatchImportRequest:
      oneOf:
        - $ref: '#/components/schemas/MetadataEnumBatchImportRequest'
        - $ref: '#/components/schemas/InstanceValueBatchImportRequest'
      discriminator:
        propertyName: dataType
        mapping:
          METADATA_ENUM: '#/components/schemas/MetadataEnumBatchImportRequest'
          INSTANCE_VALUE: '#/components/schemas/InstanceValueBatchImportRequest'

    MinioCsvFile:
      type: object
      required: [bucket, objectKey, sha256]
      properties:
        bucket: { type: string, minLength: 3, maxLength: 63 }
        objectKey: { type: string, minLength: 1, maxLength: 1024 }
        fileFormat: { type: string, enum: [CSV], default: CSV }
        encoding: { type: string, enum: [UTF-8], default: UTF-8 }
        hasHeader: { type: boolean, enum: [true], default: true }
        rowCount: { type: integer, format: int64, minimum: 0 }
        size: { type: integer, format: int64, minimum: 0 }
        sha256:
          type: string
          pattern: '^[A-Fa-f0-9]{64}$'
      additionalProperties: false

    IndexFileImportRequest:
      type: object
      required: [requestId, dataType, importMode, files]
      properties:
        requestId: { type: string, minLength: 1, maxLength: 256 }
        dataType: { type: string, enum: [METADATA_ENUM, INSTANCE_VALUE] }
        importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL] }
        files:
          type: array
          minItems: 1
          items: { $ref: '#/components/schemas/MinioCsvFile' }
      additionalProperties: false

    AsyncTaskAcceptedResponse:
      type: object
      required: [ontologyId, taskId, requestId, dataType, sourceType, status, stage]
      properties:
        ontologyId: { type: string }
        taskId: { type: string }
        requestId: { type: string }
        dataType: { type: string, enum: [METADATA_ENUM, INSTANCE_VALUE] }
        sourceType: { type: string, enum: [REST, MINIO] }
        status: { type: integer, enum: [0, 1, 2, 3] }
        stage: { type: string }

    IndexTaskResponse:
      type: object
      required: [ontologyId, taskId, requestId, dataType, sourceType, status, stage, createTime, updateTime]
      properties:
        tenantId: { type: string, nullable: true }
        ontologyId: { type: string }
        taskId: { type: string }
        requestId: { type: string }
        dataType: { type: string, enum: [SEED_NODE, METADATA_ENUM, INSTANCE_VALUE] }
        sourceType: { type: string, enum: [OMS, REST, MINIO] }
        importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL], nullable: true }
        status: { type: integer, enum: [0, 1, 2, 3] }
        stage: { type: string }
        totalCount: { type: integer, format: int64, nullable: true }
        successCount: { type: integer, format: int64, nullable: true }
        failedCount: { type: integer, format: int64, nullable: true }
        skippedCount: { type: integer, format: int64, nullable: true }
        retryCount: { type: integer, minimum: 0 }
        errorCode: { type: string, nullable: true }
        errorMessage: { type: string, nullable: true }
        createTime: { type: string, format: date-time }
        startTime: { type: string, format: date-time, nullable: true }
        updateTime: { type: string, format: date-time }
        completionTime: { type: string, format: date-time, nullable: true }

    TaskOperationAcceptedResponse:
      type: object
      required: [ontologyId, taskId, operation, accepted, status, stage]
      properties:
        ontologyId: { type: string }
        taskId: { type: string }
        operation: { type: string, enum: [RETRY, CANCEL] }
        accepted: { type: boolean }
        status: { type: integer, enum: [0, 1, 2, 3] }
        stage: { type: string }

    IndexTaskErrorItem:
      type: object
      required: [errorCode, errorMessage]
      properties:
        recordIndex: { type: integer, format: int64, nullable: true }
        objectKey: { type: string, nullable: true }
        rowNumber: { type: integer, format: int64, nullable: true }
        propertyId: { type: string, nullable: true }
        objectTypeId: { type: string, nullable: true }
        value: { type: string, nullable: true }
        errorCode: { type: string }
        errorMessage: { type: string }

    IndexTaskErrorPage:
      type: object
      required: [taskId, page, pageSize, total, items]
      properties:
        taskId: { type: string }
        page: { type: integer, minimum: 0 }
        pageSize: { type: integer, minimum: 1, maximum: 1000 }
        total: { type: integer, format: int64, minimum: 0 }
        items:
          type: array
          items: { $ref: '#/components/schemas/IndexTaskErrorItem' }

    ValidationErrorResponse:
      type: object
      required: [message]
      properties:
        message:
          type: string

    BusinessErrorResponse:
      type: object
      required: [code, descriptions]
      properties:
        code: { type: string }
        descriptions:
          type: object
          additionalProperties: { type: string }
        solutions:
          type: object
          additionalProperties: true
        descriptionDetails:
          nullable: true

  examples:
    MetadataEnumBatchImportExample:
      value:
        requestId: req-enum-20260816-000001
        dataType: METADATA_ENUM
        importMode: INCREMENTAL
        records:
          - propertyId: prop:ont:vehicle:sp:bodyColor
            objectTypeId: obj:ont:vehicle:Vehicle
            value: red
            name: red
            display_zh: 红色
            display_en: Red
            op: UPSERT
    InstanceValueBatchImportExample:
      value:
        requestId: req-instance-20260816-000001
        dataType: INSTANCE_VALUE
        importMode: INCREMENTAL
        records:
          - propertyid: prop:subscriber:subLevel
            objectTypeId: obj:subscriber:Subscriber
            value: VIP
            language: und
            op: UPSERT

  responses:
    BadRequest:
      description: 请求参数校验失败
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ValidationErrorResponse' }
    NotFound:
      description: 指定资源不存在
      content:
        application/json:
          schema: { $ref: '#/components/schemas/BusinessErrorResponse' }
    Conflict:
      description: 幂等键或任务状态冲突
      content:
        application/json:
          schema: { $ref: '#/components/schemas/BusinessErrorResponse' }
    PayloadTooLarge:
      description: REST Batch 请求体或 records 超过服务限制
      content:
        application/json:
          schema: { $ref: '#/components/schemas/BusinessErrorResponse' }
    TooManyRequests:
      description: 请求被限流
      content:
        application/json:
          schema: { $ref: '#/components/schemas/BusinessErrorResponse' }
    InternalError:
      description: 服务内部错误
      content:
        application/json:
          schema: { $ref: '#/components/schemas/BusinessErrorResponse' }
    ServiceUnavailable:
      description: 外部依赖暂不可用
      content:
        application/json:
          schema: { $ref: '#/components/schemas/BusinessErrorResponse' }
```

### 3.8.6 公共错误响应示例

#### 参数校验失败：HTTP 400

```json
{
  "message": "requestId must not be empty"
}
```

#### 幂等键冲突：HTTP 409

```json
{
  "code": "IDEMPOTENCY_CONFLICT",
  "descriptions": {
    "zh_CN": "相同 requestId 已用于不同的导入请求",
    "en_US": "The same requestId has already been used for a different import request"
  },
  "solutions": {
    "zh_CN": "复用原请求内容，或使用新的 requestId"
  },
  "descriptionDetails": null
}
```

#### 服务内部异常：HTTP 500

```json
{
  "code": "OAG_INTERNAL_ERROR",
  "descriptions": {
    "zh_CN": "服务内部错误",
    "en_US": "service internal server error"
  },
  "solutions": {},
  "descriptionDetails": null
}
```

