from pathlib import Path

p = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = p.read_text(encoding='utf-8')
marker = '# 7. 性能、配置、可观测性、评测与迁移'
assert marker in text, 'chapter 7 marker not found'
prefix = text.split(marker, 1)[0]
prefix = prefix.replace('> 版本：V6.4', '> 版本：V6.5', 1)
prefix = prefix.replace('> 日期：2026-09-05', '> 日期：2026-09-06', 1)
chapter = r'''# 7. 性能、配置、可观测性、评测与迁移

本章不重新定义索引模型、召回语义、精排规则或图算法，而是基于前述设计给出统一的工程治理基线：**配置如何分层、性能如何拆解、系统如何观测、方案如何评测、能力如何灰度迁移**。

横向治理对象分为两类工作负载：

```text
离线 / 异步：Index Build / Import
  → MinIO / OMS / OAC 数据接入
  → Normalize / Dedup / Embedding
  → GaussVector + OpenSearch 双写
  → Verify / Publish / Checkpoint

在线：Semantic Retrieval / Subgraph Retrieval
  → Entity Extraction / extractedEntities
  → ObjectType / Property 2 路混合召回
  → Value 4 路混合召回
  → 分类型 Weighted RRF
  → LLM Seed Fine Rank
  → SeedNodeProjector
  → PathProbePlan / Graph Execution
  → GraphSearchResponse + semanticExtensions
```

核心原则：

1. 在线检索优先于离线索引构建，Bulk Import 不得挤占在线线程池、连接池和 Embedding 配额；
2. 性能问题必须定位到具体阶段，不能只观察 OAG 总耗时；
3. 第 7 章只汇总配置入口，业务语义和字段定义仍以前述对应章节为权威来源；
4. 所有 TopK、阈值、RRF 权重、Batch、Chunk、并发和图限制均为可调参数，必须通过真实数据集和目标环境压测校准；
5. 评测必须同时覆盖“索引构建正确性、语义检索准确性、精排准确性、子图正确性、端到端查询效果、性能稳定性”。

---

## 7.1 配置治理与优先级

### 7.1.1 配置分层

在线检索配置沿用统一优先级：

```text
Request Retrieval Profile
>
Ontology / Domain Config
>
System Defaults
```

索引构建配置采用：

```text
Task / Import Profile
>
Deployment Config
>
System Defaults
```

图策略配置采用：

```text
Request Strategy / Limits
>
Ontology / Domain Graph Profile
>
System Defaults
```

配置覆盖只允许改变**运行参数**，不能改变以下协议语义：

```text
ObjectType / Property → 本体定义 2 路
Value                 → Enum + Instance 4 路
OpenSearch            → Keyword Fuzzy
GaussVector           → Dense
LLM Fine Rank Input   → original_query + search_context + extracted_entities
Property              → 必须保持 ObjectType 归属
Enum / Instance       → 不直接作为 Core Graph 路径节点
```

### 7.1.2 配置职责映射

| 配置域 | 主要职责 | 对应运行阶段 |
|---|---|---|
| `indexBuild` | 数据源模式、Chunk、Embedding Batch、Bulk Write、Checkpoint、Backpressure | 索引构建 / 导入 |
| `semanticRetrieval` | Lexical/Dense TopK、Dense threshold、模式选择 | 混合召回 |
| `rrf` | 分类型融合参数 | Entity Linking 粗排 |
| `rerank` | LLM 精排开关、重试、降级 TopN | Seed Fine Rank |
| `graph` | strategy、hop、path、node、edge、timeout 等限制 | 子图规划与执行 |
| `observability` | Metric / Trace / Slow-log 采样与标签 | 全链路 |
| `evaluation` | 评测集、门限、对照版本 | 离线评测 / 灰度验收 |

---

## 7.2 推荐配置基线

以下为统一配置形态和建议初值。数值只作为工程起点，最终值必须以实际数据规模、Embedding/存储吞吐和评测结果为准。

### 7.2.1 Index Build / Import

```yaml
oag:
  indexBuild:
    instanceDataSourceMode: OAC          # OAC | BUSINESS_NOTICE
    sourceFileMaxRetentionDays: 30

    capacity:
      softwareMaxUsers: 10000
      secMaxUsers: 1000000

    importProfile:
      software: LIGHTWEIGHT_BULK
      sec: RECOVERABLE_BULK

    import:
      maxConcurrentTasks: 2

    chunk:
      rows: 20000                       # 建议范围 10000~50000

    embedding:
      batchSize: 64                     # 建议范围 32~128

    writer:
      vectorBulkSize: 1000              # 建议范围 500~2000
      openSearchBulkSize: 1000          # 建议范围 500~2000
      backpressureEnabled: true

    checkpoint:
      store: T_OAG_INDEX_TASK.CHECKPOINT
      format: JSON
      version: 1
      persistOnlyAfterBothStoresCommitted: true
      replayIncompleteChunk: true

    fileIntegrity:
      algorithm: SHA-256
      trustMinioETagAsChecksum: false
```

容量 Profile 的含义保持不变：

| Profile | 源侧用户规模 | 重点验证 |
|---|---:|---|
| `LIGHTWEIGHT_BULK` | Software ≤ 1 万 | 日常全量/增量构建、低资源占用、可恢复 |
| `RECOVERABLE_BULK` | SEC / IOH ≤ 100 万 | Streaming、并行 Embedding、双 Writer、Backpressure、Checkpoint 恢复 |
| 专项 Profile | > 100 万 | uniqueValues、文件规模、Embedding 吞吐、存储写入能力专项评估 |

实际索引规模以 `uniqueValues / finalIndexRows` 为准，不能用源侧用户数直接替代向量和全文索引行数。

### 7.2.2 Semantic Retrieval / Entity Linking

```yaml
oag:
  semanticRetrieval:
    defaultMode: hybrid                  # vector | keyword | hybrid

    defaults:
      topK: 3
      similarityThreshold: 0.6

    ontologyObject:
      lexicalTopK: 3
      denseTopK: 3
      similarityThreshold: 0.6

    enum:
      lexicalTopK: 3
      denseTopK: 3
      similarityThreshold: 0.6

    instance:
      lexicalTopK: 3
      denseTopK: 3
      similarityThreshold: 0.6

  rrf:
    k: 60
    coarseTopKPerSemanticUnit: 20
    maxGlobalCandidates: 50

    ontologyDefinition:
      channelWeights:
        ontologyObjectLexical: 0.5
        ontologyObjectDense: 0.5

    value:
      channelWeights:
        enumLexical: 0.5
        enumDense: 0.5
        instanceLexical: 0.5
        instanceDense: 0.5
```

运行时必须保持分类型路由：

```text
OBJECT_TYPE / PROPERTY
  → ontologyObjectLexical + ontologyObjectDense
  → 2 路 Weighted RRF

VALUE
  → enumLexical + enumDense + instanceLexical + instanceDense
  → 4 路 Weighted RRF
```

OpenSearch lexical 只采用 Keyword Fuzzy；Dense 的 `similarityThreshold` 只作用于 GaussVector 通道。`lexicalTopK` 与 `denseTopK` 独立配置，避免一个统一 TopK 提前裁掉互补候选。

### 7.2.3 LLM Fine Rank

```yaml
oag:
  rerank:
    enabled: true
    promptName: ontology_semantic_rerank
    temperature: 0.0
    retryCount: 1
    fallback:
      mode: UPSTREAM_ORDER_TOPN
      topN: configurable
```

精排运行时输入固定为：

```text
original_query
search_context
extracted_entities
```

`extracted_entities` 是上一步 Entity Linking / 粗排后形成的结构化 ObjectType / Property 候选。LLM 只在已有候选中做 0 / 1 / N 裁剪；失败重试仍使用完全相同的三类输入，第二次失败后按上一步候选顺序执行配置化 TopN 降级。

### 7.2.4 Graph Planning / Execution

```yaml
oag:
  graph:
    topologyCache: true

    strategy:
      default: auto                     # minimal | khop | component | auto

    limits:
      maxObjectTerminals: configurable
      maxPairProbes: configurable
      maxPaths: configurable
      maxNodes: configurable
      maxEdges: configurable
      timeoutMs: configurable

    minimal:
      algorithm: metric_closure_mst
      fallbackAlgorithm: legacy_greedy

    khop:
      algorithm: multi_source_bfs
      fallbackAlgorithm: pairwise_all_path
      hopLimit: configurable

    component:
      algorithm: dsu_cached
      fallbackAlgorithm: bounded_bfs

    traversal:
      bridgeEdgeTypes:
        - defines_relation
      propertyEdgeType: has_property
      preserveOriginalDirection: true
```

图参数必须进入 `PathProbePlan.limits`，统一约束 `maxPaths / maxNodes / maxEdges / timeoutMs`；Property 通过 `has_property` 挂载，不作为跨 ObjectType 的桥接节点。

---

## 7.3 性能与容量设计

### 7.3.1 端到端耗时拆解

索引构建：

```text
T_index_build
≈ T_source_read
+ T_validate_normalize_dedup
+ T_embedding
+ T_vector_write
+ T_opensearch_write
+ T_verify_publish
```

在线检索：

```text
T_online
≈ T_entity_extraction
+ T_keyword_dense_recall
+ T_rrf
+ T_llm_rerank
+ T_seed_projection
+ T_graph_plan
+ T_graph_execute
+ T_result_assembly
```

所有阶段都应独立记录 P50 / P95 / P99，避免只看总 SLA 无法定位瓶颈。

### 7.3.2 在线并发容量估算

稳定状态下可用 Little's Law 做初步容量估算：

```text
In-flight Concurrency ≈ TPS × Average Latency
```

例如评估目标为 10 TPS、平均请求耗时约 6s：

```text
Concurrency ≈ 10 × 6 = 60
```

60 只是理论在途请求量，实际部署还需为尾延迟、重试、连接建立、突发流量和故障切换预留余量。重点压测：

```text
HTTP / Worker 线程池
Embedding 并发与队列
GaussVector 连接池
OpenSearch 连接池
LLM 并发、超时与重试
GraphTopologyCache 并发读
NebulaGraph / JGraphT 执行资源
```

### 7.3.3 候选规模控制

候选膨胀需要在每一层及时截断：

```text
Semantic Unit
→ lexicalTopK / denseTopK
→ Dense similarityThreshold
→ channel 内 group_id 去重
→ coarseTopKPerSemanticUnit
→ maxGlobalCandidates
→ LLM 0/1/N 裁剪
→ maxObjectTerminals
→ PathProbePlan limits
```

不同类型单元不能共用一套候选预算：

```text
ObjectType / Property：控制 2 路本体定义候选
Value：控制 4 路 Enum / Instance 候选
```

Value-only 场景候选域最大，应单独观察 Instance TopK、超时和候选上限。

### 7.3.4 在线与离线资源隔离

在线检索优先级高于 Bulk Import。至少隔离：

```text
Online Retrieval Executor
Index Task Executor
File Import Executor
Embedding Executor / Quota
GaussVector Bulk Writer
OpenSearch Bulk Writer
```

当 Writer Queue 达到高水位时：

```text
GaussVector/OpenSearch pressure
→ Bulk Writer queue high-water mark
→ 反压 Embedding
→ 反压 MinIO Streaming Reader
→ Import Task 降速 / 排队
```

禁止通过无界队列换取吞吐，也禁止 Bulk Import 占满在线检索连接池。

### 7.3.5 降级与故障边界

| 故障点 | 推荐行为 |
|---|---|
| 单个 Keyword/Dense 通道失败 | 同一 Fusion Profile 内其他可用通道继续，记录 degraded；全部通道不可用则当前 Semantic Unit unresolved |
| Instance 检索超时 | 不阻塞已经完成的 ObjectType/Property 结果；Value 单元按实际可用候选处理 |
| RRF 无候选 | 当前 Semantic Unit unresolved，不制造候选 |
| LLM Timeout / 非法 JSON / 非法候选 | 相同三输入重试 1 次；仍失败按上一步候选顺序配置化 TopN 降级 |
| Property→ObjectType Cache Miss | 使用现有 GQL 查询兜底，并记录 cache miss |
| enhanced minimal 失败 | fallback `legacy_greedy` |
| multi-source BFS 不可用 | fallback `pairwise_all_path` |
| component cache 不可用 | fallback 受限 BFS |
| Path / Node / Edge 超限 | 截断并标记 `truncated=true`，保留已完成结果 |
| FULL_REPLACE 发布失败 | 保持旧 Active Generation 在线，禁止暴露半成品 Generation |
| INCREMENTAL 单端写成功 | 不推进 Checkpoint，恢复后幂等重放当前 Chunk |

---

## 7.4 可观测性设计

### 7.4.1 Trace 上下文

建议统一贯穿：

```text
requestId / queryId
tenantId
ontologyId
ontologyGeneration
semanticUnitId
taskId
channel
fusionProfile
strategy
probeId
```

Index Build 与在线检索的 Trace 字段可以不同，但 `tenantId / ontologyId / generation` 应保持一致，便于定位“索引版本 → 在线结果”的因果关系。

### 7.4.2 Index Build / Import 指标

至少记录：

```text
oag_index_task_total{dataType,sourceType,importMode,status}
oag_index_task_duration{stage}
oag_import_source_rows
oag_import_unique_values
oag_import_final_index_rows
oag_import_file_bytes
oag_import_sha256_verify_duration
oag_import_chunk_total
oag_import_chunk_duration
oag_import_checkpoint_advance_total
oag_import_checkpoint_replay_rows
oag_import_records_total
oag_import_failed_records
oag_import_deduplicated_records
oag_embedding_qps
oag_vector_write_qps
oag_opensearch_write_qps
```

运行资源同时观察：

```text
readRows/s
embedRows/s
gaussRows/s
openSearchRows/s
endToEndRows/s
writer queue depth
retry rate
heap / direct-memory peak
```

### 7.4.3 混合召回与 RRF 指标

```text
oag_semantic_unit_total{type}
oag_recall_duration{channel}
oag_recall_candidates{channel}
oag_dense_threshold_filtered_total{channel}
oag_keyword_fuzzy_empty_total{channel}
oag_channel_error_total{channel}
oag_rrf_duration{fusionProfile}
oag_rrf_candidate_total{fusionProfile}
oag_rrf_output_total{fusionProfile}
oag_rrf_channel_contribution{fusionProfile,channel}
```

必须能区分：

```text
OntologyDefinitionFusion：2 路
ValueFusion：4 路
```

不再维护 Exact 检索相关指标。

`rrfScore / channelHits / supporting_hits / matched_field / matched_value` 可以保留在召回/粗排阶段的内部 Trace 或调试日志中，但不会作为 LLM Fine Rank Prompt 输入。

### 7.4.4 LLM Fine Rank 指标

```text
oag_rerank_requests_total{status}
oag_rerank_duration
oag_rerank_input_tokens
oag_rerank_output_tokens
oag_rerank_selected_objecttype_total
oag_rerank_selected_property_total
oag_rerank_unresolved_total{reasonCode}
oag_rerank_retry_total
oag_rerank_fallback_total
```

精排 Trace 重点回答：

```text
输入候选数
→ 选择后候选数
→ unresolved 数量
→ Validator 拒绝数量
→ 是否发生 retry / fallback
```

### 7.4.5 Graph / Result 指标

```text
oag_graph_projection_duration
oag_graph_projection_error_total
oag_graph_cache_hit_ratio
oag_graph_plan_duration{strategy}
oag_graph_probe_duration{probeType}
oag_graph_probe_total{probeType,status}
oag_graph_terminal_total
oag_subgraph_nodes
oag_subgraph_edges
oag_graph_truncated_total{reason}
oag_graph_fallback_total{strategy,fallback}
oag_semantic_value_mapping_total
oag_semantic_value_mapping_unresolved_total
```

Graph 可观测性至少能够回答：

```text
最终选择了哪些 Seed？
这些 Seed 是否连通？
使用了哪个 strategy / fallback？
生成了多少 Probe？
子图是否发生节点、边、路径截断？
Value 最终映射到了哪个 Property / ObjectType？
```

### 7.4.6 日志与慢请求

建议慢请求日志按阶段输出：

```text
queryId
ontologyId
entityExtractionMs
recallMs
rrfMs
rerankMs
graphPlanMs
graphExecuteMs
resultAssemblyMs
totalMs
semanticUnitCount
selectedSeedCount
subgraphNodes
subgraphEdges
degradedStages[]
```

业务 Value、实例值和原始 Query 如涉及敏感信息，应按平台日志规范脱敏，Metric label 禁止直接携带高基数字符串值。

---

## 7.5 评测体系

评测采用“阶段指标 + 端到端指标”两层结构。阶段指标用于定位问题，端到端指标用于判断方案是否真正改善业务结果。

### 7.5.1 Entity Extraction / 结构化输入

```text
ObjectType Extraction Precision / Recall / F1
Property Extraction Precision / Recall / F1
Value Extraction Precision / Recall / F1
Value-only Detection Accuracy
Property Hint Accuracy
SearchContext Target Usage Accuracy
```

重点验证 `Values` 不误收连续数值、时间、比较、聚合等非业务值，同时验证 opaque business value 的 value-only 能力。

### 7.5.2 Entity Linking 与混合召回

按本体定义和值两个 Fusion Profile 分开统计：

```text
ObjectType Recall@1/3/10
Property Recall@1/3/10
OntologyDefinition MRR / NDCG

Enum Value Recall@1/3/10
Instance Value Recall@1/3/10
Value → Property Accuracy
Value → ObjectType Accuracy
ValueFusion MRR / NDCG
```

同义词命中作为字段级能力评测，不作为独立 Target Type：

```text
Synonym Hit Accuracy
Synonym Matched Value Accuracy
Display / Description Hit Accuracy
Keyword Fuzzy Typo Recall
```

### 7.5.3 LLM Fine Rank

以 `original_query + search_context + extracted_entities` 为唯一运行时输入评测：

```text
Selected ObjectType Precision / Recall
Selected Property Precision / Recall
Seed Set Exact Match
Minimal Sufficient Seed Accuracy
0/1/N Decision Accuracy
Unresolved Accuracy
Wrong Candidate Drop Rate
Property Ownership Violation Rate
Validator Reject Rate
P50 / P95 / P99 Latency
Input / Output Tokens
Fallback Rate
```

`Property Ownership Violation Rate` 的目标应为 0；LLM 产生输入集合之外 ID 的结果应被 Validator 识别并计入失败样本。

### 7.5.4 子图与关系评测

```text
Terminal Coverage
Relationship Precision / Recall
Required Property Coverage
Path Correctness
Minimal Subgraph Node Count
Minimal Subgraph Edge Count
Extra Node / Edge Ratio
Disconnected Seed Rate
K-hop Expansion Size
Component Accuracy
Graph Build P50 / P95 / P99
Path Explosion Rate
Fallback Rate
```

`minimal`、`khop`、`component` 必须分别统计，禁止用一个总平均掩盖某个策略的路径爆炸或连通率问题。

### 7.5.5 ValueMapping 与端到端查询评测

```text
sourceValue → canonicalValue Accuracy
Value → Property/ObjectType Mapping Accuracy
defaultDataValue Accuracy
semanticExtensions Completeness
Cypher / nGQL / OQL Seed Accuracy
Relation Accuracy
Value Filter Accuracy
Executable Rate
End-to-End Query Accuracy
```

OAG 自身只提供确定性的值、本体归属和子图；查询语句准确率属于跨 OAG + Agent/LLM 的端到端验收指标，应与 OAG 阶段指标同时保留，便于区分是语义检索错误还是查询生成错误。

### 7.5.6 Index Build / Import 可靠性评测

容量基线：

```text
Software 1W FULL_REPLACE
Software 1W INCREMENTAL
Software INSTANCE_VALUE CLEAR
SEC 100W FULL_REPLACE
SEC 100W INCREMENTAL
SEC INSTANCE_VALUE CLEAR
```

每组记录：

```text
sourceUsers
sourceRows
semanticProperties
uniqueValues
finalIndexRows
fileBytes
buildDuration
peakMemory
embeddingQPS
vectorWriteQPS
openSearchWriteQPS
```

同一数据集的 `OAC` 与 `BUSINESS_NOTICE` 模式最终应满足：

```text
GaussVector 业务键集合一致
OpenSearch _id 集合一致
Embedding 输入一致
在线检索结果一致
```

### 7.5.7 文件完整性与 Checkpoint 故障注入

文件完整性覆盖：

```text
正确 SHA-256
错误 SHA-256
objectKey 被覆盖
file size 变化
Multipart ETag 与摘要不一致
源文件过期
```

故障注入至少覆盖：

```text
CSV 已读、Embedding 前
Embedding 后、GaussVector 前
GaussVector 成功、OpenSearch 前
双端成功、Checkpoint 前
Checkpoint 成功后
Verify
Publish
```

验收条件：

```text
无业务重复
无漏数据
Checkpoint 只单调推进到双端成功安全点
未完成 Chunk 可整体幂等重放
FULL_REPLACE 发布前不影响旧 Active Generation
INCREMENTAL 单端失败后可恢复一致
CLEAR 失败时不提前破坏旧 Active Generation
```

---

## 7.6 子图算法专项对比

同一批 Query 使用固定 Seed 和固定 ontology generation 做 A/B：

| Strategy | Baseline | Candidate |
|---|---|---|
| `minimal` | `legacy_greedy` | `metric_closure_mst` |
| `khop` | `pairwise_all_path` | `multi_source_bfs` |
| `component` | bounded BFS | `dsu_cached` |

统一比较：

```text
Terminal Coverage
Relationship Precision
Node / Edge Count
Extra Node / Edge Ratio
NebulaGraph Query Count
Probe Count
Path Count
P95 Latency
CPU / Memory
Result Stability
Fallback Rate
End-to-End Query Accuracy
```

只有在准确性不回退且资源收益明确时，enhanced 算法才切换为默认。

---

## 7.7 灰度迁移与回滚

迁移遵循“先可观测、再影子、后灰度、最后切默认”。

### 7.7.1 Phase 0：建立基线

冻结一套代表性 Query / Ontology / Value 测试集，记录：

```text
旧 Seed Recall
旧子图大小 / 连通率
旧查询生成准确率
在线 P50 / P95 / P99
索引构建吞吐与资源占用
```

### 7.7.2 Phase 1：索引与导入协议收敛

```text
本体对象索引
Enum Value 索引
Instance Value 索引
+
MinIO CSV / OMS / OAC
+
Task / Checkpoint / Verify / Publish
```

新旧索引可在灰度期双写，先验证业务键集合、Count、Sample、Query 一致性，不立即切在线流量。

### 7.7.3 Phase 2：分类型 Hybrid + RRF

影子执行：

```text
legacy retrieval
vs
OBJECT_TYPE / PROPERTY 2 路
VALUE 4 路
```

重点比较 Recall@K、MRR/NDCG、Value Mapping Accuracy、P95、错误率。OpenSearch 统一以 Keyword Fuzzy 作为 lexical 方案，不再灰度 Exact Ranked List。

### 7.7.4 Phase 3：LLM Fine Rank

按流量比例启用三输入精排：

```text
original_query
+ search_context
+ extracted_entities
```

观测 Seed Precision/Recall、0/1/N、unresolved、Validator Reject、Latency、Token、Fallback。异常时可关闭 `rerank.enabled` 或直接使用上一步候选顺序 TopN 降级，不影响索引和图层。

### 7.7.5 Phase 4：Seed 投影与图策略增强

按策略独立灰度：

```text
SeedNodeProjector / GraphTopologyCache
minimal enhanced
khop enhanced
component enhanced
PathProbePlan limits
```

每个策略单独保留 fallback，禁止一次性同时替换全部算法后再定位问题。

### 7.7.6 Phase 5：semanticExtensions 接入下游

灰度 `semanticExtensions.valueMappings`，对比：

```text
Value → Property/ObjectType Accuracy
下游过滤字段准确率
canonicalValue / defaultDataValue 使用正确率
Query Executable Rate
End-to-End Query Accuracy
```

### 7.7.7 Phase 6：切换默认与清理兼容层

满足以下条件后再切默认：

```text
Recall / Mapping Accuracy 不回退
LLM Seed Precision 可接受
Relationship / Subgraph Accuracy 可接受
P95 / P99 在目标范围
错误率与 fallback rate 可接受
索引构建可恢复性验证通过
至少一个完整 ontology generation 灰度稳定
```

回滚粒度必须支持独立关闭：

```text
new index read path
hybrid retrieval
rerank
enhanced graph strategy
semanticExtensions consumer
```

避免一个总开关导致无法快速定位或局部回退。

---

## 7.8 配置变更、评测与发布闭环

所有核心参数变更建议遵循：

```text
配置变更
→ 离线评测
→ 压测
→ Shadow
→ 小流量 Canary
→ 指标对比
→ 扩大灰度
→ 切默认
```

需要纳入评测/灰度的关键参数包括：

```text
lexicalTopK / denseTopK
similarityThreshold
RRF k / channelWeights
coarseTopKPerSemanticUnit / maxGlobalCandidates
rerank retry / fallbackTopN
chunkRows / embeddingBatchSize / bulkSize / maxConcurrentTasks
maxObjectTerminals / hopLimit / maxPaths / maxNodes / maxEdges / timeoutMs
```

每次配置发布至少记录：

```text
configVersion
ontologyId / generation
benchmarkDatasetVersion
before / after metrics
releaseTime
rollbackVersion
```

不建议把运维版本、Hash 等字段写入每一条向量记录；版本信息应放在 Import Task、Generation 和配置发布元数据中。

---

## 7.9 第 7 章最终约束

1. 第 7 章只负责性能、配置、可观测性、评测与迁移，不重新定义前述业务协议；
2. 在线检索优先级高于 Bulk Import，必须通过线程池、连接池、队列和 Backpressure 隔离资源；
3. ObjectType/Property 固定走本体定义 2 路，Value 固定走 Enum/Instance 4 路；
4. OpenSearch lexical 统一使用 Keyword Fuzzy，不维护 Exact Ranked List；
5. RRF 按 Semantic Unit 类型分别执行 OntologyDefinitionFusion 和 ValueFusion，不做跨类型一次 6 路融合；
6. LLM Fine Rank 的运行时输入固定为 `original_query + search_context + extracted_entities`；
7. 召回阶段内部证据可以进入 Trace/调试日志，但不作为 LLM 精排输入；
8. LLM 精排失败按“相同三输入重试 1 次 → 上一步候选顺序配置化 TopN”降级；
9. `PathProbePlan.limits` 是所有图策略统一的运行时保护边界；
10. FULL_REPLACE / INCREMENTAL / CLEAR 都必须遵守任务状态、双端一致性和恢复语义；
11. 评测必须同时覆盖阶段准确率、端到端准确率、性能、资源、故障恢复和结果稳定性；
12. 所有核心参数必须通过“离线评测 → 压测 → Shadow → Canary → 默认切换”闭环发布。

### 一句话总结

> **第 7 章把前述索引构建、2 路/4 路混合召回、三输入 LLM 精排、Seed 投影和 PathProbePlan 串成一套可配置、可压测、可观测、可评测、可灰度回滚的工程闭环：离线构建强调 Streaming/Checkpoint/双写可恢复，在线检索强调分阶段延迟与候选规模控制，最终以语义准确率、Value Mapping、子图正确性、端到端查询准确率和稳定性共同决定是否切换默认。**

---
'''

p.write_text(prefix + chapter, encoding='utf-8')
