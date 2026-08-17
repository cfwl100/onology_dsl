#### 3.8.4.1 批量查询索引任务

##### 典型场景

业务侧提交多个 REST Batch / MinIO File Import 后，希望一次查询多个 `taskId` 的当前阶段、进度和失败原因，避免逐任务轮询产生大量 HTTP 请求。

##### 接口功能

按 `taskIds` 批量读取 GaussDB `T_OAG_INDEX_TASK`。接口必须校验 `tenant + ontologyId` 归属；单个 task 不存在或不属于当前本体时，不让整个批次失败，而是在 `notFoundTaskIds` 中返回。

批量查询选择 `POST + JSON Body` 而不是 GET Query 参数，原因是 taskId 数量较多时容易触发 URL 长度和网关限制；该接口虽然使用 POST，但语义上仍为只读、无副作用查询。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/batch-query
```

##### 请求参数

**表 11  BatchTaskIdsRequest 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `taskIds` | Array[String] | 是 | - | `minItems: 1`，`uniqueItems: true`；最大数量由 `maxTaskIdsPerRequest` 配置 | 待查询的索引任务 ID 列表 |

服务端对重复 `taskId` 先去重并保持首次出现顺序。建议 `maxTaskIdsPerRequest` 默认从 100 起步，通过接口压测调整，不在协议中绑定数据库 `IN` 子句的固定上限。

##### 请求示例

```json
{
  "taskIds": [
    "idx-task-20260816-000001",
    "idx-task-20260816-000002",
    "idx-task-20260816-000003"
  ]
}
```

##### 返回参数

**表 12  BatchTaskQueryResponse 参数列表（HTTP 200）**

| 参数名称 | 类型 | 说明 |
|:--|:--|:--|
| `ontologyId` | String | 本体 ID |
| `requestedCount` | Integer | 去重后的请求 task 数量 |
| `foundCount` | Integer | 实际查询到的任务数量 |
| `tasks` | Array[IndexTaskResponse] | 已找到任务的状态、进度和错误摘要 |
| `notFoundTaskIds` | Array[String] | 不存在或不属于当前 tenant/ontology 的 taskId |

`IndexTaskResponse` 保持原任务字段，并新增：

```text
retryable = true / false
```

其值由 `ERROR_CODE` 的重试策略计算；非失败任务默认为 `false`。

##### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "requestedCount": 3,
  "foundCount": 2,
  "tasks": [
    {
      "ontologyId": "dtmi.ontology.xxx.1",
      "taskId": "idx-task-20260816-000001",
      "requestId": "req-enum-001",
      "dataType": "METADATA_ENUM",
      "sourceType": "REST",
      "importMode": "INCREMENTAL",
      "status": 1,
      "stage": "FINISHED",
      "retryCount": 0,
      "retryable": false,
      "errorCode": null,
      "errorMessage": null,
      "createTime": "2026-08-16T22:10:00+08:00",
      "updateTime": "2026-08-16T22:10:08+08:00"
    },
    {
      "ontologyId": "dtmi.ontology.xxx.1",
      "taskId": "idx-task-20260816-000002",
      "requestId": "req-instance-002",
      "dataType": "INSTANCE_VALUE",
      "sourceType": "MINIO",
      "importMode": "INCREMENTAL",
      "status": 2,
      "stage": "WRITING_VECTOR",
      "retryCount": 0,
      "retryable": true,
      "errorCode": "VECTOR_WRITE_FAILED",
      "errorMessage": "temporary vector storage write failure",
      "createTime": "2026-08-16T22:11:00+08:00",
      "updateTime": "2026-08-16T22:11:08+08:00"
    }
  ],
  "notFoundTaskIds": ["idx-task-20260816-000003"]
}
```

批量查询允许部分命中，因此单个 task 不存在时仍返回 `200`；只有 ontology 不存在、请求体非法或服务异常才使用请求级 `4xx/5xx`。

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/batch-query:
  post:
    operationId: batchQueryIndexTasks
    summary: 批量查询索引任务
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TenantId'
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/BatchTaskIdsRequest'
    responses:
      '200':
        description: 批量查询成功，允许部分 task 未找到
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BatchTaskQueryResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
```

---

#### 3.8.4.2 批量重试索引任务

##### 典型场景

一批索引任务因 Embedding、GaussVector、OpenSearch、MinIO 读取或发布阶段的临时故障失败，业务侧希望一次性重试其中可恢复的任务。

##### 接口功能

批量检查 `taskIds`，仅把满足以下条件的任务重新加入执行队列：

```text
任务存在且 tenant/ontology 归属一致
AND STATUS = 2（FAILED）
AND retryable = true
AND 原始 REST Payload 或 MinIO Source/Checkpoint 仍可恢复
AND RETRY_COUNT 未超过服务配置上限
```

批量操作采用**逐任务判定、允许部分成功**。一个 task 不可重试不能阻断其他 task。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/batch-retry
```

##### 请求参数

复用表 11 `BatchTaskIdsRequest`。

##### 可重试错误码

业务侧应优先使用任务返回的 `retryable` 字段，而不是在客户端复制一套判断逻辑；错误码表用于故障定位和兜底判断。

| 错误码 | retryable | 处理建议 |
|---|---:|---|
| `MINIO_READ_FAILED` | true | MinIO 临时读取失败，可从 Checkpoint 重试 |
| `EMBEDDING_FAILED` | true | Embedding 服务超时/5xx 等临时失败，可重试 |
| `VECTOR_WRITE_FAILED` | true | GaussVector 临时写失败，利用组合键幂等 UPSERT 重试 |
| `SEARCH_WRITE_FAILED` | true | OpenSearch 临时写失败，可按业务键幂等重试 |
| `VERIFY_FAILED` | true | 双写后的临时校验失败，可重新 Verify/补写 |
| `PUBLISH_FAILED` | true | Generation 发布阶段临时失败，可重新发布 |
| `INVALID_REQUEST` | false | 请求结构错误，修正数据后重新提交新任务 |
| `INVALID_DATA_TYPE` | false | dataType 错误，修正后重新提交 |
| `ONTOLOGY_NOT_FOUND` | false | 本体不存在，需要先修复本体资产 |
| `PROPERTY_NOT_FOUND` | false | Property 映射不存在，需要修复本体/输入 |
| `OBJECT_TYPE_MISMATCH` | false | ObjectType 与 Property 归属冲突，需要修正数据 |
| `CSV_SCHEMA_ERROR` | false | CSV Header/字段格式错误，需要重新生成文件 |
| `MINIO_OBJECT_NOT_FOUND` | false | 源文件不存在，需要重新上传并新建导入任务 |
| `CHECKSUM_MISMATCH` | false | 文件内容已变化/损坏，需要重新生成并提交 |

如果同一个高层错误码存在可重试和不可重试两类根因，OAG 必须以 `retryable` 作为最终判断，不要求业务侧解析 `errorMessage`。

##### 返回参数

**表 13  BatchTaskOperationResponse 参数列表（HTTP 202）**

| 参数名称 | 类型 | 说明 |
|:--|:--|:--|
| `ontologyId` | String | 本体 ID |
| `operation` | String | `RETRY` / `CANCEL` |
| `requestedCount` | Integer | 去重后的请求 task 数量 |
| `acceptedCount` | Integer | 已进入异步操作的任务数量 |
| `rejectedCount` | Integer | 未接受操作的任务数量 |
| `results` | Array[TaskOperationResult] | 每个 task 的独立处理结果 |

`TaskOperationResult`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `taskId` | String | 任务 ID |
| `accepted` | Boolean | 当前操作是否被接受 |
| `status` | Integer | 当前任务状态；任务不存在时可为空 |
| `stage` | String | 当前任务阶段；任务不存在时可为空 |
| `retryable` | Boolean | 对 RETRY 表示当前失败是否允许重试 |
| `reasonCode` | String | `TASK_NOT_FOUND / TASK_STATE_CONFLICT / NOT_RETRYABLE / RETRY_LIMIT_EXCEEDED / SOURCE_UNRECOVERABLE` 等 |
| `message` | String | 简短处理说明 |

##### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "operation": "RETRY",
  "requestedCount": 3,
  "acceptedCount": 1,
  "rejectedCount": 2,
  "results": [
    {
      "taskId": "idx-task-001",
      "accepted": true,
      "status": 0,
      "stage": "CREATED",
      "retryable": true,
      "reasonCode": null,
      "message": "retry accepted"
    },
    {
      "taskId": "idx-task-002",
      "accepted": false,
      "status": 2,
      "stage": "FINISHED",
      "retryable": false,
      "reasonCode": "NOT_RETRYABLE",
      "message": "CSV_SCHEMA_ERROR must be fixed and resubmitted"
    },
    {
      "taskId": "idx-task-404",
      "accepted": false,
      "status": null,
      "stage": null,
      "retryable": false,
      "reasonCode": "TASK_NOT_FOUND",
      "message": "task not found"
    }
  ]
}
```

请求结构合法时返回 `202`，逐 task 是否真正进入队列由 `results[].accepted` 表达；不使用单个 task 的 `409/404` 把整个批次打失败。

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/batch-retry:
  post:
    operationId: batchRetryIndexTasks
    summary: 批量重试失败的索引任务
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TenantId'
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/BatchTaskIdsRequest'
    responses:
      '202':
        description: 批量重试请求已处理，逐 task 查看 accepted
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BatchTaskOperationResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
      '503': { $ref: '#/components/responses/ServiceUnavailable' }
```

---

#### 3.8.4.3 批量取消索引任务

##### 典型场景

业务侧发现多个导入任务的数据范围错误或需要停止一组耗时任务，希望一次取消多个任务。

##### 接口功能

对 `STATUS=0` 的运行中/排队任务设置 `STAGE=CANCEL_REQUESTED`。Worker 在安全检查点停止后更新为 `STATUS=3`。批量取消同样逐 task 判定、允许部分成功。

取消操作要求幂等：已处于 `STATUS=3` 的任务返回 `accepted=true`、`reasonCode=ALREADY_CANCELLED`，不重复触发取消；`STATUS=1/2` 的终态任务返回 `accepted=false`、`reasonCode=TASK_STATE_CONFLICT`。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/batch-cancel
```

##### 请求参数

复用表 11 `BatchTaskIdsRequest`。

##### 返回参数

复用表 13 `BatchTaskOperationResponse`，其中 `operation=CANCEL`。

##### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "operation": "CANCEL",
  "requestedCount": 3,
  "acceptedCount": 2,
  "rejectedCount": 1,
  "results": [
    {
      "taskId": "idx-task-001",
      "accepted": true,
      "status": 0,
      "stage": "CANCEL_REQUESTED",
      "retryable": false,
      "reasonCode": null,
      "message": "cancel accepted"
    },
    {
      "taskId": "idx-task-002",
      "accepted": true,
      "status": 3,
      "stage": "FINISHED",
      "retryable": false,
      "reasonCode": "ALREADY_CANCELLED",
      "message": "task already cancelled"
    },
    {
      "taskId": "idx-task-003",
      "accepted": false,
      "status": 1,
      "stage": "FINISHED",
      "retryable": false,
      "reasonCode": "TASK_STATE_CONFLICT",
      "message": "completed task cannot be cancelled"
    }
  ]
}
```

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/batch-cancel:
  post:
    operationId: batchCancelIndexTasks
    summary: 批量取消索引任务
    parameters:
      - $ref: '#/components/parameters/OntologyId'
      - $ref: '#/components/parameters/TenantId'
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/BatchTaskIdsRequest'
    responses:
      '202':
        description: 批量取消请求已处理，逐 task 查看 accepted
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BatchTaskOperationResponse'
      '400': { $ref: '#/components/responses/BadRequest' }
      '404': { $ref: '#/components/responses/NotFound' }
      '429': { $ref: '#/components/responses/TooManyRequests' }
      '500': { $ref: '#/components/responses/InternalError' }
```

---
