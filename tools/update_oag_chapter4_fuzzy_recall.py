from pathlib import Path

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
WORKFLOW = Path('.github/workflows/one-shot-oag-ch4-fuzzy-recall.yml')
SCRIPT = Path('tools/update_oag_chapter4_fuzzy_recall.py')

CHAPTER4 = r'''# 4. 实体提取、Entity Linking 与 6 路混合召回

本章定义从 `extractedEntities` 结构化实体结果到真实本体 ObjectType / Property / Enum Value / Instance Value 的候选召回、归属解析与粗排。在线检索统一采用：

> **OpenSearch 关键词模糊检索（Keyword Fuzzy） + GaussVector 向量检索（Dense） + Weighted RRF。**

“6 路”表示系统总共有 6 条检索通道，但**不是每个 Semantic Unit 都执行 6 路**。基于 `ExtractedEntity` 的结构化语义直接路由：

```text
ObjectType / Properties
  → 本体定义索引
  → 2 路：ontologyObjectLexical + ontologyObjectDense
  → 2 路 Weighted RRF

Values
  → 枚举元素索引 + 实例元素索引
  → 4 路：enumLexical + enumDense + instanceLexical + instanceDense
  → 4 路 Weighted RRF
```

执行主线统一为：

```text
query + searchContext / extractedEntities
→ Entity Extraction
→ ExtractedEntity Normalize
→ OBJECT_TYPE / PROPERTY / VALUE Semantic Units
→ 按 Semantic Unit 类型路由
   ├─ OBJECT_TYPE / PROPERTY → 本体定义 2 路混合召回
   └─ VALUE                 → 值 4 路混合召回
→ SearchHit 标准化
→ 通道内按真实本体归属去重
→ 分类型 Weighted RRF
→ ObjectType 作用域内 Property Linking
→ Enum / Instance Value Linking
→ Entity Linking 粗排结果 + supporting_hits
→ 第 5 章 LLM Fine Rank
```

本章只负责**候选召回、归属解析和粗排**；LLM 最终选择、0/1/N 判定与 `retrievalResults` 生成由第 5 章负责。

---

## 4.1 实体提取结构化输入与 Semantic Unit 路由

### 4.1.1 ExtractedEntity 数据模型

实体提取是子图检索的第 ① 步，输入为 `query + searchContext`，或者直接接收业务侧提供的 `extractedEntities`。正式结构只包含：

```text
ExtractedEntity
  ├─ ObjectType?
  ├─ Properties[]
  └─ Values[]
       ├─ Property?
       └─ Value
```

标准结构：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "字符串",
      "Properties": ["属性1", "属性2"],
      "Values": [
        {
          "Property": "属性1",
          "Value": "用户原始业务值"
        },
        {
          "Value": "归属暂不确定的业务值"
        }
      ]
    },
    {
      "Values": [
        {
          "Value": "完全无法确定 ObjectType/Property 归属的业务值"
        }
      ]
    }
  ]
}
```

核心规则：

1. `ObjectType` 生成 OBJECT_TYPE Semantic Unit；
2. `Properties[]` 中每个 Property 生成 PROPERTY Semantic Unit，并继承所属 `ObjectType` 作用域；
3. `Values[]` 中每个 Value 生成 VALUE Semantic Unit；
4. Value 携带 `Property` 时，将该 Property 作为强归属 Hint；
5. Value 未携带 `Property`、但位于带 `ObjectType` 的实体内时，保留 ObjectType 作用域，Property 由值索引命中后解析；
6. ObjectType/Property 都未知的 value-only 允许跨 Enum / Instance 索引检索后再确定真实归属；
7. Entity Extraction 不区分 Enum Value / Instance Value，不根据编码形态猜 Site/BaseStation/nativeId 等类型；
8. Relationship 不由实体提取直接输出，专家路径通过 `searchContext.search_path` 进入后续图规划；
9. 连续数值、时间、比较、聚合语义默认保留在原始 `query`，不强行塞入 `Values`。

完整 Schema、Prompt、SearchContext 和兼容规则见 [OAG语义子图检索接口extractedEntities结构设计方案](./OAG语义子图检索接口extractedEntities结构设计方案.md)。

### 4.1.2 结构化结果到 Semantic Unit

Entity Extraction 已经完成语义短语识别，检索阶段**不再二次按词法逐词拆分**。例如：

```text
ObjectType = "FORMAL用户"
Property   = "Mobile Number"
```

默认分别作为完整 Semantic Unit 检索，不拆成：

```text
FORMAL / 用户 / Mobile / Number
```

只有 Query Understanding 明确产出辅助短语时，才允许作为额外 evidence；主检索单元始终优先使用完整业务表达。

结构化转换：

```text
ExtractedEntity(ObjectType="Account")
→ OT:Account

Properties=["accountStatus", "customerLevel"]
→ PROP:Account:accountStatus
→ PROP:Account:customerLevel

Values=[
  {Property="accountStatus", Value="在用"},
  {Property="customerLevel", Value="VIP"}
]
→ VALUE:Account:accountStatus:在用
→ VALUE:Account:customerLevel:VIP
```

### 4.1.3 Semantic Unit 检索路由

| Semantic Unit | 输入来源 | 检索对象 | 通道数 | 融合方式 |
|---|---|---|---:|---|
| `OBJECT_TYPE` | `ExtractedEntity.ObjectType` | 本体对象索引中的 ObjectType | 2 | 本体定义 2 路 Weighted RRF |
| `PROPERTY` | `ExtractedEntity.Properties[]` | 当前候选 ObjectType 作用域内的 Property | 2 | 本体定义 2 路 Weighted RRF |
| `VALUE` | `ExtractedEntity.Values[]` | Enum Value + Instance Value | 4 | 值 4 路 Weighted RRF |

因此总体 6 个通道的职责边界为：

```text
本体定义：2 路
  ontologyObjectLexical
  ontologyObjectDense

值：4 路
  enumLexical
  enumDense
  instanceLexical
  instanceDense
```

禁止把 OBJECT_TYPE / PROPERTY Semantic Unit 无差别发送到 Enum/Instance 索引；也禁止把 VALUE Semantic Unit 发送到本体对象索引后与本体定义候选混在同一 Ranked List 中。

---

## 4.2 6 路混合召回与 Retrieval Profile

### 4.2.1 六个物理检索通道

| 逻辑域 | 通道 | 存储 | 在线查询方式 | 适用 Semantic Unit |
|---|---|---|---|---|
| 本体定义 | `ontologyObjectLexical` | OpenSearch | Keyword Fuzzy | OBJECT_TYPE / PROPERTY |
| 本体定义 | `ontologyObjectDense` | GaussVector | Dense / COSINE | OBJECT_TYPE / PROPERTY |
| 枚举值 | `enumLexical` | OpenSearch | Keyword Fuzzy | VALUE |
| 枚举值 | `enumDense` | GaussVector | Dense / COSINE | VALUE |
| 实例值 | `instanceLexical` | OpenSearch | Keyword Fuzzy | VALUE |
| 实例值 | `instanceDense` | GaussVector | Dense / COSINE | VALUE |

历史实现若仍读取 `seed* / metadata* / instance*`，只允许在配置兼容层做别名映射；新代码、新配置和日志统一使用上述 6 个正式通道名。

### 4.2.2 OpenSearch 关键词模糊检索

OpenSearch 的 lexical 通道统一采用**关键词模糊查询**，使用 Analyzer + BM25 排序 + `fuzziness` 扩展召回，不再维护独立的精确字符串召回通道。

在线评分查询推荐：

```json
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"type": "OBJECT_TYPE"}}
      ],
      "must": [
        {
          "multi_match": {
            "query": "无线小区",
            "type": "best_fields",
            "fields": [
              "name^4",
              "display_zh^3",
              "display_en^3",
              "display_lang_1^2.5",
              "display_lang_2^2.5",
              "synonyms^3",
              "description_zh^1.5",
              "description_en^1.5",
              "description_lang_1^1.2",
              "description_lang_2^1.2"
            ],
            "fuzziness": "AUTO",
            "prefix_length": 1,
            "max_expansions": 50,
            "minimum_should_match": "70%"
          }
        }
      ]
    }
  }
}
```

三类索引建议字段：

```text
本体对象：
  name / display_* / synonyms / description_*

Enum Value：
  value / display_* / synonyms / description_*

Instance Value：
  value / synonyms
```

初始 Boost 建议：

```text
name/value        4.0
synonyms          3.0
display_*         2.5~3.0
description_*     1.0~1.5
```

说明：

1. OpenSearch 的 `_score` 只用于 lexical 通道内部排序，进入 RRF 后只消费 rank；
2. `fuzziness=AUTO`、`prefix_length`、`max_expansions`、`minimum_should_match` 必须通过离线评测和目标语言调优；
3. 中文、英文和小语种继续使用第 2 章定义的 Analyzer/多语言字段；
4. `synonyms` 仍是记录字段，不拆成独立召回通道；
5. `type / parent_id / property_id / object_type_id` 等结构约束可以使用 keyword filter，但 filter 只用于限定候选域，不构成新的 lexical Ranked List；
6. 在线语义召回不再设置单独的字符串精确匹配分支，不再形成额外 Ranked List。

#### Property 作用域查询

Property lexical 检索必须使用候选 ObjectType 归属 filter：

```json
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"type": "PROPERTY"}},
        {"term": {"parent_id": "<targetObjectTypeId>"}}
      ],
      "must": [
        {
          "multi_match": {
            "query": "客户等级",
            "fields": ["name^4", "display_*^3", "synonyms^3", "description_*^1.5"],
            "fuzziness": "AUTO"
          }
        }
      ]
    }
  }
}
```

这里 `term` 仅作为结构过滤器，不参与关键词召回评分。

### 4.2.3 GaussVector Dense 检索

Dense 通道使用第 2 章定义的 BGE-M3 1024 维向量和 COSINE 相似度。每类索引独立执行 ANN TopK：

```text
ontologyObjectDense
  → t_oag_{ontology_id}

enumDense
  → t_oag_enum_{ontology_id}

instanceDense
  → t_oag_instance_{ontology_id}
```

Dense 规则：

```text
query text
→ Embedding
→ ANN TopK
→ similarityThreshold
→ Ranked List
```

`similarityThreshold` 只作用于 Dense 通道；OpenSearch Keyword Fuzzy 不使用 Dense 阈值过滤。

### 4.2.4 topK / similarityThreshold 分域配置

```yaml
semanticRetrieval:
  defaults:
    topK: 3
    similarityThreshold: 0.6

  ontologyObject:
    lexicalTopK: 10
    denseTopK: 10
    similarityThreshold: 0.6

  enum:
    lexicalTopK: 10
    denseTopK: 10
    similarityThreshold: 0.6

  instance:
    lexicalTopK: 5
    denseTopK: 5
    similarityThreshold: 0.6
```

说明：

- 本体定义优先保证 Recall；
- Enum 允许多个 value/display/synonym 命中同一 Property；
- Instance 数据量最大，TopK 初始更保守；
- 三类 Dense 分数分布不同，阈值必须独立校准；
- lexicalTopK 与 denseTopK 独立配置，避免一个统一 TopK 提前裁掉有价值候选。

配置优先级：

```text
Request Retrieval Profile
>
Domain/Table Config
>
System Defaults
```

### 4.2.5 seedRetrievalMode 兼容

接口兼容：

```text
vector
keyword
hybrid
```

语义统一为：

```text
vector:
  OBJECT_TYPE / PROPERTY → ontologyObjectDense
  VALUE                  → enumDense + instanceDense

keyword:
  OBJECT_TYPE / PROPERTY → ontologyObjectLexical
  VALUE                  → enumLexical + instanceLexical

hybrid:
  OBJECT_TYPE / PROPERTY → ontologyObjectLexical + ontologyObjectDense
  VALUE                  → enumLexical + enumDense + instanceLexical + instanceDense
```

推荐在线模式为 `hybrid`。历史默认值如果仍为 `vector`，可通过配置灰度切换，但不改变上述通道职责。

---

## 4.3 SearchHit 标准化与证据保留

### 4.3.1 统一 SearchHit

RRF 前，OAG 将 GaussVector 与 OpenSearch 结果统一成 SearchHit，不向上层透出底层存储原生结构。

#### 本体对象 Keyword Fuzzy SearchHit

```json
{
  "id": "dtmi:com:huawei:ict:Cell:1.0",
  "type": "OBJECT_TYPE",
  "name": "Cell",
  "parent_id": null,
  "matched_field": "synonyms",
  "matched_value": "小区",
  "score": 12.37,
  "retrieval_mode": "KEYWORD_FUZZY",
  "channel": "ontologyObjectLexical"
}
```

#### 本体对象 Dense SearchHit

```json
{
  "id": "dtmi:com:huawei:ict:Cell:1.0",
  "type": "OBJECT_TYPE",
  "name": "Cell",
  "matched_field": "DENSE_VECTOR",
  "matched_value": null,
  "distance": 0.18,
  "score": 0.82,
  "retrieval_mode": "DENSE",
  "channel": "ontologyObjectDense"
}
```

#### Enum Keyword Fuzzy SearchHit

```json
{
  "propertyId": "prop:ont:vehicle:sp:bodyColor",
  "objectTypeId": "vehicle-object-id",
  "type": "ENUM_VALUE",
  "value": "red",
  "matched_field": "synonyms",
  "matched_value": "Rojo",
  "score": 18.42,
  "retrieval_mode": "KEYWORD_FUZZY",
  "channel": "enumLexical"
}
```

#### Instance Keyword Fuzzy SearchHit

```json
{
  "propertyId": "subClass-property-id",
  "objectTypeId": "subscriber-object-id",
  "type": "INSTANCE_VALUE",
  "value": "VIP",
  "matched_field": "value",
  "matched_value": "VIP",
  "score": 9.31,
  "retrieval_mode": "KEYWORD_FUZZY",
  "channel": "instanceLexical"
}
```

Dense 的 Enum/Instance SearchHit 使用相同业务身份字段，只将 `retrieval_mode/channel/score/distance` 切换到对应 Dense 通道。

`matched_field / matched_value` 用于解释用户文本具体命中了 `name/display/description/synonyms/value` 中哪一项。对于 fuzziness 命中，`matched_value` 保存命中字段中最能解释本次匹配的真实源文本，不保存查询扩展词本身。

### 4.3.2 group_id 与通道内去重

统一分组：

```text
ObjectType hit：
  group_id = "OT:" + hit.id

Property hit：
  group_id = "PROP:" + hit.parent_id + ":" + hit.id

Enum Value hit：
  group_id = "PROP:" + hit.objectTypeId + ":" + hit.propertyId

Instance Value hit：
  group_id = "PROP:" + hit.objectTypeId + ":" + hit.propertyId
```

同一 Property 可能通过多个 Enum/Instance value 或 synonyms 命中。RRF 前按：

```text
semantic_unit_id + channel + group_id
```

通道内去重，使同一候选归属在同一通道只占一个 rank；同时保留：

```text
primary_hit
top 3~5 supporting_hits
hit_count
```

所有 supporting hit 必须保留 `recordType / objectTypeId / propertyId / value / matched_field / matched_value / channel / rank` 等真实证据字段。

---

## 4.4 分类型 Weighted RRF：本体定义 2 路、值 4 路

### 4.4.1 融合原则

本设计不再让每个 Semantic Unit 无差别进入 6 路，也不对 6 条通道做一个跨语义类型的统一 RRF。

采用两种 Fusion Profile：

```text
OntologyDefinitionFusion（2 路）
  ontologyObjectLexical
  ontologyObjectDense

ValueFusion（4 路）
  enumLexical
  enumDense
  instanceLexical
  instanceDense
```

每个 Semantic Unit 只在自己的 Fusion Profile 内执行一次 Weighted RRF：

```text
RRF(candidate) = Σ weight(channel) / (k + rank_channel(candidate))
```

RRF 不直接比较 OpenSearch `_score` 与 Dense cosine 分数，只消费通道内 rank。

### 4.4.2 推荐权重

```yaml
rrf:
  k: 60
  coarseTopKPerSemanticUnit: 20
  maxGlobalCandidates: 50

  ontologyDefinition:
    channelWeights:
      ontologyObjectLexical: 1.3
      ontologyObjectDense: 1.0

  value:
    channelWeights:
      enumLexical: 1.2
      enumDense: 1.0
      instanceLexical: 1.0
      instanceDense: 0.8
```

权重含义：

- 本体定义名称/显示名/同义词通常具有较高词面辨识度，初始给予 lexical 较高权重；
- Enum 的业务语义通常比自由实例值更稳定，因此 Enum lexical/dense 权重略高；
- Instance 规模最大、噪声更高，初始权重更保守；
- 所有权重必须通过真实 Query 集离线评测校准，不写死为协议常量。

### 4.4.3 本体定义 2 路融合样例

查询 Semantic Unit：

```text
OBJECT_TYPE = "无线小区"
```

候选：

| 通道 | A=`Cell` | B=`RadioCell` |
|---|---:|---:|
| ontologyObjectLexical | rank=1 | rank=2 |
| ontologyObjectDense | rank=2 | rank=1 |

则：

```text
A = 1.3/(60+1) + 1.0/(60+2)
B = 1.3/(60+2) + 1.0/(60+1)
```

RRF 只使用 rank，OpenSearch `_score` 与 cosine 不需要归一到同一数值空间。

### 4.4.4 Value 4 路融合样例

查询：

```text
VALUE = "VIP"
```

候选先根据真实索引记录投影到 Property 归属，例如：

```text
A = Account.customerLevel
B = Subscriber.subscriberLevel
```

四路 rank：

| 通道 | A | B |
|---|---:|---:|
| enumLexical | rank=1 | 未命中 |
| enumDense | rank=2 | 未命中 |
| instanceLexical | rank=3 | rank=1 |
| instanceDense | rank=2 | rank=1 |

计算：

```text
A = 1.2/(60+1) + 1.0/(60+2) + 1.0/(60+3) + 0.8/(60+2)
B = 1.0/(60+1) + 0.8/(60+1)
```

候选组内继续保留 Enum/Instance 的具体 `value + matched_field + matched_value + supporting_hits`，避免只留下 Property 而丢失用户值证据。

### 4.4.5 开发伪代码

```java
FusionProfile profile = switch (unit.type()) {
    case OBJECT_TYPE, PROPERTY -> ontologyDefinitionProfile; // 2 channels
    case VALUE -> valueProfile;                              // 4 channels
};

for (RankedList channel : profile.channels()) {
    double w = profile.weight(channel.name());
    for (int i = 0; i < channel.size(); i++) {
        int rank = i + 1;
        Candidate c = normalizeAndProject(channel.get(i), unit);
        c.rrfScore += w / (rrfK + rank);
        c.addEvidence(channel.name(), rank, channel.get(i));
    }
}
```

Dense 在进入 RRF 前执行 `similarityThreshold`；Keyword Fuzzy 由 OpenSearch 查询自身的 `minimum_should_match / fuzziness / TopK` 控制召回边界。

---

## 4.5 ObjectType / Property Entity Linking：本体定义 2 路

### 4.5.1 ObjectType Linking

对于每个 `ExtractedEntity.ObjectType`：

```text
sourceObjectType
→ ontologyObjectLexical（OpenSearch Keyword Fuzzy）
→ ontologyObjectDense（GaussVector Dense）
→ 按 OT:{objectTypeId} 通道内去重
→ 本体定义 2 路 Weighted RRF
→ targetObjectTypes[]
```

ObjectType 默认保留 Top 3 粗排候选，具体数量由 Retrieval Profile 控制。

### 4.5.2 Property 必须在候选 ObjectType 作用域内检索

对于 `Properties[]`，链接顺序固定为：

```text
sourceObjectType
  → targetObjectTypes[]
  → 对每一个 targetObjectType.id 分别处理 sourceProperty
     ├─ ontologyObjectLexical + parent_id filter
     └─ ontologyObjectDense   + parent_id filter
  → 每个 Property 单独执行本体定义 2 路 RRF
  → propertyLinks[]
```

结构约束：

```text
GaussVector:
  type = PROPERTY
  AND parent_id = targetObjectType.id

OpenSearch filter:
  type = PROPERTY
  AND parent_id = targetObjectType.id

GraphTopologyCache:
  Property 必须属于该 ObjectType
```

禁止先在全本体范围检索 Property，再把同一候选列表挂到所有 ObjectType 下。

### 4.5.3 粗排输出结构

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

字段定义：

| 字段 | 类型 | 说明 |
|---|---|---|
| `sourceObjectType` | String | Entity Extraction 输出的原始 ObjectType |
| `targetObjectTypes[]` | Array | 2 路 RRF 后的真实 ObjectType 候选 |
| `targetObjectTypes[].score` | Number | 由 RRF 分数单调归一后的粗排分数，不等同 OpenSearch `_score` 或 cosine |
| `propertyLinks[]` | Array | 当前 targetObjectType 作用域内的 Property 链接 |
| `sourceProperty` | String | Entity Extraction 输出的原始 Property |
| `targetProperties[]` | Array | 当前 ObjectType 下经 2 路 RRF 后的 Property 候选 |

示例：

```json
{
  "seedNodes": [
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
                {"name": "poor_cnt", "id": "prop-poor-cnt", "score": 0.931},
                {"name": "call_drop", "id": "prop-call-drop", "score": 0.911}
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
  ]
}
```

内部仍保留每个候选的 `rrfScore / channelHits / supporting_hits / matched_field / matched_value`，供第 5 章 LLM Fine Rank 使用。

### 4.5.4 排序与异常规则

1. `targetObjectTypes` 按 ObjectType 的 2 路 RRF 分数降序；
2. 每个 `targetProperties` 只在当前 `targetObjectType.id` 范围内执行 2 路 RRF 和裁剪；
3. ObjectType 默认 Top 3，每个 sourceProperty 默认 Top 3 Property；
4. 无合格 ObjectType 候选时允许 `targetObjectTypes=[]`，不能制造结果；
5. 某 Property 无合格候选时保留 `sourceProperty`，返回 `targetProperties=[]`；
6. 同一 ID 在同一层只保留证据最完整、RRF 分数最高的候选；
7. LLM 只能选择检索返回的真实候选，不得生成新的 ObjectType/Property ID。

---

## 4.6 Enum / Instance Value Entity Linking：值 4 路

`ExtractedEntity.Values[]` 不在 NER 阶段预判 Enum/Instance，每个 VALUE Semantic Unit 固定进入 4 路值检索：

```text
sourceValue
├─ enumLexical     → OpenSearch Keyword Fuzzy
├─ enumDense       → GaussVector Dense
├─ instanceLexical → OpenSearch Keyword Fuzzy
└─ instanceDense   → GaussVector Dense
        ↓
按真实 property_id + object_type_id 聚合
        ↓
值 4 路 Weighted RRF
        ↓
Value Linking Candidates
```

最终候选补齐：

```text
valueType = ENUM_VALUE | INSTANCE_VALUE
actual value
property_id
object_type_id
matched_field
matched_value
supporting_hits
rrfScore
```

其中 `actual value` 来自真实索引 `value`，不在 OAG 内维护第二套 canonical 字典。

### 4.6.1 Value 携带 Property Hint

输入：

```json
{
  "ObjectType": "Account",
  "Properties": ["accountStatus"],
  "Values": [
    {"Property": "accountStatus", "Value": "在用"}
  ]
}
```

处理：

```text
Account
→ 先完成 ObjectType 2 路 Linking

accountStatus
→ 在每个 Account 候选作用域内完成 Property 2 路 Linking

在用
→ 对已链接的 Property/ObjectType 候选施加归属 filter
→ 执行 Value 4 路召回
→ 4 路 RRF
```

Property Hint 是强作用域提示，但必须经过真实本体 Property Linking 后才能转换为 `property_id` filter，不能把用户文本直接当内部 ID。

### 4.6.2 Value 未携带 Property、但 ObjectType 已知

输入：

```json
{
  "ObjectType": "Account",
  "Properties": [],
  "Values": [
    {"Value": "VIP"}
  ]
}
```

处理：

```text
Account → 2 路 Linking → targetObjectTypes[]
VIP     → Enum/Instance 4 路召回
        → 使用 targetObjectTypes[] 作为 object_type_id 候选作用域
        → 根据命中记录反解 Property
```

### 4.6.3 Value-only

完全不知道 ObjectType/Property 时：

```json
{
  "Values": [
    {"Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"}
  ]
}
```

执行：

```text
Value-only
→ 全本体 Enum 2 路 + Instance 2 路
→ 共 4 路召回
→ 根据命中记录中的 property_id + object_type_id 聚合
→ 4 路 RRF
→ 解析真实 Property/ObjectType 归属
```

规则：

1. 不根据编码形态猜 Site/BaseStation/nativeId；
2. Enum/Instance 不是 Core Graph 顶点，图规划时投影到真实 Property/ObjectType；
3. `value / matched_field / matched_value / supporting_hits` 必须一直保留到第 5 章 LLM Fine Rank；
4. 同一个业务 Value 可在不同 Property 下存在，不能仅按 value 文本全局去重；
5. value-only 的候选域更大，应使用更严格的 TopK、候选上限和超时保护。

### 4.6.4 Enum 与 Instance 的冲突处理

同一 VALUE Semantic Unit 可能同时命中 Enum 与 Instance。粗排阶段不提前强行二选一：

```text
Enum evidence
+ Instance evidence
→ 按真实 Property/ObjectType 归属聚合
→ 4 路 RRF
→ 保留 recordType 和 supporting_hits
→ 第 5 章 LLM 结合 Query / Property Hint / Graph Hint 选择最终 0/1/N
```

如果 Enum 与 Instance 命中同一 Property，两个 recordType 的具体命中仍保留在 supporting_hits 中；如果命中不同 Property，则形成不同候选组分别进入 RRF 排序。

---

## 4.7 基于 ExtractedEntity 的端到端路由示例

输入：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "字符串",
      "Properties": ["属性1", "属性2"],
      "Values": [
        {
          "Property": "属性1",
          "Value": "用户原始业务值"
        },
        {
          "Value": "归属暂不确定的业务值"
        }
      ]
    },
    {
      "Values": [
        {
          "Value": "完全无法确定 ObjectType/Property 归属的业务值"
        }
      ]
    }
  ]
}
```

执行拆解：

```text
Entity #1
│
├─ ObjectType = "字符串"
│    ├─ ontologyObjectLexical
│    ├─ ontologyObjectDense
│    └─ 2 路 RRF → targetObjectTypes[]
│
├─ Property = "属性1"
│    └─ 对每个 targetObjectType
│         ├─ ontologyObjectLexical + parent_id filter
│         ├─ ontologyObjectDense + parent_id filter
│         └─ 2 路 RRF → targetProperties[]
│
├─ Property = "属性2"
│    └─ 同上，独立执行 2 路 RRF
│
├─ Value = "用户原始业务值", PropertyHint = "属性1"
│    ├─ enumLexical
│    ├─ enumDense
│    ├─ instanceLexical
│    ├─ instanceDense
│    └─ 在属性1真实候选作用域内执行 4 路 RRF
│
└─ Value = "归属暂不确定的业务值"
     ├─ enumLexical / enumDense
     ├─ instanceLexical / instanceDense
     └─ 在已链接 ObjectType 作用域内执行 4 路 RRF并反解 Property

Entity #2（value-only）
└─ Value = "完全无法确定 ObjectType/Property 归属的业务值"
     ├─ enumLexical / enumDense
     ├─ instanceLexical / instanceDense
     └─ 全局 4 路 RRF → 由真实命中反解 ObjectType/Property
```

核心原则：

> **实体提取结果决定检索路由，检索结果反向补齐真实本体归属。ObjectType/Property 与 Value 不再混用同一组召回通道。**

---

## 4.8 本章输出与第 5 章衔接

本章输出是可供 LLM Fine Rank 使用的**真实候选集合 + 归属 + 多通道证据**，不是最终检索结果。

```text
ObjectType / Property
  → 本体定义 2 路 RRF
  → seedNodes[].targetObjectTypes[].propertyLinks[]
  → rrfScore + channelHits + supporting_hits

Enum / Instance Value
  → 值 4 路 RRF
  → valueType + actual value + property_id + object_type_id
  → rrfScore + matched_field + matched_value + supporting_hits
```

核心约束：

1. OpenSearch lexical 统一采用关键词模糊查询，不维护额外字符串精确召回 Ranked List；
2. OBJECT_TYPE / PROPERTY 只使用本体定义 2 路融合；
3. VALUE 只使用 Enum/Instance 4 路融合；
4. Property 必须在每个候选 ObjectType 作用域内独立召回和排序；
5. Enum/Instance 按真实 `Property + ObjectType` 归属聚合，具体 value 证据不能在投影时丢失；
6. `matched_field / matched_value` 必须保留到 LLM Fine Rank；
7. RRF 只融合各通道 rank，不直接比较 OpenSearch `_score` 与 cosine 原始分数；
8. LLM 只能从真实候选中选择，不能生成新的 ObjectType/Property/Value ID；
9. Relationship 不在本章直接 Entity Linking，由后续图规划结合 `searchContext.search_path` 和 Graph Hint 处理。

---

'''

text = DOC.read_text(encoding='utf-8')
start_marker = '# 4. 实体提取、Entity Linking 与 6 路混合召回'
end_marker = '# 5. LLM 精排与最终语义检索结果'
start = text.index(start_marker)
end = text.index(end_marker, start)

prefix = text[:start]
suffix = text[end:]

# 同步刷新文档版本与第 1 章高层检索描述，避免与新的第 4 章冲突。
prefix = prefix.replace('> 版本：V6.1  ', '> 版本：V6.2  ', 1)
prefix = prefix.replace('> 日期：2026-08-23  ', '> 日期：2026-09-05  ', 1)
prefix = prefix.replace('支持 BM25/Exact + Dense 混合召回；', '支持 OpenSearch 关键词模糊 + GaussVector Dense 混合召回；')
prefix = prefix.replace('OpenSearch<br/>Exact/BM25', 'OpenSearch<br/>Keyword Fuzzy')

new_text = prefix + CHAPTER4 + suffix

chapter = new_text[new_text.index(start_marker):new_text.index(end_marker)]
required = [
    'ontologyObjectLexical', 'ontologyObjectDense',
    'enumLexical', 'enumDense', 'instanceLexical', 'instanceDense',
    'Keyword Fuzzy', '本体定义 2 路', '值 4 路',
    'ExtractedEntity 数据模型', 'Value-only', 'searchContext.search_path'
]
for token in required:
    assert token in chapter, f'missing required token: {token}'
assert 'Exact' not in chapter, 'chapter 4 still contains legacy Exact retrieval wording'
assert chapter.count('ontologyObjectLexical') >= 5
assert chapter.count('enumLexical') >= 5
assert new_text.count(start_marker) == 1
assert new_text.count(end_marker) == 1

DOC.write_text(new_text, encoding='utf-8')

# one-shot cleanup: final PR must only contain the formal markdown change.
if WORKFLOW.exists():
    WORKFLOW.unlink()
if SCRIPT.exists():
    SCRIPT.unlink()
