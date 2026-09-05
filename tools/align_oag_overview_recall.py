from pathlib import Path

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
WORKFLOW = Path('.github/workflows/one-shot-oag-overview-recall.yml')
SCRIPT = Path('tools/align_oag_overview_recall.py')

text = DOC.read_text(encoding='utf-8')

text = text.replace(
    '- 使用一次 Weighted RRF 融合 6 路检索结果；',
    '- 按 Semantic Unit 类型分别执行 Weighted RRF：ObjectType/Property 使用本体定义 2 路融合，Value 使用 Enum/Instance 4 路融合；',
    1,
)

old_overview = '''```mermaid
flowchart LR
    OMS[OMS 本体资产] --> IDX[OAG Index Build]
    OAC[OAC] --> M[MinIO CSV]
    BUS[DataSync/业务服务] --> M
    M --> IDX
    IDX --> GV[GaussVector]
    IDX --> OS[OpenSearch]

    Q[Query] --> QU[Query Understanding]
    QU --> R[6 路 Recall]
    GV --> R
    OS --> R
    R --> RRF[Weighted RRF]
    RRF --> LR[LLM Rerank]
    LR --> P[SeedNodeProjector]
    P --> G[GraphTopologyCache / NebulaGraph]
    G --> S[minimal / khop / component]
    S --> PP[PathProbePlan + Loop]
    PP --> N[nGQL / Graph Probe]
    N --> RES[GraphSearchResponse]
```'''

new_overview = '''```mermaid
flowchart LR
    OMS[OMS 本体资产] --> IDX[OAG Index Build]
    OAC[OAC] --> M[MinIO CSV]
    BUS[DataSync/业务服务] --> M
    M --> IDX
    IDX --> GV[GaussVector]
    IDX --> OS[OpenSearch]

    Q[Query] --> QU[Query Understanding / extractedEntities]
    QU --> ROUTE{Semantic Unit 类型}
    ROUTE --> OD[ObjectType / Property<br/>本体定义 2 路]
    ROUTE --> VAL[Value<br/>Enum + Instance 4 路]
    GV --> OD
    OS --> OD
    GV --> VAL
    OS --> VAL
    OD --> ORRF[OntologyDefinition<br/>2 路 Weighted RRF]
    VAL --> VRRF[Value<br/>4 路 Weighted RRF]
    ORRF --> LR[LLM Rerank]
    VRRF --> LR
    LR --> P[SeedNodeProjector]
    P --> G[GraphTopologyCache / NebulaGraph]
    G --> S[minimal / khop / component]
    S --> PP[PathProbePlan + Loop]
    PP --> N[nGQL / Graph Probe]
    N --> RES[GraphSearchResponse]
```'''

assert old_overview in text
text = text.replace(old_overview, new_overview, 1)

start_marker = '### 1.2 子图端到端总体架构\n\n```mermaid\n'
start = text.index(start_marker) + len('### 1.2 子图端到端总体架构\n\n')
end = text.index('\n```\n\n运行阶段统一为：', start) + len('\n```')
old_detail = text[start:end]
new_detail = '''```mermaid
flowchart TD
    Q[用户原始问题] --> EE[Entity Extraction<br/>extractedEntities]
    EE --> SU[OBJECT_TYPE / PROPERTY / VALUE<br/>Semantic Units]
    SU --> ROUTE{按 Semantic Unit 类型路由}

    subgraph OD[本体定义 2 路]
      OL[OpenSearch<br/>Keyword Fuzzy]
      ODV[GaussVector<br/>Dense]
    end

    subgraph VV[值 4 路]
      EL[Enum OpenSearch<br/>Keyword Fuzzy]
      ED[Enum GaussVector<br/>Dense]
      IL[Instance OpenSearch<br/>Keyword Fuzzy]
      ID[Instance GaussVector<br/>Dense]
    end

    ROUTE -->|OBJECT_TYPE / PROPERTY| OL
    ROUTE -->|OBJECT_TYPE / PROPERTY| ODV
    ROUTE -->|VALUE| EL
    ROUTE -->|VALUE| ED
    ROUTE -->|VALUE| IL
    ROUTE -->|VALUE| ID

    OL --> ORRF[OntologyDefinitionFusion<br/>2 路 Weighted RRF]
    ODV --> ORRF
    EL --> VRRF[ValueFusion<br/>4 路 Weighted RRF]
    ED --> VRRF
    IL --> VRRF
    ID --> VRRF

    ORRF --> COARSE[Entity Linking 粗排候选]
    VRRF --> COARSE
    Q --> RC[RerankContextBuilder]
    COARSE --> RC
    SU --> RC
    RC --> LLM[LLM Fine Ranker]
    LLM --> RESULT[Final Retrieval Results]

    RESULT --> SP[SeedNodeProjector]
    SP --> SG[SubgraphBuilder]
    SG --> CORE[Ontology Core Subgraph]

    RESULT --> EXT[Semantic Extension Assembler]
    CORE --> EXT
    EXT --> OUT[检索结果 + 本体子图 + 语义扩展]
    OUT --> CYPHER[下游 LLM / Cypher]
```'''
text = text[:start] + new_detail + text[end:]

text = text.replace('阶段2：6 路召回', '阶段2：按类型混合召回（ObjectType/Property 2 路，Value 4 路）', 1)
text = text.replace('阶段3：一次 Weighted RRF 粗排', '阶段3：分类型 Weighted RRF 粗排（本体定义 2 路 / Value 4 路）', 1)

# Validate overview and chapter 4 are aligned.
assert '每个 Semantic Unit 的 6 路召回' not in text
assert '一次融合 6 条 Ranked List' not in text[:text.index('# 4. 实体提取、Entity Linking 与 6 路混合召回')]
assert 'OntologyDefinitionFusion' in text
assert 'ValueFusion' in text
assert '本体定义 2 路融合' in text
assert 'Enum/Instance 4 路融合' in text

DOC.write_text(text, encoding='utf-8')
if WORKFLOW.exists():
    WORKFLOW.unlink()
if SCRIPT.exists():
    SCRIPT.unlink()
