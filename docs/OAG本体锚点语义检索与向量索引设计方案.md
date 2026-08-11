# OAG 面向本体锚点的语义检索、混合排序与本体子图构建设计方案

> 版本：V5.3  
> 目标：在保留既有 OAG 索引设计、Anchor/Evidence 模型、DataSync 分工、混合召回、RRF、LLM 精排、三类子图策略和 Bulk Import 设计的基础上，统一“最终检索目标”语义：ObjectType、Property、同义词、枚举值、实例列值均可作为最终检索结果，同时携带其 ObjectType / Property 上下文，为子图构建和下游 Cypher 生成提供完整、准确、可解释的语义依据。  
> 设计原则：**Semantic Match First，Anchor Context Always，Evidence Preserved，RRF Anchor-Group Fusion，Core Graph 与 Semantic Extension 分离，兼容现状、渐进增强。**

---

# 1. 文档目标与设计边界

OAG 的向量检索、OpenSearch 全文检索、同义词检索、枚举值检索、实例列值检索，以及后续的 RRF、LLM 精排和图算法，需要区分两个概念：

```text
最终检索结果（Retrieval Result）
        ≠
子图构建锚点（Graph Anchor）
```

OAG 的最终检索目标包括两类。

## 1.1 本体结构目标

```text
ObjectType
Property
```

它们本身既是最终检索结果，也是子图构建所使用的 Anchor。

## 1.2 语义值目标

以下对象**本身也是最终检索结果**，不能在命中后只保留 Anchor 而丢弃实际命中项：

```text
ObjectType Alias / 同义词
Property Alias / 同义词
Enum Value
Enum Alias / 枚举值同义词
Instance Value / 实例列值
Instance Alias / 实例值同义词
```

因此，本方案只明确排除以下内容作为最终业务检索结果：

```text
底层 Vector Document 的物理文档身份
OpenSearch 内部 Document 身份
RRF 分数本身
ANN/BM25 原始 score 本身
```

这些只是检索实现细节或排序证据。

最终检索结果统一定义为：

> **Matched Semantic Item + ObjectType / Property Anchor Context。**

也就是说，当检索命中 Alias、Enum、Instance Value 时，结果中必须同时保留：

```text
命中的语义项本身
item_id / evidence_ID
item_type / evidence_type
matched_value
canonical_value
aliases（如有）

+

所属 ObjectType
所属 Property（对象级 Alias 场景可为空）
anchor_ID
parent_ID
```

### ObjectType / Object Alias

```text
matched item
   ↓
ObjectType Context
```

### Property / Property Alias

```text
matched item
   ↓
Property Context
   ↓
Parent ObjectType Context
```

### Enum / Instance Value / Alias

```text
matched value / alias
   ↓
canonical_value
   ↓
Property Context
   ↓
ObjectType Context
```

例如用户查询：

```text
正式用户
```

最终结果可以是：

```text
target_type     = ENUM_ALIAS
matched_value   = FORMAL
canonical_value = 1
Property        = Subscriber.subClass
ObjectType      = Subscriber
```

这里 `FORMAL` 本身就是最终检索目标；`Subscriber.subClass` 和 `Subscriber` 是该结果必须携带的本体上下文，同时也是后续子图构建的 Anchor 来源。

因此完整目标是：

> **准确返回用户真正命中的本体元素或语义值本身，同时携带确定性的 ObjectType / Property 映射；随后仅将 ObjectType / Property 投影为 Graph Anchor 构建本体子图。**

---

# 2. 完整端到端架构

```mermaid
flowchart TD
    Q[用户原始问题] --> QU[Query Understanding<br/>Semantic Phrase Extraction]
    QU --> U[Semantic Units]

    subgraph RET[阶段1：多路召回]
      U --> AE[Anchor Exact/BM25]
      U --> AV[Anchor Dense]
      U --> ME[Metadata Evidence Exact/BM25]
      U --> MV[Metadata Evidence Dense]
      U --> IE[Instance Evidence Exact/BM25]
      U --> IV[Instance Evidence Dense]
    end

    AE --> N[SemanticCandidateNormalizer<br/>Matched Item + Anchor Context]
    AV --> N
    ME --> N
    MV --> N
    IE --> N
    IV --> N

    N --> RRF[Aggregator<br/>Weighted RRF by anchor_ID]
    RRF --> COARSE[Anchor Group 粗排<br/>保留 Matched Items]

    Q --> RC[RerankContextBuilder]
    U --> RC
    COARSE --> RC
    RC --> LLM[LLM Fine Ranker<br/>预置提示词]
    LLM --> MATCH[Final Semantic Matches<br/>Anchor / Alias / Enum / Instance]

    MATCH --> AP[GraphAnchorProjector<br/>提取 ObjectType / Property]
    AP --> AN[Anchor Normalization<br/>Property补Parent ObjectType]
    AN --> SG[SubgraphBuilder]

    SG --> MIN[minimal]
    SG --> KH[khop]
    SG --> CMP[component]

    MIN --> CORE[Ontology Core Subgraph]
    KH --> CORE
    CMP --> CORE

    MATCH --> EXT[ExtensionAssembler]
    CORE --> EXT
    EXT --> OUT[Retrieval Results<br/>+ Ontology Subgraph<br/>+ Semantic Extensions]
    OUT --> CYPHER[下游 LLM / Cypher Generation]
```

运行阶段划分：

```text
阶段0：索引构建 / Bulk Import
阶段1：Semantic Unit 多路召回
阶段2：Matched Item 保留 + Anchor Context 归一化 + RRF 粗排
阶段3：LLM 精排，得到 Final Semantic Matches
阶段4：Final Semantic Matches → ObjectType / Property Graph Anchors
阶段5：Anchor Normalization
阶段6：本体子图构建
阶段7：Semantic Extension 上下文扩展
阶段8：下游 Cypher 生成
```

关键边界：

```text
RRF / LLM 的业务输出：语义项本身 + Anchor Context
Graph Algorithm 的输入：ObjectType / Property Anchor
```

Enum、Alias、Instance Value 可以是最终检索结果，但不直接作为 Core Graph 的路径节点。

---

# 3. 与当前 OAG 代码的兼容基线

当前代码已经形成以下主链路：

```text
graphSearchV3()
  └─ performGraphSearchOptimized()
       ├─ interpretQueryIntent()
       ├─ getSeedIds()
       │    ├─ vectorService.searchOntologyByQuery()
       │    ├─ elasticSearchRestRepository.searchOntologyByQuery()
       │    └─ hybridRecallHelper.hybridRecall()
       ├─ loadAllEdges()
       └─ subgraphQuery()
            ├─ getPathInfos()
            │    ├─ computePairwiseShortestPaths()
            │    └─ computePairwiseNumPaths()
            │          └─ findAllPath()
            └─ buildMstSubgraph() / buildAllSubgraph()
```

现有请求参数主要包括：

```text
graphExpansionStrategy = minimal
hopLimit = 3
seedRetrievalMode = vector
topK = 3
includeFunctions = 0
includeActions = 0
```

V5.3 不要求一次性替换现有链路，而是在现有类和接口上渐进演进：

```text
现有 getSeedIds()
    ↓
SearchDispatcher
    ↓
SemanticCandidateNormalizer
    ↓
Weighted RRF Anchor Groups
    ↓
LLM Fine Ranker
    ↓
Final Semantic Matches
    ├─ ObjectType / Property
    ├─ Alias
    ├─ Enum Value / Alias
    └─ Instance Value / Alias
    ↓
GraphAnchorProjector
    ↓
Final Graph Anchors
```

现有 `seedIds` / `seedNodes` 仍然可以作为**图构建锚点兼容字段**保留，但不能再代表完整检索结果；完整检索结果由新增的 `retrievalResults` 表达。

现有 `subgraphQuery()`：

```text
保留 external strategy 名称
    ↓
minimal / khop / component
    ↓
内部支持 legacy / enhanced 两套算法
```

因此本次调整不改变三种图算法的边界，只改变“检索输出是什么”以及“何时投影成 Anchor”。

---

# 4. 核心设计原则

## 4.1 Semantic Match First，Anchor Context Always

最终检索结果的主身份不再统一强制为 `anchor_ID`。

推荐统一定义：

```text
直接命中 ObjectType / Property：
item_id = anchor_ID

命中 Alias / Enum / Instance：
item_id = evidence_ID
```

但是所有结果必须携带稳定的 Anchor Context：

```text
anchor_ID
anchor_type
parent_ID
ObjectType Context
Property Context（适用时）
```

因此：

```text
anchor_ID
```

继续作为：

```text
RRF 聚合组键
跨通道去重键
本体映射键
Graph Anchor 投影键
```

但不再是所有最终检索结果唯一的业务主键。

## 4.2 Evidence 既是检索目标，也是 Anchor 映射载体

以下信息统一属于 Evidence：

```text
ObjectType Alias
Property Alias
Enum Value
Enum Alias
Enum Description
Instance Value
Instance Alias
业务黑话
```

Evidence 命中后必须同时满足两个要求：

```text
1. Evidence 本身可作为最终检索结果返回
2. Evidence 必须能确定性反向定位 ObjectType / Property Anchor
```

不能再采用：

```text
Evidence 命中
 → 映射 Anchor
 → 丢弃 Evidence 本身
```

## 4.3 Evidence for Cypher

Evidence 命中不能在映射为 Anchor 后被丢弃。

下游还需要：

```text
evidence_ID
evidence_type
evidence_value
canonical_value
aliases
enum_ref
matched_phrase
ObjectType Context
Property Context
```

其中：

```text
Enum / Instance Alias → canonical_value
```

直接决定下游过滤条件是否能使用真实业务值。

## 4.4 Core Graph 与 Semantic Match 分离

真实本体拓扑中参与最短路径 / K-hop / 连通分量的节点主要是：

```text
ObjectType
Property
Relation
以及按配置扩展的 Function / Action
```

而：

```text
FORMAL
VIP
Mobile Number
Subscriber category
```

可以是最终检索结果，但**不作为 Core Graph 的最短路径节点**。

它们通过：

```text
Final Semantic Match
   ↓ Anchor Projector
ObjectType / Property
```

进入图算法。

## 4.5 召回保 Recall，RRF 保组级公平，精排保语义目标准确，子图保最小充分

```text
多路召回：宁可多召回真实语义项
RRF：按 Anchor Group 跨通道稳健融合，避免 Evidence 数量偏置
LLM：选择真正命中的具体语义项，并验证 Anchor Context
Graph：仅使用投影后的 ObjectType / Property 构图
```

## 4.6 同一结果同时服务“检索解释”和“图构建”

最终命中：

```text
matched item
+
ObjectType / Property context
```

既可以告诉上层“到底命中了什么”，又可以直接给 GraphAnchorProjector 提供确定性的构图入口。

---

# 5. Anchor 与 Evidence 逻辑模型

## 5.1 Anchor

当前 Anchor 类型：

```text
type = 0：ObjectType
type = 1：Property
```

未来可扩展：

```text
Relation
Function
Action
Metric
```

当前索引主表仍保持 `0/1`，避免破坏既有实现。

Anchor 字段语义：

```text
ID          = 本体元素全局唯一 ID，即 anchor_ID
type        = 0 ObjectType / 1 Property
parent_ID   = Property 所属 ObjectType ID
name        = 本体真实名称
display_*   = 多语言显示名
description_*= 多语言描述
aliases     = ObjectType / Property 同义词
```

直接命中 Anchor 时：

```text
item_id   = ID
item_type = OBJECT_TYPE / PROPERTY
```

## 5.2 Evidence

推荐 `evidence_type`：

| evidence_type | 含义 | 最终检索类型 | Anchor Context |
|---|---|---|---|
| `OBJECT_ALIAS` | ObjectType 同义词 | `OBJECT_ALIAS` | ObjectType |
| `PROPERTY_ALIAS` | Property 同义词 | `PROPERTY_ALIAS` | Property + ObjectType |
| `ENUM_VALUE` | 枚举真实值 | `ENUM_VALUE` | Property + ObjectType |
| `ENUM_ALIAS` | 枚举值同义词 | `ENUM_ALIAS` | Property + ObjectType |
| `INSTANCE_VALUE` | 语义实例列值 | `INSTANCE_VALUE` | Property + ObjectType |
| `INSTANCE_ALIAS` | 实例值同义词 | `INSTANCE_ALIAS` | Property + ObjectType |

所有 Evidence 至少保存：

```text
evidence_ID
evidence_type
anchor_ID
anchor_type
parent_ID
anchor_name
parent_name
evidence_value
canonical_value
aliases
```

Evidence 的 `anchor_ID` 表示所属 ObjectType / Property，不表示 Evidence 自身被 Anchor 替代。

## 5.3 Final Retrieval Item

统一的最终检索结果建议使用以下逻辑模型：

```json
{
  "semanticUnitId": "u1",
  "itemId": "evidence-or-anchor-id",
  "targetType": "ENUM_ALIAS",
  "matchedValue": "FORMAL",
  "canonicalValue": "1",
  "objectType": {
    "ID": "subscriber-object-id",
    "name": "Subscriber"
  },
  "property": {
    "ID": "subClass-property-id",
    "name": "subClass"
  },
  "anchor_ID": "subClass-property-id",
  "rrfScore": 0.071,
  "rerankScore": 0.97,
  "matchSource": "METADATA_EVIDENCE"
}
```

字段约束：

```text
OBJECT_TYPE / OBJECT_ALIAS
  → objectType 必填，property 可空

PROPERTY / PROPERTY_ALIAS / ENUM_* / INSTANCE_*
  → objectType 必填，property 必填
```

这样上层不需要再次根据 `evidence_ID` 查询才能知道该值属于哪个对象和属性。

---

# 6. 物理索引划分

逻辑上是：

```text
Anchor
Evidence
```

物理上拆成三类：

| 物理表 / Index | Owner | 数据 | 典型规模 |
|---|---|---|---|
| `{ontology_id}_anchor` | OAG | ObjectType / Property | 万～百万 |
| `{ontology_id}_metadata_evidence` | OAG | Alias / Enum | 万～百万 |
| `{ontology_id}_instance_evidence` | OAG（DataSync 提供数据） | Instance Value / Alias | 百万～千万/亿 |

这一设计同时保留历史逻辑通道：

```text
Object / Property canonical
Object / Property synonym
Enum value
Enum synonym
Instance semantic value
Instance value synonym
```

但不再为每一种逻辑通道创建一张独立物理表。

---

# 7. OAG 与 DataSync 分工

## 7.1 OAG：元数据层

OAG 负责：

```text
ObjectType
Property
ObjectType Alias
Property Alias
Enum Type
Enum Value
Enum Alias
多语言 display / description
```

流程：

```text
OMS / 本体模型
  ↓
OAG Metadata Reader
  ↓
Anchor Builder
  ├─ GaussVector Anchor
  └─ OpenSearch Anchor

Metadata Evidence Builder
  ├─ GaussVector Metadata Evidence
  └─ OpenSearch Metadata Evidence
```

## 7.2 DataSync：实例数据生产层

DataSync 负责：

```text
读取 is_semantic=true Property
访问实际数据源
DISTINCT / 基础标准化实例值
整理真实业务存在的实例值同义词
建立实例数据与本体 Property / ObjectType 的映射
生成 Import Package（Manifest + Data Files）
通过 File / MinIO 交付 OAG
```

DataSync 不负责：

```text
Embedding
GaussVector / OpenSearch 物理索引写入
ANN 索引构建
Evidence 物理表结构
索引 Generation 发布
```

`INSTANCE_VALUE` 与 `INSTANCE_ALIAS` 均是合法的 Instance Evidence，并且两者本身都可以成为最终 `retrievalResults`。

流程：

```text
Property Metadata
  ↓
is_semantic eligibility
  ↓
Data Source
  ↓
DISTINCT / Normalize / Alias整理 / Statistics
  ↓
Import Package
  ↓ File / MinIO
OAG BulkImportService
  ↓
Instance Evidence Builder
  ↓
Embedding
  ├─ GaussVector
  └─ OpenSearch
```

## 7.3 统一关联键

```text
ontology_id
anchor_ID  = Property ID
parent_ID  = ObjectType ID
```

DataSync 不维护独立的本体语义主键体系。

---

# 8. GaussVector Anchor 表结构

推荐表：

```text
{ontology_id}_anchor
```

| # | 字段名称 | 字段类型 | 是否非空 | 说明 |
|---|---|---|---|---|
| 1 | `vector` | `DOUBLE[]` | ✔ | 本体元素向量 |
| 2 | `type` | `INT` | ✔ | 0 ObjectType，1 Property |
| 3 | `ID` | `VARCHAR(256 CHAR)` | ✔ | 本体元素全局唯一 ID |
| 4 | `parent_ID` | `VARCHAR(256 CHAR)` |  | type=1 时记录父 ObjectType ID |
| 5 | `name` | `VARCHAR(256 CHAR)` | ✔ | 本体真实名称 |
| 6 | `display_en` | `VARCHAR(512 CHAR)` |  | 英文显示名 |
| 7 | `display_zh` | `VARCHAR(512 CHAR)` |  | 中文显示名 |
| 8 | `description_en` | `VARCHAR(1024 CHAR)` |  | 英文描述 |
| 9 | `description_zh` | `VARCHAR(1024 CHAR)` |  | 中文描述 |
| 10 | `aliases` | `TEXT` |  | 同义词 JSON Array |
| 11 | `i18n_content` | `TEXT` |  | 西语等扩展语言 |
| 12 | `content` | `TEXT` | ✔ | 实际 Embedding 文本 |
| 13 | `normalized_name` | `VARCHAR(512 CHAR)` |  | 规范化 name |
| 14 | `content_hash` | `VARCHAR(64 CHAR)` |  | 判断内容是否变化 |
| 15 | `model_version` | `VARCHAR(128 CHAR)` |  | Embedding 模型版本 |
| 16 | `source_version` | `VARCHAR(128 CHAR)` |  | 本体版本 |
| 17 | `updated_at` | `BIGINT` |  | 更新时间 |

关键约束：

> `ID` 就是 `anchor_ID`，不做 Hash。

---

# 9. Anchor Vector 内容

当前代码基础结构：

```text
{name}
{display_zh}
{display_en}
{description_zh}
{description_en}
```

V5.3 保持兼容并增强为：

```text
{name}
{display_zh}
{display_en}
{aliases}
{description_zh}
{description_en}
{other_i18n_display_description}
```

当前 BGE-M3 向量维度沿用：

```text
1024
```

当前代码 Embedding 批处理和失败重试机制可以继续保留，例如：

```text
batch size = 30
retry = 3
```

具体数值作为工程配置，不作为协议约束。

---

# 10. 多语言向量设计

## 10.1 默认策略：同一语义目标，多语言共用一个 Vector

若以下内容描述同一个 Anchor：

```text
中文名称
英文名称
西语名称
中文描述
英文描述
西语描述
多语言 Alias
```

默认构成一个 Global Multilingual Semantic Profile。

例如：

```text
Subscriber
用户
Subscriber
Mobile Number; Number; Mobile Phone
用户实体，代表服务的实际使用者...
Subscriber entity representing...
Suscriptor ...
```

只生成一个 Anchor Vector。

判断标准不是：

```text
有多少语言
```

而是：

> **是否描述同一个 Anchor / Evidence。**

## 10.2 不允许跨目标拼接

不推荐：

```text
Property
+ 全部 Enum
+ 全部 Instance
+ 其他 Property
```

因为语义目标已经改变。

## 10.3 Shadow Vector

只有评测证明某语言 Recall 明显下降时，才允许可选增加：

```text
global vector
zh shadow vector
en shadow vector
es shadow vector
```

Shadow Vector 必须最终 GROUP BY 同一 `anchor_ID`，避免 TopK 被同一 Anchor 多语言副本占满。

---

# 11. Property Vector 是否带 ObjectType

默认：

> **Property Vector 第一行只使用 Property 自身 name，不把 ObjectType 名称作为固定前缀。**

推荐：

```text
subClass
用户类别
Subscriber category
...
```

不推荐默认：

```text
Subscriber
subClass
...
```

原因：

1. 用户经常只表达 Property 概念；
2. ObjectType 前缀会改变主向量语义重心；
3. 同名 Property 的消歧应交给 `parent_ID + Query Context + Rerank + Graph`；
4. 当前实际子图中同一自然语言短语可以对应多个不同对象下的同名/近义 Property，应该允许 Recall 后再消歧。

若评测显示同名 Property 冲突严重，可增加可选 Shadow Vector：

```text
主向量：
Property自身语义

上下文Shadow：
Property + Parent ObjectType
```

---

# 12. OpenSearch Anchor 索引

推荐 Index：

```text
{ontology_id}_anchor
```

| # | 字段 | 类型 | 非空 | 说明 |
|---|---|---|---|---|
| 1 | `content` | `text` | ✔ | 与 Vector content 一致 |
| 2 | `type` | `integer` | ✔ | 0 ObjectType / 1 Property |
| 3 | `ID` | `keyword` | ✔ | 本体全局 ID |
| 4 | `parent_ID` | `keyword` |  | 父 ObjectType |
| 5 | `name` | `keyword` | ✔ | 本体真实名称 |
| 6 | `display_en` | `keyword` |  | 英文显示名 |
| 7 | `display_zh` | `keyword` |  | 中文显示名 |
| 8 | `description_en` | `keyword` + `text` |  | 英文描述 |
| 9 | `description_zh` | `keyword` + `text` |  | 中文描述 |
| 10 | `aliases` | `keyword` + `text` |  | 同义词 |
| 11 | `normalized_name` | `keyword` |  | 规范化名称 |
| 12 | `i18n_content` | `text` |  | 扩展语言 |
| 13 | `source_version` | `keyword` |  | 本体版本 |

职责优先级：

```text
ID/name/alias exact
> phrase/BM25
> content fallback
```

---

# 13. Metadata Evidence 表结构

推荐：

```text
{ontology_id}_metadata_evidence
```

| # | 字段 | 类型 | 非空 | 说明 |
|---|---|---|---|---|
| 1 | `vector` | `DOUBLE[]` | ✔ | Evidence 向量 |
| 2 | `evidence_ID` | `VARCHAR(512 CHAR)` | ✔ | Evidence 唯一键 |
| 3 | `evidence_type` | `INT` | ✔ | Alias / Enum 类型 |
| 4 | `anchor_ID` | `VARCHAR(256 CHAR)` | ✔ | 映射 ObjectType / Property |
| 5 | `anchor_type` | `INT` | ✔ | 0 ObjectType / 1 Property |
| 6 | `parent_ID` | `VARCHAR(256 CHAR)` |  | Property 所属 ObjectType |
| 7 | `anchor_name` | `VARCHAR(256 CHAR)` | ✔ | Property/ObjectType 真实 name |
| 8 | `parent_name` | `VARCHAR(256 CHAR)` |  | ObjectType name |
| 9 | `evidence_value` | `VARCHAR(4096 CHAR)` | ✔ | 当前可检索字符串 |
| 10 | `normalized_value` | `VARCHAR(4096 CHAR)` |  | 规范化值 |
| 11 | `canonical_value` | `VARCHAR(4096 CHAR)` |  | 枚举真实值 |
| 12 | `aliases` | `TEXT` |  | Alias 集合 |
| 13 | `enum_ref` | `VARCHAR(256 CHAR)` |  | 枚举引用 |
| 14 | `description` | `TEXT` |  | 多语言描述 |
| 15 | `term_language` | `VARCHAR(16 CHAR)` |  | zh/en/es/mixed/und |
| 16 | `content` | `TEXT` | ✔ | Embedding 文本 |
| 17 | `content_hash` | `VARCHAR(64 CHAR)` |  | 内容变化检测 |
| 18 | `source_version` | `VARCHAR(128 CHAR)` |  | 本体版本 |

---

# 14. Metadata Evidence Vector 规则

Enum / Alias 主向量：

```text
{value}
{aliases}
{description_zh/en/es}
{optional property display/description}
```

原则：

> **Value First，Property Context Last，Mapping in Metadata。**

不默认以：

```text
ObjectType: ...
Property: ...
```

作为向量开头。

### Enum 被多个 Property 复用

若一个 EnumType 被多个 Property 引用，不能只创建：

```text
enum_id + enum_value
```

一个全局语义文档。

必须建立**Property Context Mapping**：

```text
shared enum value
    ↓
Property A anchor_ID
Property B anchor_ID
...
```

可共享 `enum_value_source_id`，但 Evidence 文档的 Anchor Mapping 必须是 Property-specific。

---

# 15. evidence_ID 设计

`anchor_ID` 直接使用本体 ID。

`evidence_ID` 若源模型有唯一 ID，直接复用。

若没有唯一 ID，推荐稳定构造：

```text
{anchor_ID}::{evidence_type}::{source_key}
```

例如：

```text
PropertyID::ENUM_VALUE::SubClass::1
PropertyID::ENUM_ALIAS::SubClass::1::FORMAL
```

只有 `source_key` 过长或含数据库不适合作为 Key 的字符时，可对 `source_key` 局部 Hash。

禁止对 `anchor_ID` 再 Hash。

---

# 16. Instance Evidence 表

推荐：

```text
{ontology_id}_instance_evidence
```

Owner：OAG（DataSync 通过 Bulk Import 提供实例数据与本体映射）。

| 字段 | 说明 |
|---|---|
| `vector` | 实例语义向量 |
| `evidence_ID` | 稳定唯一键 |
| `evidence_type` | INSTANCE_VALUE / INSTANCE_ALIAS |
| `anchor_ID` | Property ID |
| `anchor_type` | 固定 1 |
| `parent_ID` | ObjectType ID |
| `anchor_name` | Property name |
| `parent_name` | ObjectType name |
| `evidence_value` | 实际 DISTINCT Value |
| `normalized_value` | 标准化值 |
| `canonical_value` | 默认等于真实 Value |
| `aliases` | 实例值同义词 |
| `term_language` | 语言 Hint |
| `content` | Embedding 文本 |
| `content_hash` | 增量判断 |
| `data_version` | 数据同步版本 |

Instance 与 Metadata Evidence 字段逻辑一致，但物理表必须分开。

---

# 17. Instance Value 向量准入规则

`is_semantic=true` 是必要条件，不是充分条件。

推荐：

```text
semantic_enabled =
  is_semantic
  AND datatype_eligible
  AND value_shape_eligible
  AND cardinality_eligible
```

## 17.1 只索引 DISTINCT Value

例如：

```text
5000万 Subscriber 行
subLevel 只有 VIP/GOLD/SILVER/NORMAL
```

只生成 4 组 Value Evidence，而不是 5000 万个向量。

## 17.2 默认不向量化

以下值通常不进入 Dense：

```text
UUID
手机号
纯技术主键
时间戳
日期
连续数值
高随机编码
```

它们仍可在 OpenSearch keyword / 数据源查询中精确处理。

## 17.3 适合向量化

```text
产品名称
品牌名称
客户等级
区域名称
业务状态
自然语言标签
人可理解业务分类
```

## 17.4 高基数自由文本

高基数自然语言长文本不应无限进入 Instance Evidence。

建议进入单独的：

```text
Document / RAG Index
```

而不是本体 Anchor Resolver 的 Instance Value Index。

---

# 18. Instance Vector 内容

推荐：

```text
{instance_value}
{instance_aliases}
{optional property display}
{optional property description}
```

仍然坚持：

> **Value First，Property Context Last。**

Property/ObjectType 映射完全依赖：

```text
anchor_ID
parent_ID
```

而不是依赖向量文本解析。

---

# 19. OpenSearch Evidence Index

Metadata / Instance 两个物理 Index 均建议：

```text
content           text
evidence_ID       keyword
evidence_type     integer
anchor_ID         keyword
anchor_type       integer
parent_ID         keyword
anchor_name       keyword
parent_name       keyword
evidence_value    keyword + text
normalized_value  keyword
canonical_value   keyword
aliases           keyword + text
enum_ref          keyword
description       text
term_language     keyword
source_version    keyword
```

Exact Priority：

```text
evidence_value.keyword
normalized_value
canonical_value
aliases.keyword
anchor_name
```

---

# 20. 规范化规则

所有可检索字符串保留原值，并额外生成：

```text
normalized_name
normalized_value
```

推荐标准化：

```text
trim
Unicode normalize
casefold（仅用于 normalized field）
连续空白归一
全半角归一
```

禁止直接覆盖原始值，因为 Cypher 和业务展示仍需要原始 Canonical Value。

---

# 21. term_language 与 language_hint

对于：

```text
FORMAL
IOT_FORMAL
Subscriber
subClass
A001
```

无法可靠归类为自然语言的 Token：

```text
term_language = und
```

对于混合短语：

```text
FORMAL用户
```

可标：

```text
mixed
```

Language 仅作为：

```text
可观测
Analyzer Hint
Ranking Boost
```

不作为 Dense 强过滤条件。

---

# 22. 数据质量治理

OAG 元数据同步阶段必须检查：

```text
Alias 与 Canonical 重复
Alias 重复
同一 ObjectType 下 Property Alias 冲突
一个 Alias 映射多个不相关 Anchor
Enum Ref 不存在
Enum Value 重复
Enum Alias 冲突
Description 多语言格式错误
Parent ObjectType 缺失
```

冲突处理原则：

```text
不能静默覆盖
必须可观测
必要时阻断当前 Evidence 入库
```

DataSync 额外检查：

```text
空值
超长 Value
distinct_count
高基数
无意义随机串
Instance Alias 冲突
```

---

# 23. 增量索引与幂等

Anchor / Evidence 建议维护：

```text
content_hash
model_version
source_version
updated_at
```

更新策略：

```text
content 无变化
 → 不重新 Embedding

仅 Metadata 非向量字段变化
 → 只更新 Metadata

Embedding 模型变化
 → 按 model_version 重建 Vector

本体删除
 → 删除 Anchor + 对应 Metadata Evidence
 → OAG 清理对应 Instance Evidence / Generation
 → 必要时通知 DataSync 停止后续该 Property 数据同步
```

---

# 24. GaussVector 索引算法

Anchor / Metadata Evidence：

```text
GsIVFFLAT
COSINE
```

适用规模：

```text
约 1*10^4 ～ 2*10^6
```

推荐：

```text
IVF_NLIST = 4 * sqrt(N)
```

其中：

```text
N = 当前物理表实际记录数
```

Instance Evidence：

```text
中小规模 → GsIVFFLAT
千万 / 亿级 → GsDiskANN
```

Metadata 与 Instance 分表的一个核心原因就是允许 ANN 算法独立演进。

---

# 25. Query Understanding：LLM 不是普通分词器

LLM 应执行：

> **Semantic Phrase Extraction**

而不是按词法逐词拆分。

错误：

```text
FORMAL
用户
Mobile
Number
```

推荐主单元：

```text
FORMAL用户
Mobile Number
```

必要时可同时保留辅助短语：

```text
FORMAL用户
FORMAL
用户
Mobile Number
```

但完整业务短语优先。

---

# 26. Query Understanding 推荐结构

兼容现有：

```json
{
  "main_object": "Cell",
  "aggregation": "sum",
  "objectType": ["Type1"],
  "property": ["prop1"],
  "concepts": ["concept1"],
  "essential_ids": ["id1"],
  "slot_top_k_overrides": {
    "slot1": 5
  }
}
```

目标结构：

```json
{
  "main_object_hint": "Cell",
  "aggregation": {
    "operator": "sum",
    "target": null
  },
  "semantic_units": [
    {
      "id": "u1",
      "text": "影响业务的活跃告警",
      "role_hint": "unknown",
      "language_hint": "zh",
      "importance": "required"
    },
    {
      "id": "u2",
      "text": "发生时间",
      "role_hint": "property_or_value",
      "language_hint": "zh",
      "importance": "required"
    }
  ],
  "object_type_hints": ["Cell"],
  "constraints": [],
  "output_intent": "ontology_subgraph"
}
```

`role_hint` 可取：

```text
object
property
value
object_or_property
property_or_value
object_or_property_or_value
unknown
```

只用于 Boost，不关闭其他检索通道。

---

# 27. 为什么不建议 LLM 直接输出 slot_top_k_overrides

TopK 属于检索系统策略，应由：

```text
表规模
索引类型
召回评测
延迟预算
查询 Profile
```

控制。

LLM 可以输出：

```text
importance = required / optional
```

系统映射：

```text
required → high_recall profile
optional → normal profile
```

避免让 LLM 直接决定底层性能参数。

---

# 28. 多路检索通道

每个 Semantic Unit 同时执行：

```text
Anchor Exact/BM25
Anchor Dense

Metadata Evidence Exact/BM25
Metadata Evidence Dense

Instance Evidence Exact/BM25
Instance Evidence Dense
```

运行时不要求提前判断：

```text
FORMAL 是 enum？
VIP 是 instance？
Cell 是 object？
name 是 property？
```

未知字符串统一进入多路检索。

---

# 29. Exact 与 Dense 阈值的关系

Exact / Keyword 命中：

```text
不受 similarityThreshold 限制
```

Dense：

```text
ANN TopK
  ↓
similarityThreshold
```

原因：

```text
Exact 是确定性字符串证据
Dense threshold 只表示向量相似度过滤
```

不能用 Dense 阈值删除已经精确命中的真实名称或 Value。

---

# 30. topK / similarityThreshold 分表配置

三类物理表必须支持独立配置。

```yaml
semanticRetrieval:
  defaults:
    topK: 3
    similarityThreshold: 0.6

  anchor:
    topK: 10
    similarityThreshold: 0.6

  metadataEvidence:
    topK: 10
    similarityThreshold: 0.6

  instanceEvidence:
    topK: 5
    similarityThreshold: 0.6
```

说明：

- `3 / 0.6` 为历史兼容默认值；
- Anchor 优先 Recall；
- Metadata Evidence 允许多个 Evidence 命中并保留具体 Matched Item，RRF 再按 Anchor Group 融合；
- Instance Evidence 数据巨大，TopK 初始更保守；
- `0.6` 可作为共同起始值，但必须独立校准。

参数优先级：

```text
Request Retrieval Profile
    >
Table-level Config
    >
System Defaults
```

---

# 31. legacy GraphSearchRequest.topK 的兼容语义

当前 `GraphSearchRequest.topK=3` 不应继续被简单复用于所有内部物理表。

V5.3 建议：

```text
legacy topK
 → 最终 Semantic Match / Seed 投影输出上限的兼容值
```

内部召回使用：

```text
anchor.topK
metadataEvidence.topK
instanceEvidence.topK
```

若旧调用方只传 `topK`：

```text
内部仍使用表级默认召回
最终精排输出数量受 legacy topK 限制
```

避免：

```text
内部每个通道都只取3
```

导致 Recall 在 RRF 前丢失。

---

# 32. seedRetrievalMode 兼容

现有：

```text
vector
```

目标支持：

```text
vector
keyword
hybrid
```

推荐目标模式：

```text
hybrid
```

但为了兼容，接口默认值可暂时维持现有行为，通过配置灰度切换。

语义：

```text
vector → Dense only
keyword → Exact/BM25
hybrid → Exact/BM25/Dense + Evidence + RRF
```

---

# 33. SemanticCandidateNormalizer（兼容 AnchorCandidateNormalizer）

现有类名可以暂时保留 `AnchorCandidateNormalizer` 以降低改造成本，但目标语义应升级为：

> **把所有通道结果统一成“Matched Semantic Item + Anchor Context”，而不是把 Evidence 压扁成只有 Anchor 的候选。**

Evidence 示例：

```text
“正式用户”
  ↓
ENUM_ALIAS: FORMAL
  ↓
canonical_value = 1
  ↓
Property = Subscriber.subClass
  ↓
ObjectType = Subscriber
```

Normalized Candidate：

```json
{
  "semantic_unit_id": "u1",
  "item_id": "subClass-property-id::ENUM_ALIAS::1::FORMAL",
  "item_type": "ENUM_ALIAS",
  "evidence_ID": "subClass-property-id::ENUM_ALIAS::1::FORMAL",
  "matched_value": "FORMAL",
  "canonical_value": "1",
  "anchor_ID": "subClass-property-id",
  "anchor_type": 1,
  "object_type": {
    "ID": "subscriber-object-id",
    "name": "Subscriber"
  },
  "property": {
    "ID": "subClass-property-id",
    "name": "subClass"
  },
  "source_channel": "metadata_vector",
  "source_rank": 2,
  "source_score": 0.81
}
```

直接 Anchor 命中：

```text
item_id   = anchor_ID
item_type = OBJECT_TYPE / PROPERTY
```

Evidence 命中：

```text
item_id   = evidence_ID
item_type = OBJECT_ALIAS / PROPERTY_ALIAS / ENUM_VALUE / ENUM_ALIAS / INSTANCE_VALUE / INSTANCE_ALIAS
```

后续 RRF 可以按 `anchor_ID` 聚合，但 `item_id/item_type/matched_value/canonical_value` 必须保留到最终精排和响应。

---

# 34. 通道内 Anchor Group 去重，但保留 Matched Items

同一 Property 可能同时命中很多：

```text
Property 自身
Property Alias
Enum Value
Enum Alias
Instance Value
Instance Alias
```

如果这些 Evidence 全部各占一个 RRF 排名位置，会导致 Evidence 数量越多的 Property 被不公平抬高。

因此 RRF 前仍然执行：

```text
GROUP BY semantic_unit_id + channel + anchor_ID
```

但是**只去重 RRF Group，不删除具体命中项**。

每个 Anchor Group 保留：

```text
primary_hit
matched_items top N
supporting_evidence top N
evidence_hit_count
best_exact_rank
best_dense_rank
```

其中 `matched_items` 每项至少包含：

```text
item_id
item_type
matched_value
canonical_value
source_rank
source_score
```

例如：

```text
Property: Subscriber.subClass
  ├─ PROPERTY_ALIAS: 用户类别
  ├─ ENUM_ALIAS: FORMAL → 1
  └─ INSTANCE_VALUE: VIP → VIP
```

它们在 RRF 中只形成一个 `anchor_ID=subClass` 的组级候选，但 LLM 精排仍可以选择 `FORMAL`、`VIP` 或 Property 本身作为最终语义目标。

对于一个 Semantic Unit 明确包含多个值的情况，例如：

```text
VIP 或 GOLD 用户
```

`matched_items` 允许保留同一 Property 下多个不同 `canonical_value`，不能只保留一个 primary hit。

---

# 35. Aggregator：Weighted RRF

RRF 的融合单位继续保持：

> **anchor_ID Group**

而不是：

```text
evidence_ID
item_id
```

公式：

```text
RRF(anchor_group) = Σ weight(channel) / (rrf_k + rank_channel(anchor_group))
```

推荐起始配置：

```yaml
rrf:
  k: 60
  coarseTopKPerSemanticUnit: 20
  maxGlobalCandidates: 50
  maxMatchedItemsPerAnchorGroup: 5
  channelWeights:
    anchorExact: 1.5
    anchorBm25: 1.1
    anchorVector: 1.0
    metadataExact: 1.4
    metadataBm25: 1.0
    metadataVector: 1.0
    instanceExact: 1.2
    instanceBm25: 0.8
    instanceVector: 0.8
```

这样做的原因：

```text
RRF 解决不同检索通道排序不可比问题
anchor_ID Group 防止 Evidence 数量造成排名偏置
matched_items 保证 Alias / Enum / Instance 本身不会丢失
```

因此 RRF 的职责不是决定最终具体值，而是：

```text
先选出值得进入 LLM 精排的 Anchor Groups
+
为每个 Group 携带最相关的 Matched Items
```

最终具体返回哪个 Alias / Enum / Instance Value，由 LLM Fine Ranking 在原始问题上下文中裁决。

RRF 的优势仍然是：

```text
不要求 BM25、Cosine、Exact 的原始 score 在同一数值空间
主要利用 rank
降低跨检索引擎 score 不可比问题
```

这也意味着此前“不做 Anchor / Metadata / Instance 两级 RRF”的结论保持不变：所有 Channel 统一归一化后做一次 Weighted RRF 即可。

---

# 36. Exact 不是绝对锁定

Exact 是强证据，但：

```text
name
status
active
1
A
VIP
```

可能跨对象、跨属性或跨 Evidence 重复。

因此：

```text
Exact Matched Item
 → 高权重进入对应 Anchor Group
 → RRF
 → LLM Rerank
 → Final Semantic Match
```

而不是无条件：

```text
Exact Evidence → 直接 Final
```

只有：

```text
本体全局唯一 ID exact
```

可以视为强确定性 ObjectType / Property Anchor。

对于 Alias / Enum / Instance 的 exact 命中，即使字符串完全相同，也仍需要结合：

```text
Property
ObjectType
其他 Semantic Unit
原始问题
```

判断它属于哪个业务上下文。

---

# 37. RRF 粗排输出

RRF 输出的是 Anchor Group 排名，但每个组中完整保留真实 Matched Items。

```json
{
  "semantic_unit_id": "u4",
  "semantic_unit": "正式用户",
  "candidates": [
    {
      "anchor_ID": "subClass-property-id",
      "anchor_type": 1,
      "object_type": {
        "ID": "subscriber-object-id",
        "name": "Subscriber"
      },
      "property": {
        "ID": "subClass-property-id",
        "name": "subClass"
      },
      "rrf_score": 0.071,
      "channel_hits": [
        {"channel": "metadata_exact", "rank": 1},
        {"channel": "metadata_vector", "rank": 2}
      ],
      "matched_items": [
        {
          "item_id": "subClass-property-id::ENUM_ALIAS::1::FORMAL",
          "item_type": "ENUM_ALIAS",
          "matched_value": "FORMAL",
          "canonical_value": "1",
          "source_channel": "metadata_exact",
          "source_rank": 1
        }
      ]
    }
  ]
}
```

如果直接命中 Property 本身，则 `matched_items` 中可包含：

```json
{
  "item_id": "subClass-property-id",
  "item_type": "PROPERTY",
  "matched_value": "subClass"
}
```

因此粗排阶段已经同时具备：

```text
Anchor Group 排名
+
具体语义目标候选
```

而不是只有 Anchor。

---

# 38. LLM Fine Ranking 目标

LLM 使用预置提示词，输入：

```text
原始问题
Semantic Units
RRF 粗排 Anchor Groups
每个 Group 的 Matched Items
Anchor Metadata
Parent ObjectType
Matched Evidence
Canonical Value
轻量 Graph Hint
```

任务：

```text
深度语义理解
业务限定词校验
对象/属性上下文对齐
判断最终目标是 Anchor 本身还是 Alias / Enum / Instance
枚举/实例值到属性的映射验证
具体 matched_value / canonical_value 选择
多候选消歧
必要语义目标完整性检查
```

输出分成两层：

```text
Final Semantic Matches
  ├─ ObjectType / Property
  ├─ Object/Property Alias
  ├─ Enum Value / Alias
  └─ Instance Value / Alias

Graph Anchor Projection
  └─ ObjectType / Property IDs
```

LLM 的直接业务输出是准确的 **Semantic Match**，而不是只有 ObjectType / Property Anchor。

---

# 39. 为什么精排必须使用原始问题

例如：

```text
Semantic Unit = 发生时间
```

可能匹配：

```text
update_time
firstoccurrence
lastoccurrence
```

原始问题：

```text
查询站点上影响业务的活跃告警首次发生时间
```

能进一步确定：

```text
AP_ALARM_LIVE.firstoccurrence
```

因此 LLM 不得只使用拆词结果。

---

# 40. Rerank Context

推荐：

```json
{
  "original_query": "查询正式用户的手机号",
  "semantic_units": [...],
  "candidate_groups": [
    {
      "anchor_ID": "subClass-property-id",
      "anchor_type": 1,
      "rrf_score": 0.071,
      "object_type": {
        "ID": "subscriber-object-id",
        "name": "Subscriber",
        "display": "用户"
      },
      "property": {
        "ID": "subClass-property-id",
        "name": "subClass",
        "display": "用户类别"
      },
      "matched_items": [
        {
          "item_id": "...FORMAL",
          "item_type": "ENUM_ALIAS",
          "matched_value": "FORMAL",
          "canonical_value": "1",
          "channels": ["metadata_exact", "metadata_vector"]
        }
      ],
      "graph_hint": {
        "neighbor_object_types": ["Offering"],
        "relation_names": ["SUBSCRIBE_TO"]
      }
    }
  ]
}
```

对于 Anchor 直接命中，同样作为 `matched_items` 传入：

```text
item_type = OBJECT_TYPE / PROPERTY
item_id   = anchor_ID
```

Graph Hint 只取一跳或轻量摘要，不在精排前构建完整子图。

精排 Prompt 不要求 LLM 从 Evidence 文本重新推断所属对象/属性，因为这些映射已经由索引元数据确定性提供。

---

# 41. LLM 精排 Prompt 约束

System Prompt：

```text
Role:
你是 OAG 本体语义目标精排器。

Objective:
根据原始问题、语义单元、候选 Anchor Group、具体 Matched Item、ObjectType / Property 元数据、
canonical value 和轻量本体关系上下文，选出真正表达用户意图的最终语义目标。

Rules:
1. 最终目标可以是 ObjectType、Property、Alias、Enum Value/Alias、Instance Value/Alias。
2. 只能选择输入 candidate_groups / matched_items 中存在的 item_id，不得创造不存在的目标。
3. 直接 Anchor 命中时，item_id=anchor_ID；Evidence 命中时，item_id=evidence_ID。
4. Evidence 被选中时，必须原样保留 item_type、matched_value、canonical_value 及其 ObjectType/Property Context。
5. Property、Property Alias、Enum、Instance 必须结合 Parent ObjectType 判断。
6. Exact/BM25/Vector/RRF 分数只是证据，不等价于最终业务语义正确。
7. 必须结合原始问题和其他 Semantic Unit 做跨单元一致性判断。
8. 一个 Semantic Unit 可以选择多个必要 Semantic Match，例如同一 Property 下多个值。
9. 全部不匹配允许 no_match=true。
10. 输出简洁 reason，不输出内部详细思维过程。
11. 严格输出 JSON Schema。
```

特别禁止：

```text
命中 Evidence 后只输出 anchor_ID，导致真实命中的 Alias / Enum / Instance 消失
```

Anchor Context 是必须携带的上下文，不是 Evidence 的替代品。

---

# 42. 精排输出与 0/1/N

允许：

```text
0：全部不匹配
1：唯一准确 Semantic Match
N：多个业务上同时必要的 Semantic Match
```

这里的 Match 可以是：

```text
Anchor
Alias
Enum
Instance Value
```

示例一：`发生时间` 最终选中 Property 本身：

```json
{
  "semantic_unit_id": "u2",
  "selected_matches": [
    {
      "item_id": "property-first-id",
      "target_type": "PROPERTY",
      "matched_value": "firstoccurrence",
      "object_type": {
        "ID": "alarm-object-id",
        "name": "AP_ALARM_LIVE"
      },
      "property": {
        "ID": "property-first-id",
        "name": "firstoccurrence"
      },
      "rank_score": 0.96,
      "reason": "与原始问题中的首次发生时间一致"
    }
  ],
  "no_match": false
}
```

示例二：`正式用户` 最终选中枚举别名本身：

```json
{
  "semantic_unit_id": "u4",
  "selected_matches": [
    {
      "item_id": "subClass-property-id::ENUM_ALIAS::1::FORMAL",
      "target_type": "ENUM_ALIAS",
      "matched_value": "FORMAL",
      "canonical_value": "1",
      "object_type": {
        "ID": "subscriber-object-id",
        "name": "Subscriber"
      },
      "property": {
        "ID": "subClass-property-id",
        "name": "subClass"
      },
      "rank_score": 0.97,
      "reason": "正式用户与FORMAL语义一致，真实过滤值为1"
    }
  ],
  "no_match": false
}
```

所有 Semantic Unit 精排完成后再生成：

```json
{
  "final_anchor_ids": [
    "subscriber-object-id",
    "subClass-property-id"
  ]
}
```

`final_anchor_ids` 是 GraphAnchorProjector 的派生结果，不替代 `selected_matches`。

---

# 43. LLM 精排可靠性与降级

程序校验：

```text
JSON Schema
item_id ∈ Input Anchor / Matched Item
item_type 与输入一致
Evidence 的 anchor_ID / property / objectType 映射不可被 LLM 改写
canonical_value 必须来自输入候选
rank_score 合法
去重
数量上限
```

异常：

```text
LLM Timeout / JSON错误
 → 重试1次
 → 仍失败
 → fallback=RRF
 → 对每个 RRF Anchor Group 选择 primary_hit 作为 Final Semantic Match
 → rerank_status=DEGRADED
```

降级时也不能只返回 `anchor_ID`；如果 primary hit 是 Alias / Enum / Instance，仍应保留该 Matched Item。

正常 `no_match` 不属于异常。

---

# 44. Final Semantic Match → Graph Anchor Normalization

图算法前增加明确的：

```text
GraphAnchorProjector
```

它只负责从最终语义命中中提取 ObjectType / Property，不改变或删除最终检索结果。

映射规则：

| Final target_type | Graph Anchor 投影 |
|---|---|
| `OBJECT_TYPE` | 当前 ObjectType |
| `OBJECT_ALIAS` | Alias 所属 ObjectType |
| `PROPERTY` | 当前 Property + Parent ObjectType |
| `PROPERTY_ALIAS` | Alias 所属 Property + Parent ObjectType |
| `ENUM_VALUE` | Enum 所属 Property + Parent ObjectType |
| `ENUM_ALIAS` | Enum Alias 所属 Property + Parent ObjectType |
| `INSTANCE_VALUE` | Instance Value 所属 Property + Parent ObjectType |
| `INSTANCE_ALIAS` | Instance Alias 所属 Property + Parent ObjectType |

Property 类目标统一形成：

```text
explicit_property_anchors
object_terminals
mandatory_has_property_edges
```

ObjectType 类目标：

```text
直接进入 object_terminals
```

最终图算法跨对象连接时主要处理：

```text
object_terminals
```

Property 通过强制 `has_property` 挂回。

这样既满足：

```text
最终检索返回 Alias / Enum / Instance 本身
```

又保证：

```text
图算法只处理合法本体拓扑
```

并显著减少：

```text
Seed Pair 数
最短路径组合数
```

注意：

> **Evidence → Anchor 在这里表示“为构图投影 Anchor”，不是“把 Evidence 转换后丢弃”。**

---

# 45. Property → ObjectType 扩展：优先 parent_ID

当前代码存在：

```text
MATCH (n)-[:has_property]->(nodes)
WHERE id(nodes) IN [...]
RETURN distinct n
```

运行时根据 Property ID 查父 ObjectType。

V5.0 推荐优先：

```text
Anchor.parent_ID
```

因为索引阶段已经记录该映射。

流程：

```text
Property Anchor
  ↓
parent_ID available?
  ├─ yes → 直接补 Parent ObjectType
  └─ no  → 调用现有 GQL addObjectTypeByProperty() 兼容兜底
```

并可使用本体图 `has_property` 做一致性校验。

这样既保留现有实现，又减少每次查询额外 GQL。

---

# 46. 当前三种子图策略：必须区分“接口语义”与“实际算法”

外部策略名：

```text
minimal
khop
component
```

保持不变。

但当前实现事实是：

| Strategy | 当前真实实现 | 不是严格意义上的 |
|---|---|---|
| minimal | Seed 两两最短路径 → 按路径长度排序 → 贪心加入直到连通 | 标准 MST / 最优 Steiner Tree |
| khop | Seed 两两组合 → `FIND ALL PATH ... UPTO k STEPS` | 真正 Multi-Source BFS |
| component | Seed 两两 `FIND ALL PATH ... UPTO 10 STEPS` | 真正无界 Connected Component |

文档和代码必须明确这一点。

---

# 47. minimal：当前实现分析

当前流程：

```text
Seeds
 ↓
computePairwiseShortestPaths
 ↓
Pair Paths
 ↓
按 Path Length 排序
 ↓
逐条 collectFromPath
 ↓
DisjointSet 判断所有 Seed 是否连通
 ↓
addMissingEdgesFromObjects
 ↓
removeEdgesWithMismatchedId
```

其优点：

```text
实现简单
可复用现有最短路径能力
输出通常比较紧凑
已有线上代码基础
```

限制：

1. 路径按长度贪心加入，不等价于先构造 Terminal Metric Closure 再做标准 MST；
2. 不保证得到全局最小 Steiner Tree；
3. 多条等长最短路径的业务语义优先级没有充分表达；
4. Seed 数增大后两两最短路径数量 O(S²)；
5. Property Seed 没先折叠 Parent ObjectType 时会增加 Pair 数。

---

# 48. minimal：增强方案

建议保留：

```text
minimal.algorithm = legacy_greedy
```

并增加：

```text
minimal.algorithm = metric_closure_mst
```

目标实现：

```text
1. Property → Parent ObjectType
2. 得到 object_terminals
3. 计算 terminal pair shortest path
4. 构造 Metric Closure
5. Metric Closure 上做 MST
6. 将 MST virtual edge 展开回原始 shortest path
7. 合并节点 / 边
8. 加回 Property + has_property
9. 剪除非 Anchor 的无意义叶子
```

这是更规范的：

```text
Shortest Path + MST Steiner Approximation
```

但仍然不是严格 NP-hard Steiner Tree 的最优解，应在文档中称：

```text
Steiner Tree Approximation
```

---

# 49. minimal 路径选择增强

当前最短路径主要按 Hop 数。

如果多个等长路径，可按稳定 tie-break：

```text
1. 与 Query / 已命中 relation hint 语义更匹配
2. active relation 优先
3. 中间 ObjectType 更少
4. junction/backing 复杂度更低
5. relationship priority
6. 稳定 ID 排序
```

建议配置：

```yaml
subgraph:
  minimal:
    pathCostMode: hop_count
    tieBreak:
      semanticRelation: true
      preferActive: true
      preferLowerJunctionComplexity: true
```

第一阶段保持 `hop_count` 兼容，后续可灰度 `semantic_weighted`。

---

# 50. khop：当前实现分析

当前 `khop` 实际：

```text
getPairs(seedIds)
 ↓
parallelStream
 ↓
每个 src/dst
 ↓
FIND ALL PATH FROM src TO dst OVER * UPTO k STEPS
 ↓
收集所有 PathInfo
```

优点：

```text
能显式获得 Seed 间多条 k-hop 路径
实现基于现有 NebulaGraph GQL
```

核心风险：

1. 不是 Multi-Source BFS；
2. Seed 数为 S 时 Pair 数 O(S²)；
3. `FIND ALL PATH` 的路径数量在稠密图中可能组合爆炸，复杂度不能简单理解成 O(S²×k)；
4. 大量路径在后续又会共享相同节点和边，存在重复 IO / 解析；
5. `parallelStream` 会把路径爆炸转化成更高瞬时 GraphDB 压力；
6. 默认 k=3 通常可控，但仍需要 Path/Node/Time 上限。

---

# 51. khop：兼容模式与增强模式

保留：

```text
khop.algorithm = pairwise_all_path
```

作为现有兼容实现。

增加：

```text
khop.algorithm = multi_source_bfs
```

目标行为：

```text
所有 object_terminals 同时入队
visited[node] = min_hop
reachable_from[node] = anchor_set
frontier 按层批量扩展
达到 hop_limit 停止
```

目标输出：

```text
node.min_hop
node.reachable_from_anchor_ids
edge.discovery_hop
```

优势：

```text
避免 Seed Pair 两两重复
避免枚举所有路径
更适合“邻域扩展”语义
更容易 maxNodes/maxEdges 截断
```

---

# 52. Multi-Source BFS 实现建议

若图数据库没有直接满足需求的多源 API，可在 OAG 层做分层 frontier：

```text
frontier[0] = all terminals
for depth = 1..k:
    batch query neighbors(frontier[depth-1])
    remove visited
    add frontier[depth]
    update reached_from
```

关键：

```text
批量查询
visited 去重
edge type filter
active filter
maxNodes/maxEdges
timeout
```

不需要枚举所有简单路径。

---

# 53. legacy khop 必须增加防爆参数

在完全替换为 Multi-Source BFS 前，现有 `FIND ALL PATH` 模式至少增加：

```yaml
subgraph:
  khop:
    hopLimit: 3
    maxPathsPerPair: 20
    maxTotalPaths: 200
    maxNodes: 100
    maxEdges: 200
    queryTimeoutMs: 2000
    pairConcurrency: 8
```

并记录：

```text
path_truncated
timeout_pairs
total_path_count
```

---

# 54. component：当前实现分析

当前代码：

```text
component
 → computePairwiseNumPaths(seedIds, 10)
 → FIND ALL PATH ... UPTO 10 STEPS
```

这是：

> **有界 10-hop 连通近似**

并不是真正的 Graph Connected Component。

风险：

1. 两个节点可能实际同一连通分量，但最短路径 > 10，因此被错误判定不连通；
2. 仍然枚举 `ALL PATH`，大分量中成本高；
3. `10` 是工程上“大值”，不是图论意义的全连通；
4. component 语义和实现语义存在偏差。

---

# 55. component：增强为真实 Connected Component

当前 OAG 已有：

```text
loadAllEdges()
DisjointSet
buildDsuFromNodesAndEdges()
```

因此最优增强不是继续扩大：

```text
UPTO 10 → UPTO 20
```

而是：

```text
本体版本加载/变更时
  ↓
加载 active ontology core edges
  ↓
构建 DSU / Connected Component Index
  ↓
component_id[node]
```

请求时：

```text
Final Anchor
  ↓
component_id
  ↓
直接取相关 connected component
```

这样得到真正的 Connected Component 语义。

---

# 56. Component Cache

建议新增：

```text
GraphTopologyCache
```

按：

```text
ontology_id + source_version
```

缓存：

```text
adjacency
active_edges
component_id
object_type metadata
property parent mapping
relation metadata
```

优势：

```text
避免每次 loadAllEdges
Component O(1) 判断
支持 Multi-Source BFS
支持本地快速连通性校验
```

本体版本变化后整体失效重建。

---

# 57. `component` API 兼容策略

外部仍使用：

```text
graphExpansionStrategy=component
```

内部配置：

```yaml
component:
  algorithm: dsu_cached
  legacyHopLimit: 10
```

灰度阶段：

```text
shadow execute:
 legacy bounded-component
 enhanced dsu-component

比较:
 connectivity
 nodes
 latency
```

验证后切换默认。

---

# 58. 三种策略最终定义

| Strategy | 最终推荐算法 | 默认用途 | 输出规模 |
|---|---|---|---|
| `minimal` | Metric Closure + MST Approximation | Cypher / 确定性问数 | 最小 |
| `khop` | Multi-Source BFS | 探索、补桥、邻域 | 中 |
| `component` | DSU / BFS 真连通分量 | 模型诊断、全局探索 | 最大 |

同时保留 legacy implementation 供灰度。

---

# 59. auto 策略

推荐：

```text
auto
```

但为了兼容现有 `GraphSearchRequest`，可先作为新值引入。

流程：

```text
Final Anchors
  ↓
minimal
  ↓
全部连通?
  ├─ yes → 返回 minimal
  └─ no
       ↓
     khop multi-source BFS(k=3)
       ↓
     发现合理桥接?
       ├─ yes → 返回 enhanced khop result
       └─ no
            ↓
          connected_groups
          + unresolved anchors
```

不默认自动进入完整 component，避免上下文爆炸。

---

# 60. 子图构建中的 Anchor Terminal 设计

LLM 最终 Anchor 可能包含：

```text
ObjectType
Property
```

构图时：

```text
ObjectType → Terminal
Property → parent ObjectType 作为 Terminal
```

Property 自身作为：

```text
mandatory leaf
```

即：

```text
Parent ObjectType
  └─ has_property
      └─ Property
```

这能减少：

```text
Terminal count
Pairwise shortest path count
路径搜索成本
```

---

# 61. 本体图中关系的作用

核心本体子图需要保留：

```text
has_property
defines_relation
relation node / metadata
junction mapping
businessSemanticType
cardinality
linkType
```

下游 Cypher 真正的关系连接依据来自本体图，而不是 Vector。

例如：

```text
SITE_TO_ALARM
NE_TO_SITE
NE_TO_2G
```

及其：

```text
junctionConfig
sourceName
targetName
```

必须在最终 Core Graph / Relation Metadata 中保留。

---

# 62. Relation 路径选择

当一个 Anchor Pair 存在多条路径：

```text
A → B
A → C → B
A → D → B
```

不应仅依据向量分数。

推荐 Path Score：

```text
PathCost =
  hop_cost
  + relation_complexity_penalty
  + inactive_penalty
  - semantic_relation_bonus
```

第一版可只做 tie-break，不改变现有 shortest-hop 主语义。

---

# 63. includeFunctions / includeActions

现有请求已经支持：

```text
includeFunctions
includeActions
```

V5.0 保留。

推荐处理阶段：

```text
Final Core Subgraph
  ↓
CapabilityExtensionAssembler
  ├─ includeFunctions=1 → 扩展相关 Function
  └─ includeActions=1   → 扩展相关 Action
```

Function/Action 默认不进入 Anchor RRF 主排序，除非未来明确把它们升级为 Anchor 类型。

最终输出可独立：

```json
{
  "capabilityExtensions": {
    "functions": [],
    "actions": []
  }
}
```

避免 Function/Action 干扰 ObjectType/Property 核心拓扑。

---

# 64. Retrieval Results 与 Semantic Extensions

最终响应需要明确区分三层：

```text
retrievalResults
ontologySubgraph
semanticExtensions
```

## retrievalResults

表示 LLM 精排后真正命中的语义目标：

```text
ObjectType / Property
ObjectType / Property Alias
Enum Value / Alias
Instance Value / Alias
```

这些是**最终检索结果本身**。

## ontologySubgraph

只包含通过 Final Semantic Matches 投影出的 ObjectType / Property Anchor 以及图算法扩展出来的真实本体拓扑。

## semanticExtensions

是在最终命中基础上追加的上下文，例如：

```text
ObjectType → 其他 Alias
Property → 其他 Alias
Property → Enum sibling values / aliases
Property → matched/topN Instance Value / Alias
```

因此：

```text
retrievalResults = 用户真正命中的目标
semanticExtensions = 为 LLM / Cypher 补充的附加语义上下文
```

两者不能混为一谈。

Alias、Enum、Instance 不参与图算法，但它们可以作为 `retrievalResults` 的一等结果存在。

---

# 65. Enum Retrieval Result 与 Extension 返回模式

如果最终精排选中：

```text
ENUM_VALUE
ENUM_ALIAS
```

该命中项必须无条件出现在：

```text
retrievalResults
```

例如：

```text
FORMAL → canonical_value=1
```

不能因为 `enumMode=matched_only` 而只返回 Property Anchor。

`semanticExtensions.enumMode` 控制的是**额外枚举域上下文**：

```text
matched_only
all_values
```

推荐默认：

```text
matched_only
```

含义：

```text
retrievalResults：始终返回真正命中的 Enum Item
semanticExtensions：默认只附带已命中的 Enum；显式 all_values 时再返回完整枚举域
```

这样既保证检索结果准确，又避免把完整枚举列表无条件塞给下游。

---

# 66. Instance Retrieval Result 与 Extension 返回模式

Instance 可能百万/千万/亿，但最终命中的单个或少量实例值本身仍然是合法检索目标。

如果 LLM 最终选中：

```text
INSTANCE_VALUE
INSTANCE_ALIAS
```

必须出现在：

```text
retrievalResults
```

禁止的是：

```text
因为命中了某 Property，就返回该 Property 的所有 Instance Value
```

而不是禁止返回实际命中的 Instance Value。

`semanticExtensions.instanceMode` 只控制额外上下文：

```text
matched_only
matched + topN
```

例如：

```yaml
extension:
  instanceMode: matched_only
  maxInstanceEvidencePerProperty: 10
```

含义：

```text
retrievalResults：保留 LLM 最终选中的 Instance Value / Alias
semanticExtensions：默认只附带 matched items；需要时最多额外 topN
```

这样不会因为实例库规模巨大而污染响应，同时保证“实例列值本身是最终检索目标”。

---

# 67. retrievalResults 与 seedNodes 结构

`seedNodes` 继续兼容现有调用方，但必须明确：

> **seedNodes 是 Graph Anchor Projection，不再等同于完整检索结果。**

## 67.1 retrievalResults

Evidence 最终命中示例：

```json
{
  "semanticUnitId": "u4",
  "llmDrawEntityName": "正式用户",
  "matches": [
    {
      "itemId": "subClass-property-id::ENUM_ALIAS::1::FORMAL",
      "targetType": "ENUM_ALIAS",
      "matchedValue": "FORMAL",
      "canonicalValue": "1",
      "objectType": {
        "ID": "subscriber-object-id",
        "name": "Subscriber"
      },
      "property": {
        "ID": "subClass-property-id",
        "name": "subClass"
      },
      "rrfScore": 0.071,
      "rerankScore": 0.97,
      "matchSource": "METADATA_EVIDENCE"
    }
  ]
}
```

Property 本身命中示例：

```json
{
  "itemId": "property-first-id",
  "targetType": "PROPERTY",
  "matchedValue": "firstoccurrence",
  "objectType": {
    "ID": "alarm-object-id",
    "name": "AP_ALARM_LIVE"
  },
  "property": {
    "ID": "property-first-id",
    "name": "firstoccurrence"
  }
}
```

## 67.2 seedNodes

由 `retrievalResults` 投影生成：

```json
{
  "semanticUnitId": "u4",
  "llmDrawEntityName": "正式用户",
  "anchors": [
    {
      "ID": "subClass-property-id",
      "type": 1,
      "name": "subClass",
      "parent_ID": "subscriber-object-id",
      "parent_name": "Subscriber",
      "derivedFromItemId": "subClass-property-id::ENUM_ALIAS::1::FORMAL"
    }
  ]
}
```

这样兼容现有子图代码，同时不会丢失最终命中的具体语义项。

---

# 68. Final Response 数据结构

推荐：

```json
{
  "message_type": "message_ontology_subgraph",
  "content": {
    "retrievalResults": [
      {
        "semanticUnitId": "u4",
        "matches": [
          {
            "itemId": "...",
            "targetType": "ENUM_ALIAS",
            "matchedValue": "FORMAL",
            "canonicalValue": "1",
            "objectType": {
              "ID": "subscriber-object-id",
              "name": "Subscriber"
            },
            "property": {
              "ID": "subClass-property-id",
              "name": "subClass"
            },
            "rrfScore": 0.071,
            "rerankScore": 0.97
          }
        ]
      }
    ],
    "seedNodes": [],
    "nodes": [],
    "edges": [],
    "semanticExtensions": {
      "anchors": []
    },
    "capabilityExtensions": {
      "functions": [],
      "actions": []
    },
    "metadata": {
      "retrievalMode": "hybrid",
      "rerankStatus": "SUCCESS",
      "graphStrategy": "minimal",
      "graphAlgorithm": "metric_closure_mst",
      "connected": true,
      "truncated": false,
      "unresolvedSemanticUnits": [],
      "unconnectedAnchorIds": []
    }
  }
}
```

保持：

```text
nodes
edges
seedNodes
```

兼容已有调用方。

新增：

```text
retrievalResults
```

作为**完整最终检索结果的权威字段**。

`seedNodes` 仅用于兼容图构建锚点语义，不能代替 `retrievalResults`。新增字段均可通过版本化接口/兼容开关渐进发布。

---

# 69. Cypher 生成最小充分上下文

## Final Retrieval Context

```text
item_id
target_type
matched phrase / matched_value
canonical_value
match source
```

这是告诉 LLM“用户真正命中了什么”的直接依据。

## Anchor Context

```text
ObjectType ID / name
Property ID / name
Property parent_ID
```

这是告诉 LLM“该语义项属于哪个本体对象和属性”的确定性映射。

## Evidence Context

```text
evidence_ID
evidence type
evidence value
canonical value
aliases
enum_ref
```

## Relation Context

```text
relation id / name
businessSemanticType
cardinality
linkType
junctionConfig
source/target mapping
```

例如：

```text
retrieval target = ENUM_ALIAS: FORMAL
canonical_value  = 1
Property         = Subscriber.subClass
ObjectType       = Subscriber
```

LLM 生成 Cypher 时不再需要猜：

```text
FORMAL 是最终命中的 Alias 还是 Property 名称
FORMAL 对应的真实值是什么
Property 属于哪个 ObjectType
两个 ObjectType 用什么字段关联
```

因此准确的 Cypher 上下文是：

> **Final Semantic Match + Anchor Context + Relation Context。**

---

# 70. 完整运行时序

```mermaid
sequenceDiagram
    participant U as User/Agent
    participant QU as QueryUnderstanding
    participant D as SearchDispatcher
    participant GV as GaussVector
    participant OS as OpenSearch
    participant N as SemanticCandidateNormalizer
    participant R as RRF Aggregator
    participant C as RerankContextBuilder
    participant L as LLM Fine Ranker
    participant P as GraphAnchorProjector
    participant G as GraphTopology/SubgraphBuilder
    participant E as ExtensionAssembler

    U->>QU: 原始问题
    QU-->>D: Semantic Units

    par Anchor
      D->>GV: Anchor Dense
      D->>OS: Anchor Exact/BM25
    and Metadata Evidence
      D->>GV: Metadata Dense
      D->>OS: Metadata Exact/BM25
    and Instance Evidence
      D->>GV: Instance Dense
      D->>OS: Instance Exact/BM25
    end

    D->>N: 所有 Channel Results
    N->>N: 保留 Matched Item + Anchor Context
    N->>N: channel 内按 anchor_ID Group 去重
    N->>R: Ranked Anchor Groups + Matched Items
    R-->>C: RRF Coarse Groups

    U->>C: Original Query
    QU->>C: Semantic Units
    C->>C: Metadata/Evidence/Graph Hint
    C->>L: Prebuilt Rerank Prompt
    L-->>P: Final Semantic Matches

    P->>P: Match → ObjectType / Property Anchors
    P-->>G: Final Graph Anchors
    G->>G: Property→Parent normalization
    G->>G: minimal/khop/component
    G-->>E: Ontology Core Subgraph

    L-->>E: Final Semantic Matches
    E->>E: Extra Alias/Enum/Matched Instance Context
    E->>E: Function/Action optional
    E-->>U: retrievalResults + Final Subgraph Response
```

这里最关键的边界是：

```text
LLM Fine Ranker 输出具体 Semantic Match
GraphAnchorProjector 才负责把它投影成子图 Seed
```

因此 Evidence 不会在 RRF 或 LLM 后被提前丢弃。

---

# 71. 索引构建流程

V5.3 统一采用“**OAG 负责索引构建，DataSync 负责实例数据生产**”的职责边界：

```mermaid
flowchart LR
    subgraph OMS[本体模型]
      OT[ObjectType]
      P[Property]
      A[Alias]
      EN[Enum]
    end

    subgraph DS[DataSync]
      SC[读取 is_semantic Property]
      SRC[(业务数据源)]
      DV[DISTINCT / Normalize / Alias整理]
      PKG[Import Package<br/>Manifest + Data Files]
    end

    subgraph TRANS[批量数据面]
      FS[(File / Shared Storage)]
      MI[(MinIO)]
    end

    subgraph OAG[OAG]
      AB[Anchor Builder]
      MB[Metadata Evidence Builder]
      BI[BulkImportService]
      IB[Instance Evidence Builder]
      EMB[Embedding]
    end

    subgraph GV[GaussVector]
      GA[Anchor]
      GM[Metadata Evidence]
      GI[Instance Evidence]
    end

    subgraph OS[OpenSearch]
      OA[Anchor]
      OM[Metadata Evidence]
      OI[Instance Evidence]
    end

    OT --> AB
    P --> AB
    A --> AB
    A --> MB
    EN --> MB

    AB --> GA
    AB --> OA
    MB --> GM
    MB --> OM

    P --> SC
    SRC --> DV
    SC --> DV
    DV --> PKG
    PKG --> FS
    PKG --> MI
    FS --> BI
    MI --> BI
    BI --> IB
    IB --> EMB
    EMB --> GI
    EMB --> OI
```

职责约束：

```text
DataSync：不生成 Vector，不直接写 GaussVector/OpenSearch
OAG：统一 Evidence 构造、Embedding、双写、ANN/全文索引构建和 Generation 发布
```

`INSTANCE_VALUE / INSTANCE_ALIAS` 在此流程中既是 Instance Evidence 索引数据，也是后续可直接返回的最终 `retrievalResults`。

---

# 72. GraphTopologyCache

由于当前子图代码存在：

```text
loadAllEdges()
```

建议将静态本体拓扑按版本缓存：

```text
Key = ontology_id + source_version
```

Value：

```text
nodesById
edgesById
adjacency
reverseAdjacency
propertyParentMap
componentId
relationMetadata
```

失效条件：

```text
本体版本变化
Relation变更
ObjectType/Property删除
```

收益：

```text
降低重复 loadAllEdges
加速 component
加速 one-hop graph hint
支持 Multi-Source BFS
支持 Rerank Context
```

---

# 73. 性能风险控制

## Retrieval

```text
table-level TopK
similarityThreshold
timeout
并行通道隔离
Instance Evidence 限流
```

## Candidate Normalize / RRF

```text
channel 内 anchor_ID Group 去重
maxMatchedItemsPerAnchorGroup
coarseTopKPerSemanticUnit
maxGlobalCandidates
```

这里必须同时控制：

```text
Anchor Group 数量
每个 Group 内 Matched Item 数量
```

否则虽然 RRF Group 数量可控，但某个高频 Property 仍可能携带过多 Enum/Instance Evidence 进入 Prompt。

## LLM

```text
maxCandidateGroupsPerSemanticUnit
maxMatchedItemsPerAnchorGroup
maxGlobalCandidates
maxSelectedSemanticMatchesPerUnit
Prompt token budget
retry=1
fallback=RRF primary_hit
```

## Graph

```text
maxObjectTerminals
maxPairShortestPathQueries
maxPathsPerPair
maxTotalPaths
hopLimit
maxNodes
maxEdges
timeout
```

Final Semantic Matches 可以多于最终 Graph Anchor 数，因为多个值可能映射到同一个 Property。

---

# 74. 推荐配置

```yaml
oag:
  semanticRetrieval:
    defaults:
      topK: 3
      similarityThreshold: 0.6

    anchor:
      topK: 10
      similarityThreshold: 0.6

    metadataEvidence:
      topK: 10
      similarityThreshold: 0.6

    instanceEvidence:
      topK: 5
      similarityThreshold: 0.6

  rrf:
    k: 60
    coarseTopKPerSemanticUnit: 20
    maxGlobalCandidates: 50
    maxMatchedItemsPerAnchorGroup: 5
    channelWeights:
      anchorExact: 1.5
      anchorBm25: 1.1
      anchorVector: 1.0
      metadataExact: 1.4
      metadataBm25: 1.0
      metadataVector: 1.0
      instanceExact: 1.2
      instanceBm25: 0.8
      instanceVector: 0.8

  rerank:
    enabled: true
    promptName: ontology_anchor_rerank
    temperature: 0.0
    maxCandidatesPerSemanticUnit: 20
    maxGlobalCandidates: 50
    maxSelectedPerSemanticUnit: 5
    maxSelectedSemanticMatchesPerUnit: 5
    retryCount: 1
    fallback: RRF

  graph:
    topologyCache: true

    strategy:
      default: auto

    minimal:
      algorithm: metric_closure_mst
      fallbackAlgorithm: legacy_greedy
      maxPathLength: 6
      pathCostMode: hop_count

    khop:
      algorithm: multi_source_bfs
      fallbackAlgorithm: pairwise_all_path
      hopLimit: 3
      maxPathsPerPair: 20
      maxTotalPaths: 200
      pairConcurrency: 8

    component:
      algorithm: dsu_cached
      legacyHopLimit: 10

    limits:
      maxNodes: 100
      maxEdges: 200
      timeoutMs: 3000
      includeInactive: false

  extension:
    includeObjectAliases: true
    includePropertyAliases: true
    enumMode: matched_only
    instanceMode: matched_only
    maxInstanceEvidencePerProperty: 10

  capabilityExtension:
    includeFunctionsDefault: false
    includeActionsDefault: false
```

所有数值都是起始值，必须通过真实数据评测调整。

---

# 75. 异常与降级

| 异常 | 降级 |
|---|---|
| 单个检索通道失败 | 其他通道继续 |
| Instance Evidence 超时 | 不阻塞 Anchor/Metadata |
| RRF 无候选 | unresolved unit |
| LLM 超时/JSON错误 | 重试1次 → RRF fallback |
| LLM 返回不存在 ID | 丢弃并记录 |
| parent_ID 缺失 | 调用现有 `addObjectTypeByProperty()` |
| enhanced minimal 失败 | fallback legacy_greedy |
| multi-source BFS 不可用 | fallback pairwise_all_path |
| DSU component cache 不可用 | fallback legacy hop=10 |
| K-hop 路径过多 | 截断，`truncated=true` |
| Final Anchor 不连通 | 返回 connected_groups |
| Instance Extension 过大 | matched/topN |

---

# 76. 可观测性

## Retrieval

```text
semantic_unit_count
channel_latency
channel_return_count
threshold_filtered_count
exact_hit_count
evidence_hit_count
target_type_count{type}
```

## Candidate Normalize / RRF

```text
before_dedup_count
after_anchor_group_dedup_count
rrf_anchor_group_count
matched_items_retained_count
matched_items_truncated_count
channel_contribution
```

## Rerank

```text
candidate_group_count
candidate_item_count
input_tokens
output_tokens
latency
rerank_status
selected_semantic_match_count
selected_target_type_count{type}
selected_anchor_count
no_match_count
```

## Graph Projection

```text
semantic_match_count
graph_anchor_count
match_to_anchor_projection_count
projection_error_count
```

## Graph

```text
strategy
algorithm
object_terminal_count
pair_count
path_query_count
path_count
node_count
edge_count
connected_groups
unconnected_anchor_ids
truncated
graph_cache_hit
```

可观测性必须能回答两个不同问题：

```text
1. 用户最终命中了什么语义项？
2. 这些语义项最终投影成了哪些图 Anchor？
```

---

# 77. 评测体系

## 77.1 Final Semantic Target

```text
SemanticTargetRecall@1/3/10
SemanticTargetPrecision@1/3/10
TargetTypeAccuracy
MatchedValueAccuracy
```

分别统计：

```text
ObjectTypeTargetAccuracy
PropertyTargetAccuracy
ObjectAliasTargetAccuracy
PropertyAliasTargetAccuracy
EnumValueTargetAccuracy
EnumAliasTargetAccuracy
InstanceValueTargetAccuracy
InstanceAliasTargetAccuracy
```

## 77.2 Anchor Context

```text
ObjectAnchorRecall@1/3/10
PropertyAnchorRecall@1/3/10
TargetToObjectTypeAccuracy
TargetToPropertyAccuracy
TargetToAnchorContextAccuracy
AnchorMRR
AnchorNDCG
```

## 77.3 Evidence / Canonical Value

```text
AliasHit@K
EnumResolveAccuracy
InstanceValueToPropertyAccuracy
EvidenceToAnchorAccuracy
CanonicalValueAccuracy
MatchedItemRetentionRate
```

## 77.4 多语言

```text
CrossLanguageRecall
MixedLanguageRecall
CrossLanguageTargetAccuracy
```

## 77.5 RRF

```text
RRFAnchorGroupRecall@10/20
RRFMRR
ChannelContributionRate
MatchedItemRetentionAfterRRF
```

RRF 的评测不仅看 Anchor Group 是否召回，还要看正确的 Alias/Enum/Instance Item 是否仍保留在该 Group 内。

## 77.6 LLM 精排

```text
SemanticMatchPrecision@K
SemanticMatchRecall@K
TargetTypeAccuracy
MatchedValueAccuracy
CanonicalValueAccuracy
AnchorContextAccuracy
WrongMatchDropRate
RequiredSemanticUnitCoverage
NoMatchAccuracy
P50/P95/P99
Tokens
```

## 77.7 子图

```text
AnchorConnectivityRate
SubgraphNodePrecision
SubgraphEdgePrecision
MinimalSubgraphSize
BridgeNodeCount
KhopExpansionSize
DisconnectedAnchorRate
ComponentAccuracy
GraphLatency
PathExplosionRate
```

## 77.8 Cypher

```text
CypherSemanticTargetAccuracy
CypherAnchorAccuracy
CypherRelationAccuracy
CypherCanonicalValueAccuracy
CypherExecutableRate
EndToEndQueryAccuracy
```

最终端到端准确率必须同时覆盖：

```text
是否找对具体语义项
+
是否携带正确 ObjectType / Property
+
是否生成正确关系与 canonical value
```

---

# 78. 子图算法专项对比测试

同一组 Query 同时执行：

```text
minimal legacy_greedy
minimal metric_closure_mst

khop pairwise_all_path
khop multi_source_bfs

component bounded_hop_10
component dsu_cached
```

比较：

```text
节点数
边数
Anchor连通率
是否缺失正确路径
NebulaGraph查询次数
返回Path数量
P95延迟
CPU
内存
结果稳定性
Cypher准确率
```

---

# 79. 迁移与灰度

## Phase 0：指标基线

记录当前：

```text
vector/es seed recall
minimal/khop/component latency
subgraph size
Cypher accuracy
```

## Phase 1：索引 V2

```text
Anchor
Metadata Evidence
Instance Evidence
```

双写，旧检索保持。

## Phase 2：Hybrid + RRF

影子执行：

```text
legacy getSeedIds
vs
hybrid/RRF
```

## Phase 3：LLM Rerank

灰度启用，保留 RRF fallback。

## Phase 4：Graph Enhanced

逐策略灰度：

```text
minimal enhanced
khop enhanced
component enhanced
```

## Phase 5：切换默认

数据证明：

```text
Recall提升
Cypher准确率提升
Latency可控
```

后再切换。

---

# 80. 与现有类的建议映射

```text
GraphSearchHelper
  └─ 保留总编排入口

LlmQueryInterpreter
  └─ 升级 Semantic Unit 输出

getSeedIds()
  └─ SearchDispatcher

HybridRecallHelper
  └─ 扩展多物理表、多通道召回

AnchorCandidateNormalizer（兼容类名）
  └─ 语义升级为 SemanticCandidateNormalizer
      ├─ 保留 Matched Item
      ├─ 补齐 ObjectType / Property Context
      └─ 形成 Anchor Group

WeightedRrfAggregator
  └─ 按 anchor_ID Group 融合，保留 matched_items

OntologyAnchorRanker（兼容类名）
  └─ 目标升级为 SemanticMatchRanker
      └─ 输出 Final Semantic Matches

新增：
  SemanticCandidateNormalizer
  WeightedRrfAggregator
  RerankContextBuilder
  SemanticMatchRanker
  GraphAnchorProjector
  GraphTopologyCache
  EnhancedSubgraphBuilder
  ExtensionAssembler
```

现有：

```text
computePairwiseShortestPaths
computePairwiseNumPaths
findAllPath
buildMstSubgraph
DisjointSet
addObjectTypeByProperty
```

全部保留，作为：

```text
legacy / fallback / reuse implementation
```

核心改造点不是推翻图代码，而是在图代码之前新增清晰的：

```text
Final Semantic Matches
        ↓
GraphAnchorProjector
        ↓
现有/增强 SubgraphBuilder
```

---

# 81. 图遍历方向与边类型策略

子图“连通性搜索”和最终 Cypher “关系方向”是两个不同问题，必须分开处理。

推荐建立 **Topology Projection**：

```text
用于连通性/最短路径的投影图
  ├─ ObjectType nodes
  ├─ defines_relation 等允许的对象关系
  └─ 可配置是否按无向方式参与 connectivity

最终输出图
  └─ 始终保留原始 sourceId / targetId / direction / relation metadata
```

Property：

```text
不作为跨对象桥接节点
通过 mandatory has_property 挂载
```

避免出现：

```text
ObjectA → PropertyA → ... → PropertyB → ObjectB
```

这种不符合本体业务关系语义的“属性桥接”。

推荐配置：

```yaml
graph:
  traversal:
    bridgeEdgeTypes:
      - defines_relation
    propertyEdgeType: has_property
    connectivityDirection: configurable
    preserveOriginalDirection: true
```

如果现网当前路径查询严格按有向边运行，灰度初期保持同样语义；只有经过用例验证后才允许使用 undirected connectivity projection。

---

# 82. RRF 与 LLM 的分组层级

RRF 建议首先按：

```text
semantic_unit_id
```

独立融合。

每个 Semantic Unit 内部流程：

```text
各 Channel Raw Hits
  ↓
保留具体 Matched Item
  ↓
按 channel + anchor_ID 形成 Anchor Groups
  ↓
Weighted RRF
  ↓
Top Anchor Groups + matched_items
```

原因：

```text
“站点”
“活跃告警”
“首次发生时间”
“正式用户”
```

是不同语义目标，不能在粗排阶段被一个高频 Anchor 的得分互相覆盖。

同时，RRF 不直接对 `evidence_ID` 做全局排名，因为：

```text
同一个 Property 拥有大量 Alias / Enum / Instance
```

会造成 Evidence 数量偏置。

因此：

```text
RRF 排 Anchor Group
但 Group 内保留具体 Matched Items
```

随后 LLM 精排输入所有 Semantic Unit 的 Group + Item 候选，执行两类判断：

```text
1. 跨单元 Anchor Context 一致性
2. 当前 Semantic Unit 最终命中的具体 Item 是什么
```

例如：

```text
“正式用户”
   ↓
Anchor Group = Subscriber.subClass
   ↓
Matched Item = ENUM_ALIAS: FORMAL
   ↓
LLM 最终选择 FORMAL 本身
   ↓
GraphAnchorProjector 仍提取 Subscriber.subClass
```

因此：

```text
RRF：局部高 Recall + Anchor Group 公平
LLM：具体 Semantic Item 精确选择 + 全局上下文一致性
GraphAnchorProjector：把最终 Match 转成构图 Anchor
```

候选裁剪推荐：

```text
RRF Top 10~20 Anchor Groups / Semantic Unit
每 Group 保留 top 3~5 Matched Items
全局 Anchor Group 去重后 30~50
LLM 每个 Unit 最多选择 3~5 Semantic Matches
```

`LLM rank_score` 是精排语义分，不与 Cosine `similarityThreshold` 共用阈值，也不应直接与 RRF score 相加。

---

# 83. 现有方法级增强映射

| 当前方法/结构 | 当前职责 | V5.3 增强 |
|---|---|---|
| `interpretQueryIntent()` | LLM 意图解析 | 输出 Semantic Units / hints |
| `getSeedIds()` | Vector/ES 获取 Seed | 多物理表、多通道 Dispatcher；输出 Raw Semantic Hits |
| `hybridRecall()` | 混合召回 | SemanticCandidateNormalizer + Weighted RRF |
| `AnchorCandidateNormalizer` | Evidence→Anchor | 保留 Evidence Item，并构造 Anchor Group + ObjectType/Property Context |
| `OntologyAnchorRanker` | Anchor 精排 | 升级为 Final Semantic Match 精排 |
| 新增 `GraphAnchorProjector` | 无 | Final Match → ObjectType/Property Graph Anchors |
| `addObjectTypeByProperty()` | Property 查父对象 | `parent_ID` 优先，GQL fallback |
| `loadAllEdges()` | 请求时加载拓扑 | `GraphTopologyCache` 按版本缓存 |
| `computePairwiseShortestPaths()` | minimal 最短路径 | 可复用为 Metric Closure 输入 |
| `buildMstSubgraph()` | Greedy path union | 保留 legacy；新增标准 MST approximation |
| `computePairwiseNumPaths()` | khop/component | 保留 legacy fallback |
| `findAllPath()` | 枚举 k-hop 路径 | 仅 legacy 模式使用并增加防爆限制 |
| `DisjointSet` | 子图连通性判断 | 扩展到全图 component cache |
| `collectFromPath()` | 收集 Path 节点/边 | 继续复用 |
| `addMissingEdgesFromObjects()` | 边补齐 | 继续复用并增加 edge-type 校验 |
| `removeEdgesWithMismatchedId()` | 清理异常边 | 继续作为输出校验 |

这样可以做到：

> **检索结果语义升级，但图算法最大程度复用当前稳定代码，不要求推倒重写。**

---

# 84. 设计中不应出现的误区

## 误区1

```text
把所有 Enum/Instance 拼进 Property Vector
```

错误：混淆 Anchor 语义，仍应保持独立 Evidence 索引。

## 误区2

```text
Enum/Instance 不能成为最终检索结果
```

错误。Enum Value/Alias、Instance Value/Alias 都可以是最终 `retrievalResults`；错误的是把它们直接当成 Core Graph 路径节点。

正确边界：

```text
Enum/Instance = Final Semantic Match
       ↓
GraphAnchorProjector
       ↓
Property + ObjectType = Graph Anchors
```

## 误区3

```text
RRF 对 evidence_ID 独立排名
```

错误：Evidence 多的属性会被人为抬高。RRF 应按 `anchor_ID` Group 聚合，同时保留 Group 内 `matched_items`。

## 误区4

```text
Evidence 映射到 Anchor 后即可丢弃 Evidence
```

错误。Evidence 本身可能就是用户最终要检索的同义词、枚举值或实例值。

## 误区5

```text
LLM 精排必须选一个
```

错误：一个语义单元可命中多个必要值，也可以 no_match。

## 误区6

```text
khop 当前就是 Multi-Source BFS
```

错误：当前是 Pairwise FIND ALL PATH。

## 误区7

```text
component 当前就是全连通分量
```

错误：当前是 10-hop 近似。

## 误区8

```text
Property 一定要把 ObjectType 放在向量开头
```

不推荐。Parent Context 应在 Metadata/Rerank 中使用。

## 误区9

```text
所有表用 topK=3 / threshold=0.6
```

不推荐。必须支持独立配置。

## 误区10

```text
seedNodes 就是最终检索结果
```

错误。`seedNodes` 是构图 Anchor Projection；完整最终检索结果必须看 `retrievalResults`。

---

# 85. 最终设计决策

1. **最终检索对象不再只有 ObjectType / Property；ObjectType、Property、Object/Property Alias、Enum Value/Alias、Instance Value/Alias 均可作为最终检索结果。**
2. **最终检索结果统一表达为 Matched Semantic Item + ObjectType / Property Anchor Context。**
3. **Alias / Enum / Instance 命中后必须保留其自身 `item_id/evidence_ID、target_type、matched_value、canonical_value`，不能映射 Anchor 后丢弃。**
4. **ObjectType / Object Alias 至少携带 ObjectType Context；Property / Property Alias / Enum / Instance 必须同时携带 Property + Parent ObjectType Context。**
5. **Anchor ID 直接使用本体元素全局唯一 ID，不 Hash。**
6. **Property 保存 parent_ID。**
7. **Alias / Enum / Instance 仍统一建模为 Evidence，但 Evidence 同时是一等检索目标。**
8. **Anchor / Metadata Evidence / Instance Evidence 物理隔离。**
9. **OAG 管元数据索引；DataSync 生产实例数据，V5.2 起通过 Bulk Import 由 OAG 统一完成 Instance Evidence 索引构建。**
10. **Instance 只索引符合语义规则的 DISTINCT Value；INSTANCE_ALIAS 保留真实业务支持。**
11. **高基数自由文本进入独立 RAG，不污染本体实例 Evidence。**
12. **同一 Anchor 的多语言描述默认放入一个 Vector。**
13. **Property Vector 默认不以 ObjectType 开头。**
14. **Enum/Instance Vector 坚持 Value First。**
15. **未知字符串无需预分类，统一走 Anchor / Metadata / Instance 多路检索。**
16. **Exact 不受 Dense similarityThreshold 限制。**
17. **每张物理表独立 topK / similarityThreshold。**
18. **CandidateNormalizer 必须先保留具体 Matched Item，再补齐 Anchor Context。**
19. **RRF Key 仍为 anchor_ID Group，而不是 evidence_ID，防止 Evidence 数量偏置。**
20. **同一通道先按 Anchor Group 去重，但 Group 内保留 topN Matched Items。**
21. **不需要 Anchor / Metadata / Instance 两级 RRF；所有 Channel 一次 Weighted RRF 即可。**
22. **LLM 使用原始问题 + Anchor Group + Matched Items + 多维上下文精排。**
23. **LLM 精排输出 Final Semantic Matches，允许 0/1/N，并支持 RRF primary-hit 降级。**
24. **新增 GraphAnchorProjector，将 Final Semantic Matches 投影为 ObjectType / Property Graph Anchors。**
25. **Enum / Alias / Instance 可以是最终 retrievalResults，但不直接参与 Core Graph 图算法。**
26. **Property 构图前优先通过 parent_ID 补 Parent ObjectType。**
27. **当前 minimal 是 greedy path union，应保留兼容并增强为 Metric Closure MST Approximation。**
28. **当前 khop 是 pairwise FIND ALL PATH，应增强为真正 Multi-Source BFS。**
29. **当前 component 是 hop=10 近似，应增强为 DSU/BFS 真 Connected Component。**
30. **loadAllEdges 相关拓扑建议按 ontology version 缓存。**
31. **图算法只处理真实本体拓扑。**
32. **retrievalResults 表达最终命中；semanticExtensions 只表达额外语义上下文，两者分离。**
33. **Function / Action 按 includeFlags 在 Core Graph 后扩展。**
34. **所有 enhanced 算法必须有 legacy fallback 和灰度评测。**
35. **最终优化目标是 Semantic Target + ObjectType/Property Context + Relation + Canonical Value + Cypher 端到端正确性。**

---

# 86. 一句话总结

> **OAG 最终应成为一个“Semantic Target Resolver + Ontology Anchor Projector + Subgraph Constructor”：先利用 Anchor、同义词、Enum、Instance 等多源索引，通过 Exact/BM25/Dense 多路召回、Matched Item 保留、按 anchor_ID 的 Weighted RRF 和 LLM 精排，准确返回用户真正命中的 ObjectType、Property、Alias、Enum Value/Alias 或 Instance Value/Alias 本身，并为每个结果携带确定性的 ObjectType / Property Context；随后通过 GraphAnchorProjector 只抽取 ObjectType / Property 进入 minimal/khop/component 子图算法，再将关系、扩展语义和 canonical value 一并提供给下游 Cypher，从而同时保证“值检索准确”和“本体拓扑构建正确”。**

---

# 87. OAG 实例数据 Bulk Import 总体设计

> 本节是对第 6、7、16、71 节中“DataSync 直接构建/写入 Instance Evidence 索引”描述的职责边界升级。历史内容保留用于说明方案演进；**从 V5.2 起，以本节定义为准：DataSync 是实例数据生产方，OAG 是统一索引构建、向量化、OpenSearch/GaussVector 写入和检索引擎。**

新的职责边界：

```text
DataSync
  负责：数据源访问 / DISTINCT / 基础标准化 / 实例值与本体 Property 映射 / 文件生成
  不负责：Embedding / Vector表结构 / ANN索引 / OpenSearch Mapping / 双写一致性

OAG
  负责：导入任务管理 / 映射校验 / Evidence构造 / 向量化 / OpenSearch全文索引
       / GaussVector写入与ANN构建 / 版本发布 / 在线检索
```

核心原则：

> **DataSync 交付“业务数据 + 本体映射”，OAG 负责把它转换为可检索的 Instance Evidence。**

不建议大批量数据通过同步 JSON Body 直接调用 OAG 入库。大规模实例索引使用：

```text
File / Shared Storage
或
MinIO Object Storage
```

作为数据面，HTTP API 只承担控制面：创建任务、提交 Manifest、查询状态、重试、取消和获取错误报告。

---

# 88. Bulk Import 总体架构

```mermaid
flowchart LR
    DS[DataSync] --> SRC[(业务数据源)]
    SRC --> DS

    DS --> DIST[DISTINCT / Normalize / Alias整理]
    DIST --> PKG[生成 Import Package<br/>Manifest + Data Files]

    PKG -->|方式1| FS[(共享文件/临时文件区)]
    PKG -->|方式2 推荐| MINIO[(MinIO)]

    DS --> API[OAG Import API<br/>创建异步任务]
    FS --> IMP[OAG BulkImportService]
    MINIO --> IMP
    API --> IMP

    IMP --> VAL[Manifest / Mapping / Checksum校验]
    VAL --> PARSE[File Reader / Chunker]
    PARSE --> NORM[Evidence Normalize / Dedup]
    NORM --> EMB[Embedding Worker]

    EMB --> VW[GaussVector Bulk Writer]
    EMB --> OW[OpenSearch Bulk Writer]

    VW --> VIDX[ANN Index Build / Verify]
    OW --> OIDX[Full-text Index Verify]

    VIDX --> PUB[Version Publisher]
    OIDX --> PUB
    PUB --> CAT[OAG Index Catalog<br/>active_version]

    CAT --> SEARCH[OAG Retrieval Engine]
```

设计上严格分为：

```text
控制面：REST API + Import Job Metadata
数据面：File / MinIO + Streaming Reader
计算面：Normalize + Embedding + Bulk Writer
存储面：GaussVector + OpenSearch
发布面：Version/Generation Switch
```

---

# 89. 为什么采用 File / MinIO 中转

不推荐：

```text
DataSync
  ↓
每100/1000条同步HTTP JSON
  ↓
OAG实时Embedding并写库
```

原因：

1. 大量 HTTP 请求放大序列化、网络和连接开销；
2. DataSync 与 OAG 强耦合，OAG短时限流会反压数据同步链路；
3. Embedding、GaussVector、OpenSearch 任一阶段抖动都会导致同步调用超时；
4. 难以做到断点续传和批次级重试；
5. 重试容易造成重复数据；
6. 无法方便保存原始输入用于失败复盘；
7. 大批量全量重建时需要数十分钟甚至更长，天然不适合同步接口。

推荐：

```text
DataSync 先生成不可变批量文件
      ↓
OAG 创建异步 Import Job
      ↓
OAG 自己按可承受速率消费
```

MinIO 模式优先级最高，原因是：

```text
支持大文件
天然跨Pod/跨节点
易于校验checksum
易保留失败现场
支持生命周期清理
DataSync/OAG无需共享本地磁盘
```

共享文件模式主要作为：

```text
单机/边缘部署
无MinIO环境
测试环境
兼容模式
```

---

# 90. 导入模式

支持两类主模式：

## 90.1 FULL_REPLACE

表示 DataSync 提交某个导入 Scope 的完整实例语义快照。

```text
旧 active generation
       ↓
创建 staging generation
       ↓
全量导入
       ↓
构建 ANN / OpenSearch Index
       ↓
一致性校验
       ↓
原子发布 active generation
       ↓
异步清理旧 generation
```

适合：

```text
首次建库
Embedding模型升级后的重建
大规模数据重新同步
实例语义索引整体修复
```

## 90.2 INCREMENTAL

每条记录携带：

```text
UPSERT
DELETE
```

按照稳定 `evidence_ID` 幂等修改当前 active generation。

适合：

```text
日常增量同步
新增枚举式实例值
实例 Alias 调整
数据源删除值
```

FULL_REPLACE 推荐支持 Scope：

```text
ONTOLOGY
OBJECT_TYPE
PROPERTY_SET
PROPERTY
```

大规模场景优先 Property/PropertySet 分区，可减少一次全量重建范围。

---

# 91. Import Package 结构

一个 Import Package 由：

```text
manifest.json
+
N 个 data file
```

组成。

推荐目录：

```text
/oag-import/{ontology_id}/{data_version}/{job_request_id}/
  manifest.json
  property_001/part-00000.parquet
  property_001/part-00001.parquet
  property_002/part-00000.parquet
  ...
```

推荐文件格式：

| 格式 | 建议 | 场景 |
|---|---|---|
| Parquet + Snappy/ZSTD | **首选** | 千万/亿级、批量、高吞吐 |
| NDJSON + gzip | 支持 | 兼容、调试、流式生成 |
| CSV | 不推荐作为主格式 | Alias数组、转义、多语言复杂 |

推荐一个文件只承载一个 Property Anchor 的实例 Evidence；这样：

```text
anchor_ID / parent_ID / property mapping
```

可以放在 Manifest 中，不必在每行重复，能明显减少数据体积。

若业务必须混合多个 Property，可启用：

```text
mappingMode = PER_RECORD
```

由每条记录携带 Property ID，但不是默认方案。

---

# 92. Manifest 设计

示例：

```json
{
  "schemaVersion": "1.0",
  "ontologyId": "dtmi.ontology.xxx.1",
  "dataVersion": "20260811-001",
  "requestId": "datasync-20260811-000001",
  "importMode": "FULL_REPLACE",
  "scope": "PROPERTY_SET",
  "generatedAt": "2026-08-11T08:20:00+08:00",
  "sourceSystem": "datasync",
  "files": [
    {
      "uri": "minio://oag-import/dtmi.ontology.xxx.1/20260811-001/subclass/part-00000.parquet",
      "format": "PARQUET",
      "compression": "SNAPPY",
      "sizeBytes": 268435456,
      "rowCount": 1200000,
      "sha256": "...",
      "mapping": {
        "objectTypeId": "subscriber-object-id",
        "objectTypeName": "Subscriber",
        "propertyId": "subClass-property-id",
        "propertyName": "subClass",
        "isSemantic": true,
        "valueColumn": "value",
        "evidenceTypeColumn": "evidence_type",
        "canonicalValueColumn": "canonical_value",
        "aliasesColumn": "aliases",
        "sourceKeyColumn": "source_key",
        "operationColumn": "op"
      }
    }
  ]
}
```

Manifest 是导入协议的一部分，必须做版本化：

```text
schemaVersion
```

以后增加字段时保持向后兼容。

---

# 93. Data File Record 设计

Property 固定映射模式下，每行只需要业务 Evidence 数据。

## INSTANCE_VALUE

```json
{
  "source_key": "VIP",
  "evidence_type": "INSTANCE_VALUE",
  "value": "VIP",
  "canonical_value": "VIP",
  "aliases": ["高价值客户", "重要客户"],
  "op": "UPSERT"
}
```

## INSTANCE_ALIAS

真实业务存在实例值同义词时，可以显式传入 Alias Evidence：

```json
{
  "source_key": "VIP::高价值客户",
  "evidence_type": "INSTANCE_ALIAS",
  "value": "高价值客户",
  "canonical_value": "VIP",
  "aliases": [],
  "op": "UPSERT"
}
```

OAG 内部转换：

```text
Manifest.propertyId
       +
Record.evidence_type/value/canonical_value
       ↓
Evidence Builder
       ↓
anchor_ID / parent_ID / evidence_ID / normalized_value / content
```

DataSync **不发送**：

```text
vector
embedding model version
OpenSearch document
GaussVector physical table name
ANN index parameter
```

这些全部属于 OAG 内部实现。

---

# 94. evidence_ID 生成与幂等

沿用 V5.0 既有规则：

```text
{anchor_ID}::{evidence_type}::{source_key}
```

若 DataSync 已提供全局稳定 ID，可直接作为 `source_key`。

幂等键：

```text
ontology_id
+
data_version / active_generation
+
evidence_ID
```

同一个 Job/Chunk 重试：

```text
UPSERT 同 evidence_ID
 → 覆盖/无变化
 → 不产生重复记录
```

DELETE：

```text
按 evidence_ID 删除 GaussVector + OpenSearch
```

如果 `content_hash` 未变化：

```text
不重新调用 Embedding
```

---

# 95. OAG Import API

接口采用异步 Job 模型。

## 95.1 创建导入任务

```http
POST /v1/ontologies/{ontologyId}/instance-evidence/import-jobs
Content-Type: application/json
```

MinIO 请求：

```json
{
  "requestId": "datasync-20260811-000001",
  "dataVersion": "20260811-001",
  "importMode": "FULL_REPLACE",
  "transport": {
    "type": "MINIO",
    "manifestUri": "minio://oag-import/dtmi.ontology.xxx.1/20260811-001/manifest.json",
    "connectionRef": "oag-shared-minio"
  },
  "validateOnly": false
}
```

返回：

```http
HTTP/1.1 202 Accepted
```

```json
{
  "jobId": "imp-01K2...",
  "requestId": "datasync-20260811-000001",
  "status": "SUBMITTED",
  "ontologyId": "dtmi.ontology.xxx.1",
  "dataVersion": "20260811-001"
}
```

`requestId` 必须幂等：同一个 DataSync requestId 重复提交时返回原 Job，而不是重新执行。

## 95.2 查询任务

```http
GET /v1/ontologies/{ontologyId}/instance-evidence/import-jobs/{jobId}
```

返回：

```json
{
  "jobId": "imp-01K2...",
  "status": "RUNNING",
  "stage": "EMBEDDING",
  "progress": 0.63,
  "statistics": {
    "fileCount": 32,
    "totalRows": 15000000,
    "parsedRows": 10000000,
    "deduplicatedRows": 9500000,
    "embeddedRows": 9000000,
    "vectorWrittenRows": 8700000,
    "openSearchWrittenRows": 8700000,
    "failedRows": 12
  },
  "startedAt": "...",
  "updatedAt": "..."
}
```

## 95.3 重试

```http
POST /v1/ontologies/{ontologyId}/instance-evidence/import-jobs/{jobId}:retry
```

仅重跑：

```text
FAILED / RETRYABLE chunks
```

不从文件头全部重来。

## 95.4 取消

```http
POST /v1/ontologies/{ontologyId}/instance-evidence/import-jobs/{jobId}:cancel
```

取消后：

```text
停止领取新 Chunk
正在执行的 Chunk 完成或超时退出
staging generation 不发布
```

## 95.5 错误报告

```http
GET /v1/ontologies/{ontologyId}/instance-evidence/import-jobs/{jobId}/errors
```

大错误报告建议返回：

```json
{
  "errorReportUri": "minio://oag-import-errors/.../errors.parquet"
}
```

避免将百万级错误行直接塞进 HTTP Response。

---

# 96. File 模式接口

File 模式支持两种部署形态。

## 96.1 Shared Path

DataSync 与 OAG 能访问同一共享文件系统：

```json
{
  "transport": {
    "type": "FILE",
    "manifestUri": "file:///oag-import/xxx/manifest.json"
  }
}
```

OAG 必须限制允许的根目录：

```text
/oag-import
```

禁止任意文件系统路径访问。

## 96.2 OAG Staging Upload

无共享盘但文件不太大时，可先上传 OAG staging：

```http
POST /v1/ontologies/{ontologyId}/instance-evidence/staging-files
Content-Type: multipart/form-data
```

返回内部：

```text
staging://{uploadId}/manifest.json
```

再使用 Import Job API 创建任务。

对于超大文件仍推荐 DataSync 直接上传 MinIO，避免 OAG API Pod 成为文件转发瓶颈。

---

# 97. MinIO 模式设计

推荐生产默认模式：

```text
DataSync → MinIO → OAG
```

关键约束：

1. DataSync 上传完成后才提交 Job；
2. Manifest 和 Data File 在 Job 生命周期中视为 immutable；
3. OAG 校验 `size + ETag/sha256`；
4. 文件变化则拒绝继续断点任务；
5. OAG 使用预配置 `connectionRef` 获取凭据；
6. API 请求中禁止传长期 `accessKey/secretKey`；
7. OAG 流式读取 Object，不要求完整下载到本地；
8. import prefix 配置生命周期，成功后延时清理。

MinIO Object Key 推荐包含：

```text
ontology_id
data_version
request_id
property_id
part_number
```

便于：

```text
问题定位
生命周期清理
权限隔离
任务重跑
```

---

# 98. Import Job 状态机

```mermaid
stateDiagram-v2
    [*] --> SUBMITTED
    SUBMITTED --> VALIDATING
    VALIDATING --> READY
    VALIDATING --> FAILED
    READY --> RUNNING
    RUNNING --> BUILDING_INDEX
    RUNNING --> FAILED
    BUILDING_INDEX --> VERIFYING
    BUILDING_INDEX --> FAILED
    VERIFYING --> PUBLISHING
    VERIFYING --> FAILED
    PUBLISHING --> SUCCEEDED
    PUBLISHING --> FAILED
    RUNNING --> CANCELLING
    CANCELLING --> CANCELLED
    FAILED --> RETRYING
    RETRYING --> RUNNING
```

状态含义：

| 状态 | 含义 |
|---|---|
| SUBMITTED | API已接收 |
| VALIDATING | Manifest、文件、本体映射校验 |
| READY | 可以开始消费 |
| RUNNING | Parse/Normalize/Embedding/Bulk Write |
| BUILDING_INDEX | 构建/刷新ANN和全文索引 |
| VERIFYING | 双存储数量/checksum抽检 |
| PUBLISHING | 发布新的 active generation |
| SUCCEEDED | 成功 |
| FAILED | 失败，可判断是否可重试 |
| CANCELLED | 用户取消，未发布 |

---

# 99. OAG 内部处理流水线

```text
ImportJobService
   ↓
ManifestValidator
   ↓
OntologyMappingValidator
   ↓
ObjectReader(File/MinIO)
   ↓
ChunkPlanner
   ↓
RecordParser
   ↓
EvidenceNormalizer
   ↓
Deduplicator
   ↓
ContentBuilder
   ↓
EmbeddingBatcher
   ↓
┌──────────────────────┐
│                      │
GaussVectorBulkWriter  OpenSearchBulkWriter
│                      │
└──────────┬───────────┘
           ↓
ChunkCommitCoordinator
           ↓
IndexBuilder / Verifier
           ↓
GenerationPublisher
```

OAG 复用前文已有：

```text
normalized_value
content_hash
evidence_ID
Value First vector content
BGE-M3 1024 dimension
```

DataSync 不复制这些规则，避免两套实现长期漂移。

---

# 100. Chunk 与断点续传

导入不能以整个文件作为一个事务单元。

推荐：

```text
File
  ↓
Chunk
  ↓
Embedding Batch
  ↓
Storage Bulk Batch
```

Parquet：

```text
优先按 row group 切 Chunk
```

NDJSON：

```text
按 byte offset + record boundary 切 Chunk
```

Chunk ID 推荐：

```text
sha256(file_checksum + start_offset/row_group + end_offset)
```

每个 Chunk 持久化：

```text
chunk_id
file_uri
range
input_count
output_count
embedding_count
vector_write_count
os_write_count
retry_count
status
last_error
```

Worker 崩溃后：

```text
重新领取未 COMMITTED Chunk
```

已 COMMITTED Chunk 不重复执行；即使重复执行，稳定 evidence_ID 仍保证幂等。

---

# 101. GaussVector 与 OpenSearch 双写一致性

OAG 不是使用分布式事务强行绑定两种存储，而采用：

> **Chunk 级幂等 + 状态协调 + 最终一致 + 发布前校验。**

流程：

```text
Chunk transformed
  ↓
GaussVector UPSERT
  ↓ success
OpenSearch BULK UPSERT
  ↓ success
Chunk = COMMITTED
```

如果：

```text
OpenSearch成功
GaussVector失败
```

Chunk 状态仍为 FAILED/RETRYABLE，重试时按照 `evidence_ID` 幂等补写 GaussVector。

反之同理。

FULL_REPLACE 在所有 Chunk COMMITTED 前：

```text
禁止将 staging generation 暴露给在线查询
```

只有两边均通过 Verify 后才能 PUBLISH。

---

# 102. Full Import 的版本化发布

为了避免：

```text
全量导入一半时在线查询看到新旧混合数据
```

FULL_REPLACE 必须采用 Generation 模型。

逻辑：

```text
ontology_id
  ↓
instance_evidence_generation = g123
```

OpenSearch：

```text
建立 versioned physical index
完成后切 Alias
```

GaussVector：

如果底层没有原生 Alias，OAG 维护：

```text
IndexCatalog:
ontology_id + logical_index
  → active physical table/generation
```

检索永远通过 OAG 的 IndexCatalog 找 active generation，不允许调用方直接绑定物理表名。

发布操作：

```text
DB metadata transaction:
active_generation g122 → g123
```

旧 generation 延迟删除，保留短期 rollback 能力。

---

# 103. Incremental Import 一致性

INCREMENTAL 不创建完整新 generation，而对 active generation 做幂等变更。

每个 Record：

```text
UPSERT
DELETE
```

建议 DataSync 提供单调递增：

```text
dataVersion
```

OAG 对同一 Property 记录：

```text
last_applied_data_version
```

拒绝明显过旧的批次覆盖新数据。

对于乱序增量，需使用：

```text
source_update_version / event_time
```

做业务级版本判定。

---

# 104. 本体映射校验

OAG 收到 DataSync 的 Mapping 后必须基于当前本体元数据验证：

```text
ontologyId 存在
ObjectType ID 存在
Property ID 存在
Property.parent_ID == ObjectType ID
Property.is_semantic == true
Property未删除/未失效
Alias/Instance Alias映射到合法canonical value
```

不允许 DataSync 传一个不存在的 `anchor_ID` 后由 OAG 静默建索引。

Mapping 错误属于：

```text
JOB_FATAL
```

应在 VALIDATING 阶段直接失败，不进入大规模 Embedding。

---

# 105. 行级错误与隔离

错误分两类。

## 105.1 Job Fatal

```text
Manifest不可解析
Checksum不一致
Ontology不存在
Property映射非法
Embedding模型不可用
目标索引创建失败
```

直接停止 Job。

## 105.2 Row Rejectable

```text
空Value
Value超长
非法UTF-8
Alias格式错误
不支持的evidence_type
单条标准化失败
```

可写入：

```text
Reject / DLQ File
```

推荐阈值：

```text
rejectRatio <= configured threshold
```

低于阈值允许任务继续并最终：

```text
SUCCEEDED_WITH_WARNINGS
```

超过阈值则 FAILED。

---

# 106. 大数据量性能设计

## 106.1 DataSync 侧

尽量提前：

```text
DISTINCT
过滤NULL/空串
基础Normalize
按Property分区
生成Parquet
```

避免把5000万业务明细行传给 OAG，再让 OAG 做 DISTINCT。

OAG仍执行轻量二次去重作为防御。

## 106.2 文件大小

建议起始值：

```text
单文件 128MB～512MB
```

避免：

```text
数十GB单文件 → 重试粒度过大
数百万小文件 → 对象存储/List开销过大
```

## 106.3 Pipeline 并发隔离

分别配置：

```text
readerConcurrency
normalizeConcurrency
embeddingConcurrency
vectorWriterConcurrency
openSearchWriterConcurrency
```

中间使用有界 Queue：

```text
Reader快于Embedding
 → Queue满
 → Reader反压
```

禁止无限堆积内存。

## 106.4 Embedding Batch

建议按模型吞吐评测配置，例如：

```text
64～256 records / batch
```

不是协议固定值。

## 106.5 OpenSearch Bulk

建议同时以：

```text
doc count
bulk bytes
```

控制，例如起始：

```text
1000～5000 docs
或 5～15MB / bulk
```

FULL_REPLACE 的 staging index 可降低 refresh 频率，批量完成后再恢复并 refresh。

## 106.6 GaussVector Bulk

优先批量写入，再在 FULL_REPLACE 数据加载完成后统一：

```text
Build/Rebuild ANN Index
```

避免每写一条记录都维护高成本 ANN 结构。

大规模 Instance Evidence 根据前文规模策略选择：

```text
GsIVFFLAT
或
GsDiskANN
```

---

# 107. 在线检索与导入资源隔离

OAG 同时承担：

```text
Online Retrieval
Bulk Indexing
```

必须保证：

> **在线查询优先级高于离线导入。**

推荐：

```text
独立线程池
独立连接池
Bulk QPS/并发限额
Embedding worker限额
OpenSearch Bulk限速
GaussVector写入限速
```

系统资源达到阈值时：

```text
暂停领取新的Import Chunk
```

而不是让在线检索 P95/P99 被批量导入拖垮。

同一 ontology：

```text
FULL_REPLACE 默认最多1个运行任务
```

避免两个 Generation 相互竞争。

---

# 108. MinIO / File 安全与可靠性边界

虽然本方案重点是性能和可靠性，接口仍需满足基础边界：

```text
connectionRef引用预配置凭据
禁止请求体明文secret
File模式限制根目录
MinIO bucket/prefix白名单
对象checksum校验
文件不可变校验
最大文件/任务配额
Manifest schema校验
```

Import Job 只允许访问：

```text
该任务 Manifest 明确声明的对象
```

不能把 OAG 变成通用 Object Storage Reader。

---

# 109. Import Metadata 表

建议 OAG 持久化四类任务元数据。

## import_job

```text
job_id
request_id
ontology_id
data_version
import_mode
scope
transport_type
manifest_uri
status
stage
active_generation_before
staging_generation
statistics
created_at
started_at
finished_at
last_error
```

## import_file

```text
job_id
file_id
uri
checksum
size
row_count
property_id
status
```

## import_chunk

```text
job_id
chunk_id
file_id
range
status
input_count
output_count
vector_write_count
os_write_count
retry_count
last_error
```

## import_generation

```text
ontology_id
generation_id
vector_physical_index
os_physical_index
status
created_by_job
created_at
published_at
```

这些状态是断点续传、重试、审计和版本发布的基础。

---

# 110. 可观测性

新增 Import 指标：

```text
import_job_count{status}
import_running_jobs
import_files_total
import_bytes_total
import_rows_total
import_rows_per_second
import_parse_latency
import_embedding_latency
import_embedding_batch_size
import_vector_write_latency
import_os_bulk_latency
import_chunk_retry_count
import_rejected_rows
import_checkpoint_lag
import_generation_build_latency
import_publish_latency
```

必须关联：

```text
job_id
ontology_id
data_version
property_id
```

日志中禁止打印完整海量业务值，只记录：

```text
source_key / evidence_ID / truncated value / error code
```

---

# 111. 错误码建议

| 错误码 | 含义 | 是否可重试 |
|---|---|---|
| IMPORT_MANIFEST_INVALID | Manifest格式错误 | 否 |
| IMPORT_SOURCE_NOT_FOUND | File/Object不存在 | 是/视情况 |
| IMPORT_SOURCE_CHANGED | ETag/checksum变化 | 否，需重新提交 |
| IMPORT_MAPPING_INVALID | 本体映射非法 | 否 |
| IMPORT_ONTOLOGY_VERSION_CONFLICT | 本体版本冲突 | 否/重新生成包 |
| IMPORT_EMBEDDING_UNAVAILABLE | Embedding不可用 | 是 |
| IMPORT_VECTOR_WRITE_FAILED | GaussVector写失败 | 是 |
| IMPORT_OS_BULK_FAILED | OpenSearch Bulk失败 | 是 |
| IMPORT_INDEX_BUILD_FAILED | ANN/全文索引构建失败 | 是 |
| IMPORT_VERIFY_FAILED | 双存储校验失败 | 是 |
| IMPORT_PUBLISH_FAILED | Generation发布失败 | 是 |
| IMPORT_REJECT_RATIO_EXCEEDED | 行错误比例超阈值 | 否/修数据 |
| IMPORT_CANCELLED | 用户取消 | 否 |

错误响应同时提供：

```text
面向调用方的message
面向开发定位的detail/errorStage/jobId/chunkId
```

---

# 112. 配置建议

```yaml
oag:
  import:
    enabled: true
    preferredTransport: minio

    job:
      maxRunningPerOntology: 1
      retryCount: 3
      retryBackoffMs: 1000

    file:
      allowedRoots:
        - /oag-import
      targetFileSizeMB: 256

    minio:
      allowedConnectionRefs:
        - oag-shared-minio
      allowedBuckets:
        - oag-import
      streamRead: true

    chunk:
      targetRows: 50000
      checkpointEnabled: true

    pipeline:
      readerConcurrency: 4
      normalizeConcurrency: 4
      embeddingConcurrency: 4
      vectorWriterConcurrency: 2
      openSearchWriterConcurrency: 2
      queueCapacity: 16

    embedding:
      batchSize: 128

    openSearch:
      bulkDocs: 2000
      bulkMaxBytesMB: 10

    reliability:
      verifyChecksum: true
      rejectRatioThreshold: 0.001
      retainFailedPackageDays: 7
      retainOldGenerationHours: 24
```

所有并发和批量数值均为工程起始值，最终通过：

```text
Embedding TPS
GaussVector写吞吐
OpenSearch Bulk吞吐
OAG CPU/内存
在线检索P95/P99
```

联合压测确定。

---

# 113. DataSync → OAG 完整时序

```mermaid
sequenceDiagram
    participant DS as DataSync
    participant M as MinIO/File
    participant API as OAG Import API
    participant J as ImportJobService
    participant E as Embedding
    participant GV as GaussVector
    participant OS as OpenSearch
    participant C as IndexCatalog

    DS->>DS: 读取is_semantic Property + 数据源
    DS->>DS: DISTINCT / Normalize / Alias整理
    DS->>M: 写Manifest + Parquet分片
    M-->>DS: URI + checksum

    DS->>API: POST import-job(manifestUri,dataVersion)
    API->>J: 创建幂等Job
    API-->>DS: 202 + jobId

    J->>M: 校验Manifest/Checksum
    J->>J: 校验Ontology/Property Mapping

    loop Chunk
        J->>M: Stream读取Chunk
        J->>J: Normalize/Dedup/Build Evidence
        J->>E: Batch Embedding
        E-->>J: vectors
        par 双写
            J->>GV: Bulk UPSERT
            J->>OS: Bulk API
        end
        J->>J: Chunk Commit/Checkpoint
    end

    J->>GV: Build/Verify ANN
    J->>OS: Refresh/Verify Index
    J->>C: Publish generation
    C-->>J: active_version switched

    DS->>API: GET job status
    API-->>DS: SUCCEEDED + statistics
```

---

# 114. 与现有索引设计的衔接

本导入模块不改变 Instance Evidence 的物理隔离、Value First 和 Property Mapping 设计，只改变“谁负责真正构建索引”的职责边界，并在 V5.3 明确：

> **Instance Evidence 不仅用于反向发现 Property Anchor，INSTANCE_VALUE / INSTANCE_ALIAS 本身也是最终检索目标。**

保持不变：

```text
INSTANCE_VALUE
INSTANCE_ALIAS
anchor_ID = Property ID
parent_ID = ObjectType ID
Value First
Property Context Last
Instance Evidence 与 Metadata Evidence 物理隔离
```

语义更新为：

```text
旧理解：
Evidence → Anchor → Final Anchor

V5.3：
Evidence → 保留 Final Semantic Item
        + 确定性 Anchor Context
        ↓
GraphAnchorProjector
        ↓
Property / ObjectType Graph Anchors
```

因此 DataSync 导入的：

```text
value
evidence_type
canonical_value
aliases
source_key
Property Mapping
```

都必须被 OAG 保留到检索结果模型中，而不是仅服务于向量化后丢弃。

职责仍然是：

```text
旧描述：
DataSync → Instance Evidence Builder → GaussVector/OpenSearch

V5.2 / V5.3：
DataSync → Import Package → OAG BulkImportService
                         → Instance Evidence Builder
                         → Embedding
                         → GaussVector/OpenSearch
```

DataSync 不再依赖：

```text
Embedding SDK
GaussVector Client
OpenSearch Client
具体Index Mapping
ANN索引参数
```

所有索引实现统一封装在 OAG 内部；所有 Evidence→ObjectType/Property Context 映射也由 OAG 在检索结果中统一输出。

---

# 115. 导入接口最终设计决策

1. **OAG 是 Instance Evidence 索引的唯一构建和检索引擎。**
2. **DataSync 是实例数据生产方，负责数据源读取、DISTINCT、基础标准化和本体映射。**
3. **DataSync 不生成 vector，也不直接写 GaussVector/OpenSearch。**
4. **大数据量导入采用异步 Job，不使用同步海量 JSON API。**
5. **生产环境优先 MinIO，中小部署支持受控 File/Shared Path。**
6. **Data Package = Manifest + 不可变数据分片。**
7. **Parquet 是大规模场景首选格式。**
8. **推荐按 Property 分区/分片，Mapping 放 Manifest，减少每行重复字段。**
9. **OAG 必须校验 Property/Parent ObjectType/is_semantic 映射。**
10. **OAG 复用统一 Evidence Builder、Normalize、Embedding Content 规则。**
11. **INSTANCE_VALUE 与 INSTANCE_ALIAS 均通过同一导入协议支持，并且两者本身均可作为最终 retrievalResults 返回。**
12. **evidence_ID 稳定生成，Chunk 重试必须幂等。**
13. **Parquet RowGroup / NDJSON Offset 作为断点 Checkpoint。**
14. **GaussVector/OpenSearch 使用 Chunk 级双写协调和最终一致。**
15. **FULL_REPLACE 使用 staging generation，全部成功后原子发布。**
16. **INCREMENTAL 使用 UPSERT/DELETE + dataVersion 防止旧数据覆盖。**
17. **OAG 在线查询资源优先于 Bulk Import，必须独立线程池和限流。**
18. **失败行进入 Reject/DLQ File，Job Fatal 与 Row Rejectable 分级处理。**
19. **任务、文件、Chunk、Generation 状态全部持久化，支持重启续传。**
20. **最终目标是在不牺牲在线检索 SLA 的前提下，支持千万/亿级实例 Evidence 稳定导入，并确保命中的实例值/实例同义词可携带 Property + ObjectType Context 直接作为最终检索结果。**

---

# 116. 更新后的索引构建职责一句话总结

> **DataSync 负责把“底层真实实例数据”加工成带本体 Property 映射的批量 Import Package，并通过 File/MinIO 交付给 OAG；OAG 作为唯一索引引擎，以异步、可断点、可重试、可版本发布的 Bulk Import Pipeline 统一完成 Evidence 构造、Embedding、GaussVector 与 OpenSearch 双写和索引发布，并在检索时将命中的 INSTANCE_VALUE / INSTANCE_ALIAS 本身连同 Property + ObjectType Context 返回，从而把大规模数据同步链路与在线本体检索能力稳定解耦。**