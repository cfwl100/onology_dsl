from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8')

CH3 = '# 3. 语义索引管理：构建、数据接入、任务、MinIO 与一致性'
CH4 = '# 4. 实体提取、Entity Linking 与 6 路混合召回'
CH5 = '# 5. LLM 精排与最终语义检索结果'
assert text.count(CH3) == 1 and text.count(CH4) == 1 and text.count(CH5) == 1

# -----------------------------------------------------------------------------
# 1. Restore CLEAR semantics in chapter 3
# -----------------------------------------------------------------------------
s3 = text.index(CH3)
s4 = text.index(CH4)
ch3 = text[s3:s4]

# Formal task abstraction / task response semantics.
ch3 = ch3.replace(
    'importMode = FULL_REPLACE | INCREMENTAL\n',
    'importMode = FULL_REPLACE | INCREMENTAL | CLEAR\n',
    1,
)
ch3 = ch3.replace(
    '| `IMPORT_MODE`          | VARCHAR(32)   |          | `FULL_REPLACE` / `INCREMENTAL`',
    '| `IMPORT_MODE`          | VARCHAR(32)   |          | `FULL_REPLACE` / `INCREMENTAL` / `CLEAR`',
)
ch3 = ch3.replace(
    '| `importMode` | String | `FULL_REPLACE / INCREMENTAL`；OMS 内部任务可为空 |',
    '| `importMode` | String | `FULL_REPLACE / INCREMENTAL / CLEAR`；OMS 内部任务可为空；`CLEAR` 仅用于 `INSTANCE_VALUE` 全量清理 |',
)
ch3 = ch3.replace(
    'importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL], nullable: true }',
    'importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL, CLEAR], nullable: true }',
)

# Interface definition requested by user.
old_row = '| `importMode` | String              | 是    | -   | `enum: [FULL_REPLACE, INCREMENTAL]` | 全量替换或增量导入                                               |\n| `files`      | Array[MinioCsvFile] | 是    | -   | `minItems: 1`                              | 待导入的 MinIO CSV 对象列表 |'
new_row = '| `importMode` | String              | 是    | -   | `enum: [FULL_REPLACE, INCREMENTAL, CLEAR]` | 全量替换、增量导入或全量清理索引；`CLEAR` 仅允许 `dataType=INSTANCE_VALUE` |\n| `files`      | Array[MinioCsvFile] | 条件必选 | -   | `minItems: 1`                              | `FULL_REPLACE/INCREMENTAL` 时必选；`CLEAR` 时选填，同时必须指定 `INSTANCE_VALUE` |'
assert old_row in ch3, 'chapter3 importMode/files table marker changed'
ch3 = ch3.replace(old_row, new_row, 1)

ch3 = ch3.replace(
    '注册已经上传到 MinIO 的一个或多个 UTF-8 CSV 对象。接口同步校验请求结构和基础资源信息，创建持久化异步任务。',
    '注册已经上传到 MinIO 的一个或多个 UTF-8 CSV 对象，或在 `dataType=INSTANCE_VALUE, importMode=CLEAR` 时发起实例值全量索引清理。接口同步校验请求结构和基础资源信息，创建持久化异步任务。',
    1,
)

# Add explicit CLEAR example immediately after regular file import example if not already present.
clear_example = '''\n\n##### CLEAR 请求示例\n\n`CLEAR` 用于清理当前本体的全量 `INSTANCE_VALUE` 索引，不依赖 MinIO 文件，因此 `files` 可以省略：\n\n```json\n{\n  "requestId": "clear-instance-20260823-000001",\n  "dataType": "INSTANCE_VALUE",\n  "importMode": "CLEAR"\n}\n```\n\n约束：\n\n- `dataType` 必须为 `INSTANCE_VALUE`；\n- `files` 为选填，OAG 不以文件内容作为 CLEAR 的执行前提；\n- `METADATA_ENUM + CLEAR` 返回 `400 INVALID_IMPORT_MODE`；\n- CLEAR 仍创建持久化 Task，并按双存储一致性规则完成清理、Verify 与 Publish。\n'''
needle = '##### 返回参数\n\n复用 `AsyncTaskAcceptedResponse`。'
if '##### CLEAR 请求示例' not in ch3:
    assert needle in ch3
    ch3 = ch3.replace(needle, clear_example + '\n' + needle, 1)

# OpenAPI conditional-file semantics. OpenAPI 3.0.3 has no if/then, so document condition explicitly.
old_schema = '''    IndexFileImportRequest:\n      type: object\n      required: [requestId, dataType, importMode, files]\n      properties:\n        requestId: { type: string, minLength: 1, maxLength: 256 }\n        triggerTaskId: { type: string, maxLength: 256 }\n        dataType: { type: string, enum: [METADATA_ENUM, INSTANCE_VALUE] }\n        importMode: { type: string, enum: [FULL_REPLACE, INCREMENTAL] }\n        files:\n          type: array\n          minItems: 1\n          items: { $ref: '#/components/schemas/MinioCsvFile' }\n      additionalProperties: false'''
new_schema = '''    IndexFileImportRequest:\n      type: object\n      required: [requestId, dataType, importMode]\n      description: FULL_REPLACE/INCREMENTAL 时 files 必选；CLEAR 时仅允许 dataType=INSTANCE_VALUE，files 选填\n      properties:\n        requestId: { type: string, minLength: 1, maxLength: 256 }\n        triggerTaskId: { type: string, maxLength: 256 }\n        dataType: { type: string, enum: [METADATA_ENUM, INSTANCE_VALUE] }\n        importMode:\n          type: string\n          enum: [FULL_REPLACE, INCREMENTAL, CLEAR]\n          description: CLEAR 用于清理全量 INSTANCE_VALUE 索引\n        files:\n          type: array\n          minItems: 1\n          description: FULL_REPLACE/INCREMENTAL 时必选；CLEAR 时选填\n          items: { $ref: '#/components/schemas/MinioCsvFile' }\n      additionalProperties: false'''
assert old_schema in ch3, 'IndexFileImportRequest schema marker changed'
ch3 = ch3.replace(old_schema, new_schema, 1)

# Synchronous validation boundary.
ch3 = ch3.replace(
    'dataType / importMode Schema 校验\nfiles 非空\nbucket allowlist 校验\nobjectKey 格式校验\nsha256 格式校验',
    'dataType / importMode Schema 校验\nFULL_REPLACE / INCREMENTAL：files 非空\nCLEAR：dataType 必须为 INSTANCE_VALUE，files 可省略\n存在 files 时：bucket allowlist / objectKey / sha256 格式校验',
    1,
)

# MinIO file protocol has a CLEAR exception because CLEAR has no source file requirement.
ch3 = ch3.replace(
    '动态 Enum / Instance 的唯一正式交付形式是**不可变 UTF-8 CSV + MinIO/S3 对象 + SHA-256 文件身份**。接口只注册文件，不通过超大 JSON Body 传输业务记录。',
    '除 `INSTANCE_VALUE + CLEAR` 外，动态 Enum / Instance 的唯一正式数据交付形式是**不可变 UTF-8 CSV + MinIO/S3 对象 + SHA-256 文件身份**。`CLEAR` 不要求源 CSV；其他导入模式只注册文件，不通过超大 JSON Body 传输业务记录。',
    1,
)

# Formal import modes section.
ch3 = ch3.replace('### 3.6.2 FULL_REPLACE 与 INCREMENTAL', '### 3.6.2 FULL_REPLACE、INCREMENTAL 与 CLEAR', 1)
clear_mode = '''\n\n#### CLEAR\n\n`CLEAR` 用于清理当前本体的**全量实例值索引**，只允许：\n\n```text\ndataType = INSTANCE_VALUE\nimportMode = CLEAR\nfiles = optional\n```\n\n执行语义：\n\n```text\nCreate Task\n→ Validate INSTANCE_VALUE + CLEAR\n→ Build Empty/Staging Instance Generation\n→ Verify GaussVector/OpenSearch 目标 Generation 为空\n→ Atomic Publish Empty Generation\n→ Retire/Cleanup Old Instance Generation\n→ FINISHED\n```\n\nCLEAR 不要求读取 MinIO、不执行 Embedding，也不通过逐条 DELETE 清理百万/千万级实例数据。通过空 Staging Generation + Verify + Publish 保证 GaussVector/OpenSearch 清理边界一致；失败时旧 Active Generation 继续在线，避免单侧清空导致检索不一致。\n'''
inc_end = '适用于动态 Enum Value UPSERT/DELETE、实例值新增/删除和小规模业务数据变化。METADATA_ENUM 使用 `object_type_id + property_id + normalized(value)`，INSTANCE_VALUE 使用 `object_type_id + property_id + normalized(value)` 作为幂等业务键；相同请求或 Chunk 重试只能覆盖原记录，不能追加重复记录。'
assert inc_end in ch3
if '#### CLEAR\n' not in ch3:
    ch3 = ch3.replace(inc_end, inc_end + clear_mode, 1)

# Publish visibility includes CLEAR.
vis = '''INCREMENTAL\n  → 对 Active Generation 使用稳定业务键幂等 UPSERT / DELETE\n  → 双端均成功并校验后推进 Task/Checkpoint'''
vis_new = vis + '''\n\nCLEAR\n  → 构建空的 Instance Staging Generation\n  → 双端 Verify 为空\n  → 原子 Publish\n  → 再清理旧 Instance Generation'''
assert vis in ch3
ch3 = ch3.replace(vis, vis_new, 1)

# Final constraints / selection wording.
ch3 = ch3.replace(
    '选择规则：首次创建或明确重建使用 `FULL_REPLACE`；只提交变化数据使用 `INCREMENTAL`。不要用 `INCREMENTAL` 模拟首次全量，也不要把日常增量提交为全量替换。',
    '选择规则：首次创建或明确重建使用 `FULL_REPLACE`；只提交变化数据使用 `INCREMENTAL`；需要清空当前本体全部实例值索引时使用 `INSTANCE_VALUE + CLEAR`。不要用 `INCREMENTAL` 模拟首次全量，也不要把日常增量提交为全量替换。',
    1,
)
ch3 = ch3.replace(
    '5. 首次创建/重建使用 `FULL_REPLACE`，变化数据使用 `INCREMENTAL`；',
    '5. 首次创建/重建使用 `FULL_REPLACE`，变化数据使用 `INCREMENTAL`；清理当前本体全量实例索引使用 `dataType=INSTANCE_VALUE, importMode=CLEAR`，此时 `files` 选填；',
    1,
)

# -----------------------------------------------------------------------------
# 2. Restructure chapter 4 into one authoritative sequence
# -----------------------------------------------------------------------------
old_ch4 = text[s4:text.index(CH5)]
detail_marker = '## 4.1 详细设计与实现'
assert detail_marker in old_ch4
detail = old_ch4[old_ch4.index(detail_marker):]


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
            return '\n'.join(lines[i + 1:]).strip() + '\n'
    return block.strip() + '\n'


def clean_inner_headings(block):
    out = []
    for line in block.splitlines():
        m = re.match(r'^(#{4,6})\s+\d+(?:\.\d+)+\s+(.*)$', line)
        if m:
            line = f'{m.group(1)} {m.group(2)}'
        out.append(line)
    return '\n'.join(out).strip() + '\n'

entity = clean_inner_headings(drop_first_heading(between(detail, '### 4.0 实体提取（Entity Extraction）', '### 4.1 Query Understanding：Semantic Phrase Extraction')))
phrase = clean_inner_headings(drop_first_heading(between(detail, '### 4.1 Query Understanding：Semantic Phrase Extraction', '### 4.2 Query Understanding 推荐结构')))
qu_struct = clean_inner_headings(drop_first_heading(between(detail, '### 4.2 Query Understanding 推荐结构', '### 4.3 为什么不建议 LLM 直接输出底层 TopK')))
topk_principle = clean_inner_headings(drop_first_heading(between(detail, '### 4.3 为什么不建议 LLM 直接输出底层 TopK', '### 4.4 6 路检索通道')))
channels = clean_inner_headings(drop_first_heading(between(detail, '### 4.4 6 路检索通道', '### 4.5 Exact/BM25 与 Dense 阈值关系')))
thresholds = clean_inner_headings(drop_first_heading(between(detail, '### 4.5 Exact/BM25 与 Dense 阈值关系', '### 4.6 topK / similarityThreshold 分表配置')))
profile = clean_inner_headings(drop_first_heading(between(detail, '### 4.6 topK / similarityThreshold 分表配置', '### 4.7 legacy GraphSearchRequest.topK 兼容语义')))
legacy_topk = clean_inner_headings(drop_first_heading(between(detail, '### 4.7 legacy GraphSearchRequest.topK 兼容语义', '### 4.8 seedRetrievalMode 兼容')))
seed_mode = clean_inner_headings(drop_first_heading(between(detail, '### 4.8 seedRetrievalMode 兼容', '### 4.9 GaussVector / OpenSearch 返回结构与结果标准化')))
searchhit = clean_inner_headings(drop_first_heading(between(detail, '### 4.9 GaussVector / OpenSearch 返回结构与结果标准化', '### 4.10 通道内按本体对象去重并保留具体命中')))
dedup = clean_inner_headings(drop_first_heading(between(detail, '### 4.10 通道内按本体对象去重并保留具体命中', '### 4.11 RRF Aggregator：一次 Weighted RRF')))
rrf = clean_inner_headings(drop_first_heading(between(detail, '### 4.11 RRF Aggregator：一次 Weighted RRF', '### 4.12 Exact 不是绝对锁定')))
exact = clean_inner_headings(drop_first_heading(between(detail, '### 4.12 Exact 不是绝对锁定', '### 4.13 RRF 粗排输出：Entity Linking 结果')))
entity_link = clean_inner_headings(drop_first_heading(between(detail, '### 4.13 RRF 粗排输出：Entity Linking 结果', '### 4.14 RRF 与 LLM 的分组层级')))
rrf_llm = clean_inner_headings(drop_first_heading(detail[detail.index('### 4.14 RRF 与 LLM 的分组层级'):]))

# The old detailed wording said stage 2 only handles ObjectType/Property. Current chapter core also
# defines Value -> Enum/Instance Entity Linking. Make the boundary explicit without deleting either design detail.
entity_link = entity_link.replace(
    '> 当前阶段只处理 ObjectType、Property。Relationship、RelationshipProperty 不在本阶段实体链接范围内。',
    '> ObjectType/Property 使用本节的作用域化链接流程；`Values[]` 使用第 4.6 节的 Enum/Instance Value Linking。Relationship、RelationshipProperty 不作为 Entity Linking 的直接检索目标。',
    1,
)

value_link = '''对于 `ExtractedEntity.Values[]`，OAG 不在 NER 阶段预判 Enum/Instance，而是同时查询枚举索引和实例索引：

```text
sourceValue
→ enumLexical / enumDense
→ instanceLexical / instanceDense
→ 按真实 Property/ObjectType 归属聚合
→ Weighted RRF + 上下文消歧
→ actual value + property_id + object_type_id
```

最终补齐：

```text
valueType = ENUM_VALUE | INSTANCE_VALUE
canonical/actual value
Property
ObjectType
matched_field / matched_value
supporting_hits
```

其中 `canonical` 只是对真实索引 `value` 的下游投影名称，不维护第二套 canonical 字典。

### 4.6.1 Property Hint 与 Value-only

两种输入都合法：

```json
{
  "ObjectType": "Account",
  "Properties": ["accountStatus"],
  "Values": [
    {"Property": "accountStatus", "Value": "在用"}
  ]
}
```

以及完全不知道归属时的 value-only：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "ALARM",
      "Properties": ["告警TICKET ID", "告警发生时间"],
      "Values": []
    },
    {
      "Values": [
        {"Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"}
      ]
    }
  ]
}
```

规则：

1. Value 携带 `Property` Hint 时优先在该 Property / ObjectType 作用域内召回；
2. Value-only 时允许跨 Enum/Instance 索引召回后再确定归属；
3. 不根据编码形态猜 Site/BaseStation/nativeId 等 ObjectType/Property；
4. Enum/Instance 自身不是本体图顶点，图规划时投影到其真实 Property/ObjectType；
5. 具体 `value/matched_field/matched_value/supporting_hits` 必须继续传给第 5 章 LLM Fine Rank，不能只留下 Property 节点。

### 4.6.2 Relationship 边界

Relationship / RelationshipProperty 不由 Entity Extraction 或 Entity Linking 直接输出。业务提供的专家路径、关系和方向提示进入 `searchContext`，在后续图规划阶段作为 PathPlan/Graph Hint 约束使用。
'''

chapter4 = f'''{CH4}

本章定义从自然语言实体到真实本体对象/属性/值归属的**粗召回与 Entity Linking**。执行主线统一为：

```text
query + searchContext / extractedEntities
→ Entity Extraction
→ Semantic Phrase Extraction
→ OBJECT_TYPE / PROPERTY / VALUE Semantic Units
→ 6 路 Lexical + Dense Recall
→ SearchHit 标准化
→ 通道内按真实本体归属去重
→ 一次 Weighted RRF
→ ObjectType 作用域内 Property Linking
→ Enum / Instance Value Linking
→ Entity Linking 粗排结果 + supporting_hits
→ 第 5 章 LLM Fine Rank
```

本章只负责**候选召回、归属解析和粗排**；LLM 最终选择、0/1/N 判定与 `retrievalResults` 生成由第 5 章负责。

---

## 4.1 实体提取与 Query Understanding

### 4.1.1 ExtractedEntity 数据模型

{entity}

### 4.1.2 Semantic Phrase Extraction

{phrase}

### 4.1.3 Query Understanding 推荐结构

{qu_struct}

### 4.1.4 检索参数职责边界

{topk_principle}

---

## 4.2 6 路混合召回与 Retrieval Profile

### 4.2.1 六路检索通道

{channels}

### 4.2.2 Exact/BM25 与 Dense 阈值边界

{thresholds}

### 4.2.3 topK / similarityThreshold 分表配置

{profile}

### 4.2.4 legacy GraphSearchRequest.topK 兼容

{legacy_topk}

### 4.2.5 seedRetrievalMode 兼容

{seed_mode}

---

## 4.3 SearchHit 标准化与通道证据保留

### 4.3.1 GaussVector / OpenSearch SearchHit 标准化

{searchhit}

### 4.3.2 通道内去重与 supporting_hits

{dedup}

---

## 4.4 Weighted RRF 粗排融合

### 4.4.1 一次 Weighted RRF

{rrf}

### 4.4.2 Exact 是强证据但不是绝对锁定

{exact}

---

## 4.5 ObjectType / Property Entity Linking

### 4.5.1 ObjectType 作用域内 Property Linking 与粗排输出

{entity_link}

### 4.5.2 ObjectType / Property 分组与 LLM 衔接

{rrf_llm}

---

## 4.6 Enum / Instance Value Entity Linking

{value_link}

---

## 4.7 本章输出与第 5 章衔接

阶段 4 的输出不是最终语义检索结果，而是可供 LLM Fine Rank 使用的**真实候选集合 + 归属 + 证据**：

```text
ObjectType / Property
  → seedNodes[].targetObjectTypes[].propertyLinks[]
  → 每个候选携带 rrfScore/channelHits/supporting_hits

Enum / Instance Value
  → valueType + actual value + property_id + object_type_id
  → matched_field / matched_value + supporting_hits
```

核心约束：

1. ObjectType 候选先粗排，Property 必须在每个候选 ObjectType 作用域内独立召回和排序；
2. Enum/Instance 按真实 `Property + ObjectType` 归属聚合，具体 value 证据不能在投影时丢失；
3. `matched_field/matched_value` 必须一直保留到 LLM Fine Rank，用于解释 name/display/description/synonyms/value 的真实命中来源；
4. RRF 只融合各通道 rank，不直接比较 BM25、Exact 与 cosine 原始分数；
5. LLM 只能从这些真实候选中选择，不能生成新的 ObjectType/Property/Value ID；
6. Relationship 不在本章直接 Entity Linking，由后续图规划结合 `searchContext` 和 Graph Hint 处理。

---

'''

# Update cross-chapter references to old chapter-4 numbering.
rest = text[text.index(CH5):]
rest = rest.replace('将 4.13 的嵌套 Entity Linking 结果', '将 4.5 的嵌套 Entity Linking 结果')
rest = rest.replace('不替代 4.13 对外输出', '不替代 4.5 对外输出')

new_text = text[:s3] + ch3 + chapter4 + rest

# -----------------------------------------------------------------------------
# 3. Validation
# -----------------------------------------------------------------------------
new_s3 = new_text.index(CH3)
new_s4 = new_text.index(CH4)
new_s5 = new_text.index(CH5)
new_ch3 = new_text[new_s3:new_s4]
new_ch4 = new_text[new_s4:new_s5]

# CLEAR contract.
assert '`enum: [FULL_REPLACE, INCREMENTAL, CLEAR]`' in new_ch3
assert '`files`      | Array[MinioCsvFile] | 条件必选' in new_ch3
assert 'required: [requestId, dataType, importMode]\n      description: FULL_REPLACE/INCREMENTAL 时 files 必选；CLEAR 时仅允许 dataType=INSTANCE_VALUE' in new_ch3
assert '### 3.6.2 FULL_REPLACE、INCREMENTAL 与 CLEAR' in new_ch3
assert '#### CLEAR' in new_ch3
assert 'Build Empty/Staging Instance Generation' in new_ch3
assert 'dataType=INSTANCE_VALUE, importMode=CLEAR' in new_ch3

# Chapter 4 structure.
required_headings = [
    '## 4.1 实体提取与 Query Understanding',
    '## 4.2 6 路混合召回与 Retrieval Profile',
    '## 4.3 SearchHit 标准化与通道证据保留',
    '## 4.4 Weighted RRF 粗排融合',
    '## 4.5 ObjectType / Property Entity Linking',
    '## 4.6 Enum / Instance Value Entity Linking',
    '## 4.7 本章输出与第 5 章衔接',
]
for h in required_headings:
    assert new_ch4.count(h) == 1, f'missing/duplicate heading: {h}'
for obsolete in ['## 4.0 核心设计', '## 4.1 详细设计与实现', '### 4.13 RRF 粗排输出：Entity Linking 结果', '### 4.14 RRF 与 LLM 的分组层级']:
    assert obsolete not in new_ch4, f'obsolete structure remains: {obsolete}'

required_terms = [
    'Semantic Phrase Extraction', 'ontology_object_lexical', 'ontology_object_dense',
    'enum_lexical', 'enum_dense', 'instance_lexical', 'instance_dense',
    'similarityThreshold', 'seedRetrievalMode', 'matched_field', 'matched_value',
    'group_id', 'supporting_hits', 'Weighted RRF', 'RRF(candidate)',
    'targetObjectTypes', 'propertyLinks', 'parent_id', 'GraphTopologyCache',
    'valueType = ENUM_VALUE | INSTANCE_VALUE', '12JKS0885_IN_RSNM_KALIBATA3_MC',
    'maxGlobalCandidates', 'coarseTopKPerSemanticUnit', 'ontologyObjectLexical: 1.3',
]
for term in required_terms:
    assert term in new_ch4, f'required chapter4 detail lost: {term}'

# Detailed design was ~1000 lines; keep enough substance while removing duplicate core copy.
assert len(new_ch4.splitlines()) > 850, f'chapter4 unexpectedly short: {len(new_ch4.splitlines())}'
assert '4.13 的嵌套 Entity Linking' not in new_text
assert '不替代 4.13 对外输出' not in new_text

DOC.write_text(new_text, encoding='utf-8')
print(f'chapter3 CLEAR restore: PASS ({len(new_ch3.splitlines())} lines)')
print(f'old chapter4 lines: {len(old_ch4.splitlines())}')
print(f'new chapter4 lines: {len(new_ch4.splitlines())}')
print('chapter4 restructure validation: PASS')
