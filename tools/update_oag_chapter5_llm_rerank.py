from pathlib import Path

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
WORKFLOW = Path('.github/workflows/one-shot-oag-ch5-rerank.yml')
SELF = Path(__file__)

text = DOC.read_text(encoding='utf-8')
start_marker = '# 5. LLM 精排与最终语义检索结果'
end_marker = '# 6. 本体对象投影、子图策略、路径探测、nGQL 与最终返回'
start = text.index(start_marker)
end = text.index(end_marker)

chapter5 = r'''# 5. LLM 精排与最终语义检索结果

本章定义第 4 章 Entity Linking 粗排候选进入 LLM 后的**语义精排与种子节点裁剪**。核心原则是：

> **LLM 只做“从真实候选中选择”，不做“生成新候选”。精排必须同时结合原始问题、业务注入的 SearchContext、Skill 上下文知识和检索证据，最终输出精准、最小充分的种子节点。**

精排主链路：

```text
原始 Query
+ extractedEntities / Semantic Units
+ SearchContext(target_entity / search_path / extensions)
+ Skill Context Knowledge
+ 4.5.3 coarse seedNodes
+ Value supporting evidence
+ Graph Hint
        ↓
RerankContextBuilder
        ↓
LLM Seed Pruner / Fine Ranker
        ↓
selectedSeedNodes
        ↓
程序侧 Candidate Membership / Topology / Schema 校验
        ↓
SeedNodeProjector
        ↓
第 6 章本体子图构建
```

---

## 5.1 精排目标与职责边界

### 5.1.1 输入基线

第 5 章的本体种子候选直接来自第 4.5.3 节粗排结构：

```text
seedNodes[]
  ├─ sourceObjectType
  └─ targetObjectTypes[]
       ├─ name / id / score
       └─ propertyLinks[]
            ├─ sourceProperty
            └─ targetProperties[]
                 └─ name / id / score
```

内部候选继续保留：

```text
rrfScore
channelHits
supporting_hits
matched_field
matched_value
```

这些字段是 LLM 判断“为什么该候选被召回”的证据，但不是最终语义真值。

### 5.1.2 LLM 的职责

LLM Fine Rank 只负责：

1. 根据完整上下文判断粗排候选与用户真实意图是否一致；
2. 对每个 `sourceObjectType` 从 `targetObjectTypes[]` 中选择 0 / 1 / N 个真实候选；
3. 对每个已选 ObjectType，在其自身 `propertyLinks[]` 作用域内选择 0 / 1 / N 个 Property；
4. 删除“向量/关键词相似但业务语义不相关”的候选；
5. 保留 Query、SearchContext 或 Skill 明确要求且有真实候选支持的必要种子；
6. 在确实无法消歧时允许多个候选并存，而不是强行选 1 个；
7. 在无可信候选时返回 unresolved，不制造本体对象。

LLM 不负责：

```text
生成新的 ObjectType / Property / Relationship ID
修改候选 id / name / score
创建第 4 章不存在的候选
绕过 Property → ObjectType 归属关系
直接生成 nGQL / Cypher / OQL
在本阶段重新执行图路径查询
```

### 5.1.3 精排输出目标

精排后的种子节点要求满足：

```text
精准性：语义与用户问题、业务上下文一致
真实性：所有 id/name 必须来自粗排候选
归属性：Property 必须属于被选中的 ObjectType
最小性：删除对当前任务无贡献的相似候选
完整性：保留过滤、返回、关联、聚合所必需的对象/属性
可解释性：程序侧保留原始 RRF/supporting evidence 供 Trace 使用
```

---

## 5.2 多上下文联合精排设计

精排不能只看 RRF 分数，也不能只看单个 Semantic Unit。`RerankContextBuilder` 必须同时提供下列上下文。

### 5.2.1 原始 Query：用户意图主事实

`original_query` 保留未经拆词和改写的用户原始问题，用于识别：

- 查询目标对象；
- 需要返回的属性；
- 过滤条件和业务值；
- 时间、比较、聚合、排序等语义；
- 多实体之间的业务意图。

例如 `发生时间` 可能同时召回多个 Property，只有结合：

```text
查询站点上影响业务的活跃告警首次发生时间
```

才能判断应优先选择“首次发生时间”而不是“最后发生时间”。

### 5.2.2 SearchContext：业务显式注入上下文

SearchContext 的正式结构来自《OAG语义子图检索接口 extractedEntities / 实体提取设计方案》3.3：

```text
searchContext
  ├─ target_entity
  ├─ search_path
  └─ extensions
```

在精排阶段的作用：

| 字段 | 精排作用 | 边界 |
|---|---|---|
| `target_entity` | 业务侧显式目标实体强提示；用于保留/提升与目标实体匹配的 ObjectType 候选 | 仍只能选择粗排中真实存在的候选，不能把文本直接当内部 ID |
| `search_path` | 专家路径提示；用于判断哪些 ObjectType/Property 更符合预期业务链路 | 必须结合 Graph Hint/本体拓扑验证，不能直接当可执行路径 |
| `extensions` | few-shot、领域术语、黑话、业务约束等扩展上下文 | 只有注册并明确语义的扩展信息参与精排，不得改变候选 Schema |

示例：

```json
{
  "target_entity": "ID(xxx),BillingAccount,Invoice,BillDetail",
  "search_path": "Subscriber(id:{msisdn}) --> SubscribeRelation --> Offering",
  "extensions": {
    "domain_terms": ["账期", "出账"]
  }
}
```

### 5.2.3 Skill Context：业务 Skill 中的领域知识

`skill_context` 是 **Agent/Skill Runtime 内部注入给 RerankContextBuilder 的运行时上下文**，不是当前语义检索接口新增的对外 Body 字段。

Skill 上下文可以包含：

```text
Skill 的任务目标和适用场景
领域术语、缩写、黑话和同义表达
业务对象与属性的常用语义
业务查询约束和必需字段
专家经验 / few-shot
生成查询时必须保留的关键对象或属性
```

Skill Context 的作用是帮助 LLM 理解领域语义，例如：

```text
“首次发生时间”在告警 Skill 中对应 firstOccurrenceTime
“账期”在账务 Skill 中优先关联 BillingCycle
```

但 Skill Context **不能**：

1. 创造粗排候选中不存在的 ID；
2. 覆盖用户明确表达的相反意图；
3. 绕过本体真实 Property/ObjectType 归属；
4. 直接把 Skill 中的示例 ID 当作当前本体的真实结果。

### 5.2.4 Graph Hint 与检索证据

GraphTopologyCache 可提供轻量 Graph Hint：

```text
Property 所属 ObjectType
候选 ObjectType 是否同连通分量
候选之间最短 hop 摘要
Relationship 名称 / 方向摘要
search_path 是否可由真实拓扑支持
```

检索证据包括：

```text
RRF rank / score
channelHits
OpenSearch matched_field / matched_value
Dense supporting_hits
Enum / Instance Value 对 Property/ObjectType 的真实归属
```

Graph Hint 和检索证据只提供辅助判断，不替代原始 Query 与业务上下文。

### 5.2.5 上下文优先级与冲突处理

精排采用以下优先级：

```text
0. 候选真实性 + 本体归属/拓扑硬约束
1. 原始 Query 的显式用户意图
2. SearchContext 的显式业务目标 / 专家路径 / 注册扩展约束
3. Skill Context 的领域知识与任务规则
4. RRF / Lexical / Dense 排名与 supporting evidence
```

处理原则：

1. **候选真实性是硬约束**：任何上下文都不能让 LLM 生成输入中不存在的候选；
2. **Query 不被静默覆盖**：SearchContext/Skill 可以补充和消歧，但不能删除用户明确要求；
3. `target_entity` 可以补充 Query 未显式说出的业务目标，但只有命中真实候选时才能进入最终种子；
4. `search_path` 与 Graph Hint 一致时可提升路径上候选；路径无法验证时不得据此强选；
5. Skill Context 用于术语映射和业务规则，优先级低于 Query 和显式 SearchContext；
6. RRF 高分只表示召回强度，若与完整语义冲突可以被裁掉；
7. 上下文存在不可调和冲突且无法确定唯一候选时，保留必要的多候选或返回 unresolved，不编造确定结论。

---

## 5.3 RerankContext 数据结构

推荐内部结构：

```json
{
  "original_query": "查询指定用户订购的产品及相关账务实体",
  "extracted_entities": [
    {
      "ObjectType": "Subscriber",
      "Properties": ["id"],
      "Values": []
    }
  ],
  "search_context": {
    "target_entity": "BillingAccount,Invoice,BillDetail",
    "search_path": "Subscriber(id:{msisdn}) --> SubscribeRelation --> Offering",
    "extensions": {}
  },
  "skill_context": {
    "skill_name": "billing-query",
    "knowledge": "账务查询中 BillingAccount 是账户主体，Invoice/BillDetail 是账单结果对象。",
    "constraints": [
      "用户查询账单明细时需要保留 BillDetail"
    ]
  },
  "coarse_seed_nodes": [
    {
      "sourceObjectType": "Subscriber",
      "targetObjectTypes": [
        {
          "id": "obj-subscriber",
          "name": "Subscriber",
          "score": 0.982,
          "propertyLinks": [
            {
              "sourceProperty": "id",
              "targetProperties": [
                {"id": "prop-subscriber-id", "name": "id", "score": 0.955}
              ]
            }
          ]
        }
      ]
    }
  ],
  "value_supporting_evidence": [],
  "graph_hint": {
    "validatedSearchPath": true,
    "pathObjectTypes": ["Subscriber", "SubscribeRelation", "Offering"]
  }
}
```

字段说明：

| 字段 | 来源 | 说明 |
|---|---|---|
| `original_query` | API `query` | 精排主语义事实 |
| `extracted_entities` | 第 4.1 节 | 提供原始 ObjectType/Property/Value 结构 |
| `search_context` | API `searchContext` | 业务显式目标、路径与扩展信息 |
| `skill_context` | Agent/Skill Runtime | 领域知识和业务任务约束；内部字段 |
| `coarse_seed_nodes` | 第 4.5.3 节 | LLM 唯一允许选择的 ObjectType/Property 候选集合 |
| `value_supporting_evidence` | 第 4.6 节 | Enum/Instance 命中对 Property/ObjectType 的辅助证据 |
| `graph_hint` | GraphTopologyCache | 一跳/轻量拓扑与 search_path 校验摘要 |

要求：

- `skill_context` 不进入对外 OpenAPI；
- Prompt 中对各上下文设置明确标签，避免不同来源文本混淆；
- 对于过长 Skill/few-shot，上游应先裁剪到与当前 Query 相关的知识片段，避免挤占候选上下文窗口；
- 不在精排前构建完整 K-hop 子图，只提供轻量 Graph Hint。

---

## 5.4 种子节点裁剪算法

### 5.4.1 ObjectType 裁剪

对每个 `sourceObjectType`：

```text
targetObjectTypes[]
  ↓
结合 Query + target_entity + search_path + Skill + evidence
  ↓
选择 0 / 1 / N 个 targetObjectType
```

规则：

1. 用户明确表达单一对象且候选语义清晰时，通常选择 1 个；
2. Query 明确涉及多个真实业务对象，或 `target_entity` 显式指定多个目标时，可以保留多个候选；
3. 候选名称相似但不满足任务语义、路径或 Skill 业务约束时应裁掉；
4. 粗排 Top1 不具备语义一致性时允许选择 Top2/Top3；
5. 所有候选都不可信时，当前 `sourceObjectType` 不输出 target，并记录 unresolved。

### 5.4.2 Property 裁剪

Property 只能在已选 `targetObjectType.propertyLinks[]` 内选择：

```text
selected targetObjectType
  ↓
sourceProperty
  ↓
targetProperties[]
  ↓
选择 0 / 1 / N 个 targetProperty
```

规则：

1. 不能跨 ObjectType 复用 Property 候选；
2. `sourceProperty` 的完整业务短语优先，不因局部关键词相似而选择错误属性；
3. Query 中明确用于过滤、返回、聚合、排序或后续查询生成的 Property 应保留；
4. Skill 明确规定的必需字段可作为保留依据，但该字段必须存在于当前候选列表；
5. Value supporting evidence 命中了某真实 Property 时，可作为该 Property 的强辅助证据；
6. 如果多个 Property 在当前语义下均合理，允许保留多个，交由后续查询规划继续约束；
7. 无可信 Property 时返回空数组并记录 unresolved，不从其他 ObjectType 猜一个属性补齐。

### 5.4.3 最小充分种子原则

最终种子集合不是“分数最高的候选全集”，而是满足任务所需的**最小充分本体对象集合**：

```text
保留：
- 用户查询目标 ObjectType
- 生成过滤条件必需的 Property
- 返回字段必需的 Property
- SearchContext 明确目标且与 Query 一致的 ObjectType/Property
- Skill 规则要求且真实存在的必要 ObjectType/Property

删除：
- 仅名字相似但不服务当前问题的候选
- 与 target_entity/search_path/Skill 业务语义明显冲突的候选
- 同义重复且没有额外业务价值的候选
- 仅因 RRF 分数高而进入、但无法解释其任务作用的候选
```

---

## 5.5 LLM 种子节点精排 Prompt

本节 Prompt 是种子节点裁剪的正式运行时基线。中文和英文版本保持相同输入输出 Schema 与约束。

### 5.5.1 中文版 Prompt

````text
# Role
你是 OAG（Ontology Augmented Generation）语义检索的“种子节点精排器 / Seed Node Fine Ranker”。

你的任务不是生成新的本体对象，而是基于输入的粗排候选进行严格裁剪：结合用户原始问题、业务 SearchContext、Skill 上下文知识、Value/检索证据和轻量 Graph Hint，从 coarse_seed_nodes 中选择最符合真实业务意图的 ObjectType 和 Property，输出精准、最小充分的 selectedSeedNodes。

# Hard Constraints
1. 只能选择 coarse_seed_nodes 中真实存在的候选。
2. 禁止生成、修改或猜测任何新的 ObjectType ID、Property ID、name 或 score。
3. Property 只能从当前已选 targetObjectType 自己的 propertyLinks[].targetProperties[] 中选择，禁止跨 ObjectType 归属选择。
4. 不生成 Relationship、RelationshipProperty、Function、Action、nGQL、Cypher 或 OQL。
5. 不根据模型自身知识补造候选；Skill/SearchContext 只能用于理解和裁剪现有候选。
6. score 必须原样保留输入值，不能由你重新打分。
7. 只输出符合 Output Schema 的 JSON，不输出 Markdown、解释性段落或详细推理过程。

# Context Inputs
你会收到以下上下文：

## Original Query
用户未经改写的原始问题，是判断用户真实意图的主要事实来源。

## Extracted Entities
实体提取得到的 ObjectType / Properties / Values，用于保持源实体和源属性语义。

## SearchContext
业务侧显式注入的上下文：
- target_entity：业务希望重点检索/返回的目标实体强提示；
- search_path：业务专家提供的路径提示；只有 Graph Hint 验证可成立时才作为强路径证据；
- extensions：已注册语义的业务扩展、few-shot、术语、黑话或约束。

## Skill Context
当前业务 Skill 的领域知识和任务规则，可用于术语理解、业务对象/属性选择、必需字段判断和消歧。
Skill Context 不能覆盖用户明确相反的意图，也不能创建粗排候选中不存在的 ID。

## Coarse Seed Nodes
第 4.5.3 节输出的粗排候选，是你唯一允许选择的 ObjectType / Property 集合。

## Value Supporting Evidence
Enum/Instance Value 命中后得到的 Property/ObjectType 归属证据，可用于辅助判断哪个种子节点与用户 Value 一致。

## Graph Hint
本体拓扑的轻量校验结果，例如 Property 归属、候选连通性、search_path 是否可验证等。

# Decision Priority
按以下优先级判断：
0. 候选真实性和本体归属/拓扑硬约束；
1. Original Query 的显式用户意图；
2. SearchContext 的显式业务目标、路径和注册扩展约束；
3. Skill Context 的领域知识和任务规则；
4. RRF / Lexical / Dense 排名及 supporting evidence。

注意：RRF 高分只是检索先验。如果高分候选与完整业务语义不一致，应裁掉。

# Selection Rules
1. 对每个 sourceObjectType，从 targetObjectTypes[] 中选择 0 / 1 / N 个真实候选。
2. 用户意图明确且只有一个候选真正匹配时，只保留该候选。
3. Query 明确需要多个实体，或 target_entity 显式声明多个目标且这些目标均有真实候选时，可以保留多个 ObjectType。
4. search_path 与 Graph Hint 验证一致时，优先保留符合路径的候选；路径未验证时不能仅凭 search_path 强行选择。
5. Skill Context 用于理解业务术语和任务约束，但优先级低于 Query 和显式 SearchContext。
6. 对每个已选 ObjectType，逐个处理 sourceProperty，只能从当前 ObjectType 自己的 targetProperties[] 中选择。
7. Query 中用于过滤、返回、聚合、排序、时间或后续查询生成的必要 Property 应保留。
8. Value Supporting Evidence 如果明确指向某 Property/ObjectType，可作为强辅助证据。
9. 名称相似但不服务当前 Query/业务目标的候选应删除，即使它的 RRF score 更高。
10. 如果多个候选在当前上下文中都合理且无法可靠消歧，可以保留多个，不要虚构唯一答案。
11. 如果没有可信 ObjectType 或 Property，允许不选择，并写入 unresolved。
12. 最终 selectedSeedNodes 应是满足当前任务的最小充分集合，避免无关节点膨胀后续子图。

# Output Schema
严格输出：
{
  "selectedSeedNodes": [
    {
      "sourceObjectType": "输入中的原始 sourceObjectType",
      "targetObjectTypes": [
        {
          "id": "必须来自输入候选",
          "name": "必须来自输入候选",
          "score": 0.0,
          "propertyLinks": [
            {
              "sourceProperty": "输入中的原始 sourceProperty",
              "targetProperties": [
                {
                  "id": "必须来自当前 ObjectType 的输入候选",
                  "name": "必须来自当前 ObjectType 的输入候选",
                  "score": 0.0
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "unresolved": [
    {
      "sourceObjectType": "可选",
      "sourceProperty": "可选",
      "reasonCode": "NO_CONFIDENT_OBJECT_TYPE | NO_CONFIDENT_PROPERTY | CONTEXT_CONFLICT"
    }
  ]
}

# Output Rules
1. id/name/score 必须逐字来自输入候选；不能修改。
2. selectedSeedNodes 只输出最终保留的候选，不复制已裁掉候选。
3. 如果选中 Property，其父 targetObjectType 必须同时存在于输出。
4. 如果某个 sourceProperty 无匹配，可不输出该 propertyLink，并在 unresolved 中记录。
5. 如果某个 sourceObjectType 无任何可信 targetObjectType，可不输出该 seedNode，并在 unresolved 中记录。
6. unresolved 只输出 reasonCode，不输出详细思维过程。
7. 如果所有候选都应裁掉：{"selectedSeedNodes":[],"unresolved":[...]}。

# Runtime Input
Original Query:
{{original_query}}

Extracted Entities:
{{extracted_entities}}

SearchContext:
{{search_context}}

Skill Context:
{{skill_context}}

Coarse Seed Nodes:
{{coarse_seed_nodes}}

Value Supporting Evidence:
{{value_supporting_evidence}}

Graph Hint:
{{graph_hint}}

# Task
根据以上规则裁剪 coarse_seed_nodes，只输出 JSON。
````

### 5.5.2 English Prompt

````text
# Role
You are the Seed Node Fine Ranker for OAG (Ontology Augmented Generation) semantic retrieval.

Your job is NOT to create ontology candidates. Your job is to strictly prune the retrieved candidates. Combine the original user query, business SearchContext, Skill context knowledge, value/retrieval evidence, and lightweight Graph Hint, then select only the ObjectType and Property candidates from coarse_seed_nodes that best match the real business intent. Return a precise and minimally sufficient selectedSeedNodes set.

# Hard Constraints
1. You may select only candidates that already exist in coarse_seed_nodes.
2. Never generate, modify, infer, or fabricate a new ObjectType ID, Property ID, name, or score.
3. A Property may only be selected from the propertyLinks[].targetProperties[] of its selected targetObjectType. Never move a Property candidate across ObjectType scopes.
4. Do not generate Relationship, RelationshipProperty, Function, Action, nGQL, Cypher, or OQL.
5. Do not use your own model knowledge to invent candidates. Skill Context and SearchContext may only help interpret and prune existing candidates.
6. Preserve every selected candidate score exactly as provided in the input. Do not rescore candidates.
7. Output JSON that matches the Output Schema only. Do not output Markdown, prose explanations, or detailed chain-of-thought.

# Context Inputs

## Original Query
The user's original, unmodified question. This is the primary source for the user's explicit intent.

## Extracted Entities
The structured ObjectType / Properties / Values extracted from the query. Use it to preserve source entity and property semantics.

## SearchContext
Business-injected context:
- target_entity: a strong hint about business target entities;
- search_path: an expert path hint; treat it as strong path evidence only when Graph Hint validates it;
- extensions: registered business extensions, few-shot examples, terminology, slang, or constraints.

## Skill Context
Domain knowledge and task rules from the active business Skill. Use it for domain terminology, object/property semantics, required-field rules, and disambiguation.
Skill Context must not override explicit contradictory user intent and must never create IDs absent from the candidate list.

## Coarse Seed Nodes
The coarse candidates produced by Section 4.5.3. This is the ONLY allowed ObjectType / Property candidate set.

## Value Supporting Evidence
Enum/Instance Value hits and their real Property/ObjectType ownership. Use them only as supporting evidence for seed selection.

## Graph Hint
Lightweight ontology topology evidence, such as Property ownership, candidate connectivity, and whether search_path is validated.

# Decision Priority
Use the following priority order:
0. Candidate reality and ontology ownership/topology hard constraints;
1. Explicit intent in the Original Query;
2. Explicit business targets, path hints, and registered constraints in SearchContext;
3. Domain knowledge and task rules in Skill Context;
4. RRF / lexical / dense ranking and supporting evidence.

A high RRF score is only a retrieval prior. Drop a high-scoring candidate when it conflicts with the complete business semantics.

# Selection Rules
1. For each sourceObjectType, select 0 / 1 / N candidates from targetObjectTypes[].
2. If user intent is clear and only one candidate truly matches, keep only that candidate.
3. Keep multiple ObjectTypes when the query explicitly requires multiple entities, or when target_entity explicitly names multiple targets and real candidates exist for them.
4. Prefer candidates consistent with search_path when Graph Hint validates that path. Do not force-select a candidate from an unvalidated path hint.
5. Use Skill Context for terminology and business rules, but keep it lower priority than the Query and explicit SearchContext.
6. For every selected ObjectType, process each sourceProperty independently and select only from that ObjectType's own targetProperties[].
7. Keep Properties required for filtering, output fields, aggregation, ordering, time semantics, or downstream query generation.
8. If Value Supporting Evidence clearly points to a Property/ObjectType, treat that as strong supporting evidence.
9. Remove semantically irrelevant candidates even when they have higher RRF scores.
10. If multiple candidates remain legitimately plausible and cannot be safely disambiguated, keep multiple candidates instead of fabricating certainty.
11. If no trustworthy ObjectType or Property exists, select none and record it in unresolved.
12. selectedSeedNodes should be the minimally sufficient seed set for the task, avoiding unnecessary graph expansion.

# Output Schema
Return exactly:
{
  "selectedSeedNodes": [
    {
      "sourceObjectType": "original sourceObjectType from input",
      "targetObjectTypes": [
        {
          "id": "must come from input candidate",
          "name": "must come from input candidate",
          "score": 0.0,
          "propertyLinks": [
            {
              "sourceProperty": "original sourceProperty from input",
              "targetProperties": [
                {
                  "id": "must come from this ObjectType's input candidates",
                  "name": "must come from this ObjectType's input candidates",
                  "score": 0.0
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "unresolved": [
    {
      "sourceObjectType": "optional",
      "sourceProperty": "optional",
      "reasonCode": "NO_CONFIDENT_OBJECT_TYPE | NO_CONFIDENT_PROPERTY | CONTEXT_CONFLICT"
    }
  ]
}

# Output Rules
1. Every id/name/score must be copied exactly from an input candidate.
2. selectedSeedNodes must contain selected candidates only. Do not copy pruned candidates.
3. If a Property is selected, its parent targetObjectType must also be present in the output.
4. If a sourceProperty has no valid match, omit that propertyLink and add an unresolved entry.
5. If a sourceObjectType has no trustworthy targetObjectType, omit that seed node and add an unresolved entry.
6. unresolved contains reasonCode only; do not expose detailed reasoning.
7. If all candidates should be pruned, return: {"selectedSeedNodes":[],"unresolved":[...]}.

# Runtime Input
Original Query:
{{original_query}}

Extracted Entities:
{{extracted_entities}}

SearchContext:
{{search_context}}

Skill Context:
{{skill_context}}

Coarse Seed Nodes:
{{coarse_seed_nodes}}

Value Supporting Evidence:
{{value_supporting_evidence}}

Graph Hint:
{{graph_hint}}

# Task
Prune coarse_seed_nodes according to the rules above and output JSON only.
````

---

## 5.6 精排输出、程序校验与 0/1/N

### 5.6.1 输出结构

LLM 输出 `selectedSeedNodes` 保持 4.5.3 的归属层级，只删除不需要的候选，不改变候选身份：

```json
{
  "selectedSeedNodes": [
    {
      "sourceObjectType": "WhatsApp应用",
      "targetObjectTypes": [
        {
          "name": "WhatsAPP应用",
          "id": "obj-whatsapp",
          "score": 0.996,
          "propertyLinks": [
            {
              "sourceProperty": "体验质量",
              "targetProperties": [
                {"name": "poor_cnt", "id": "prop-poor-cnt", "score": 0.931}
              ]
            },
            {
              "sourceProperty": "时间",
              "targetProperties": [
                {"name": "occurrenceTime", "id": "prop-time", "score": 0.655}
              ]
            }
          ]
        }
      ]
    }
  ],
  "unresolved": []
}
```

0 / 1 / N 语义：

```text
0：没有可信候选，记录 unresolved
1：唯一明确匹配
N：多个候选都与当前上下文一致，暂不能安全裁成 1 个
```

### 5.6.2 程序侧强校验

LLM 输出必须经过程序 Validator，不允许直接进入图构建：

1. `selectedSeedNodes` JSON Schema 校验；
2. `sourceObjectType/sourceProperty` 必须来自输入粗排结构；
3. 每个 ObjectType `id/name/score` 必须与输入某一候选完全一致；
4. 每个 Property `id/name/score` 必须存在于当前选中 ObjectType 的 `propertyLinks` 内；
5. 禁止出现跨 ObjectType Property；
6. 输出不能出现输入候选之外的新 ID；
7. 同层 ID 去重；
8. 候选数量不得超过精排配置上限；
9. `unresolved.reasonCode` 只允许白名单枚举；
10. Value supporting evidence 只能作为选择证据，不能绕过候选 membership 校验创建新 seed。

校验失败视为 LLM 输出异常，进入第 5.7 节降级流程。

---

## 5.7 LLM 可靠性与降级

推荐执行：

```text
LLM Fine Rank
→ JSON / Candidate Membership / Ownership 校验
→ 成功：rerank_status = SUCCESS

Timeout / JSON 错误 / 非法候选
→ 使用相同上下文重试 1 次
→ 仍失败
→ fallback = 每个粗排 Group 的 primary candidate
→ rerank_status = DEGRADED
```

Fallback 约束：

1. 只从原粗排候选选择，不恢复任何已不存在的候选；
2. ObjectType 使用 4.5.3 每组 RRF primary candidate；
3. Property 仍必须在对应 ObjectType 作用域内使用 primary candidate；
4. 无候选保持 unresolved；
5. 降级状态写入 Trace/metadata，业务可观测；
6. 合法的 `selectedSeedNodes=[]` 或 unresolved 不属于异常。

建议指标：

```text
oag_rerank_request_total
oag_rerank_duration_ms
oag_rerank_retry_total
oag_rerank_degraded_total
oag_rerank_invalid_candidate_total
oag_rerank_unresolved_total
oag_rerank_pruned_candidate_total
```

---

## 5.8 最终语义检索结果与 Value 处理

### 5.8.1 retrievalResults

最终语义事实继续以 `retrievalResults` 表达：

```text
retrievalResults
  = 权威的最终 ObjectType / Property / Enum Value / Instance Value 命中事实
```

Enum/Instance 的真实命中必须保留：

```text
objectTypeId
propertyId
value
matched_field
matched_value
supporting_hits
```

示例：

```json
{
  "retrievalResults": [
    {
      "objectTypeId": "obj:alarm:Alarm",
      "propertyId": "prop:alarm:severity",
      "value": "CRITICAL",
      "matchedField": "synonyms",
      "matchedValue": "严重"
    }
  ]
}
```

### 5.8.2 Value 与 selectedSeedNodes 的一致性

第 4.6 节 Enum/Instance Value 4 路召回得到的真实归属，可作为种子精排证据，并在精排后执行一致性约束：

```text
Value selected
→ propertyId + objectTypeId
→ 对应 Property/ObjectType 必须进入 SeedNodeProjector 的 terminal 集合
```

如果 Value-only 场景通过真实索引命中解析出新的 Property/ObjectType，而该对象没有出现在 4.5.3 的文本型 `coarse_seed_nodes` 中，则由程序侧 `ValueSeedProjector` 根据真实 `property_id + object_type_id` 补充 terminal；**不要求 LLM 在种子精排 Prompt 中生成新 ID**。

这样保持：

```text
LLM Seed Pruner
  → 只裁剪 4.5.3 真实候选

ValueSeedProjector
  → 只投影 4.6 真实值命中的已知 property_id/object_type_id
```

两者都不能生成不存在的本体身份。

### 5.8.3 semanticExtensions

`semanticExtensions.valueMappings` 是对最终 Enum/Instance 命中的查询生成投影：

```text
sourceValue
→ canonicalValue = retrievalResults.value
→ Property
→ ObjectType
```

`canonicalValue` 直接来自真实索引 `value`，不维护第二套 canonical 字典。

### 5.8.4 SeedNodeProjector 前置输出

精排后形成：

```text
selectedSeedNodes
+ selected Value retrievalResults
        ↓
SeedNodeProjector / ValueSeedProjector
        ↓
ObjectType terminals
Property terminals
mandatory has_property ownership
```

最终图构建 Seed 与第 4.5.3 的粗排 Seed 候选处于不同生命周期，不能直接等同。

---

## 5.9 精排运行时序

```mermaid
sequenceDiagram
    participant U as User/Agent
    participant EE as Entity Extraction
    participant D as SearchDispatcher
    participant R as Typed RRF
    participant C as RerankContextBuilder
    participant S as Skill Runtime
    participant T as GraphTopologyCache
    participant L as LLM Fine Ranker
    participant V as Rerank Validator
    participant P as SeedNodeProjector

    U->>EE: original query + SearchContext
    EE-->>D: extractedEntities / Semantic Units
    D->>D: ObjectType/Property 2路 + Value 4路召回
    D->>R: ranked candidates
    R-->>C: 4.5.3 coarse seedNodes + supporting evidence
    U->>C: original query + SearchContext
    S-->>C: relevant Skill context knowledge
    T-->>C: lightweight Graph Hint / search_path validation
    C->>L: RerankContext
    L-->>V: selectedSeedNodes + unresolved
    V->>V: Schema + candidate membership + ownership validation
    V-->>P: validated precise seeds
    P->>P: ObjectType / Property / Value seed projection
```

精排完成后，第 6 章只消费**已经通过程序校验的精准种子节点**进行 `minimal / khop / component` 子图规划。

---

'''

new_text = text[:start] + chapter5 + text[end:]
new_text = new_text.replace('> 版本：V6.2  ', '> 版本：V6.3  ', 1)
new_text = new_text.replace('> 日期：2026-09-05  ', '> 日期：2026-09-05  ', 1)

# Guardrails
required = [
    '## 5.2 多上下文联合精排设计',
    '### 5.2.2 SearchContext：业务显式注入上下文',
    '### 5.2.3 Skill Context：业务 Skill 中的领域知识',
    '### 5.5.1 中文版 Prompt',
    '### 5.5.2 English Prompt',
    '{{original_query}}',
    '{{search_context}}',
    '{{skill_context}}',
    '{{coarse_seed_nodes}}',
    'selectedSeedNodes',
    'ValueSeedProjector',
]
for token in required:
    assert token in new_text, token

assert new_text.count('# 5. LLM 精排与最终语义检索结果') == 1
assert '# 6. 本体对象投影、子图策略、路径探测、nGQL 与最终返回' in new_text

DOC.write_text(new_text, encoding='utf-8')

# Remove one-shot helpers before the workflow commits the final document.
if SELF.exists():
    SELF.unlink()
if WORKFLOW.exists():
    WORKFLOW.unlink()
