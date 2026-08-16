## 3.9 任务状态机与恢复

任务创建流程：

```text
API 收到请求
  ↓
校验 ontologyId / requestId / dataType
  ↓
INSERT T_OAG_INDEX_TASK
STATUS=0, STAGE=CREATED
  ↓
提交后台执行队列
  ↓
HTTP 202
```

如果任务记录写 GaussDB 失败，不返回“已接受”，也不开始索引执行。后台持续更新 `STAGE / TOTAL_COUNT / SUCCESS_COUNT / FAILED_COUNT / SKIPPED_COUNT / CHECKPOINT / UPDATE_TIME`。

终态：

```text
SUCCESS   → STATUS=1, STAGE=FINISHED, COMPLETION_TIME
FAILED    → STATUS=2, ERROR_CODE/ERROR_MESSAGE, COMPLETION_TIME
CANCELLED → STATUS=3, COMPLETION_TIME
```

OAG 重启后从 GaussDB 找到未完成任务，根据 `SOURCE_TYPE + CHECKPOINT` 决定恢复、重试或标记失败。任务查询接口必须以 GaussDB 为事实来源，而不是以内存 Future/线程状态作为权威状态。

---

## 3.10 统一 Import Pipeline

无论数据来自 REST 还是 MinIO，统一执行：

```text
Input → SchemaValidator → OntologyMappingValidator → Normalizer → Deduplicator
      → EmbeddingInputBuilder → Embedding
      → GaussVector Bulk Writer + OpenSearch Bulk Writer
      → Verifier → Publisher
```

### METADATA_ENUM

唯一业务范围：`objectTypeId + propertyid + normalized(value)`。Embedding 严格复用第 2.9 节：`value + name + display_* + description_* + synonyms_value + synonyms_description`。

### INSTANCE_VALUE

唯一业务范围：`objectTypeId + propertyid + normalized(value)`。Embedding 严格复用第 2.12 节：`{value}`。

> **所有导入路径都必须保证同一个业务唯一键最终在 GaussVector 和 OpenSearch 中各只有一条有效记录。**

---

## 3.11 FULL_REPLACE 与 INCREMENTAL

### FULL_REPLACE

适用于 Ontology 全量安装/升级、某个 Property 实例值全量重建、大规模动态枚举域重建：

```text
Create Task → Build Staging Generation → Import/Embed/Write → Verify → Atomic Publish → Cleanup Old Generation
```

发布前在线检索始终读取旧 Generation。

### INCREMENTAL

适用于动态 Enum Value UPSERT/DELETE、实例值新增/删除和小规模业务数据变化。METADATA_ENUM 与 INSTANCE_VALUE 都使用 `objectTypeId + propertyid + normalized(value)` 作为幂等业务键；相同请求或 Chunk 重试只能覆盖原记录，不能追加重复记录。

---

## 3.12 CSV Streaming、Chunk 与 Checkpoint

百万/千万级 CSV 必须流式处理：

```text
MinIO InputStream → CSV Streaming Parser → Chunk → Normalize/Dedup → Embedding Batch → Storage Bulk Batch
```

Chunk 大小属于性能参数，通过压测配置，不写入协议常量。Checkpoint 至少包含 objectKey、已处理行号或可恢复 offset、最近 committed chunk。任务表 `CHECKPOINT` 保存恢复位置摘要。

稳定 Chunk ID 可由 `objectKey + file sha256 + row-range` 计算。只有 Chunk 完成 GaussVector/OpenSearch 写入并通过幂等校验后，才能推进 Checkpoint。

---

## 3.13 GaussVector / OpenSearch 双写一致性

不引入跨 GaussVector 和 OpenSearch 的分布式事务，采用：

> **业务唯一键 + Chunk 幂等 + 任务持久化 + 发布前 Verify + 最终一致性。**

FULL_REPLACE 使用 Staging Generation，两边全部写入并完成 Count/Sample/Query Verify 后再切换 Active Generation；任一侧失败都不发布新 Generation。

INCREMENTAL 对同一业务唯一键在 GaussVector/OpenSearch 执行 UPSERT/DELETE；失败记录进入 task error，由任务重试补齐，不能因为一侧成功就把任务标记成功。

---

## 3.14 接口与文件通道选型

| 数据规模/场景 | 首选入口 | 原因 |
|---|---|---|
| 单条/几十条动态枚举 | REST Batch | 延迟低、无需文件 |
| 数百/数千动态枚举 | REST Batch 或 MinIO CSV | 按频率和批量选择 |
| 少量实例增量 | REST Batch | 调用简单 |
| 大规模实例全量 | MinIO CSV | 避免大 JSON、支持流式/断点 |
| 百万/千万实例值 | MinIO CSV | 文件不可变、易重试、适合批处理 |
| 定期 DataSync 同步 | MinIO CSV | DataSync/OAG 解耦 |

> **REST 解决动态性，MinIO CSV 解决规模；两者不能演化成两套索引实现。**

---

## 3.15 资源隔离与限流

在线检索优先级高于 Bulk Import。建议独立 REST Import Executor、File Import Executor、Embedding Executor、GaussVector Bulk Writer、OpenSearch Bulk Writer，并至少配置：

```text
REST maxRecordsPerRequest
import maxConcurrentTasks
CSV read buffer
embedding batchSize / QPS
vector bulkSize
opensearch bulkSize
task progress flush interval
```

后端压力过高时 Import Task 排队/降速，不能挤占语义检索线程池。
