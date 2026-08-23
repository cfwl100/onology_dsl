from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8')

CH3 = '# 3. 语义索引管理：构建、数据接入、任务、MinIO 与一致性'
CH4 = '# 4. 实体提取、Entity Linking 与 6 路混合召回'
assert text.count(CH3) == 1 and text.count(CH4) == 1
start = text.index(CH3)
end = text.index(CH4)
old = text[start:end]

# Detailed-design blocks are treated as the implementation information baseline.
detail_marker = '## 3.1 详细设计与实现'
assert detail_marker in old
detail = old[old.index(detail_marker):]

def between(s, a, b):
    assert a in s, f'missing start marker: {a}'
    assert b in s, f'missing end marker: {b}'
    i = s.index(a)
    j = s.index(b, i + len(a))
    return s[i:j].rstrip() + '\n'

def drop_first_heading(block):
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('#'):
            return '\n'.join(lines[i+1:]).strip() + '\n'
    return block.strip() + '\n'

def clean_inner_headings(block):
    out = []
    for line in block.splitlines():
        # Remove stale chapter-number prefixes from markdown headings while keeping hierarchy.
        m = re.match(r'^(#{4,6})\s+\d+(?:\.\d+)+\s+(.*)$', line)
        if m:
            line = f'{m.group(1)} {m.group(2)}'
        out.append(line)
    s = '\n'.join(out)
    # Remove stale table-number references; schema names remain authoritative.
    s = re.sub(r'\*\*表\s*\d+\s+', '**', s)
    s = re.sub(r'复用表\s*\d+\s*', '复用 ', s)
    return s.strip() + '\n'

responsibilities = drop_first_heading(between(detail, '### 3.1 职责边界', '### 3.2 总体索引构建架构'))
architecture = drop_first_heading(between(detail, '### 3.2 总体索引构建架构', '### 3.3 统一 REST API 规范'))
common_api = clean_inner_headings(drop_first_heading(between(detail, '#### 3.3.1 公共协议约束', '#### 3.3.2 语义子图检索接口')))
build_api = clean_inner_headings(drop_first_heading(between(detail, '#### 3.4.3 组合一：手动构建/更新索引，经 OAC 抽取', '#### 3.4.4 组合二：MinIO 文件就绪后通知 OAG')))
notice_api = clean_inner_headings(drop_first_heading(between(detail, '### 3.5 索引数据通知和抽取接口', '### 3.6 CSV 文件结构')))
csv_block = clean_inner_headings(drop_first_heading(between(detail, '### 3.6 CSV 文件结构', '### 3.7 MinIO 文件交互协议')))
minio_block = clean_inner_headings(drop_first_heading(between(detail, '### 3.7 MinIO 文件交互协议', '### 3.8 GaussDB 索引任务持久化')))
task_persist = clean_inner_headings(drop_first_heading(between(detail, '### 3.8 GaussDB 索引任务持久化', '#### 3.8.4 索引任务管理接口详细定义')))
task_api = clean_inner_headings(drop_first_heading(between(detail, '#### 3.8.4 索引任务管理接口详细定义', '#### 3.8.5 OpenAPI 3.0.3 公共 Components 定义')))
components = clean_inner_headings(drop_first_heading(between(detail, '#### 3.8.5 OpenAPI 3.0.3 公共 Components 定义', '#### 3.8.6 公共错误响应示例')))
error_examples = clean_inner_headings(drop_first_heading(between(detail, '#### 3.8.6 公共错误响应示例', '### 3.9 任务状态机与恢复')))
state_machine = clean_inner_headings(drop_first_heading(between(detail, '### 3.9 任务状态机与恢复', '### 3.10 统一 Import Pipeline')))
pipeline = clean_inner_headings(drop_first_heading(between(detail, '### 3.10 统一 Import Pipeline', '### 3.11 FULL_REPLACE 与 INCREMENTAL')))
modes = clean_inner_headings(drop_first_heading(between(detail, '### 3.11 FULL_REPLACE 与 INCREMENTAL', '### 3.12 CSV Streaming、Chunk 与 Checkpoint')))
consistency = clean_inner_headings(drop_first_heading(between(detail, '### 3.13 GaussVector / OpenSearch 双写一致性', '### 3.14 接口与文件通道选型')))
resource = clean_inner_headings(drop_first_heading(between(detail, '### 3.15 资源隔离与限流', '### 3.16 错误处理与可观测性')))
errors = clean_inner_headings(drop_first_heading(between(detail, '### 3.16 错误处理与可观测性', '### 3.17 端到端时序')))
sequence = clean_inner_headings(drop_first_heading(between(detail, '### 3.17 端到端时序', '### 3.18 本章最终约束')))

# Remove tangential pasted-image placeholder from architecture and retain the actual flow diagram.
architecture = architecture.replace('![[Pasted image 20260823094556.png]]', '').strip() + '\n'
architecture = re.sub(r'\n1、手动创建索引->OAC.*?非首次增量数据索引入库\n', '\n', architecture, flags=re.S)

# Components: keep current index-management contract only. Semantic-search belongs to chapters 4-6;
# historical REST batch schemas are intentionally not part of the formal index-management contract.
if '    SemanticSearchRequest:' in components and '    MinioCsvFile:' in components:
    a = components.index('    SemanticSearchRequest:')
    b = components.index('    MinioCsvFile:', a)
    components = components[:a] + components[b:]
components = components.replace('enum: [OMS, OAC, REST, MINIO]', 'enum: [OMS, OAC, MINIO]')
components = components.replace('enum: [OMS, OAC, REST, MINIO]', 'enum: [OMS, OAC, MINIO]')

# Current formal file-import protocol has only FULL_REPLACE / INCREMENTAL.
notice_api = notice_api.replace('`enum: [FULL_REPLACE, INCREMENTAL, CLEAR]`', '`enum: [FULL_REPLACE, INCREMENTAL]`')
notice_api = notice_api.replace('全量替换、增量导入或全量清理索引', '全量替换或增量导入')
notice_api = notice_api.replace('，当`importMode`是CLEAR时候选填，同时指定INSTANCE_VALUE', '')
components = components.replace('enum: [FULL_REPLACE, INCREMENTAL, CLEAR]', 'enum: [FULL_REPLACE, INCREMENTAL]')

# Ensure triggerTaskId is explicit in the detailed request table.
request_row = '| `requestId`  | String              | 是    | -   | `minLength: 1`，`maxLength: 256`            | 调用方幂等键；文件直接导入时用于创建任务，关联任务时用于通知幂等                               |'
if request_row in notice_api and '`triggerTaskId`' not in notice_api.split('**MinioCsvFile',1)[0]:
    notice_api = notice_api.replace(request_row, request_row + '\n| `triggerTaskId` | String | 否 | - | `maxLength: 256` | OAC 交付文件时关联手动构建产生的原任务；直接文件导入不传 |', 1)

# CSV physical columns follow chapter 2 snake_case; JSON API may continue to use camelCase DTO fields.
csv_block = csv_block.replace('propertyId,objectTypeId,value,display_zh', 'property_id,object_type_id,value,display_zh')
csv_block = csv_block.replace('propertyid,objectTypeId,value,synonyms,op', 'property_id,object_type_id,value,synonyms,op')
csv_block = csv_block.replace('| `property_id`        | `property_id`        | Property 所属 ObjectType.id', '| `object_type_id`     | `object_type_id`     | Property 所属 ObjectType.id')
csv_block = csv_block.replace('objectTypeId + propertyid + normalized(value)', 'object_type_id + property_id + normalized(value)')

# Task source model: OAC is a first-class source mode; REST is compatibility history only and is not retained here.
task_persist = task_persist.replace('`OMS` /  `MINIO`', '`OMS` / `OAC` / `MINIO`')
task_persist = task_persist.replace('OMS、OAC 小批/分页、REST 可空；同一 Task 只允许一个 Bucket', 'OMS 任务可空；动态文件任务记录实际 Bucket；同一 Task 只允许一个 Bucket')
task_persist = task_persist.replace('OMS、OAC 小批/分页、REST 可空', 'OMS 任务可空')

# Pipeline wording: all dynamic OAC data reaches OAG through MinIO now.
pipeline = pipeline.replace('无论数据来自 OMS、 还是 MinIO', '无论数据来自 OMS 资产还是 MinIO 文件')
pipeline = pipeline.replace('objectTypeId + propertyid + normalized(value)', 'object_type_id + property_id + normalized(value)')
pipeline = pipeline.replace('objectTypeId + propertyId + normalized(value)', 'object_type_id + property_id + normalized(value)')
# Move performance baseline out of the pipeline section to a dedicated performance section.
perf_baseline = ''
perf_marker = '#### 首次入库性能基线'
if perf_marker in pipeline:
    p = pipeline.index(perf_marker)
    perf_baseline = pipeline[p + len(perf_marker):].strip() + '\n'
    pipeline = pipeline[:p].rstrip() + '\n'

modes = modes.replace('objectTypeId + propertyId + normalized(value)', 'object_type_id + property_id + normalized(value)')
modes = modes.replace('objectTypeId + propertyid + normalized(value)', 'object_type_id + property_id + normalized(value)')

# Remove residual old numbering/table references in assembled content.
for name in ['responsibilities','architecture','common_api','build_api','notice_api','csv_block','minio_block','task_persist','task_api','components','error_examples','state_machine','pipeline','modes','consistency','resource','errors','sequence']:
    val = locals()[name]
    val = re.sub(r'第\s*3\.\d+(?:\.\d+)*\s*节', '本章对应小节', val)
    locals()[name] = val

chapter = f'''{CH3}

本章定义 OAG 语义索引从**触发、数据准备、文件交付、任务执行、双存储写入到校验发布**的完整生命周期。第 2 章回答“索引存什么、怎么检索”，本章回答“这些索引如何可靠地构建、更新和恢复”。

统一执行主线：

```text
触发/通知
→ 创建或关联持久化 Task
→ OMS 读取或 MinIO 文件交付
→ Schema / Ontology Mapping 校验
→ Streaming / Normalize / Dedup
→ Embedding
→ GaussVector + OpenSearch 幂等双写
→ Verify
→ Publish
→ FINISHED
```

核心原则：**动态 Enum / Instance 无论数据量大小，都统一通过 MinIO CSV + `index-data/notice` 交付；`instanceDataSourceMode` 只决定谁读取业务数据源，不决定是否使用 MinIO。**

---

## 3.1 职责边界与总体架构

### 3.1.1 角色职责

{responsibilities}

### 3.1.2 总体索引构建架构

{architecture}

### 3.1.3 统一 Import Pipeline 边界

所有来源最终进入同一 Pipeline：

```text
Input
→ SchemaValidator
→ OntologyMappingValidator
→ Normalizer
→ Deduplicator
→ EmbeddingInputBuilder
→ Embedding
→ GaussVector Bulk Writer + OpenSearch Bulk Writer
→ Verifier
→ Publisher
```

生产者（OAC / DataSync / 业务服务）只提供**业务语义数据**，不生成 `vector`，不直接访问 GaussVector/OpenSearch，也不管理 Generation 终态。OAG 对最终去重、Embedding、双写一致性、Verify 和 Publish 负责。

---

## 3.2 数据来源、接入模式与场景选择

### 3.2.1 数据读取责任模式

```yaml
indexBuild:
  instanceDataSourceMode: OAC   # OAC | BUSINESS_NOTICE
```

| 模式 | 谁访问业务数据源 | 固定数据流 | 适用场景 |
|---|---|---|---|
| `OAC` | OAC | OAG build → OAC 抽取 → MinIO → `index-data/notice(triggerTaskId)` → OAG | OAC 能访问目标业务数据源，适合人工创建/更新 |
| `BUSINESS_NOTICE` | DataSync / 业务服务 | 业务服务抽取 → MinIO → `index-data/notice` → OAG | OAC 不对接该源，或同步责任属于业务域 |

`instanceDataSourceMode` 是部署/业务架构配置，不允许根据单次任务数据量动态切换。小数据量和大数据量的数据交付协议完全一致，差异只在文件大小、Chunk 数、Worker/Batch 参数。

### 3.2.2 数据类型与来源

```text
SEED_NODE
  → OMS 本体资产

METADATA_ENUM
  → OMS 静态 Enum；或 OAC / 业务生产者交付动态 Enum CSV

INSTANCE_VALUE
  → OAC / DataSync / 业务服务交付 Instance CSV
```

统一任务抽象：

```text
dataType   = SEED_NODE | METADATA_ENUM | INSTANCE_VALUE
sourceType = OMS | OAC | MINIO
importMode = FULL_REPLACE | INCREMENTAL
```

其中 `BUSINESS_NOTICE` 是数据读取责任模式；直接文件通知创建的 Task 使用 `sourceType=MINIO`。OAC 手动构建 Task 使用 `sourceType=OAC`，OAC 后续通过 `triggerTaskId` 绑定文件时仍保持原 Task 和原 sourceType。

### 3.2.3 场景选择矩阵

| 场景 | 外部调用组合 | `instanceDataSourceMode` | `importMode` | 数据交付 |
|---|---|---|---|---|
| App 安装/OMS 事件构建本体对象 | OMS → OAG | - | `FULL_REPLACE` | OMS 本体资产 |
| 首次全量，有 OAC | build → OAC → MinIO → notice → query | `OAC` | `FULL_REPLACE` | MinIO CSV |
| 人工触发增量更新，有 OAC | build → OAC → MinIO → notice → query | `OAC` | `INCREMENTAL` | MinIO CSV |
| 定时/事件同步，由业务侧负责 | putObject → notice → query | `BUSINESS_NOTICE` | `INCREMENTAL` | MinIO CSV |
| 已有全量文件导入/重建 | putObject → notice → query | `BUSINESS_NOTICE` | `FULL_REPLACE` | MinIO CSV |

选择规则：首次创建或明确重建使用 `FULL_REPLACE`；只提交变化数据使用 `INCREMENTAL`。不要用 `INCREMENTAL` 模拟首次全量，也不要把日常增量提交为全量替换。

### 3.2.4 容量规格

| 档位 | 源侧用户规模 | 数据交付 | OAG Profile |
|---|---:|---|---|
| Software | ≤ 10,000 用户（1W） | MinIO CSV | `LIGHTWEIGHT_BULK` |
| SEC | ≤ 1,000,000 用户（100W） | MinIO CSV | `RECOVERABLE_BULK` |
| 超出 SEC | > 1,000,000 用户 | MinIO CSV | 专项容量/性能评估 |

1W/100W 表示**源侧业务用户数**，不是最终去重后的向量条数。容量验收至少同时记录：

```text
sourceUsers
sourceRows
semanticProperties
uniqueValues
finalIndexRows
```

实际 Embedding 和存储规模以 `uniqueValues / finalIndexRows` 为准。

---

## 3.3 对外接口与任务操作契约

本章只定义**索引管理接口**。语义检索 `subgraph/semantic-search` 属于第 4～6 章运行态检索链路，本章不重复定义其 Request/Response。

所有索引管理 REST API 使用统一 Namespace：

```text
/v1/onto-retrieval/{{ontologyId}}
```

### 3.3.1 公共协议

{common_api}

当前索引管理接口清单：

| 场景 | Method | URI | 说明 |
|---|---|---|---|
| 手动构建/更新 | POST | `/v1/onto-retrieval/{{ontologyId}}/index-tasks/build` | OAG 创建 Task；动态数据由 OAG 编排 OAC |
| MinIO 数据通知 | POST | `/v1/onto-retrieval/{{ontologyId}}/index-data/notice` | 注册不可变 CSV；可使用 `triggerTaskId` 绑定已有 OAC Task |
| 批量查询任务 | POST | `/v1/onto-retrieval/{{ontologyId}}/index-tasks/query` | 查询任务、进度、错误码和文件信息 |
| 批量重试任务 | POST | `/v1/onto-retrieval/{{ontologyId}}/index-tasks/retry` | 对业务选择的失败 Task 执行技术可恢复性校验并重试 |
| 批量取消任务 | POST | `/v1/onto-retrieval/{{ontologyId}}/index-tasks/cancel` | 请求取消非终态 Task |
| 查询记录级错误 | GET | `/v1/onto-retrieval/{{ontologyId}}/index-tasks/{{taskId}}/errors` | 分页读取记录级错误 |

异步写入接口统一遵循：

```text
同步参数/幂等校验
→ Task 持久化成功
→ HTTP 202 + taskId
→ 后台执行
```

`202 Accepted` 只表示任务已接受，不表示索引已经可检索。

### 3.3.2 手动构建/更新索引

{build_api}

### 3.3.3 MinIO 索引数据通知

`triggerTaskId` 语义：

- 不传：OAG 新建 `sourceType=MINIO` Task，适用于 DataSync/业务服务直接交付全量或增量文件；
- 传入：只允许 OAC/受信任生产者使用，必须与原 Task 的 tenant/ontology/dataType/importMode 一致；绑定后不创建第二个 Task；
- 同一 `triggerTaskId` 重复提交相同 `files + sha256` 返回原 Task；内容变化返回 `409 IDEMPOTENCY_CONFLICT`；
- 普通管理台不自行拼装 `triggerTaskId`。

{notice_api}

### 3.3.4 任务查询、重试与取消

{task_api}

### 3.3.5 OpenAPI 3.0.3 公共 Components

{components}

### 3.3.6 公共错误响应示例

{error_examples}

---

## 3.4 CSV 与 MinIO 文件交付协议

动态 Enum / Instance 的唯一正式交付形式是**不可变 UTF-8 CSV + MinIO/S3 对象 + SHA-256 文件身份**。接口只注册文件，不通过超大 JSON Body 传输业务记录。

### 3.4.1 CSV Schema 与编码规则

{csv_block}

### 3.4.2 MinIO Bucket、Object Key 与 S3 访问

{minio_block}

### 3.4.3 文件身份与 SHA-256 完整性

文件身份统一定义为：

```text
bucket + objectKey + size + sha256
```

`sha256` 是 MinIO 对象**原始字节流**的 SHA-256，输出 64 位十六进制字符串。校验顺序：

```text
HEAD object / size
→ stream getObject
→ 流式计算 SHA-256
→ 与 notice.sha256 比较
→ 校验通过后进入 CSV Chunk 导入
```

规则：

1. `objectKey` 在 Task 结束前不可覆盖；
2. 恢复任务时必须重新确认 `objectKey + size + sha256` 未变化；
3. MD5 只可用于生产者本地辅助诊断，不作为 OAG 权威文件身份；
4. **禁止假设 MinIO/S3 ETag 等于文件 MD5**，Multipart Upload 下该假设不成立；
5. SHA-256 同时参与任务幂等、Chunk ID 和断点恢复。

### 3.4.4 文件生命周期

源 CSV 的职责边界保持：

```text
生产者（OAC / DataSync / 业务服务）
  → 拥有业务源文件生命周期

OAG
  → 只读消费
  → 记录 FILE_LIST / ERR_FILE_LIST / FILE_RETENTION_UNTIL
  → 不主动删除生产者源文件

MinIO / 平台
  → Lifecycle 硬 TTL 兜底
```

`sourceFileMaxRetentionDays` 必须配置化；超过 `FILE_RETENTION_UNTIL` 后原 Task 不再保证可重试，需要重新上传并创建新 Task。OAG 自己生成的 staging/cache 临时文件可由 OAG 独立清理。

---

## 3.5 任务持久化与状态机

### 3.5.1 GaussDB `T_OAG_INDEX_TASK`

{task_persist}

### 3.5.2 状态机与事实来源

{state_machine}

任务状态采用“粗状态 + 细阶段”：

```text
STATUS=0  构建中
STATUS=1  成功
STATUS=2  失败
STATUS=3  已取消
```

执行阶段：

```text
CREATED
→ WAITING_SOURCE / EXTRACTING
→ VALIDATING
→ READING
→ DEDUPLICATING
→ EMBEDDING
→ WRITING_VECTOR
→ WRITING_SEARCH
→ VERIFYING
→ PUBLISHING
→ FINISHED
```

取消中的 Task 使用 `CANCEL_REQUESTED`。Task 查询以 GaussDB 为唯一事实来源，不能以内存线程、Future 或 Worker 状态作为权威结果。

### 3.5.3 Task 幂等

任务级幂等键：

```text
TENANT_ID + ONTOLOGY_ID + REQUEST_ID
```

规则：

```text
相同 requestId + 相同请求语义
→ 返回原 taskId / 原 tasks

相同 requestId + 不同 dataType/importMode/文件身份
→ 409 IDEMPOTENCY_CONFLICT
```

文件关联 Task 时进一步使用 `triggerTaskId + files[].objectKey + size + sha256` 校验通知幂等。

---

## 3.6 Import Pipeline 与导入模式

### 3.6.1 统一 Pipeline

{pipeline}

### 3.6.2 FULL_REPLACE 与 INCREMENTAL

{modes}

### 3.6.3 发布可见性

```text
FULL_REPLACE
  → 新建 Staging Generation
  → 完成 GaussVector / OpenSearch 全量写入
  → Count / Sample / Query Verify
  → 原子切换 Active Generation
  → 再退休旧 Generation

INCREMENTAL
  → 对 Active Generation 使用稳定业务键幂等 UPSERT / DELETE
  → 双端均成功并校验后推进 Task/Checkpoint
```

因此 `202 Accepted`、文件读取完成、Embedding 完成均不代表新数据已经对在线检索可见；只有 Publish/增量双端提交完成后才可见。

---

## 3.7 Streaming、Chunk、Checkpoint 与故障恢复

### 3.7.1 Streaming 与 Chunk

```text
MinIO InputStream
→ CSV Streaming Parser
→ Chunk
→ Normalize / Dedup
→ Embedding Batch
→ GaussVector Bulk
→ OpenSearch Bulk
```

百万/千万级 CSV 禁止整文件加载到 JVM Heap。Chunk 大小是性能参数，通过部署压测配置，不进入业务协议常量。

### 3.7.2 Checkpoint 数据结构

`T_OAG_INDEX_TASK.CHECKPOINT` 使用 `TEXT` 保存版本化 JSON，只表示**最后一个 GaussVector + OpenSearch 都成功的连续安全恢复点**：

```json
{{
  "version": 1,
  "fileIndex": 0,
  "objectKey": "onto-retrieval/t1/ontology/INSTANCE_VALUE/task/part-00000.csv",
  "fileSha256": "7c222fb2927d828af22f592134e8932480637c0d4d7b31a7d7e6c80b7f5506ab",
  "fileSize": 183421234,
  "committedRowEnd": 49999,
  "lastChunkId": "c4b2...",
  "updatedAt": "2026-08-23T15:00:00+08:00"
}}
```

**不新增 `T_OAG_INDEX_CHUNK`，也不逐 Chunk 持久化 `gauss_status / opensearch_status`。** 单 Chunk 过程状态进入日志和指标，Task 只持久化连续安全点。

### 3.7.3 稳定 Chunk ID

```text
chunkSource = objectKey + "\\n" + fileSha256 + "\\n" + rowStart + ":" + rowEnd
chunkId     = SHA-256(UTF-8(chunkSource))
```

Chunk ID 同时绑定不可变文件身份和确定性行范围。同一个文件使用固定 `chunkRows` 重建后必须得到相同 Chunk ID。

### 3.7.4 单端成功故障窗口

例如 Chunk 10：GaussVector 已写成功，OpenSearch 尚未成功时进程 Crash。Checkpoint 仍停在 Chunk 9；恢复后整体重放 Chunk 10：

```text
GaussVector
  → 业务唯一键 UPSERT，重复写安全

OpenSearch
  → 确定性 _id UPSERT，重复写安全

两端成功 + Verify
  → 原子推进 CHECKPOINT
```

不需要为单端成功额外维护 Chunk 状态表。

### 3.7.5 恢复流程

```text
1. 读取 FILE_LIST + CHECKPOINT
2. 根据 fileIndex 定位当前对象
3. HEAD MinIO 校验 size
4. 流式重新计算 SHA-256
5. objectKey/size/hash 变化 → FILE_CHANGED / CHECKSUM_MISMATCH，禁止续跑
6. nextRow = committedRowEnd + 1
7. 按固定 chunkRows 重建 row range + chunkId
8. 未完成 Chunk 对 GaussVector / OpenSearch 整体幂等重放
9. 两端成功并 Verify → 原子 UPDATE CHECKPOINT
10. 当前文件完成 → fileIndex++
11. 全部文件完成 → VERIFYING → PUBLISHING → FINISHED
```

恢复必须同时依赖 `FILE_LIST + fileSha256 + fileSize + committedRowEnd`；禁止只保存行号而丢失文件身份。

---

## 3.8 GaussVector / OpenSearch 双写一致性

{consistency}

补充约束：

```text
GaussVector
  → 稳定业务组合唯一键
  → INSERT ... ON DUPLICATE KEY UPDATE

OpenSearch
  → 稳定业务键生成确定性 _id
  → UPSERT / DELETE 幂等
```

Checkpoint 只能在双端成功后推进；FULL_REPLACE 只有双端 Verify 全部通过才能 Publish。系统不引入跨 GaussVector/OpenSearch 的分布式事务。

---

## 3.9 重试、取消、错误与源文件恢复

### 3.9.1 重试原则

业务侧根据：

```text
status
errorCode / errorCodes
fileList / errFileList
fileRetentionUntil
```

决定是否调用 retry。OAG 不返回服务端 `retryable=true/false` 之类布尔判断，只校验技术恢复条件：Task 状态、重试次数、Checkpoint、文件存在性和 SHA-256 完整性。

对于 MinIO Task：

```text
ERR_FILE_LIST 非空
  → 默认优先重处理失败文件

失败位于 VERIFY / PUBLISH
  → 从对应 STAGE / Checkpoint 恢复
  → 不机械重读全部 CSV

文件内容需要修正
  → 不覆盖原 objectKey
  → 新文件 + 新 requestId + 新 Task
```

### 3.9.2 错误码与可观测错误信息

{errors}

### 3.9.3 取消语义

```text
STATUS=0
  → 设置 CANCEL_REQUESTED
  → Worker 在安全点停止
  → STATUS=3

STATUS=3
  → 重复取消幂等成功

STATUS=1 / 2
  → 已进入终态，不重新进入取消流程
```

---

## 3.10 性能、资源隔离与可观测性

### 3.10.1 Bulk 参数基线

{perf_baseline}

建议初值统一收敛为：

```yaml
embeddingBatchSize: 32~128
storageBulkSize: 500~2000
chunkRows: 10000~50000
```

所有值必须配置化，并在目标部署环境压测后固化。

### 3.10.2 资源隔离与反压

{resource}

Writer 队列达到高水位时必须向上游反压 MinIO 读取和 Embedding，禁止通过无界内存队列换吞吐。在线语义检索优先级高于 Bulk Import。

### 3.10.3 关键指标

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

---

## 3.11 端到端时序与最终约束

### 3.11.1 MinIO CSV 数据同步时序

{sequence}

### 3.11.2 OAC 手动构建时序

```mermaid
sequenceDiagram
    participant C as 管理台/OMS
    participant G as OAG
    participant A as OAC
    participant M as MinIO
    participant V as GaussVector/OpenSearch

    C->>G: POST index-tasks/build
    G->>G: 持久化 OAC Task / WAITING_SOURCE
    G-->>C: 202 + taskId
    G->>A: trigger extract(taskId, scope)
    A->>A: query / source normalize / source dedup
    A->>M: put immutable CSV
    A->>G: POST index-data/notice(triggerTaskId, files)
    G->>M: stream + size/SHA-256 verify
    G->>G: normalize / dedup / embedding
    G->>V: idempotent dual write
    G->>G: verify / publish / FINISHED
    C->>G: POST index-tasks/query
    G-->>C: final task state
```

### 3.11.3 最终约束

1. 动态 Enum / Instance 统一使用 **MinIO CSV + `index-data/notice`**，不再区分小数据直返和大数据文件两套实现；
2. `instanceDataSourceMode=OAC|BUSINESS_NOTICE` 只决定谁读取业务源；
3. OAC 手动构建通过 `triggerTaskId` 将文件绑定到原 Task，不重复创建 Task；
4. `SEED_NODE` 读取 OMS，本体外部生产者不生成 vector；
5. 首次创建/重建使用 `FULL_REPLACE`，变化数据使用 `INCREMENTAL`；
6. MinIO 文件必须不可变，权威身份使用 `objectKey + size + SHA-256`，ETag/MD5 不参与恢复身份；
7. Task 必须先写入 `T_OAG_INDEX_TASK` 再异步执行，GaussDB 是任务事实来源；
8. Checkpoint 使用 TEXT JSON，只保存双端成功的连续安全点，不新增 Chunk 状态表；
9. GaussVector/OpenSearch 通过稳定业务键、幂等重放、Verify 和 Publish 实现最终一致性，不引入跨存储分布式事务；
10. 源 CSV 生命周期属于 OAC/DataSync/业务侧，MinIO Lifecycle 负责硬 TTL，OAG 只读消费；
11. 业务根据稳定错误码和失败文件范围决定 retry，禁止解析 `errorMessage` 做自动化决策；
12. 在线检索优先于 Bulk Import，导入必须配置并发、队列和 Backpressure。

---

'''

# Final cleanup for stale prose that contradicts the formal current design.
chapter = chapter.replace('OAC 小批/分页结果、MinIO CSV 以及无 OAC 部署保留的兼容 REST Batch', 'OMS 资产和 MinIO CSV')
chapter = chapter.replace('OMS、OAC 小批/分页、兼容 REST Batch 和 MinIO 文件', 'OMS 资产和 MinIO 文件')
chapter = chapter.replace('REST maxRecordsPerRequest\n', '')
chapter = chapter.replace('sourceType = OMS | OAC | REST | MINIO', 'sourceType = OMS | OAC | MINIO')
chapter = chapter.replace('SOURCE_TYPE=REST', 'SOURCE_TYPE=MINIO')
chapter = chapter.replace('propertyid', 'property_id')
chapter = chapter.replace('objectTypeId + propertyId + normalized(value)', 'object_type_id + property_id + normalized(value)')
chapter = chapter.replace('objectTypeId + property_id + normalized(value)', 'object_type_id + property_id + normalized(value)')
chapter = chapter.replace('object_type_id + propertyId + normalized(value)', 'object_type_id + property_id + normalized(value)')

# Normalize accidental repeated separators/blank headings from extracted content.
chapter = re.sub(r'\n---\n\s*---\n', '\n---\n', chapter)
chapter = re.sub(r'\n{4,}', '\n\n\n', chapter)

# Update top reading rule so chapters 2 and 3 are both single-authority structures.
new_text = text[:start] + chapter + text[end:]
old_rule = '阅读规则：第 2 章按“总体规则 → 本体对象 → 枚举元素 → 实例元素 → 统一治理”组织，其他章节保留“核心设计 + 详细设计与实现”；同一主题只保留一处权威定义，接口、DDL、算法与运行规则引用该定义。'
new_rule = '阅读规则：第 2 章按“总体规则 → 本体对象 → 枚举元素 → 实例元素 → 统一治理”组织；第 3 章按“职责/接入 → API → 文件协议 → Task → Pipeline → Checkpoint → 一致性 → 恢复/性能”组织；其他章节保留“核心设计 + 详细设计与实现”。同一主题只保留一处权威定义。'
if old_rule in new_text:
    new_text = new_text.replace(old_rule, new_rule, 1)

# Structural and semantic validation.
new_start = new_text.index(CH3)
new_end = new_text.index(CH4)
ch = new_text[new_start:new_end]
required_headings = [
    '## 3.1 职责边界与总体架构',
    '## 3.2 数据来源、接入模式与场景选择',
    '## 3.3 对外接口与任务操作契约',
    '## 3.4 CSV 与 MinIO 文件交付协议',
    '## 3.5 任务持久化与状态机',
    '## 3.6 Import Pipeline 与导入模式',
    '## 3.7 Streaming、Chunk、Checkpoint 与故障恢复',
    '## 3.8 GaussVector / OpenSearch 双写一致性',
    '## 3.9 重试、取消、错误与源文件恢复',
    '## 3.10 性能、资源隔离与可观测性',
    '## 3.11 端到端时序与最终约束',
]
for h in required_headings:
    assert ch.count(h) == 1, f'missing or duplicate heading: {h}'
for obsolete in ['## 3.0 核心设计', '## 3.1 详细设计与实现', '### 3.18 本章最终约束', '### 3.20 设计结论']:
    assert obsolete not in ch, f'obsolete structure remains: {obsolete}'

required_terms = [
    'instanceDataSourceMode: OAC', 'BUSINESS_NOTICE', 'index-tasks/build', 'index-data/notice',
    'T_OAG_INDEX_TASK', 'FILE_LIST', 'ERR_FILE_LIST', 'ERROR_CODE_LIST', 'CHECKPOINT',
    'FULL_REPLACE', 'INCREMENTAL', 'SHA-256', 'triggerTaskId', 'GsIVFFLAT',
    'GaussVector', 'OpenSearch', 'INSERT ... ON DUPLICATE KEY UPDATE', 'CANCEL_REQUESTED',
    'sourceFileMaxRetentionDays', 'RECOVERABLE_BULK', 'LIGHTWEIGHT_BULK',
]
for term in required_terms:
    assert term in ch, f'required design detail lost: {term}'

assert '/v2/onto-retrieval/{ontologyId}' not in ch, 'stale v2 index-management URI remains'
assert 'enum: [FULL_REPLACE, INCREMENTAL, CLEAR]' not in ch, 'stale CLEAR mode remains'
assert 'enum: [OMS, OAC, REST, MINIO]' not in ch, 'stale REST source type remains'
assert '## 3.0' not in ch
assert len(ch.splitlines()) > 1200, f'chapter 3 unexpectedly short: {len(ch.splitlines())}'

DOC.write_text(new_text, encoding='utf-8')
print(f'old chapter3 lines: {len(old.splitlines())}')
print(f'new chapter3 lines: {len(ch.splitlines())}')
print('chapter3 restructure validation: PASS')
