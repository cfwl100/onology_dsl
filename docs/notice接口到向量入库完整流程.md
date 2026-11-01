# notice 接口到向量入库完整实现流程

> 模块：OntoRetrieval 本体索引构建（MinIO CSV 文件导入）
> 工程：`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval`
> 本文档基于当前 master 分支代码梳理（最新提交 e5d4d74d，2026-10-27）

---

## 1. 流程总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ① REST 入口                                                                │
│ OntologyIndexTaskRest.noticeIndexData                                        │
│ POST /onto-retrieval-api/v1/onto-retrieval/{ontologyId}/index-data/notice    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ② IndexTaskService.createTaskAndExecute                                      │
│    · 刷新本体结构缓存 (每次notice)                                            │
│    · 按 20 文件/任务 拆分多个子任务                                            │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ③ 任务生命周期（每子任务）                                                   │
│    createTask(建任务记录)                                                    │
│      → 阶段1-5 同步校验 IndexTaskValidationService                           │
│      → 阶段6 异步文件校验 FileValidationWorker (executeValidationAsync,同步等) │
│      → 阶段7 异步Embedding/写索引 TaskExecutorService.executeEmbeddingAsync   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ④ 阶段7 向量入库（按 dataType 分流）                                         │
│    INSTANCE_VALUE → InstanceIndexServiceImpl.batchInstance                   │
│    （CLEAR 模式 → clearOntologyIndex 清理）                                   │
│    （Enum 类型：EnumIndexServiceImpl.batchCreateEnumIndex）                   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⑤ 向量化 + 双写                                                            │
│    EmbeddingModelFactory → ConfiguredEmbeddingModel.embedAll()               │
│    ┌─────────────────────────────┐  ┌──────────────────────────────┐        │
│    │ GaussVector 向量库          │  │ OpenSearch 索引库             │        │
│    │ t_oag_instance_{id}         │  │ t_oag_instance_{id}          │        │
│    │ upsertInstanceData          │  │ upsertDocuments (bulk API)    │        │
│    └─────────────────────────────┘  └──────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 接口定义

### 2.1 REST 入口

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/rest/OntologyIndexTaskRest.java`

```java
@RestController
@RequestMapping("/onto-retrieval-api/v1/onto-retrieval")
public class OntologyIndexTaskRest {
    @PostMapping("/{ontologyId}/index-data/notice")
    public NewBaseRespone<List<AsyncTaskAcceptedResponse>> noticeIndexData(
            @PathVariable(value = "ontologyId") String ontologyId,
            @Valid @RequestBody IndexFileImportRequest request)
```

- **完整路径**：`POST /onto-retrieval-api/v1/onto-retrieval/{ontologyId}/index-data/notice`
- **接口级参数校验**（`OntologyIndexTaskRest.java:71-103`）：
  1. `importMode=CLEAR` 时 `dataType` 必须为 `INSTANCE_VALUE`
  2. `FULL_REPLACE` / `INCREMENTAL` 时 `files` 不能为空
  3. 每个文件：`fileFormat` 必须为 `CSV`、`encoding` 必须为 `UTF-8`、`hasHeader` 必须为 `true`

### 2.2 请求体 `IndexFileImportRequest`

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/indextask/dto/request/IndexFileImportRequest.java`

| 字段 | 必填 | 约束 | 说明 |
|---|---|---|---|
| `requestId` | ✅ | 1-256，`^[A-Za-z0-9_-]+$` | 调用方幂等键 |
| `triggerTaskId` | ❌ | ≤256 | OAC 交付时关联手动构建任务；直接导入不传 |
| `dataType` | ✅ | 仅 `INSTANCE_VALUE` | 当前仅支持实例值 |
| `importMode` | ✅ | `FULL_REPLACE` / `INCREMENTAL` / `CLEAR` | 导入模式 |
| `files` | 视模式 | `@Valid` | MinIO CSV 对象列表 |

### 2.3 文件描述 `MinioCsvFile`

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/indextask/dto/request/MinioCsvFile.java`

| 字段 | 必填 | 约束 |
|---|---|---|
| `bucket` | ✅ | 3-63 字符 |
| `objectKey` | ✅ | ≤1024，`^[A-Za-z0-9_\-/.]+$` |
| `fileFormat` | ❌ | 默认 `CSV` |
| `encoding` | ❌ | 默认 `UTF-8` |
| `hasHeader` | ❌ | 默认 `true` |
| `rowCount` / `size` | ❌ | ≥0 |
| `sha256` | ✅ | 64 位十六进制 |

### 2.4 响应体

- `AsyncTaskAcceptedResponse`：`taskId / requestId / dataType / sourceType / status / stage`
- 多文件场景返回 `List<AsyncTaskAcceptedResponse>`（每个子任务一个）

---

## 3. 任务创建与拆分（IndexTaskService）

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/indextask/service/IndexTaskService.java`

### 3.1 `createTaskAndExecute`（IndexTaskService.java:131-193）

1. **CLEAR 模式特判**（`dataType=INSTANCE_VALUE`）：直接建清理任务 → `clearOntologyIndex`（删除 ES 索引 + drop GaussVector 表）→ 结束。
2. **刷新本体结构缓存**（`OntologyStructureCacheService.refresh`，每次 /notice 调用一次，失败不阻断，任务侧 `get` 兜底回源）。
3. **任务拆分**：`taskCount = ceil(files.size() / MAX_FILES_PER_TASK)`，其中 `MAX_FILES_PER_TASK = 20`（`IndexTaskConstants.java:65`）。
4. 每个子任务构造新的 `IndexFileImportRequest`（`requestId + "_task_{n}"`），调用 `createAndExecuteSingleTask`。

### 3.2 `createTask` 幂等与前置校验（IndexTaskService.java:372-414）

- **幂等**：同 `ontologyId + requestId` 已存在则直接返回原 `taskId`
- **bucket 白名单**：`minioProperties.isBucketAllowed(bucket)` 校验
- **bucket 存在性**：`s3Service.checkBucketExists`
- 建任务记录：`IndexTask` 状态 `BUILDING(0)`、阶段 `CREATED`，`taskId` 由 `@TableId(IdType.ASSIGN_UUID)` 自动生成

### 3.3 任务状态机

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/common/model/statusenum/OntoIndexTaskStatusEnum.java`

| code | 枚举 | 含义 |
|---|---|---|
| 0 | BUILDING | 构建中 |
| 1 | BUILD_COMPLETED | 构建成功 |
| 2 | BUILD_FAILED | 构建失败 |
| 3 | BUILD_CANCELLED | 已取消 |
| 4 | CLEAR_COMPLETED | 清理完成 |
| 5 | CLEAR_FAILED | 清理失败 |

### 3.4 任务阶段（Stage）

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/indextask/constant/IndexTaskConstants.java`

| stage | 值 | 说明 |
|---|---|---|
| CREATED | `CREATED` | 已创建 |
| VALIDATING | `VALIDATING` | 校验中 |
| EMBEDDING | `EMBEDDING` | 向量化中 |
| WRITING_VECTOR_AND_SEARCH | `WRITING_VECTOR_AND_SEARCH` | 写入向量库 |
| FINISHED | `FINISHED` | 已完成 |

---

## 4. 校验阶段（阶段1-6）

### 4.1 阶段1-5 同步校验

`oag-core/src/main/java/com/huawei/ryoma/ontoretrieval/indextask/service/IndexTaskValidationService.java:64-91`

| 阶段 | 校验器 | 逻辑 |
|---|---|---|
| 1 请求结构 | `RequestStructureValidator` | request/requestId/files 非空 |
| 2 数据类型 | `DataTypeValidator` | 仅支持 `INSTANCE_VALUE` |
| 3 MinIO 文件存在 | `MinioFileValidator.validateExists` | `s3Service.objectExists` |
| 4 MinIO 文件 TTL | `MinioFileValidator.validateNotExpired` | 超 `index-task.file-ttl-hours`(默认168h) 拒绝 |
| 5 — | — | （阶段5并入阶段6的异步内容校验） |

失败时通过 `GaussUtils.updateStatusAndError` 落库 `BUILD_FAILED/FINISHED` 并抛 `TaskValidationException`。

### 4.2 阶段6 异步文件校验（同步等待结果）

入口：`TaskExecutorService.executeValidationAsync`（TaskExecutorService.java:69-80）
执行器：`FileValidationWorker.validateTask`（FileValidationWorker.java:77-104）

对每个文件（FileValidationWorker.java:91-99）：
1. **CSV Header 校验**：`INSTANCE_VALUE` 必须含 `property_id, object_type_id, value, synonyms`
2. **SHA-256 校验**：流式单遍计算实际 checksum，与请求 `sha256` 比对（`MinioFileValidator.validateChecksum`）
3. **内容格式抽样校验**：前 `validationSampleLines` 行，字段数 ≥3
4. **语义全量行校验**：
   - `PropertyValidator.validatePropertyExists` → Property 必须存在于本体（PROPERTY_NOT_FOUND 20004）
   - `ObjectTypeValidator.validateObjectTypePropertyMatch` → object_type_id 必须包含该 property_id（OBJECT_TYPE_MISMATCH 20005）

**本体结构来源**：`OntologyStructureCacheService` 从向量表 `t_oag_{ontologyId}` 的 type=1（Property）行加载 `property_id` / `parent_id` 归属关系（OntologyStructureCacheService.java:75-103），按 ontologyId 缓存。

校验失败：落库 `BUILD_FAILED`，`validationFuture.get()` 抛异常终止流程，不再执行阶段7。

---

## 5. 阶段7 Embedding / 写索引

### 5.1 异步调度

`IndexTaskService.executeTaskFlow`（IndexTaskService.java:256-301）
- 阶段6 通过后：状态置 `BUILDING`、阶段 `EMBEDDING`
- `TaskExecutorService.executeEmbeddingAsync` → `CompletableFuture.runAsync(runnable, executorService)`（TaskExecutorService.java:89-96），**不阻塞等待结果**

线程池（`TaskExecutorService.init`，TaskExecutorService.java:50-59）：
- 核心/最大线程数 = `notice.threadPoolSize`（默认 20）
- 队列 `LinkedBlockingQueue(1024)`，线程名 `ExecuteEmbedding`
- 用 brave `CurrentTraceContext.executor` 包装，保证链路追踪上下文传递

### 5.2 `executeEmbedding` 主逻辑（IndexTaskService.java:311-347）

1. 设置租户上下文（`ThreadContext` / `TenantInfo`）
2. 获取/创建 `OntologyIndex`：
   - 若不存在，通过 `ApiFabricLLMServiceImpl.getModelConfig` 查询默认 Embedding 模型（label 含 `OntoRetrieval_Default=true`），保存为 `embeddingModel`
3. 按 `dataType` 分流：
   - `INSTANCE_VALUE` → `instanceIndexService.batchInstance(ontologyIndex, request, taskId)`
   - 其他 → `enumIndexService.batchCreateEnumIndex(...)`

异常时：落库 `BUILD_FAILED/FINISHED` + `EMBEDDING_FAILED` 错误码。

---

## 6. 向量入库核心链路（INSTANCE_VALUE）

### 6.1 `InstanceIndexServiceImpl.batchInstance`（InstanceIndexServiceImpl.java:238-269）

按 `importMode` 分流：

| 模式 | 行为 |
|---|---|
| `INCREMENTAL` | `processFilesInParallelWithStats(..., flag=false)` |
| `FULL_REPLACE` | 先删 ES 索引 + `vectorService.dropTable`，再 `processFilesInParallelWithStats(..., flag=true)`，最后 `instanceVectorBaseMapper.createIndexTable`（补建 gsdiskann 向量索引） |

结束后更新任务：`BUILD_COMPLETED(1)` / `FINISHED`，并统计 `totalCount / successCount / skippedCount(duplicates) / failedCount`。

### 6.2 文件并行处理 `processFilesInParallelWithStats`（InstanceIndexServiceImpl.java:271-300）

1. `createTableIfNotExists`：建无索引向量表 `t_oag_instance_{ontologyId}`（向量维度 1024）
2. 每文件 `CompletableFuture.supplyAsync(..., executorService)` 并行解析
3. 线程池：`parseFile.threadPoolSize`（默认 20），队列 1024，线程名 `InstanceIndex`

### 6.3 单文件处理 `processSingleFileWithStats`（InstanceIndexServiceImpl.java:310-345）

- 阶段更新：`BUILDING` / `WRITING_VECTOR_AND_SEARCH`
- 流式解析 CSV（支持多行引号字段），按 `op`（UPSERT/DELETE）分组
- 按 `batchLimit = batchInstance.maxBatchSize`（默认 4000）攒批，满批提交
- 并发控制：`Semaphore(parallelFlushSize)`（`parallelFlush.Size` 默认 8），`batchInsertExecutorService`（`batchInstance.threadPoolSize` 默认 8，队列 1024，饱和策略为阻塞 put）

### 6.4 批次处理 `submitBatch` / `batchCreateInstanceIndex`（InstanceIndexServiceImpl.java:347-367, 180-222）

- **去重**：按唯一键 `objectTypeId|propertyId|normalizedValue`（`computeUniqueKey`）去重，保留首个
- **参数校验**：ontologyId 命名规范、value/propertyId 非空
- **重试**：`executeWithRetry`（`batchInstance.retry` 默认 3 次）执行 `buildInstanceIndexFull`

### 6.5 向量化与双写 `buildInstanceIndexFull`（InstanceIndexServiceImpl.java:562-577）

```java
List<String> vectorContents = newItems.map(this::buildVectorContent)  // value + synonyms
double[][] vectors = generateVectors(vectorContents, ontologyIndex)    // Embedding 模型
List<OntologyInstanceVdbEntity> newEntities = generateVectorEntities(...)
if (!flag) instanceVectorService.upsertInstanceData(...)   // GaussVector upsert
else       instanceVectorService.insertByCsv(...)          // FULL_REPLACE 走 CSV 批量导入
insertIntoOpenSearch(newEntities, tableName, vectorContents)  // OpenSearch 双写
```

**向量生成 `generateVectors`**（InstanceIndexServiceImpl.java:676-701）：
- 经 `EmbeddingModelFactory.getModel(embeddingModel)` 取模型单例 → `ConfiguredEmbeddingModel.embedAll(contents)`（每次最多 32 段一批，`embedding-{model}-` 线程池并发）
- 异常时**降级为零向量**（1024 维），不阻断入库

---

## 7. GaussVector 向量库写入

### 7.1 `InstanceVectorServiceImpl.upsertInstanceData`（InstanceVectorServiceImpl.java:129-151）

- 动态获取表列名（`information_schema.columns`）
- 每 **1000** 条一批，`instanceVectorBaseMapper.upsertData`
- 类型处理器：`VectorMixedTypeHandler`（vector 字段 JSON 数组 → floatvector）

### 7.2 建表 SQL（InstanceVectorBaseMapper.xml）

无索引表 `createOntologyNoIndexTable`：
```sql
create table if not exists "${tableName}"
(
    vector floatvector(${vectorDim}) not null,
    value VARCHAR(4096),
    synonyms text,
    property_id VARCHAR(512) not null,
    property_name VARCHAR(512),
    object_type_id VARCHAR(256) not null,
    object_type_name VARCHAR(512),
    CONSTRAINT "uk_instance_${tableName}" PRIMARY KEY (object_type_id, property_id, value)
);
```

FULL_REPLACE 完成后补建 gsdiskann 索引（InstanceVectorBaseMapper.java:40）：
```sql
set maintenance_work_mem='4GB';
create index if not exists "index_instance_vector_${tableName}" on "${tableName}"
using gsdiskann (vector COSINE)
with (enable_pq = true, lvq_nclus = 128, subgraph_count = 1,
      quantization_type = 'lvq', num_parallels = 5,
      enable_vector_copy = false, build_with_quantized_vector = true);
```

### 7.3 Upsert SQL

```sql
INSERT INTO "schema"."table" ("col"...)
VALUES (?, ?, ...)
ON DUPLICATE KEY UPDATE
"vector" = EXCLUDED."vector", "synonyms" = EXCLUDED."synonyms",
"property_name" = EXCLUDED."property_name", "object_type_name" = EXCLUDED."object_type_name";
```

---

## 8. OpenSearch 索引双写

`ElasticSearchRestRepository.upsertDocuments`（ElasticSearchRestRepository.java:79-91）

- 构造 NDJSON bulk 请求 → `POST {esUrl}/_bulk`
- 文档 ID：`objectTypeId + propertyId + normalizedValue`（`generateInstanceDocId`）
- 若索引不存在先 `createIndex`（自动建 mapping，`ElasticSearchRestRepository.java:175-191`）
- 文档字段：`value / synonyms / propertyId / objectTypeId / propertyName / objectTypeName / content`

mapping 关键点（ElasticSearchRestRepository.java:199-243）：
- `value` / `synonyms` / `content`：`text` + `.keyword` 子字段
- `propertyId` / `objectTypeId` / `propertyName` / `objectTypeName`：`keyword`

---

## 9. Enum 类型索引（备选链路）

`EnumIndexServiceImpl.batchCreateEnumIndex`（EnumIndexServiceImpl.java:202-224）
- 表名：`t_oag_enum_{ontologyId}`（`OAG_ENUM_INDEX_PREFIX`）
- 仅支持 `INCREMENTAL` 模式（其他模式空跑）
- 并行线程池：`batchEnum.threadPoolSize`（默认 20）
- 批次：`batchEnum.maxBatchSize`（默认 1000），按唯一键 `objectTypeId|propertyId|value` 去重
- 双写：
  - `EnumVectorServiceImpl.upsertEnumData` → GaussVector `t_oag_enum_{id}`（`EnumVectorBaseMapper.xml` 建表 + upsert，含 display/description 多语言字段）
  - `createOagEnumIndexAndInsertData` → OpenSearch `t_oag_enum_{id}`（文档 ID 同 instance 规则）

---

## 10. 线程池汇总

| 线程池 | 位置 | 核心/最大 | 队列 | 线程名 | 配置项 |
|---|---|---|---|---|---|
| indexTaskExecutor | TaskExecutorConfiguration.java:44-59 | `index-task.max-concurrent-tasks`(10) | `index-task.queue-length`(200) | index-task- | Spring `ThreadPoolTaskExecutor`，AbortPolicy 拒绝 |
| ExecuteEmbedding | TaskExecutorService.java:50-59 | `notice.threadPoolSize`(20) | 1024 | ExecuteEmbedding | 阶段7 异步执行 |
| InstanceIndex | InstanceIndexServiceImpl.java:140 | `parseFile.threadPoolSize`(20) | 1024 | InstanceIndex | 文件级并行 |
| InstanceExecutor | InstanceIndexServiceImpl.java:141-152 | `batchInstance.threadPoolSize`(8) | 1024 | InstanceExecutor | 批次写库，阻塞 put |
| EnumIndex | EnumIndexServiceImpl.java:122 | `batchEnum.threadPoolSize`(20) | 1024 | EnumIndex | enum 文件并行 |
| embedding-{model}- | ConfiguredEmbeddingModel.java:74-86 | `embedding-thread-core-pool-size`(8) / `embedding-thread-max-pool-size`(32) | 1024 | embedding-{model}- | Embedding 并发，模型级单例（`EmbeddingModelFactory` 按模型缓存，超 `embedding-model-cache-size`(10) 驱逐并关闭线程池） |

> ⚠️ 注意：`TaskExecutorService` / `InstanceIndexServiceImpl` / `EnumIndexServiceImpl` 的线程池均为 `@PostConstruct` 手动 `new ThreadPoolExecutor`，`core=max` 且未开 `allowCoreThreadTimeOut`，属于常驻线程，仅随容器销毁回收；`EmbeddingModelFactory` 已在 `@PreDestroy` 统一关闭（EmbeddingModelFactory.java:94-105）。

---

## 11. 超时与失败兜底

`IndexTaskTimeoutScheduler`（IndexTaskTimeoutScheduler.java:55-110）
- `@Scheduled(fixedRate=300000, initialDelay=300000)`：每 5 分钟扫描
- 逐租户（`TenantManager.getTenantIds`）查询超过 `index-task.queue-timeout-hours`(默认6h) 仍处于 `BUILDING` 的任务
- `IndexTaskService.batchMarkTimeoutTasks` 批量置为 `BUILD_FAILED` / `FINISHED` / 错误码 `QUEUE_TIME_OUT`

---

## 12. 关键配置项速查

| 配置项 | 默认值 | 作用 |
|---|---|---|
| `index-task.max-concurrent-tasks` | 10 | 索引任务线程池并发数 |
| `index-task.queue-length` | 200 | 索引任务排队队列长度 |
| `index-task.queue-timeout-hours` | 6 | 任务排队超时 |
| `index-task.file-ttl-hours` | 168 | 源文件硬 TTL |
| `notice.threadPoolSize` | 20 | 阶段7 Embedding 调度线程池 |
| `parseFile.threadPoolSize` | 20 | CSV 文件并行解析 |
| `batchInstance.threadPoolSize` | 8 | 批次写库线程池 |
| `batchInstance.maxBatchSize` | 4000 | 单批条数 |
| `batchInstance.retry` | 3 | 批次写库重试次数 |
| `parallelFlush.Size` | 8 | 文件内并发 flush 信号量 |
| `batchEnum.threadPoolSize` / `batchEnum.maxBatchSize` | 20 / 1000 | Enum 索引并行/批次 |
| `embedding-thread-core-pool-size` / `embedding-thread-max-pool-size` | 8 / 32 | Embedding 模型线程池 |
| `embedding-model-cache-size` | 10 | Embedding 模型缓存上限 |

---

## 13. 请求示例

```json
POST /onto-retrieval-api/v1/onto-retrieval/{ontologyId}/index-data/notice
{
  "requestId": "import_20261027_001",
  "dataType": "INSTANCE_VALUE",
  "importMode": "INCREMENTAL",
  "files": [
    {
      "bucket": "oag-import",
      "objectKey": "ontologyA/instance_values.csv",
      "fileFormat": "CSV",
      "encoding": "UTF-8",
      "hasHeader": true,
      "sha256": "a1b2...64位hex"
    }
  ]
}
```

**CSV 约定表头**（INSTANCE_VALUE）：`property_id, property_name, object_type_id, object_type_name, value, synonyms, op`
- `op` ∈ `UPSERT` / `DELETE`
