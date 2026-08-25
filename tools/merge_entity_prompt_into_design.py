from pathlib import Path

DESIGN = Path('docs/OAG语义子图检索接口extractedEntities结构设计方案.md')
PROMPT = Path('docs/OAG实体提取LLM提示词.md')

design = DESIGN.read_text(encoding='utf-8')
prompt = PROMPT.read_text(encoding='utf-8')

assert '> 文档版本：V2.4' in design
assert '## 12. 最终设计决策' in design
assert '# Step1 Entity Extraction Prompt v0.14' in prompt
assert '## 中文版' in prompt
assert '## English Version' in prompt

# 版本升级
updated = design.replace('> 文档版本：V2.4', '> 文档版本：V2.5', 1)
updated = updated.replace('> 更新日期：2026-08-23', '> 更新日期：2026-08-25', 1)

# 将 Prompt 拆为中英文，保留其可直接交给 LLM 的原始正文。
cn_start = prompt.index('## 中文版') + len('## 中文版')
en_start = prompt.index('## English Version')
cn = prompt[cn_start:en_start].strip()
en = prompt[en_start + len('## English Version'):].strip()

prompt_section = '''## 12. LLM 实体提取 Prompt（正式）

本节定义 OAG 在自然语言模式下调用大模型执行 Entity Extraction 时使用的正式 Prompt。Prompt 与第 4～9 章的 `extractedEntities` Schema、Values 边界和校验规则保持一致，作为运行时实现和 Prompt 评测的统一基线。

### 12.1 Prompt 使用约束

1. Prompt 版本：`Step1 Entity Extraction Prompt v0.14`；
2. 中文 Query 优先使用中文版 Prompt，英文 Query 优先使用英文版 Prompt；混合语言 Query 可根据主语言选择版本，但输出 Schema 不变；
3. `SearchContext` 作为动态上下文注入 Prompt 中预留位置，只用于领域术语、同义词、黑话、few-shot 和明确映射的辅助理解；
4. LLM 必须只输出可直接解析的 JSON，顶层仅允许 `extractedEntities`；
5. Prompt 不负责 Entity Linking、Enum/Instance 分类、Relationship 生成、比较条件解析或 SQL/OQL/Cypher 生成；
6. Prompt 与 OpenAPI Schema 必须版本联动。若 `ExtractedEntity` / `ValueHint` Schema 发生变化，必须同步更新本节 Prompt、样例和自动化评测；
7. LLM 输出仍必须经过第 9 章服务端 Validator 校验与归一化，不能仅依赖 Prompt 保证结构正确。

### 12.2 中文版完整 Prompt

````text
''' + cn + '''
````

### 12.3 English Version Prompt

````text
''' + en + '''
````

### 12.4 Prompt 与接口结构的一致性

| Prompt 语义 | 接口字段/后续处理 | 约束 |
|---|---|---|
| 对象类型 | `ExtractedEntity.ObjectType` | 只输出业务表达，不输出内部 ID |
| 对象属性 | `ExtractedEntity.Properties[]` | 必须保持 ObjectType 从属关系 |
| 业务值 | `ExtractedEntity.Values[]` | 保留用户原始表达，不提前 canonicalize |
| Value 所属属性 | `ValueHint.Property` | 只有归属明确时才填写，不允许猜测 |
| value-only | `ExtractedEntity{Values:[...]}` | ObjectType/Property 不确定时允许独立存在 |
| Enum / Instance | Entity Linking | Prompt 阶段禁止分类，由真实索引命中决定 |
| Relationship | 子图检索策略 | Prompt 阶段不输出，专家路径通过 `searchContext` 传递 |
| 时间/连续数值/聚合 | 原始 `query` | 默认不进入 `Values`，由后续查询理解处理 |

运行时链路：

```text
query + searchContext
      ↓
LLM Entity Extraction Prompt
      ↓
extractedEntities
      ↓
Schema Validator + Normalize
      ↓
Semantic Units
      ↓
Entity Linking：本体对象 / Enum / Instance 6 路召回
```

---

'''

updated = updated.replace('## 12. 最终设计决策', prompt_section + '## 13. 最终设计决策', 1)

# 顶部文档目的补充 Prompt 已纳入正式方案。
needle = '本文定义本体子图检索第 ① 步“实体提取（Entity Extraction）”的输入、输出和约束，并作为 `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search` 的 `extractedEntities` 正式结构规范。'
replacement = needle + '\n\n本文同时给出可直接用于 LLM 的中英文实体提取 Prompt，确保接口 Schema、提取规则、Values 边界、运行时 Prompt 与服务端校验保持同一份权威定义。'
updated = updated.replace(needle, replacement, 1)

# 基础一致性校验
assert '> 文档版本：V2.5' in updated
assert '## 12. LLM 实体提取 Prompt（正式）' in updated
assert '### 12.2 中文版完整 Prompt' in updated
assert '### 12.3 English Version Prompt' in updated
assert '# Role' in updated
assert 'Values' in updated
assert 'value-only' in updated
assert '## 13. 最终设计决策' in updated
assert updated.count('## 12. 最终设计决策') == 0

DESIGN.write_text(updated, encoding='utf-8')
PROMPT.unlink()

print('Merged prompt into extractedEntities design: PASS')
