from pathlib import Path
import re

DOC = Path('docs/OAG语义子图检索接口extractedEntities结构设计方案.md')
text = DOC.read_text(encoding='utf-8')

# 1) Version metadata
text = text.replace('> 文档版本：V2.5  \n> 更新日期：2026-08-25  ', '> 文档版本：V2.6  \n> 更新日期：2026-09-04  ', 1)

# 2) Interface/body description and entity-extraction responsibility
text = text.replace(
    '| `searchContext` | 否 | String | 无 | 动态搜索上下文；用于实体提取和后续语义消歧 |',
    '| `searchContext` | 否 | `SearchContext` | 无 | 结构化搜索上下文；包含目标实体、专家搜索路径和预留扩展信息，用于实体提取、Entity Linking 消歧和后续子图路径规划 |',
    1,
)
text = text.replace(
    '5. 使用 `searchContext` 中的 few-shot、专家路径、领域术语、黑话和消歧规则辅助提取。',
    '5. 使用 `searchContext.target_entity`、`searchContext.search_path` 和 `searchContext.extensions` 中的业务上下文辅助提取与消歧。',
    1,
)
text = text.replace(
    'Relationship 的发现与选择属于第 ③ 步子图检索策略。业务已有专家关系路径时，放入 `searchContext` 作为路径规划约束或优先级提示，不进入 `ExtractedEntity` Schema。',
    'Relationship 的发现与选择属于第 ③ 步子图检索策略。业务已有专家关系路径时，放入 `searchContext.search_path` 作为路径规划约束或优先级提示，不进入 `ExtractedEntity` Schema。',
    1,
)

# 3) Add formal SearchContext schema after Body parameter table
marker = '| `includeActions` | 否 | Integer | `0` | 是否扩展 Action |\n\n---\n\n## 4. extractedEntities 正式结构'
insert = '''| `includeActions` | 否 | Integer | `0` | 是否扩展 Action |

### 3.3 SearchContext

`searchContext` 从自由文本升级为结构化对象，用于显式传递业务目标实体、专家搜索路径和后续扩展信息。

| 字段 | 必选 | 类型 | 默认值 | 约束 | 说明 |
|---|---:|---|---|---|---|
| `target_entity` | 否 | String | 无 | 1～4096 字符 | 业务侧期望重点检索/返回的目标实体表达，可用英文逗号分隔多个目标；作为 ObjectType 提取、Entity Linking 和候选排序的强提示，但仍需通过真实本体完成 Linking |
| `search_path` | 否 | String | 无 | 1～8192 字符 | 业务专家提供的搜索路径/拓扑路径模板，可包含 ObjectType、Relationship、Property 占位符等；用于实体理解、候选消歧和第 ③ 步路径规划，不直接作为可执行 nGQL/Cypher |
| `extensions` | 否 | Object | `{}` | 建议最多 32 个一级 Key；整体大小由服务配置限制 | 预留扩展字段，类型为 `Map<String, Object>`；当前核心协议不约束内部 Key，可用于业务侧携带 few-shot、领域术语、黑话、约束或后续新增上下文 |

至少有一个字段包含有效内容时才建议传入 `searchContext`。

标准示例：

```json
{
  "searchContext": {
    "target_entity": "ID(xxx),BillingAccount,Invoice,BillDetail",
    "search_path": "Subscriber(id:{msisdn}) -[:HAS_SUBSCRIPTION]-> SubscribeRelation -[:SUBSCRIBE_TO]-> Offering",
    "extensions": {}
  }
}
```

字段语义：

1. `target_entity` 是**显式目标提示**。业务侧已知目标对象时，即使 Query 没有完整说出全部对象，也允许该字段补充 ObjectType 候选；但不能绕过 Entity Linking 直接生成本体内部 ID。
2. `target_entity` 中的每一项按业务表达处理，例如 `ID(xxx)` 不因为形态类似 ID 就自动解释成本体内部 ID；最终仍由本体对象索引完成匹配。
3. `search_path` 是**专家路径提示**。允许使用 `Subscriber(id:{msisdn}) -[:HAS_SUBSCRIPTION]-> SubscribeRelation -[:SUBSCRIBE_TO]-> Offering` 这类表达，并保留 `{msisdn}` 等占位符。
4. `search_path` 中的 ObjectType / Relationship 必须在 Entity Linking 与 GraphTopologyCache 阶段校验；路径不存在、方向不合法或关系无法解析时不能直接执行，应降级到正常子图规划。
5. `extensions` 是预留扩展容器，未知 Key 不得改变核心 `ExtractedEntity` Schema；只有已注册的业务扩展处理器才能赋予特定 Key 业务语义。
6. `searchContext` 不能单独满足请求合法性，`query` 与 `extractedEntities` 仍至少一个不为空。

---

## 4. extractedEntities 正式结构'''
assert marker in text, 'Body insertion marker not found'
text = text.replace(marker, insert, 1)

# 4) Replace chapter 6 with one authoritative structured definition
start = text.index('## 6. searchContext 使用规则')
end = text.index('## 7. Entity Extraction → Semantic Units')
section6 = '''## 6. searchContext 使用规则

`searchContext` 是业务侧向 OAG 注入“目标 + 路径 + 扩展上下文”的结构化输入，贯穿 Entity Extraction、Entity Linking 和 Subgraph Retrieval Strategy。

```text
SearchContext
  ├─ target_entity
  │    → 目标 ObjectType 强提示
  │    → Entity Extraction / Entity Linking / Candidate Boost
  │
  ├─ search_path
  │    → 专家拓扑路径提示
  │    → Entity Extraction 辅助理解
  │    → Entity Linking 消歧
  │    → Subgraph Retrieval Strategy 路径优先级
  │
  └─ extensions
       → 预留业务扩展上下文
       → 注册扩展处理器按需消费
```

### 6.1 `target_entity`

示例：

```json
{
  "target_entity": "ID(xxx),BillingAccount,Invoice,BillDetail"
}
```

处理规则：

1. 使用英文逗号分隔多个目标表达，服务端执行 trim、去空和稳定去重；
2. 作为调用方显式提供的目标实体强提示，可用于补充 Query 中未完整表达但业务侧已经明确的 ObjectType；
3. 每个目标仍必须进入本体对象 Entity Linking，不允许把字符串直接视为 ObjectType 内部 ID；
4. Linking 成功的目标实体进入后续 Semantic Units / RRF / LLM Fine Rank；无法匹配的目标必须可观测，不应静默伪造本体节点；
5. `target_entity` 只约束“目标对象”，不直接定义 Relationship。

### 6.2 `search_path`

示例：

```json
{
  "search_path": "Subscriber(id:{msisdn}) -[:HAS_SUBSCRIPTION]-> SubscribeRelation -[:SUBSCRIBE_TO]-> Offering"
}
```

处理规则：

1. 作为专家搜索路径模板，可描述 ObjectType、Relationship 和 Property/Value 占位符；
2. `{msisdn}` 等占位符在本阶段保持原样，待后续结合 Entity Linking / Query Understanding 结果解析；
3. 路径中的对象表达可辅助 Entity Extraction 和 Entity Linking，但 Relationship 不写入 `ExtractedEntity`；
4. 第 ③ 步路径规划优先尝试使用该路径；使用前必须校验 ObjectType、Relationship、方向和拓扑连通性；
5. `search_path` 不是 nGQL/Cypher，不允许直接拼接执行；校验失败时按 `minimal/khop/component` 正常策略降级；
6. `search_path` 与 Query 冲突时，保留两者证据并在候选消歧阶段处理，不能直接覆盖用户 Query。

### 6.3 `extensions`

`extensions` 是预留扩展 Map：

```json
{
  "extensions": {
    "domain_terms": ["账期", "出账"],
    "few_shot": "...",
    "business_constraints": {
      "region": "APAC"
    }
  }
}
```

当前核心协议不固定上述示例 Key。处理原则：

1. `extensions` 不改变 `ExtractedEntity` 三字段 Schema；
2. 未注册的扩展 Key 不参与核心检索决策，可忽略或透传；
3. 业务扩展需通过显式注册的处理器消费，避免 Key 名碰撞和隐式语义；
4. 输入必须做总长度/对象深度/Key 数量限制、Unicode Normalize 和基本安全规范化；
5. 不允许通过 `extensions` 注入可直接执行的 SQL/OQL/Cypher/nGQL。

### 6.4 总体优先级与边界

```text
用户 query
  = 原始意图与条件事实

target_entity
  = 业务侧显式目标对象提示

search_path
  = 业务侧显式路径提示

extensions
  = 可选业务扩展上下文
```

冲突处理原则：

- 不删除或改写原始 `query`；
- `target_entity/search_path` 可以补充候选和提高优先级，但必须经过真实本体校验；
- `searchContext` 不单独满足 `query/extractedEntities` 非空校验；
- 结构化模式下 `searchContext` 仍可用于 Entity Linking、候选精排和路径规划。

---

'''
text = text[:start] + section6 + text[end:]

# 5) Refresh expert-path example
old_example = '''  "searchContext": "专家路径：IndividualCustomer -> PayRelation -> Account -> CreditLimitInstance。路径只用于后续候选消歧和子图路径规划。",'''
new_example = '''  "searchContext": {
    "target_entity": "IndividualCustomer,PayRelation,Account,CreditLimitInstance",
    "search_path": "IndividualCustomer -[:PAY_RELATION]-> PayRelation -[:TO_ACCOUNT]-> Account -> CreditLimitInstance",
    "extensions": {
      "note": "路径只用于候选消歧和子图路径规划"
    }
  },'''
assert old_example in text, '8.4 legacy searchContext example not found'
text = text.replace(old_example, new_example, 1)

# Add the user-provided path example right after 8.4 explanation.
needle = '“本月”“超过 200”“总数”继续由原始 query 保存，后续查询生成阶段解释。\n\n---\n\n## 9. 校验与归一化规则'
replacement = '''“本月”“超过 200”“总数”继续由原始 query 保存，后续查询生成阶段解释。

### 8.5 `target_entity + search_path` 标准示例

```json
{
  "query": "查询指定用户订购的产品及相关账务实体",
  "searchContext": {
    "target_entity": "ID(xxx),BillingAccount,Invoice,BillDetail",
    "search_path": "Subscriber(id:{msisdn}) -[:HAS_SUBSCRIPTION]-> SubscribeRelation -[:SUBSCRIBE_TO]-> Offering",
    "extensions": {}
  }
}
```

说明：

- `target_entity` 指明业务希望重点召回/保留的目标实体；
- `search_path` 提供专家已知的查询路径；
- 两者均为检索提示，不绕过 Entity Linking、本体拓扑校验和最终候选选择；
- `{msisdn}` 保持为业务占位符，由后续查询理解/参数绑定阶段解析。

---

## 9. 校验与归一化规则'''
assert needle in text, '8.5 insertion marker not found'
text = text.replace(needle, replacement, 1)

# 6) Refresh validation rules
old_validation = '''1. `tenantId`、`ontologyId` 必须存在且满足长度要求；
2. `query` 与 `extractedEntities` 至少一个不为空；
3. 每个 `ExtractedEntity` 至少存在非空 `ObjectType` 或非空 `Values`；
4. `Properties` 非空时必须存在 `ObjectType`；
5. `ValueHint.Value` 必须为非空字符串；
6. `ValueHint.Property` 非空且同一实体有 `ObjectType` 时，应同时出现在该实体 `Properties` 中；
7. 所有文本执行 trim、Unicode Normalize、去空和规范化去重；
8. 业务名称不能直接当作本体内部 ID；
9. value-only 不允许根据值的格式猜测 ObjectType/Property；
10. `similarityThreshold` 范围为 0～1；`topk/hopLimit >= 1`。'''
new_validation = '''1. `tenantId`、`ontologyId` 必须存在且满足长度要求；
2. `query` 与 `extractedEntities` 至少一个不为空；`searchContext` 不能单独满足该条件；
3. `searchContext` 非空时必须是 `SearchContext` 对象，建议至少包含一个有效字段；
4. `target_entity` 按英文逗号切分后执行 trim、去空和稳定去重，不得直接当作本体内部 ID；
5. `search_path` 必须满足长度限制；其中的 ObjectType / Relationship / 方向需在路径规划前通过本体拓扑校验；
6. `extensions` 必须是 Object，限制总大小、嵌套深度和一级 Key 数量；未知扩展不得改变核心 Schema；
7. 每个 `ExtractedEntity` 至少存在非空 `ObjectType` 或非空 `Values`；
8. `Properties` 非空时必须存在 `ObjectType`；
9. `ValueHint.Value` 必须为非空字符串；
10. `ValueHint.Property` 非空且同一实体有 `ObjectType` 时，应同时出现在该实体 `Properties` 中；
11. 所有文本执行 trim、Unicode Normalize、去空和规范化去重；
12. 业务名称不能直接当作本体内部 ID；
13. value-only 不允许根据值的格式猜测 ObjectType/Property；
14. `similarityThreshold` 范围为 0～1；`topk/hopLimit >= 1`。'''
assert old_validation in text, 'validation block not found'
text = text.replace(old_validation, new_validation, 1)

# 7) OpenAPI: SearchContext becomes an object schema
old_openapi = '''        searchContext:
          type: string
          minLength: 1
          maxLength: 32768'''
new_openapi = '''        searchContext:
          $ref: '#/components/schemas/SearchContext' '''
assert old_openapi in text, 'OpenAPI searchContext property not found'
text = text.replace(old_openapi, new_openapi, 1)

search_context_schema = '''    SearchContext:
      type: object
      description: 结构化搜索上下文；target_entity/search_path 为标准字段，extensions 为预留扩展 Map
      minProperties: 1
      properties:
        target_entity:
          type: string
          minLength: 1
          maxLength: 4096
          description: 目标实体业务表达，多个目标使用英文逗号分隔
          example: "ID(xxx),BillingAccount,Invoice,BillDetail"
        search_path:
          type: string
          minLength: 1
          maxLength: 8192
          description: 专家搜索路径模板，仅作为检索和路径规划提示，不直接执行
          example: "Subscriber(id:{msisdn}) -[:HAS_SUBSCRIPTION]-> SubscribeRelation -[:SUBSCRIBE_TO]-> Offering"
        extensions:
          type: object
          maxProperties: 32
          description: 预留扩展 Map；内部 Key 由业务扩展处理器定义
          additionalProperties: true
      additionalProperties: false

'''
insert_before = '    ExtractedEntity:\n      type: object'
assert insert_before in text, 'ExtractedEntity schema marker not found'
text = text.replace(insert_before, search_context_schema + insert_before, 1)

# 8) Compatibility migration: old string -> structured object
old_migration = '''4. 专家关系路径移动到 `searchContext`，由第 ③ 步路径规划使用；
5. 服务端可设置一个灰度兼容期解析旧请求，但新 SDK/OpenAPI 只生成三字段结构；
6. 灰度结束后开启 `additionalProperties=false` 强校验，防止结构继续分叉。'''
new_migration = '''4. 专家关系路径移动到 `searchContext.search_path`，目标实体提示移动到 `searchContext.target_entity`；
5. 原 String 类型 `searchContext` 可在灰度兼容期接收，并在服务端映射为 `extensions.legacy_context`；新 SDK/OpenAPI 只生成结构化 `SearchContext`；
6. 业务自定义上下文统一收敛到 `searchContext.extensions`，避免继续扩散顶层字段；
7. 灰度结束后对 `SearchContext` 开启 `additionalProperties=false`，仅 `extensions` 允许扩展 Key；
8. `ExtractedEntity` 继续保持 `ObjectType / Properties / Values` 三字段强校验，防止结构继续分叉。'''
assert old_migration in text, 'migration block not found'
text = text.replace(old_migration, new_migration, 1)

# 9) Prompt contract: v0.15 + structured SearchContext semantics
text = text.replace('1. Prompt 版本：`Step1 Entity Extraction Prompt v0.14`；', '1. Prompt 版本：`Step1 Entity Extraction Prompt v0.15`；', 1)
text = text.replace(
    '3. `SearchContext` 作为动态上下文注入 Prompt 中预留位置，只用于领域术语、同义词、黑话、few-shot 和明确映射的辅助理解；',
    '3. `SearchContext` 以结构化对象注入 Prompt：`target_entity` 提供目标实体强提示，`search_path` 提供专家路径提示，`extensions` 承载预留业务上下文；三者均不得改变 `extractedEntities` 输出 Schema；',
    1,
)

cn_old = '如果提供 `SearchContext`，可以使用其中的领域术语、同义词、黑话、few-shot 和明确的对象/属性映射辅助理解；但不能改变本文规定的 JSON Schema，也不能凭空生成用户问题中不存在的业务值。'
cn_new = '''如果提供 `SearchContext`，它是一个结构化对象：

- `target_entity`：调用方显式给出的目标实体表达，可补充 Query 中未完整说出的 ObjectType 候选；仍必须经过 Entity Linking，不能直接当作本体内部 ID；
- `search_path`：调用方显式给出的专家搜索路径，可辅助实体理解、归属消歧和后续路径规划；Relationship 不写入 `ExtractedEntity`，路径也不能直接当作 nGQL/Cypher 执行；
- `extensions`：预留业务扩展上下文，可携带领域术语、同义词、黑话、few-shot 或其他已注册扩展信息。

`SearchContext` 可以补充调用方明确提供的目标/路径事实，但不能改变本文规定的 JSON Schema，也不能基于模型自身知识凭空生成调用方和用户都未提供的业务值。'''
assert cn_old in text, 'Chinese SearchContext prompt paragraph not found'
text = text.replace(cn_old, cn_new, 1)

# Allow explicit caller hints in consistency rule
text = text.replace(
    '6. 不补全用户未表达的对象、属性和值；`SearchContext` 只用于识别/消歧，不用于凭空扩写查询内容。',
    '6. 不基于模型自身知识补全调用方和用户都未提供的对象、属性和值；`SearchContext.target_entity/search_path` 属于调用方显式提示，可以补充候选，但仍需 Entity Linking / 拓扑校验。',
    1,
)

en_old = "If `SearchContext` is provided, use its domain terminology, synonyms, jargon, few-shot examples, and explicit mappings only as interpretation/disambiguation context. It must not change the JSON schema or invent values that are absent from the user's query."
en_new = '''If `SearchContext` is provided, it is a structured object:

- `target_entity`: explicit target-entity expressions supplied by the caller. It may supplement ObjectType candidates that are not fully stated in the query, but every target still requires Entity Linking and must not be treated as an internal ontology ID directly;
- `search_path`: an expert search-path hint for entity understanding, disambiguation, and downstream graph planning. Relationships must not be emitted in `ExtractedEntity`, and the path must never be executed directly as nGQL/Cypher;
- `extensions`: a reserved business-extension map for registered domain context such as terminology, synonyms, jargon, or few-shot examples.

`SearchContext` may add facts explicitly supplied by the caller, but it must not change the JSON schema or invent business values that are provided by neither the user nor the caller.'''
assert en_old in text, 'English SearchContext prompt paragraph not found'
text = text.replace(en_old, en_new, 1)

text = text.replace(
    '6. Do not add objects, properties, or values not expressed by the user. `SearchContext` assists interpretation only.',
    '6. Do not invent objects, properties, or values from model knowledge when neither the user nor caller supplied them. Explicit `SearchContext.target_entity/search_path` hints may supplement candidates but still require Entity Linking/topology validation.',
    1,
)

# Replace both Task placeholders with a structured skeleton
text = text.replace(
    '# Task\nSearchContext:\n\nInput:\n\nOutput:',
    '# Task\nSearchContext:\n{\n  "target_entity": "",\n  "search_path": "",\n  "extensions": {}\n}\n\nInput:\n\nOutput:'
)

# 10) Prompt/interface consistency table and final decisions
old_table_row = '| Relationship | 子图检索策略 | Prompt 阶段不输出，专家路径通过 `searchContext` 传递 |'
new_table_rows = '''| `target_entity` | `SearchContext.target_entity` | 调用方目标实体强提示，可补充 ObjectType 候选，但必须继续 Entity Linking |
| `search_path` | `SearchContext.search_path` | 专家路径提示；辅助消歧与图规划，不直接执行，不写入 ExtractedEntity Relationship |
| 扩展上下文 | `SearchContext.extensions` | 预留 Map；只有注册扩展处理器赋予具体业务语义 |
| Relationship | 子图检索策略 | Prompt 阶段不输出，专家路径通过 `searchContext.search_path` 传递 |'''
assert old_table_row in text, 'consistency table Relationship row not found'
text = text.replace(old_table_row, new_table_rows, 1)

text = text.replace(
    '8. 专家关系路径通过 `searchContext` 传给后续路径规划；\n9. 比较、时间、聚合等查询语义保留在原始 `query`；\n10. 该结构直接生成 Entity Linking Semantic Units，与主方案中的本体对象/枚举元素/实例元素 6 路召回衔接。',
    '8. `searchContext.target_entity` 承载调用方显式目标实体提示，目标仍必须经过本体 Entity Linking；\n9. 专家关系路径通过 `searchContext.search_path` 传给后续路径规划，并在执行前完成本体拓扑校验；\n10. `searchContext.extensions` 作为唯一预留扩展容器，未知 Key 不改变核心协议；\n11. 比较、时间、聚合等查询语义保留在原始 `query`；\n12. 该结构直接生成 Entity Linking Semantic Units，与主方案中的本体对象/枚举元素/实例元素 6 路召回衔接。',
    1,
)

# 11) Validation assertions
assert '> 文档版本：V2.6' in text
assert '> 更新日期：2026-09-04' in text
assert '| `searchContext` | 否 | `SearchContext` |' in text
assert '### 3.3 SearchContext' in text
assert '"target_entity": "ID(xxx),BillingAccount,Invoice,BillDetail"' in text
assert 'Subscriber(id:{msisdn}) -[:HAS_SUBSCRIPTION]-> SubscribeRelation -[:SUBSCRIBE_TO]-> Offering' in text
assert '    SearchContext:' in text
assert "#'/components/schemas/SearchContext'" not in text
assert "$ref: '#/components/schemas/SearchContext'" in text
assert 'Step1 Entity Extraction Prompt v0.15' in text
assert text.count('"target_entity": ""') >= 2
assert 'searchContext.search_path' in text
assert 'searchContext.extensions' in text
assert 'type: string\n          minLength: 1\n          maxLength: 32768' not in text

DOC.write_text(text, encoding='utf-8')
print('SearchContext V2.6 update: PASS')
