from pathlib import Path

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
WORKFLOW = Path('.github/workflows/one-shot-oag-ch4-ch5-boundary.yml')
SELF = Path(__file__)

text = DOC.read_text(encoding='utf-8')

repls = {
'''内部仍保留每个候选的 `rrfScore / channelHits / supporting_hits / matched_field / matched_value`，供第 5 章 LLM Fine Rank 使用。''':
'''`rrfScore / channelHits / supporting_hits / matched_field / matched_value` 仅属于召回与粗排阶段内部信息，可用于阶段内排序、调试和可观测性；形成精排输入 `extracted_entities` 后不再向 LLM 传递。''',

'''3. `value / matched_field / matched_value / supporting_hits` 必须一直保留到第 5 章 LLM Fine Rank；''':
'''3. Value Linking 在当前阶段完成真实 `value / property_id / object_type_id` 归属解析；`matched_field / matched_value / supporting_hits` 不向 LLM 精排阶段传递；''',

'''本章输出是可供 LLM Fine Rank 使用的**真实候选集合 + 归属 + 多通道证据**，不是最终检索结果。''':
'''本章输出给 LLM Fine Rank 的是**真实候选集合 + ObjectType / Property 归属结构**，不是最终检索结果。Keyword/Dense/RRF 的多通道证据在本章内部完成消费，不继续传递到精排 Prompt。''',

'''ObjectType / Property
  → 本体定义 2 路 RRF
  → seedNodes[].targetObjectTypes[].propertyLinks[]
  → rrfScore + channelHits + supporting_hits

Enum / Instance Value
  → 值 4 路 RRF
  → valueType + actual value + property_id + object_type_id
  → rrfScore + matched_field + matched_value + supporting_hits''':
'''ObjectType / Property
  → 本体定义 2 路 RRF
  → 形成结构化候选
  → 精排输入仅保留 sourceObjectType / targetObjectTypes / propertyLinks / targetProperties 及候选 id/name/score

Enum / Instance Value
  → 值 4 路 RRF
  → 完成 actual value + property_id + object_type_id 的确定性归属解析
  → 不把 lexical/dense supporting evidence 传给精排 LLM''',

'''5. Enum/Instance 按真实 `Property + ObjectType` 归属聚合，具体 value 证据不能在投影时丢失；
6. `matched_field / matched_value` 必须保留到 LLM Fine Rank；
7. RRF 只融合各通道 rank，不直接比较 OpenSearch `_score` 与 cosine 原始分数；''':
'''5. Enum/Instance 按真实 `Property + ObjectType` 归属聚合，确定性的 `value / property_id / object_type_id` 由程序侧继续用于结果投影；
6. `rrfScore / channelHits / supporting_hits / matched_field / matched_value` 在召回/粗排阶段结束后停止向下传递，不进入 LLM Fine Rank Prompt；
7. RRF 只融合各通道 rank，不直接比较 OpenSearch `_score` 与 cosine 原始分数；其融合结果用于产生候选顺序/score，原始通道证据不再向精排传递；''',
}

for old, new in repls.items():
    if old not in text:
        raise SystemExit(f'missing expected block: {old[:80]}')
    text = text.replace(old, new, 1)

DOC.write_text(text, encoding='utf-8')

updated = DOC.read_text(encoding='utf-8')
ch4_start = updated.index('# 4. 实体提取、Entity Linking 与 6 路混合召回')
ch5_start = updated.index('# 5. LLM 精排与最终语义检索结果')
ch4 = updated[ch4_start:ch5_start]

assert '形成精排输入 `extracted_entities` 后不再向 LLM 传递' in ch4
assert '`matched_field / matched_value / supporting_hits` 不向 LLM 精排阶段传递' in ch4
assert '多通道证据在本章内部完成消费，不继续传递到精排 Prompt' in ch4
assert '`rrfScore / channelHits / supporting_hits / matched_field / matched_value` 在召回/粗排阶段结束后停止向下传递' in ch4

if WORKFLOW.exists():
    WORKFLOW.unlink()
if SELF.exists():
    SELF.unlink()
