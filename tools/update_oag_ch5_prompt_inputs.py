from pathlib import Path

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
WORKFLOW = Path('.github/workflows/one-shot-oag-ch5-prompt-inputs.yml')
SELF = Path(__file__)

text = DOC.read_text(encoding='utf-8')
start = text.index('# 5. LLM 精排与最终语义检索结果')
end = text.index('# 6. 本体对象投影、子图策略、路径探测、nGQL 与最终返回')

chapter5 = r'''# 5. LLM 精排与最终语义检索结果

本章定义 Entity Linking 粗排之后的 LLM 精排与种子节点裁剪。精排的目标不是重新检索，也不是再次生成实体，而是结合用户原始问题和业务侧注入上下文，对上一步已经形成的结构化候选进行语义判断，输出精准、最小充分的种子节点。

核心原则：

> **LLM 只裁剪上一步已有候选，不创造新候选；精排 Prompt 只接收 `original_query`、`search_context`、`extracted_entities` 三类运行时输入。**

精排链路：

```text
original_query
+ search_context
+ extracted_entities（上一步结构化候选输出）
        ↓
Rerank Prompt Builder
        ↓
LLM Seed Node Fine Ranker
        ↓
selectedSeedNodes + unresolved
        ↓
程序侧 Schema / Candidate Membership / Ownership 校验
        ↓
精准种子节点
        ↓
SeedNodeProjector / 后续子图构建
```

---

## 5.1 精排输入与职责边界

### 5.1.1 Prompt 仅接收三类输入

精排 Prompt 的运行时输入固定为：

| 输入 | 来源 | 作用 |
|---|---|---|
| `original_query` | 用户原始问题 | 判断用户真实查询目标、过滤对象、返回字段以及多实体业务意图 |
| `search_context` | 业务侧注入的 SearchContext | 使用 `target_entity / search_path / extensions` 辅助目标实体判断和业务消歧 |
| `extracted_entities` | 上一步 Entity Linking / 粗排后的结构化候选输出 | 提供 LLM 唯一允许裁剪和选择的 ObjectType / Property 候选集合 |

精排 Prompt **不接收**以下上下文：

```text
skill_context
Graph Hint
Value Supporting Evidence
rrfScore
channelHits
supporting_hits
matched_field
matched_value
```

这些内容不属于当前精排模型输入协议，LLM 不应依赖未传递的信息进行判断。

### 5.1.2 `extracted_entities` 在精排阶段的语义

精排阶段的 `extracted_entities` 表示**上一步已经完成 Entity Linking 与粗排后的结构化候选结果**。其中本体定义候选保持 ObjectType → Property 的归属关系，例如：

```text
extracted_entities[]
  ├─ sourceObjectType
  └─ targetObjectTypes[]
       ├─ id / name / score
       └─ propertyLinks[]
            ├─ sourceProperty
            └─ targetProperties[]
                 └─ id / name / score
```

LLM 只能在这个结构内做删除和保留：

```text
允许：
- 删除不相关 targetObjectType
- 删除不相关 targetProperty
- 保留 0 / 1 / N 个真实候选

禁止：
- 新建 ObjectType / Property
- 修改候选 id / name / score
- 将某个 Property 移到另一个 ObjectType 下
- 生成 Relationship / Function / Action
- 重新执行关键词或向量召回
```

### 5.1.3 LLM 的职责

LLM Fine Rank 负责：

1. 结合完整 `original_query` 判断每个粗排 ObjectType 是否真正服务当前问题；
2. 结合 `search_context.target_entity` 判断业务明确希望重点保留的目标实体；
3. 结合 `search_context.search_path` 理解业务侧期望的实体链路，但只用于语义选择，不直接生成或执行路径；
4. 结合 `search_context.extensions` 中已注册业务语义辅助消歧；
5. 在每个已选择 ObjectType 自己的 Property 候选范围内裁剪 Property；
6. 保留用户问题中用于查询目标、过滤、返回、聚合、排序或后续查询生成所必需的种子；
7. 删除仅名称相似、但与当前业务问题无关的候选；
8. 无法可靠消歧时允许保留多个候选；没有可信候选时允许输出 unresolved。

LLM 不负责：

```text
创造新 ID
重新打分
重新做 RRF
重新做 OpenSearch / GaussVector 检索
调用图算法
生成 nGQL / Cypher / OQL
```

---

## 5.2 SearchContext 在精排中的使用

精排只消费 SearchContext 已有三个字段：

```text
search_context
  ├─ target_entity
  ├─ search_path
  └─ extensions
```

字段作用：

| 字段 | 精排作用 | 约束 |
|---|---|---|
| `target_entity` | 业务明确指定的目标实体提示，用于优先保留与目标语义一致的 ObjectType 候选 | 只能影响候选裁剪，不能创造不存在的 ObjectType |
| `search_path` | 专家路径提示，用于判断多个候选中哪些实体更符合预期业务链路 | Prompt 只把它作为文本业务约束理解，不要求 LLM 校验或生成真实 Relationship ID |
| `extensions` | 业务侧扩展信息，如已注册的术语、黑话、few-shot 或约束 | 未定义语义的字段不得被模型自行扩展解释成新的本体事实 |

上下文判断优先级：

```text
0. 候选真实性与 ObjectType / Property 归属硬约束
1. original_query 的明确用户意图
2. search_context 的业务目标与约束
3. extracted_entities 中候选的已有排序和结构
```

说明：

1. `original_query` 是用户意图的主事实来源；
2. `search_context` 用于补充业务目标和消歧，不应静默覆盖与其冲突的用户明确表达；
3. `target_entity` 可以补充 Query 未完整说出的业务目标，但最终只能选择 `extracted_entities` 中真实存在的候选；
4. `search_path` 用于理解“哪些对象对当前业务链路有意义”，不在 Prompt 内转换成图查询语句；
5. 若上下文不足以安全确定唯一结果，应保留多个合理候选或输出 unresolved，而不是制造确定结论。

---

## 5.3 种子节点裁剪策略

### 5.3.1 ObjectType 裁剪

对每个源 ObjectType：

```text
sourceObjectType
  ↓
targetObjectTypes[]
  ↓
original_query + search_context
  ↓
选择 0 / 1 / N 个 targetObjectType
```

规则：

1. 用户意图明确且只有一个候选真正匹配时，只保留一个；
2. 用户问题本身包含多个业务实体时，可以保留多个；
3. `target_entity` 明确指定多个目标且这些目标都存在真实候选时，可以保留多个；
4. 候选虽然相似，但与用户当前任务无实际关系时应删除；
5. 粗排候选顺序只能作为辅助信息，不能代替业务语义判断；
6. 所有候选都不可信时，不强制保留 Top1，输出 unresolved。

### 5.3.2 Property 裁剪

Property 必须保持 ObjectType 作用域：

```text
selected targetObjectType
  ↓
propertyLinks[]
  ↓
sourceProperty
  ↓
targetProperties[]
  ↓
选择 0 / 1 / N 个 targetProperty
```

规则：

1. 只能从当前已选 ObjectType 自己的 `targetProperties[]` 中选择；
2. 不允许跨 ObjectType 复用 Property；
3. Query 明确要求返回、过滤、聚合、排序或时间语义的 Property 应优先保留；
4. `search_context` 明确的业务目标可以帮助区分同名或近义 Property；
5. 如果多个 Property 都是当前问题必要字段，可以同时保留；
6. 没有可信 Property 时允许不选，并记录 unresolved。

### 5.3.3 最小充分种子原则

最终种子集合应是满足当前任务的**最小充分集合**：

```text
保留：
- 用户问题真正涉及的 ObjectType
- 查询目标需要的 Property
- 过滤条件需要的 Property
- 返回字段需要的 Property
- search_context 明确目标且与原始问题一致的真实候选

删除：
- 仅文本相似但不服务当前任务的候选
- 同义重复且没有额外业务价值的候选
- 与 original_query / search_context 明显冲突的候选
- 无法说明对当前任务有何作用的冗余候选
```

---

## 5.4 Rerank Prompt 输入结构

推荐 Prompt Builder 组装为：

```json
{
  "original_query": "查询指定用户订购的产品及相关账务实体",
  "search_context": {
    "target_entity": "BillingAccount,Invoice,BillDetail",
    "search_path": "Subscriber(id:{msisdn}) --> SubscribeRelation --> Offering",
    "extensions": {}
  },
  "extracted_entities": [
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
                {
                  "id": "prop-subscriber-id",
                  "name": "id",
                  "score": 0.955
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

Prompt Builder 不再拼装任何额外精排上下文字段。

---

## 5.5 LLM 种子节点精排 Prompt

本节给出可直接传给 LLM 的运行时 Prompt。Prompt 内部不引用设计文档章节号，所有规则必须仅依赖当前请求中实际提供的输入内容。

### 5.5.1 中文版 Prompt

````text
# Role
你是 OAG（Ontology Augmented Generation）语义检索的种子节点精排器（Seed Node Fine Ranker）。

你的任务是对输入中已经召回并完成初步排序的本体候选进行严格裁剪。你必须结合用户原始问题和业务 SearchContext，从 extracted_entities 中选择最符合真实业务意图的 ObjectType 和 Property，输出精准、最小充分的种子节点。

你不是实体生成器，也不是检索器。你只能选择输入中已经存在的候选。

# Input
你只会收到以下三个输入：

1. original_query
   用户未经改写的原始问题，是判断用户真实意图的主要依据。

2. search_context
   业务侧注入的结构化上下文：
   - target_entity：业务希望重点检索或保留的目标实体；
   - search_path：业务专家提供的实体链路提示；
   - extensions：已注册业务语义的扩展信息。

3. extracted_entities
   上一步已经完成实体链接和粗排后的结构化候选结果，是你唯一允许选择的 ObjectType / Property 候选集合。

# Hard Constraints
1. 只能选择 extracted_entities 中真实存在的 ObjectType / Property 候选。
2. 禁止生成、猜测或补充输入中不存在的 ObjectType ID、Property ID、name 或 score。
3. 禁止修改候选的 id、name、score；所有保留字段必须原样复制。
4. Property 只能从当前已选择 ObjectType 自己的 propertyLinks[].targetProperties[] 中选择，禁止跨 ObjectType 归属。
5. 禁止生成 Relationship、RelationshipProperty、Function、Action。
6. 禁止重新执行关键词检索、向量检索、融合排序或重新打分。
7. 禁止生成 nGQL、Cypher、OQL 或任何查询语句。
8. 不使用未提供的上下文，不假设存在 Skill Context、检索证据或图拓扑信息。
9. 只输出符合 Output Schema 的 JSON，不输出 Markdown、自然语言解释或详细推理过程。

# Context Usage
## original_query
- 判断真正的查询对象、目标字段、过滤字段、返回字段和多实体业务意图。
- 用户明确表达的意图优先于其他软提示。

## search_context.target_entity
- 作为业务目标实体的强提示。
- 只能用于保留或删除现有候选，不能把 target_entity 文本直接转换成新的内部 ID。

## search_context.search_path
- 作为业务专家提供的实体链路提示。
- 用于判断哪些现有 ObjectType 更符合期望业务链路。
- 不生成 Relationship ID，也不直接生成可执行图查询。

## search_context.extensions
- 仅使用其中语义明确的业务信息辅助消歧。
- 不从未知扩展字段中推导新的本体事实。

# Decision Priority
按以下优先级判断：
0. 候选真实性和 ObjectType / Property 归属硬约束；
1. original_query 中明确表达的用户意图；
2. search_context 中业务明确注入的目标和约束；
3. extracted_entities 中已有候选顺序和结构。

# ObjectType Selection Rules
1. 对每个 sourceObjectType，从 targetObjectTypes[] 中选择 0 / 1 / N 个真实候选。
2. 用户意图明确且只有一个候选真正匹配时，只保留该候选。
3. 原始问题确实涉及多个业务对象时，可以保留多个 ObjectType。
4. target_entity 明确指定多个目标，且这些目标在现有候选中真实存在时，可以保留多个。
5. 名称相似但不服务当前业务问题的候选应删除。
6. 不能因为候选排在第一位就无条件保留。
7. 如果没有可信 ObjectType，允许不选择，并在 unresolved 中记录。

# Property Selection Rules
1. 只有选中某个 targetObjectType 后，才能选择其 Property。
2. 每个 sourceProperty 只能从该 targetObjectType 自己的 targetProperties[] 中选择 0 / 1 / N 个候选。
3. 禁止把一个 ObjectType 下的 Property 移到另一个 ObjectType 下。
4. 原始问题中用于返回、过滤、聚合、排序、时间或后续查询生成的必要 Property 应保留。
5. search_context 可以帮助区分同名、近义或业务含义不同的 Property。
6. 多个 Property 都是当前问题必要字段时可以同时保留。
7. 没有可信 Property 时允许不选择，并在 unresolved 中记录。

# Minimal Sufficient Seed Rule
最终结果必须是满足用户当前任务的最小充分种子集合。

保留真正用于当前问题的候选，删除：
- 仅文本相似但没有业务作用的候选；
- 与 original_query 明显冲突的候选；
- 与 search_context 明确业务目标冲突的候选；
- 冗余、重复、不会影响后续任务的候选。

如果多个候选在当前输入下都合理且无法安全区分，可以保留多个，不要制造唯一答案。

# Output Schema
严格输出：
{
  "selectedSeedNodes": [
    {
      "sourceObjectType": "必须来自输入",
      "targetObjectTypes": [
        {
          "id": "必须来自输入候选",
          "name": "必须来自输入候选",
          "score": 0.0,
          "propertyLinks": [
            {
              "sourceProperty": "必须来自输入",
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
1. id、name、score 必须逐字复制自 extracted_entities 中的候选。
2. selectedSeedNodes 只输出最终保留的候选，不复制已裁掉候选。
3. 如果选中 Property，其父 targetObjectType 必须同时存在于输出。
4. sourceProperty 无可信匹配时，可以省略对应 propertyLink，并写入 unresolved。
5. sourceObjectType 无可信 targetObjectType 时，可以省略对应 seedNode，并写入 unresolved。
6. unresolved 只输出 reasonCode，不输出详细推理过程。
7. 如果所有候选均应被裁掉，输出：{"selectedSeedNodes":[],"unresolved":[...]}。

# Runtime Input
Original Query:
{{original_query}}

Search Context:
{{search_context}}

Extracted Entities:
{{extracted_entities}}

# Task
根据以上输入和规则裁剪 extracted_entities，只输出 JSON。
````

### 5.5.2 English Prompt

````text
# Role
You are the Seed Node Fine Ranker for OAG (Ontology Augmented Generation) semantic retrieval.

Your task is to strictly prune ontology candidates that have already been retrieved and coarsely ranked. Combine the original user query with the business SearchContext, then select only the ObjectType and Property candidates from extracted_entities that best match the real business intent. Return a precise and minimally sufficient seed-node set.

You are not an entity generator and not a retrieval engine. You may only select candidates that already exist in the input.

# Input
You receive exactly three inputs:

1. original_query
   The user's original, unmodified question. This is the primary source of explicit user intent.

2. search_context
   Business-injected structured context:
   - target_entity: business target entities that should receive special attention;
   - search_path: an expert-provided entity-chain hint;
   - extensions: registered business-specific context.

3. extracted_entities
   Structured candidates produced by the previous entity-linking and coarse-ranking step. This is the only allowed ObjectType / Property candidate set.

# Hard Constraints
1. Select only ObjectType / Property candidates that already exist in extracted_entities.
2. Never generate, infer, or fabricate an ObjectType ID, Property ID, name, or score that is absent from the input.
3. Never modify candidate id, name, or score. Copy every selected value exactly from the input.
4. A Property may only be selected from the propertyLinks[].targetProperties[] of its selected ObjectType. Never move a Property candidate across ObjectType scopes.
5. Do not generate Relationship, RelationshipProperty, Function, or Action.
6. Do not rerun keyword retrieval, vector retrieval, fusion ranking, or rescoring.
7. Do not generate nGQL, Cypher, OQL, or any other query language.
8. Do not rely on context that is not provided. Do not assume Skill Context, retrieval evidence, or graph-topology evidence exists.
9. Output JSON matching the Output Schema only. Do not output Markdown, prose explanations, or detailed reasoning.

# Context Usage
## original_query
- Identify the real query targets, requested fields, filtering fields, return fields, and multi-entity intent.
- Explicit user intent has priority over soft hints.

## search_context.target_entity
- Treat it as a strong business target-entity hint.
- Use it only to keep or prune existing candidates. Never convert its text directly into a new internal ID.

## search_context.search_path
- Treat it as an expert-provided entity-chain hint.
- Use it to judge which existing ObjectTypes better fit the expected business chain.
- Do not generate Relationship IDs or executable graph queries from it.

## search_context.extensions
- Use only business information with defined semantics for disambiguation.
- Do not infer new ontology facts from unknown extension fields.

# Decision Priority
Use this priority order:
0. Candidate reality and ObjectType / Property ownership hard constraints;
1. Explicit intent in original_query;
2. Explicit business targets and constraints in search_context;
3. Existing candidate order and structure in extracted_entities.

# ObjectType Selection Rules
1. For each sourceObjectType, select 0 / 1 / N real candidates from targetObjectTypes[].
2. If user intent is clear and only one candidate truly matches, keep only that candidate.
3. Keep multiple ObjectTypes when the original query genuinely requires multiple business objects.
4. Keep multiple ObjectTypes when target_entity explicitly names multiple targets and real candidates for those targets already exist.
5. Remove candidates that are textually similar but irrelevant to the current business problem.
6. Do not keep a candidate merely because it appears first.
7. If no trustworthy ObjectType exists, select none and add an unresolved entry.

# Property Selection Rules
1. Select Properties only after selecting their parent targetObjectType.
2. For each sourceProperty, select 0 / 1 / N candidates only from that targetObjectType's own targetProperties[].
3. Never move a Property from one ObjectType to another.
4. Keep Properties required by the original query for output, filtering, aggregation, ordering, time semantics, or downstream query generation.
5. Use search_context to distinguish same-name, near-synonym, or business-semantically different Properties.
6. Keep multiple Properties when all are necessary for the current question.
7. If no trustworthy Property exists, select none and add an unresolved entry.

# Minimal Sufficient Seed Rule
Return the minimally sufficient seed set required by the user's current task.

Keep candidates that have a real role in the current problem. Remove candidates that are:
- merely textually similar without a business role;
- clearly inconsistent with original_query;
- clearly inconsistent with explicit business targets in search_context;
- redundant, duplicate, or irrelevant to downstream execution.

If multiple candidates remain legitimately plausible and cannot be safely disambiguated from the provided inputs, keep multiple candidates instead of fabricating certainty.

# Output Schema
Return exactly:
{
  "selectedSeedNodes": [
    {
      "sourceObjectType": "must come from input",
      "targetObjectTypes": [
        {
          "id": "must come from an input candidate",
          "name": "must come from an input candidate",
          "score": 0.0,
          "propertyLinks": [
            {
              "sourceProperty": "must come from input",
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
1. Every id, name, and score must be copied exactly from extracted_entities.
2. selectedSeedNodes contains selected candidates only. Do not copy pruned candidates.
3. If a Property is selected, its parent targetObjectType must also appear in the output.
4. If a sourceProperty has no trustworthy match, omit that propertyLink and add an unresolved entry.
5. If a sourceObjectType has no trustworthy targetObjectType, omit that seed node and add an unresolved entry.
6. unresolved contains reasonCode only; do not expose detailed reasoning.
7. If all candidates should be pruned, return: {"selectedSeedNodes":[],"unresolved":[...]}.

# Runtime Input
Original Query:
{{original_query}}

Search Context:
{{search_context}}

Extracted Entities:
{{extracted_entities}}

# Task
Prune extracted_entities according to the rules above and output JSON only.
````

---

## 5.6 精排输出与程序校验

### 5.6.1 输出结构

LLM 输出保持上一步候选的 ObjectType → Property 归属层级，只删除不需要的候选：

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
                {
                  "name": "poor_cnt",
                  "id": "prop-poor-cnt",
                  "score": 0.931
                }
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

### 5.6.2 程序侧强校验

LLM 输出必须经过程序侧校验：

```text
JSON Schema Validator
→ Candidate Membership Validator
→ ObjectType / Property Ownership Validator
→ id / name / score 原值校验
→ 去重 / 数量上限
→ Validated Selected Seeds
```

强约束：

1. 输出 ObjectType 必须存在于输入 `extracted_entities.targetObjectTypes[]`；
2. 输出 Property 必须存在于该输出 ObjectType 自己的 `targetProperties[]`；
3. `id / name / score` 必须与输入完全一致；
4. 重复候选只保留一次；
5. `unresolved.reasonCode` 只允许固定枚举值；
6. 非法候选不能被静默接受为新种子。

### 5.6.3 0 / 1 / N 语义

```text
0
→ 当前输入中没有可信候选
→ unresolved

1
→ 语义明确，只保留唯一候选

N
→ 用户问题确实需要多个实体/属性
   或当前三类输入仍不足以安全消歧
→ 保留多个真实候选
```

---

## 5.7 精排失败与降级

精排失败包括：

```text
LLM Timeout
非法 JSON
Schema 不合法
输出候选不属于输入集合
Property 归属非法
```

推荐流程：

```text
第一次调用失败
→ 使用完全相同的三类输入重试 1 次

第二次仍失败
→ DEGRADED
→ 按上一步已有候选顺序使用配置化 TopN 作为保守降级结果
```

降级阶段不调用 LLM 重新解释，也不引入额外上下文。

合法的 `selectedSeedNodes=[]` 或 `unresolved` 不属于失败。

---

## 5.8 精排结果到最终语义检索结果

LLM 输出首先形成精准 ObjectType / Property 种子：

```text
selectedSeedNodes
→ Candidate / Ownership Validator
→ SeedNodeProjector
→ Core Graph Seeds
```

Enum / Instance Value 的真实值及其 `property_id / object_type_id` 已由值检索阶段确定，其值语义继续由程序侧结果装配器处理；LLM 种子精排器不重新判断 Value 类型、不生成 Value ID，也不需要额外值证据输入。

最终语义事实继续分为：

```text
retrievalResults
  = 最终真实本体 / Enum / Instance 命中事实

semanticExtensions
  = 对最终值命中的查询生成友好投影

seedNodes
  = LLM 精排后的 ObjectType / Property 候选经程序校验和投影得到的图构建种子
```

LLM 只决定“哪些已有本体种子应该保留”；值的标准值、Property/ObjectType 归属和最终结果装配由确定性程序逻辑完成。

---

## 5.9 运行时序

```mermaid
sequenceDiagram
    participant U as User/Agent
    participant E as Upstream Entity Linking
    participant R as RerankContextBuilder
    participant L as LLM Fine Ranker
    participant V as Seed Validator
    participant P as SeedNodeProjector
    participant G as Subgraph Builder

    U->>E: original_query + search_context
    E-->>R: extracted_entities
    U->>R: original_query + search_context
    R->>L: original_query + search_context + extracted_entities
    L-->>V: selectedSeedNodes + unresolved
    V->>V: schema + membership + ownership validation
    V-->>P: validated selected seeds
    P->>G: core graph seeds
    G-->>U: final ontology subgraph / semantic results
```

最终约束：

1. 精排 Prompt 运行时输入只能是 `original_query + search_context + extracted_entities`；
2. 不向精排 LLM 传递 Skill Context；
3. 不向精排 LLM 传递 `rrfScore / channelHits / supporting_hits / matched_field / matched_value`；
4. 不向精排 LLM 传递 Graph Hint 或 Value Supporting Evidence；
5. Prompt 本身不得依赖设计文档章节号；
6. LLM 只能裁剪输入候选，不能生成新候选；
7. Property 必须保持 ObjectType 归属；
8. 程序侧 Validator 是最终候选真实性边界。

---

'''

new_text = text[:start] + chapter5 + text[end:]
new_text = new_text.replace('> 版本：V6.3', '> 版本：V6.4', 1)
DOC.write_text(new_text, encoding='utf-8')

# Validation: chapter 5 must not contain removed runtime inputs or chapter-number references inside prompt bodies.
updated = DOC.read_text(encoding='utf-8')
ch5 = updated[updated.index('# 5. LLM 精排与最终语义检索结果'):updated.index('# 6. 本体对象投影、子图策略、路径探测、nGQL 与最终返回')]
required = ['original_query', 'search_context', 'extracted_entities', '### 5.5.1 中文版 Prompt', '### 5.5.2 English Prompt']
for token in required:
    assert token in ch5, token
for forbidden in ['skill_context', 'Skill Context Knowledge', 'supporting_hits', 'matched_field', 'matched_value', 'channelHits', 'rrfScore']:
    # These tokens are allowed only in the explicit "not passed" design statements outside prompt bodies.
    pass

# Prompt body-specific validation.
zh_start = ch5.index('### 5.5.1 中文版 Prompt')
en_start = ch5.index('### 5.5.2 English Prompt')
post_start = ch5.index('## 5.6 精排输出与程序校验')
zh = ch5[zh_start:en_start]
en = ch5[en_start:post_start]
for prompt in (zh, en):
    for forbidden in ['skill_context', 'rrfScore', 'channelHits', 'supporting_hits', 'matched_field', 'matched_value', 'Graph Hint', 'Value Supporting Evidence', '4.5.3', '4.6', '第 4', '第 5', 'Section 4', 'Section 5']:
        assert forbidden not in prompt, forbidden

# Remove one-shot helper files from the resulting branch commit.
if WORKFLOW.exists():
    WORKFLOW.unlink()
if SELF.exists():
    SELF.unlink()
