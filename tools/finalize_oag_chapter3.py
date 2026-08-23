from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8')
CH3 = '# 3. 语义索引管理：构建、数据接入、任务、MinIO 与一致性'
CH4 = '# 4. 实体提取、Entity Linking 与 6 路混合召回'
start = text.index(CH3)
end = text.index(CH4)
ch = text[start:end]

# 1) Remove the two stale summary lines now fully represented by 3.2 scenario matrix.
ch = re.sub(r'\n1、手动创建索引->OAC\s*:.*?\n2、通知OAG->OAG读取minio文件：.*?\n', '\n', ch, count=1)

# 2) Current task source types are OMS/OAC/MINIO; REST batch is no longer a formal path.
ch = ch.replace('`OMS / REST / MINIO`', '`OMS / OAC / MINIO`')
ch = ch.replace('"sourceType": "REST"', '"sourceType": "OMS"')
ch = ch.replace('；REST/OMS 可空', '；OMS 可空')

# Remove dangling legacy REST-batch examples from OpenAPI components.
ch = re.sub(
    r'\n  examples:\n    MetadataEnumBatchImportExample:.*?(?=\n  responses:)',
    '\n', ch, count=1, flags=re.S
)
ch = re.sub(
    r'\n    PayloadTooLarge:\n.*?(?=\n    TooManyRequests:)',
    '\n', ch, count=1, flags=re.S
)

# 3) Consolidate dual-write consistency into one authoritative definition.
sec38 = '''## 3.8 GaussVector / OpenSearch 双写一致性

OAG 不引入跨 GaussVector 和 OpenSearch 的分布式事务，统一采用：

> **稳定业务键 + 幂等双写 + Checkpoint 安全点 + 发布前 Verify + 最终一致性。**

### 3.8.1 稳定业务键与幂等写入

```text
本体对象
  key = id

Enum Value / Instance Value
  key = object_type_id + property_id + normalized(value)
```

两端写入规则：

```text
GaussVector
  → 组合唯一键
  → INSERT ... ON DUPLICATE KEY UPDATE

OpenSearch
  → 稳定业务键生成确定性 _id
  → UPSERT / DELETE 幂等
```

同一 Chunk 因 Crash、超时或单端成功而重放时，不允许产生重复业务记录。

### 3.8.2 双端提交与发布边界

```text
Chunk
  → GaussVector 成功
  → OpenSearch 成功
  → Verify 通过
  → 才允许推进 CHECKPOINT
```

`FULL_REPLACE` 使用 Staging Generation：两端全量写入并完成 Count / Sample / Query Verify 后，才原子切换 Active Generation；任一侧失败都保留旧 Generation 在线服务。

`INCREMENTAL` 直接对 Active Generation 执行同业务键 UPSERT / DELETE；只有两端写入都成功并通过校验后，该 Chunk 才视为提交完成。任一侧失败都不能把 Task 标记成功，由恢复/重试流程补齐。

---

'''
ch = re.sub(r'## 3\.8 GaussVector / OpenSearch 双写一致性\n.*?(?=## 3\.9 重试、取消、错误与源文件恢复)', sec38, ch, count=1, flags=re.S)

# 4) Consolidate performance/resource/metrics; keep each rule once.
sec310 = '''## 3.10 性能、资源隔离与可观测性

### 3.10.1 容量 Profile 与 Bulk 参数

首次全量按源侧业务规模分档，协议保持一致，只调整 Worker、Batch、Queue 和恢复能力：

| 档位 | 源侧用户规模 | OAG Profile | 运行特征 |
|---|---:|---|---|
| Software | ≤ 10,000 用户（1W） | `LIGHTWEIGHT_BULK` | Streaming / Chunk / Checkpoint 开启，较少 Worker、较小队列 |
| SEC / IOH | ≤ 1,000,000 用户（100W） | `RECOVERABLE_BULK` | Streaming、Embedding Worker 池、双 Writer、Backpressure、Checkpoint 恢复 |
| 超出 SEC | > 1,000,000 用户 | 专项 Profile | 结合 uniqueValues、文件规模和 Embedding 吞吐专项评估 |

建议初始参数范围：

```yaml
embeddingBatchSize: 32~128
storageBulkSize: 500~2000
chunkRows: 10000~50000
```

以上均为部署配置初值，必须通过目标环境压测校准。1W/100W 是**源侧用户数**，实际向量与全文索引规模以 `uniqueValues / finalIndexRows` 为准；不在协议中写死分钟级 SLA。

### 3.10.2 资源隔离与 Backpressure

在线语义检索优先级高于 Bulk Import。建议至少隔离：

```text
Index Task Executor
File Import Executor
Embedding Executor
GaussVector Bulk Writer
OpenSearch Bulk Writer
```

关键配置：

```text
import maxConcurrentTasks
CSV read buffer
embedding batchSize / QPS
vector bulkSize
opensearch bulkSize
task progress flush interval
writer queue high-water mark
```

后端压力过高时 Import Task 应排队或降速；Writer Queue 达到高水位后必须向上游反压 Embedding 和 MinIO Streaming Reader，禁止使用无界内存队列换取吞吐，也不能挤占在线检索线程池。

### 3.10.3 性能与任务指标

至少记录：

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

readRows/s
embedRows/s
gaussRows/s
openSearchRows/s
endToEndRows/s
P95 chunk latency
retry rate
heap/direct-memory peak
```

容量验收：Software 档验证日常构建体验，SEC 档验证百万级可恢复 Bulk、反压和故障恢复能力。

---

'''
ch = re.sub(r'## 3\.10 性能、资源隔离与可观测性\n.*?(?=## 3\.11 端到端时序与最终约束)', sec310, ch, count=1, flags=re.S)

# 5) Remove redundant nested title under the already explicit 3.11.1 heading.
ch = ch.replace('### 3.11.1 MinIO CSV 数据同步时序\n\n#### MinIO CSV 索引数据同步\n', '### 3.11.1 MinIO CSV 数据同步时序\n')

# Structural consistency checks.
assert '1、手动创建索引->OAC' not in ch
assert '2、通知OAG->OAG读取minio文件' not in ch
assert '`OMS / REST / MINIO`' not in ch
assert '"sourceType": "REST"' not in ch
assert 'REST Batch' not in ch
assert 'PayloadTooLarge:' not in ch
assert ch.count('## 3.8 GaussVector / OpenSearch 双写一致性') == 1
assert ch.count('## 3.10 性能、资源隔离与可观测性') == 1
assert ch.count('embeddingBatchSize: 32~128') == 1
assert ch.count('Writer Queue 达到高水位') == 1
assert 'T_OAG_INDEX_TASK.CHECKPOINT' in ch
assert 'chunkSource = objectKey' in ch
assert 'sourceType = OMS | OAC | MINIO' in ch
assert 'importMode = FULL_REPLACE | INCREMENTAL' in ch

new_text = text[:start] + ch + text[end:]
DOC.write_text(new_text, encoding='utf-8')
print('chapter 3 final cleanup: PASS')
