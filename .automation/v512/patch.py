from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch.py <document>')

p = Path(sys.argv[1])
text = p.read_text(encoding='utf-8')
original = text


def sub_once(pattern: str, replacement: str, *, flags=re.S):
    global text
    text, n = re.subn(pattern, replacement, text, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f'expected exactly one match: {pattern!r}, got {n}')


def replace_once(old: str, new: str):
    global text
    n = text.count(old)
    if n < 1:
        raise SystemExit(f'missing expected text: {old[:120]!r}')
    text = text.replace(old, new, 1)


replace_once('> 版本：V5.11', '> 版本：V5.12')
replace_once('3. 索引构建与 DataSync Bulk Import  ', '3. 索引构建与入库  ')

# 3.3.3 task retry description: business decides from stable error/file information.
text = text.replace(
    '逐 task 判断 retryable，允许部分成功',
    '业务基于错误码与失败文件选择 task，OAG 校验状态和源文件可恢复性，允许部分成功'
)

# Fix the existing INSTANCE_VALUE CSV mapping table inconsistency while touching chapter 3.
old_instance_csv_table = '''| CSV 字段           | 目标字段             | 说明                  |
| ---------------- | ---------------- | ------------------- |
| `property_id`    | `property_id`    | 所属 Property.id      |
| `object_type_id` | `object_type_id` | 所属 ObjectType.id    |
| `value`          | `value`          | 真实 Instance Value   |
| `op`             | 导入操作             | `UPSERT` / `DELETE` |'''
new_instance_csv_table = '''| CSV 字段         | 目标字段         | 说明                  |
| ---------------- | ---------------- | ------------------- |
| `propertyid`     | `propertyid`     | 所属 Property.id      |
| `objectTypeId`   | `objectTypeId`   | 所属 ObjectType.id    |
| `value`          | `value`          | 真实 Instance Value   |
| `language`       | `language`       | 可选语言标记，未知使用 `und` |
| `op`             | 导入操作             | `UPSERT` / `DELETE` |'''
if old_instance_csv_table in text:
    text = text.replace(old_instance_csv_table, new_instance_csv_table, 1)

new_37 = r'''### 3.7.3 文件不可变与校验

文件上传成功并提交 `file-import` 后，同一个 `objectKey` 在任务结束前不得覆盖。OAG 至少校验 Bucket 允许列表、Object 是否存在、size、sha256、CSV Header、dataType 对应 Schema 和可选 rowCount。百万/千万级数据必须流式读取，不允许一次性加载完整 CSV 到 JVM Heap。

同一个 `file-import` Task 内的所有 `files[]` 必须使用同一个 Bucket；`FILE_LIST` 只保存 objectKey 列表，Bucket 统一保存在任务级 `BUCKET_NAME`。如果调用方需要跨 Bucket 导入，应拆成多个 Task，避免任务持久化和重试语义出现歧义。

任务执行期间 OAG 将 `FILE_LIST` 视为不可变输入快照：

```text
file-import.files[]
  ↓
校验 bucket/objectKey/sha256
  ↓
写入 T_OAG_INDEX_TASK.FILE_LIST
  ↓
任务执行期间禁止覆盖同名 objectKey
```

### 3.7.4 文件老化与删除策略

文件生命周期采用 **“生产者负责业务删除 + MinIO Lifecycle 硬 TTL 兜底 + OAG 只读消费”** 的职责边界，不由 OAG 周期线程主动删除 DataSync/业务上传的源 CSV。

职责如下：

| 角色 | 职责 |
|---|---|
| DataSync / 业务系统 | 上传源 CSV；任务终态后根据业务重试、审计和留存要求决定是否提前删除源文件 |
| OAG | 只读消费源 CSV；记录 `FILE_LIST / ERR_FILE_LIST / FILE_RETENTION_UNTIL`；不主动删除生产者源文件 |
| MinIO / 平台 | 对 OAG 导入 Bucket/Prefix 配置 Lifecycle，作为最大保留期限的硬兜底 |

推荐策略：

```text
SUCCESS
  → 业务确认不再需要重试后可删除源文件

FAILED
  → 在决定 retry / 修复后重新提交之前保留失败文件

CANCELLED
  → 业务确认无需恢复后可删除

达到 MinIO Lifecycle 硬 TTL
  → 对象允许自动过期
  → 原 Task 不再保证可重试
  → 业务需要重新上传并创建新的导入 Task
```

MinIO 最大保留时间必须配置化，例如可从 `sourceFileMaxRetentionDays=30` 起步，不能硬编码到业务协议。OAG 根据相同配置计算并持久化 `FILE_RETENTION_UNTIL`，用于向业务暴露当前 Task 的源文件最晚可恢复时间；该字段是重试窗口提示，不代表 OAG 拥有删除权限。

OAG 自己产生的 staging/chunk/cache 临时文件不属于生产者源文件，可以由 OAG 独立定期清理。
'''
sub_once(r'### 3\.7\.3 文件不可变与校验\n.*?(?=\n## 3\.8 GaussDB 索引任务持久化)', new_37.rstrip())

# Refresh task persistence model and DDL. FILE_LIST/ERR_FILE_LIST are JSON arrays in TEXT,
# avoiding pseudo SQL Array[String], and ERROR_CODE_LIST carries multi-error tasks.
new_381_383 = r'''### 3.8.1 `T_OAG_INDEX_TASK` 表结构

任务表继续作为 Task 级事实来源，同时补齐 **稳定错误码集合 + 全量文件列表 + 失败文件列表 + 源文件保留截止时间**。业务侧据此决定是否调用重试接口，OAG 不再持久化或返回 `retryable`。

| 字段名                   | 类型            | 约束       | 说明 |
| --------------------- | ------------- | -------- | ---- |
| `TENANT_ID`           | VARCHAR(256)  | NOT NULL | 租户 ID |
| `ONTOLOGY_ID`         | VARCHAR(256)  | NOT NULL | 本体 ID |
| `TASK_ID`             | VARCHAR(256)  | PK       | 索引任务 ID |
| `REQUEST_ID`          | VARCHAR(256)  | NOT NULL | 调用幂等键 |
| `DATA_TYPE`           | VARCHAR(64)   | NOT NULL | `SEED_NODE` / `METADATA_ENUM` / `INSTANCE_VALUE` |
| `SOURCE_TYPE`         | VARCHAR(32)   | NOT NULL | `OMS` / `REST` / `MINIO` |
| `IMPORT_MODE`         | VARCHAR(32)   |          | `FULL_REPLACE` / `INCREMENTAL` |
| `STATUS`              | INT           | NOT NULL | 0 构建中；1 成功；2 失败；3 已取消 |
| `STAGE`               | VARCHAR(64)   |          | 当前执行阶段 |
| `TOTAL_COUNT`         | BIGINT        |          | 总记录数 |
| `SUCCESS_COUNT`       | BIGINT        |          | 成功记录数 |
| `FAILED_COUNT`        | BIGINT        |          | 失败记录数 |
| `SKIPPED_COUNT`       | BIGINT        |          | 去重/过滤记录数 |
| `BUCKET_NAME`         | VARCHAR(256)  |          | MinIO Bucket；REST/OMS 可空；同一 Task 只允许一个 Bucket |
| `OBJECT_PREFIX`       | VARCHAR(1024) |          | MinIO 公共 Object Prefix；REST/OMS 可空 |
| `FILE_LIST`           | TEXT          |          | JSON String Array；当前 Task 的全部 objectKey，MINIO 任务使用 |
| `ERR_FILE_LIST`       | TEXT          |          | JSON String Array；本次执行失败或需要重处理的 objectKey |
| `FILE_RETENTION_UNTIL`| TIMESTAMP     |          | 源文件硬 TTL 对应的最晚可恢复时间；REST/OMS 可空 |
| `CHECKPOINT`          | VARCHAR(1024) |          | CSV 文件/行号或内部 Chunk Checkpoint |
| `RETRY_COUNT`         | INT           | NOT NULL | 已执行重试次数，默认 0 |
| `ERROR_CODE`          | VARCHAR(128)  |          | 兼容字段；Task 主错误码/最后一个高优先级错误码 |
| `ERROR_CODE_LIST`     | TEXT          |          | JSON String Array；Task 本次执行出现的去重错误码集合，供业务决策 |
| `ERROR_MESSAGE`       | TEXT          |          | 错误摘要，仅用于展示/定位，不作为业务重试判断依据 |
| `CREATE_USER_ACCOUNT` | VARCHAR(256)  | NOT NULL | 创建者 |
| `CREATE_TIME`         | TIMESTAMP     | NOT NULL | 创建时间 |
| `START_TIME`          | TIMESTAMP     |          | 实际开始时间 |
| `UPDATE_TIME`         | TIMESTAMP     | NOT NULL | 最近状态更新时间 |
| `COMPLETION_TIME`     | TIMESTAMP     |          | 完成时间 |

数据库中的 `FILE_LIST / ERR_FILE_LIST / ERROR_CODE_LIST` 使用 `TEXT` 存储 JSON Array，而不是使用文档伪类型 `Array[String]`。API 层统一反序列化为 `Array[String]` 返回：

```text
FILE_LIST        = [".../part-00000.csv", ".../part-00001.csv"]
ERR_FILE_LIST    = [".../part-00001.csv"]
ERROR_CODE_LIST  = ["VECTOR_WRITE_FAILED", "SEARCH_WRITE_FAILED"]
```

字段语义：

```text
ERROR_CODE
  → 兼容已有单错误码调用方

ERROR_CODE_LIST
  → 当前执行发现的去重错误码集合
  → 业务侧重试/修复决策优先使用

FILE_LIST
  → 当前 Task 注册的完整 MinIO objectKey 快照

ERR_FILE_LIST
  → 当前执行失败、重试时优先处理的文件集合
```

`STATUS=0/1/2` 继续兼容现有构建中/成功/失败语义，`STATUS=3` 表示取消；更细执行阶段写入 `STAGE`：`CREATED / VALIDATING / READING / DEDUPLICATING / EMBEDDING / WRITING_VECTOR / WRITING_SEARCH / VERIFYING / PUBLISHING / CANCEL_REQUESTED / FINISHED`。

### 3.8.2 索引与约束

```sql
PRIMARY KEY (TASK_ID);

CREATE UNIQUE INDEX UQ_T_OAG_INDEX_TASK_REQUEST
ON T_OAG_INDEX_TASK (TENANT_ID, ONTOLOGY_ID, REQUEST_ID);

CREATE INDEX IDX_T_OAG_INDEX_TASK_ONTOLOGY_TIME
ON T_OAG_INDEX_TASK (TENANT_ID, ONTOLOGY_ID, CREATE_TIME);

CREATE INDEX IDX_T_OAG_INDEX_TASK_STATUS_TIME
ON T_OAG_INDEX_TASK (STATUS, UPDATE_TIME);

CREATE INDEX IDX_T_OAG_INDEX_TASK_RETENTION
ON T_OAG_INDEX_TASK (FILE_RETENTION_UNTIL);
```

`TENANT_ID + ONTOLOGY_ID + REQUEST_ID` 唯一约束确保同租户同本体的 API 重试不会创建重复任务；单租户部署也应写入固定租户值，不依赖 `NULL` 的唯一索引语义。

### 3.8.3 GaussDB 建表示例

```sql
CREATE TABLE T_OAG_INDEX_TASK
(
    TENANT_ID             VARCHAR(256)  NOT NULL,
    ONTOLOGY_ID           VARCHAR(256)  NOT NULL,
    TASK_ID               VARCHAR(256)  NOT NULL,
    REQUEST_ID            VARCHAR(256)  NOT NULL,
    DATA_TYPE             VARCHAR(64)   NOT NULL,
    SOURCE_TYPE           VARCHAR(32)   NOT NULL,
    IMPORT_MODE           VARCHAR(32),
    STATUS                INT           NOT NULL,
    STAGE                 VARCHAR(64),
    TOTAL_COUNT           BIGINT,
    SUCCESS_COUNT         BIGINT,
    FAILED_COUNT          BIGINT,
    SKIPPED_COUNT         BIGINT,
    BUCKET_NAME           VARCHAR(256),
    OBJECT_PREFIX         VARCHAR(1024),
    FILE_LIST             TEXT,
    ERR_FILE_LIST         TEXT,
    FILE_RETENTION_UNTIL  TIMESTAMP,
    CHECKPOINT            VARCHAR(1024),
    RETRY_COUNT           INT           NOT NULL DEFAULT 0,
    ERROR_CODE            VARCHAR(128),
    ERROR_CODE_LIST       TEXT,
    ERROR_MESSAGE         TEXT,
    CREATE_USER_ACCOUNT   VARCHAR(256)  NOT NULL,
    CREATE_TIME           TIMESTAMP     NOT NULL,
    START_TIME            TIMESTAMP,
    UPDATE_TIME           TIMESTAMP     NOT NULL,
    COMPLETION_TIME       TIMESTAMP,
    CONSTRAINT PK_T_OAG_INDEX_TASK_TASK_ID PRIMARY KEY (TASK_ID)
);

CREATE UNIQUE INDEX UQ_T_OAG_INDEX_TASK_REQUEST
ON T_OAG_INDEX_TASK (TENANT_ID, ONTOLOGY_ID, REQUEST_ID);
CREATE INDEX IDX_T_OAG_INDEX_TASK_ONTOLOGY_TIME
ON T_OAG_INDEX_TASK (TENANT_ID, ONTOLOGY_ID, CREATE_TIME);
CREATE INDEX IDX_T_OAG_INDEX_TASK_STATUS_TIME
ON T_OAG_INDEX_TASK (STATUS, UPDATE_TIME);
CREATE INDEX IDX_T_OAG_INDEX_TASK_RETENTION
ON T_OAG_INDEX_TASK (FILE_RETENTION_UNTIL);
```

如果现网已经存在精简版 `T_OAG_INDEX_TASK`，通过数据库升级脚本增加 `FILE_LIST / ERR_FILE_LIST / FILE_RETENTION_UNTIL / ERROR_CODE_LIST` 等字段并调整幂等索引，不新建第二张任务主表。
'''
sub_once(r'### 3\.8\.1 `T_OAG_INDEX_TASK` 表结构\n.*?(?=\n### 3\.8\.4 索引任务管理接口详细定义)', new_381_383.rstrip())

new_query = r'''#### 3.8.4.1 批量查询索引任务

##### 典型场景

业务侧提交多个索引任务后，需要一次查询多个 `taskId` 的状态、进度、稳定错误码以及 MinIO 文件列表，再由业务规则决定是否重试、修复数据或重新提交。

##### 接口功能

按 `taskIds` 批量读取 GaussDB `T_OAG_INDEX_TASK`。接口校验 `tenant + ontologyId` 归属；单个 task 不存在或不属于当前本体时，不让整个批次失败，而是在 `notFoundTaskIds` 中返回。

批量查询选择 `POST + JSON Body` 而不是 GET Query 参数，避免大量 taskId 触发 URL/网关长度限制；该接口语义仍为只读、无副作用查询。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/query
```

##### 请求参数

**表 11  BatchTaskIdsRequest 参数列表**

| 参数名称 | 类型 | 是否必选 | 默认值 | OpenAPI 约束 | 说明 |
|:--|:--|:--|:--|:--|:--|
| `taskIds` | Array[String] | 是 | - | `minItems: 1`，`uniqueItems: true`；最大数量由 `maxTaskIdsPerRequest` 配置 | 待查询的索引任务 ID 列表 |

服务端对重复 `taskId` 去重并保持首次出现顺序。建议 `maxTaskIdsPerRequest` 默认从 100 起步，通过接口压测调整。

##### 请求示例

```json
{
  "taskIds": [
    "idx-task-20260816-000001",
    "idx-task-20260816-000002"
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
| `tasks` | Array[IndexTaskResponse] | 已找到任务的状态、进度、错误和文件信息 |
| `notFoundTaskIds` | Array[String] | 不存在或不属于当前 tenant/ontology 的 taskId |

`IndexTaskResponse`：

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
| `errorCode` | String | 兼容主错误码；无错误时为空 |
| `errorCodes` | Array[String] | 本次执行出现的去重稳定错误码集合；业务重试判断优先使用 |
| `errorMessage` | String | 错误摘要，仅用于展示/定位 |
| `fileList` | Array[String] | MINIO Task 的全部 objectKey；其他来源返回空数组 |
| `errFileList` | Array[String] | 本次执行失败/需要重处理的 objectKey；其他来源或无失败返回空数组 |
| `fileRetentionUntil` | String(date-time) | MinIO 源文件硬 TTL 对应的最晚恢复时间；其他来源为空 |
| `createTime` | String(date-time) | 创建时间 |
| `startTime` | String(date-time) | 实际开始时间 |
| `updateTime` | String(date-time) | 最近更新时间 |
| `completionTime` | String(date-time) | 完成时间；未结束可为空 |

业务侧重试判断推荐只使用稳定结构化信息：

```text
status == 2
+ errorCode / errorCodes
+ fileList / errFileList
+ fileRetentionUntil
+ 业务自身重试策略
```

不得解析 `errorMessage` 文本来决定是否重试。

##### 响应示例

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "requestedCount": 2,
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
      "errorCode": null,
      "errorCodes": [],
      "errorMessage": null,
      "fileList": [],
      "errFileList": [],
      "fileRetentionUntil": null,
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
      "errorCode": "VECTOR_WRITE_FAILED",
      "errorCodes": ["VECTOR_WRITE_FAILED"],
      "errorMessage": "temporary vector storage write failure",
      "fileList": [
        "onto-retrieval/t1/dtmi.ontology.xxx.1/INSTANCE_VALUE/req-instance-002/part-00000.csv",
        "onto-retrieval/t1/dtmi.ontology.xxx.1/INSTANCE_VALUE/req-instance-002/part-00001.csv"
      ],
      "errFileList": [
        "onto-retrieval/t1/dtmi.ontology.xxx.1/INSTANCE_VALUE/req-instance-002/part-00001.csv"
      ],
      "fileRetentionUntil": "2026-09-15T22:11:00+08:00",
      "createTime": "2026-08-16T22:11:00+08:00",
      "updateTime": "2026-08-16T22:11:08+08:00"
    }
  ],
  "notFoundTaskIds": []
}
```

批量查询允许部分命中，因此单个 task 不存在时仍返回 `200`；只有 ontology 不存在、请求体非法或服务异常才使用请求级 `4xx/5xx`。

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/query:
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
'''
sub_once(r'#### 3\.8\.4\.1 批量查询索引任务\n.*?(?=\n---\n\n#### 3\.8\.4\.2 批量重试索引任务)', new_query.rstrip())

new_retry = r'''#### 3.8.4.2 批量重试索引任务

##### 典型场景

业务侧先通过任务查询获取 `errorCode/errorCodes + fileList/errFileList + fileRetentionUntil`，结合自身规则判断哪些失败 Task 需要重试，然后一次提交多个 `taskId`。

##### 接口功能

OAG **不再根据错误码返回或维护 `retryable`**。重试接口只做服务端必须保证的技术前置校验：

```text
任务存在且 tenant/ontology 归属一致
AND STATUS = 2（FAILED）
AND RETRY_COUNT 未超过服务配置上限
AND 原始 Source/Checkpoint 仍可恢复
```

MINIO Task 额外校验：

```text
当前时间 < FILE_RETENTION_UNTIL（配置了硬 TTL 时）
AND 需要重试的 objectKey 仍存在
AND 文件 sha256 与任务注册快照一致
```

重试文件范围：

```text
ERR_FILE_LIST 非空
  → 默认只重处理 ERR_FILE_LIST

ERR_FILE_LIST 为空，但失败发生在文件处理前/Task 级阶段
  → 根据 CHECKPOINT/STAGE 恢复；必要时使用 FILE_LIST

PUBLISH_FAILED / VERIFY_FAILED 等文件已处理完成的 Task 级失败
  → 优先从对应 STAGE/Checkpoint 继续，不强制重新读取全部 CSV
```

业务如果判断原始文件内容本身需要修正，不应覆盖原 objectKey 后调用 retry；应生成新文件、新 requestId，并重新调用 `file-import`。

批量操作采用**逐任务判定、允许部分成功**。一个 Task 因状态、重试次数或源文件过期被拒绝，不阻断其他 Task。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/retry
```

##### 请求参数

复用表 11 `BatchTaskIdsRequest`。业务侧传入已经根据错误码和文件信息筛选后的 taskIds。

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
| `reasonCode` | String | `TASK_NOT_FOUND / TASK_STATE_CONFLICT / RETRY_LIMIT_EXCEEDED / SOURCE_UNRECOVERABLE / SOURCE_FILE_EXPIRED / SOURCE_FILE_MISSING` 等 |
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
      "reasonCode": null,
      "message": "retry accepted; failed files will be resumed"
    },
    {
      "taskId": "idx-task-002",
      "accepted": false,
      "status": 2,
      "stage": "FINISHED",
      "reasonCode": "SOURCE_FILE_EXPIRED",
      "message": "source file retention window has expired; re-upload and create a new task"
    },
    {
      "taskId": "idx-task-404",
      "accepted": false,
      "status": null,
      "stage": null,
      "reasonCode": "TASK_NOT_FOUND",
      "message": "task not found"
    }
  ]
}
```

请求结构合法时返回 `202`；逐 task 是否真正进入队列由 `results[].accepted` 表达，不使用单个 task 的 `409/404` 把整个批次打失败。

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/retry:
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
'''
sub_once(r'#### 3\.8\.4\.2 批量重试索引任务\n.*?(?=\n---\n\n#### 3\.8\.4\.3 批量取消索引任务)', new_retry.rstrip())

new_cancel = r'''#### 3.8.4.3 批量取消索引任务

##### 典型场景

业务侧发现多个导入任务的数据范围错误或需要停止一组耗时任务，希望一次取消多个任务。

##### 接口功能

对 `STATUS=0` 的运行中/排队任务设置 `STAGE=CANCEL_REQUESTED`。Worker 在安全检查点停止后更新为 `STATUS=3`。批量取消逐 task 判定、允许部分成功。

取消操作幂等：已处于 `STATUS=3` 的任务返回 `accepted=true`、`reasonCode=ALREADY_CANCELLED`；`STATUS=1/2` 的终态任务返回 `accepted=false`、`reasonCode=TASK_STATE_CONFLICT`。

##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-tasks/cancel
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
      "reasonCode": null,
      "message": "cancel accepted"
    },
    {
      "taskId": "idx-task-002",
      "accepted": true,
      "status": 3,
      "stage": "FINISHED",
      "reasonCode": "ALREADY_CANCELLED",
      "message": "task already cancelled"
    },
    {
      "taskId": "idx-task-003",
      "accepted": false,
      "status": 1,
      "stage": "FINISHED",
      "reasonCode": "TASK_STATE_CONFLICT",
      "message": "completed task cannot be cancelled"
    }
  ]
}
```

##### OpenAPI 3.0.3 Path 定义

```yaml
/v1/onto-retrieval/{ontologyId}/index-tasks/cancel:
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
'''
sub_once(r'#### 3\.8\.4\.3 批量取消索引任务\n.*?(?=\n---\n\n### 3\.8\.5 OpenAPI 3\.0\.3 公共 Components 定义)', new_cancel.rstrip())

# Refresh task-related OpenAPI schemas only; keep the already-defined import and error schemas.
new_task_schemas = r'''    IndexTaskResponse:
      type: object
      required: [ontologyId, taskId, requestId, dataType, sourceType, status, stage, errorCodes, fileList, errFileList, createTime, updateTime]
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
        errorCodes:
          type: array
          items: { type: string }
        errorMessage: { type: string, nullable: true }
        fileList:
          type: array
          items: { type: string }
        errFileList:
          type: array
          items: { type: string }
        fileRetentionUntil: { type: string, format: date-time, nullable: true }
        createTime: { type: string, format: date-time }
        startTime: { type: string, format: date-time, nullable: true }
        updateTime: { type: string, format: date-time }
        completionTime: { type: string, format: date-time, nullable: true }

    BatchTaskIdsRequest:
      type: object
      required: [taskIds]
      properties:
        taskIds:
          type: array
          minItems: 1
          uniqueItems: true
          items: { type: string, maxLength: 256 }
      additionalProperties: false

    BatchTaskQueryResponse:
      type: object
      required: [ontologyId, requestedCount, foundCount, tasks, notFoundTaskIds]
      properties:
        ontologyId: { type: string }
        requestedCount: { type: integer, minimum: 0 }
        foundCount: { type: integer, minimum: 0 }
        tasks:
          type: array
          items: { $ref: '#/components/schemas/IndexTaskResponse' }
        notFoundTaskIds:
          type: array
          items: { type: string }

    TaskOperationResult:
      type: object
      required: [taskId, accepted]
      properties:
        taskId: { type: string }
        accepted: { type: boolean }
        status: { type: integer, enum: [0, 1, 2, 3], nullable: true }
        stage: { type: string, nullable: true }
        reasonCode: { type: string, nullable: true }
        message: { type: string, nullable: true }

    BatchTaskOperationResponse:
      type: object
      required: [ontologyId, operation, requestedCount, acceptedCount, rejectedCount, results]
      properties:
        ontologyId: { type: string }
        operation: { type: string, enum: [RETRY, CANCEL] }
        requestedCount: { type: integer, minimum: 0 }
        acceptedCount: { type: integer, minimum: 0 }
        rejectedCount: { type: integer, minimum: 0 }
        results:
          type: array
          items: { $ref: '#/components/schemas/TaskOperationResult' }

'''
sub_once(r'    IndexTaskResponse:\n.*?(?=    IndexTaskErrorItem:)', new_task_schemas)

# Task state persistence semantics.
text = text.replace(
    '后台持续更新 `STAGE / TOTAL_COUNT / SUCCESS_COUNT / FAILED_COUNT / SKIPPED_COUNT / CHECKPOINT / UPDATE_TIME`。',
    '后台持续更新 `STAGE / TOTAL_COUNT / SUCCESS_COUNT / FAILED_COUNT / SKIPPED_COUNT / FILE_LIST / ERR_FILE_LIST / ERROR_CODE_LIST / CHECKPOINT / UPDATE_TIME`。'
)
text = text.replace(
    'FAILED    → STATUS=2, ERROR_CODE/ERROR_MESSAGE, COMPLETION_TIME',
    'FAILED    → STATUS=2, ERROR_CODE/ERROR_CODE_LIST/ERROR_MESSAGE/ERR_FILE_LIST, COMPLETION_TIME'
)
text = text.replace(
    'OAG 重启后从 GaussDB 找到未完成任务，根据 `SOURCE_TYPE + CHECKPOINT` 决定恢复、重试或标记失败。批量任务查询接口必须以 GaussDB 为事实来源，而不是以内存 Future/线程状态作为权威状态。',
    'OAG 重启后从 GaussDB 找到未完成任务，根据 `SOURCE_TYPE + CHECKPOINT + FILE_LIST` 决定恢复、重试或标记失败。对于 MINIO Task，如果源对象已经超过 `FILE_RETENTION_UNTIL` 或实际不存在，任务不能继续依赖原文件恢复。批量任务查询接口必须以 GaussDB 为事实来源，而不是以内存 Future/线程状态作为权威状态。'
)

new_316 = r'''## 3.16 错误处理与可观测性

错误协议采用 **稳定错误码 + 业务侧重试决策**。OAG 不再输出 `retryable`；业务系统根据 `status / errorCode / errorCodes / fileList / errFileList / fileRetentionUntil` 和自身策略决定 `RETRY / FIX_AND_RESUBMIT / REUPLOAD_AND_RESUBMIT / IGNORE`。

错误码及建议动作：

| 错误码 | 建议业务动作 | 说明 |
|---|---|---|
| `INVALID_REQUEST` | `FIX_AND_RESUBMIT` | 请求结构错误 |
| `INVALID_DATA_TYPE` | `FIX_AND_RESUBMIT` | dataType 非法 |
| `ONTOLOGY_NOT_FOUND` | `FIX_AND_RESUBMIT` | 本体不存在，先修复/安装本体 |
| `PROPERTY_NOT_FOUND` | `FIX_AND_RESUBMIT` | Property 不存在或映射错误 |
| `OBJECT_TYPE_MISMATCH` | `FIX_AND_RESUBMIT` | ObjectType 与 Property 归属冲突 |
| `CSV_SCHEMA_ERROR` | `FIX_AND_RESUBMIT` | CSV Header/字段格式错误，需要重新生成文件 |
| `MINIO_OBJECT_NOT_FOUND` | `REUPLOAD_AND_RESUBMIT` | MinIO 源对象不存在 |
| `CHECKSUM_MISMATCH` | `REUPLOAD_AND_RESUBMIT` | 文件内容已变化/损坏，不能覆盖原 objectKey 后直接 retry |
| `SOURCE_FILE_EXPIRED` | `REUPLOAD_AND_RESUBMIT` | 已超过源文件硬 TTL，原 Task 不再保证可恢复 |
| `MINIO_READ_FAILED` | `RETRY` | 已存在对象的临时读取失败 |
| `EMBEDDING_FAILED` | `RETRY` | Embedding 服务超时/5xx 等临时失败 |
| `VECTOR_WRITE_FAILED` | `RETRY` | GaussVector 临时写入失败，组合键 UPSERT 可幂等恢复 |
| `SEARCH_WRITE_FAILED` | `RETRY` | OpenSearch 临时写入失败，可按确定性 `_id` 幂等恢复 |
| `VERIFY_FAILED` | `RETRY` | 双写后校验失败，可从 Verify/补写阶段恢复 |
| `PUBLISH_FAILED` | `RETRY` | Generation 发布阶段临时失败，可从发布阶段恢复 |

表中的“建议业务动作”是接口设计建议，不是服务端 `retryable` 判定。业务可以按自身 SLA、重试次数、错误码组合和文件范围制定更严格策略，但不得依赖 `errorMessage` 自然语言文本做自动化决策。

Task 失败时：

```text
ERROR_CODE
  → 兼容主错误码

ERROR_CODE_LIST
  → 本次执行去重后的稳定错误码集合

FILE_LIST
  → 完整输入文件 objectKey 列表

ERR_FILE_LIST
  → 本次失败、重试时应优先处理的 objectKey 列表

FILE_RETENTION_UNTIL
  → 原 MinIO 文件可恢复窗口的硬截止时间
```

对于 MINIO Task，业务侧如果选择 retry，OAG 默认只重处理 `ERR_FILE_LIST`；如果失败发生在 VERIFY/PUBLISH 等 Task 级阶段，则按 `STAGE + CHECKPOINT` 恢复而不是机械重读全部文件。

任务级错误通过 `ERROR_CODE / ERROR_CODE_LIST / ERROR_MESSAGE` 写入 `T_OAG_INDEX_TASK`；记录级错误至少保留 taskId、objectKey/rowNumber 或 recordIndex、Property 标识（Enum 为 propertyId，Instance 为 propertyid）、objectTypeId、必要时脱敏后的 value、errorCode、errorMessage。

`GET /v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors` 继续按单任务分页返回记录级错误，避免将百万条错误塞入任务主表。

关键指标：

```text
oag_index_task_total
oag_index_task_duration
oag_import_records_total
oag_import_failed_records
oag_import_deduplicated_records
oag_import_retry_requested_total
oag_import_source_file_expired_total
oag_minio_read_bytes
oag_embedding_qps
oag_vector_write_qps
oag_opensearch_write_qps
```
'''
sub_once(r'## 3\.16 错误处理与可观测性\n.*?(?=\n---\n\n## 3\.17 端到端时序)', new_316.rstrip())

new_318 = r'''## 3.18 本章最终约束

1. **所有 OAG REST API 统一使用 `/v1/onto-retrieval/{ontologyId}` Namespace。**
2. **语义检索固定使用 `POST /subgraph/semantic-search`。**
3. **Enum/Instance 动态索引支持 REST Batch 和 MinIO CSV 两类入口。**
4. **两类入口使用 `dataType=METADATA_ENUM/INSTANCE_VALUE` 显式区分数据。**
5. **REST/CSV 核心定位字段与第 2.8/2.10 节一致，不接受外部 vector/type；动态 Enum 导入不再接收 name，synonyms 使用换行分隔平铺字符串。**
6. **DataSync → MinIO 数据文件统一使用 UTF-8 CSV。**
7. **DataSync 与 OAG 约定专用 MinIO Bucket；使用 S3 API 和 Path-style 访问；同一个 Task 的 files[] 必须位于同一 Bucket。**
8. **索引任务必须先持久化到 GaussDB `T_OAG_INDEX_TASK`，再异步执行。**
9. **任务查询以 GaussDB 为事实来源；`FILE_LIST / ERR_FILE_LIST / ERROR_CODE_LIST` 在数据库以 TEXT JSON Array 存储，在 API 以 Array[String] 返回。**
10. **REST 和文件导入共享 Normalize/Dedup/Embedding/双写/Verify/Publish Pipeline。**
11. **百万/千万级数据默认走 MinIO CSV Streaming，不通过超大 JSON Body。**
12. **GaussVector/OpenSearch 不使用分布式事务，通过唯一键、幂等、Verify 和任务重试保证一致性。**
13. **GaussVector 使用 `(objectTypeId, propertyId/propertyid, value)` 组合唯一索引和 `INSERT ... ON DUPLICATE KEY UPDATE`，保证重复导入覆盖而不是新增向量。**
14. **任务查询、重试、取消统一提供批量接口；批量操作逐 task 返回结果，允许部分成功。**
15. **重试决策归业务侧：业务根据 `status + errorCode/errorCodes + fileList/errFileList + fileRetentionUntil` 选择 task；OAG 不再返回 `retryable`。**
16. **OAG 重试接口只校验 Task 状态、重试次数、Checkpoint 和源文件存在性/完整性；MINIO Task 默认只重处理失败文件集合。**
17. **DataSync/业务侧拥有源 CSV 生命周期；OAG 不主动删除源文件，MinIO Lifecycle 作为硬 TTL 兜底；OAG 仅清理自身 staging/cache 临时文件。**
18. **批量取消幂等处理已经取消的任务；终态成功/失败任务不再进入取消流程。**
'''
sub_once(r'## 3\.18 本章最终约束\n.*?(?=\n---\n\n## 3\.19 兼容与迁移说明)', new_318.rstrip())

text = text.replace(
    '动态枚举和实例列值共享协议、任务、去重、Embedding 和双存储能力，同时保留 REST 的动态性和 MinIO CSV 的规模能力。任务管理采用 batch-query / batch-retry / batch-cancel，数据写入采用数据库级组合键 UPSERT，使接口幂等与存储幂等形成闭环。',
    '动态枚举和实例列值共享协议、任务、去重、Embedding 和双存储能力，同时保留 REST 的动态性和 MinIO CSV 的规模能力。任务管理采用 batch-query / batch-retry / batch-cancel；业务根据稳定错误码和失败文件列表决定是否重试，OAG 负责技术前置校验和失败文件恢复；DataSync/业务拥有源 CSV 生命周期，MinIO Lifecycle 提供硬 TTL 兜底。数据写入继续采用数据库级组合键 UPSERT，使接口幂等、重试幂等与存储幂等形成闭环。'
)

# Remove stale retryable phrasing that may survive outside rewritten blocks in chapter 3.
chapter3_start = text.index('# 3. 索引构建与入库')
chapter4_start = text.index('# 4. Query Understanding 与 6 路召回')
chapter3 = text[chapter3_start:chapter4_start]

if 'TODO' in chapter3:
    raise SystemExit('TODO remains in chapter 3')
if 'retryable' in chapter3:
    raise SystemExit('stale retryable remains in chapter 3')
for required in [
    'ERROR_CODE_LIST',
    'FILE_RETENTION_UNTIL',
    'ERR_FILE_LIST',
    '生产者负责业务删除 + MinIO Lifecycle 硬 TTL 兜底 + OAG 只读消费',
    '业务根据 `status + errorCode/errorCodes + fileList/errFileList + fileRetentionUntil` 选择 task',
    'sourceFileMaxRetentionDays=30',
]:
    if required not in chapter3:
        raise SystemExit(f'missing required V5.12 contract: {required}')

if '| `property_id`' in chapter3 or '| `object_type_id`' in chapter3:
    raise SystemExit('stale INSTANCE CSV field mapping remains')
if 'FILE_LIST           | Array[String]' in chapter3:
    raise SystemExit('stale pseudo SQL Array[String] remains for FILE_LIST')

if text == original:
    raise SystemExit('patch produced no changes')

p.write_text(text, encoding='utf-8')
print('V5.12 chapter-3 TODO patch applied and validated')
