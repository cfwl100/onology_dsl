from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8').replace('\r\n', '\n')

if '> 版本：V6.0（全量整合版）' not in text:
    raise RuntimeError('expected V6.0 marker not found')
text = text.replace('> 版本：V6.0（全量整合版）', '> 版本：V6.1（全量整合版）', 1)

priority_old = '''### 0.5 最终规范优先级

1. 本文 V6.0 各章中的“最终规范/规范收敛”条目为当前推荐行为；
2. V5.16 详细设计中的旧路径、旧接口值、旧 Checkpoint 描述等作为历史实现与兼容背景保留，不应覆盖已明确收敛的 V5.17/PR #42 规则；
3. 当前关键收敛包括：动态 Enum/Instance 统一 MinIO CSV 交付、`instanceDataSourceMode=OAC|BUSINESS_NOTICE`、Software ≤1W 源侧用户、SEC ≤100W 源侧用户、SHA-256、`T_OAG_INDEX_TASK.CHECKPOINT` TEXT JSON、未完成 Chunk 幂等重放、最终返回增加 `semanticExtensions.valueMappings`；
4. `retrievalResults` 是语义命中事实，`seedNodes/nodes/edges` 是图构建/兼容结构，`semanticExtensions.valueMappings` 是查询生成友好的确定性投影视图。'''
priority_new = '''### 0.5 最终规范优先级

1. 本文 V6.1 各章中的“最终规范/规范收敛”条目为当前推荐行为；
2. V5.16 详细设计中的旧路径、旧接口值、旧 Checkpoint 描述等作为历史实现与兼容背景保留，不应覆盖已明确收敛的 V5.17/PR #42/V6.1 规则；
3. 当前关键收敛包括：动态 Enum/Instance 统一 MinIO CSV 交付、`instanceDataSourceMode=OAC|BUSINESS_NOTICE`、Software ≤1W 源侧用户、SEC ≤100W 源侧用户、SHA-256、`T_OAG_INDEX_TASK.CHECKPOINT` TEXT JSON、未完成 Chunk 幂等重放、最终返回增加 `semanticExtensions.valueMappings`；
4. `retrievalResults` 是语义命中事实，`seedNodes/nodes/edges` 是图构建/兼容结构，`semanticExtensions.valueMappings` 是查询生成友好的确定性投影视图；
5. **V6.1 Schema 修正**：`t_oag_{ontology_id}` 保持各语言字段逐列展开；`t_oag_instance_{ontology_id}` 恢复内嵌 `synonyms` 字段。实例同义词不建立独立物理记录，真实过滤值仍使用 `value`；历史章节中“Instance 仅保存 value / Instance Dense 仅使用 `{value}`”的描述视为旧方案。'''
if priority_old not in text:
    raise RuntimeError('priority block not found')
text = text.replace(priority_old, priority_new, 1)

start_marker = '## 2.0 V5.17 规范收敛与新增设计（完整保留）'
end_marker = '## 2.1 V5.16 完整详细设计（信息基线，完整保留）'
start = text.index(start_marker)
end = text.index(end_marker, start)
current = text[start:end]

# Keep the physical index overview aligned with the corrected Instance schema.
current, n = re.subn(
    r'(\| 实例元素 \| `t_oag_instance_\{ontology_id\}` \| OAG，业务侧提供源数据 \| )Instance Value( \|)',
    r'\1Instance Value + Synonyms\2',
    current,
    count=1,
)
if n != 1:
    raise RuntimeError(f'instance overview row replacement count={n}')

new_23 = r'''### 2.3 `t_oag_{ontology_id}` GaussVector 表结构

本体对象表保持原有的**各语言字段逐列展开**结构，不使用 `display_zh/en/lang_1/lang_2`、`description_zh/en/lang_1/lang_2` 这类合并字段表示。中文、英文为固定字段，另外最多保留 2 个可演进语言槽位：

| 字段 | 类型 | 非空 | 说明 |
|---|---|---:|---|
| `vector` | `DOUBLE[]` | ✔ | BGE-M3 1024 维向量 |
| `type` | `INT` |  | 0 ObjectType，1 Property |
| `id` | `VARCHAR(256 CHAR)` | ✔ | ObjectType / Property 全局唯一 ID |
| `parent_id` | `VARCHAR(256 CHAR)` |  | 父元素 ID；当 type=1 时记录 Property 所属 ObjectType ID |
| `name` | `VARCHAR(256 CHAR)` |  | 本体真实名称 |
| `display_zh` | `VARCHAR(512 CHAR)` |  | 中文显示名 |
| `display_en` | `VARCHAR(512 CHAR)` |  | 英文显示名 |
| `display_lang_1` | `VARCHAR(512 CHAR)` |  | 第 1 个额外语言显示名 |
| `display_lang_2` | `VARCHAR(512 CHAR)` |  | 第 2 个额外语言显示名 |
| `description_zh` | `VARCHAR(1024 CHAR)` |  | 中文描述 |
| `description_en` | `VARCHAR(1024 CHAR)` |  | 英文描述 |
| `description_lang_1` | `VARCHAR(1024 CHAR)` |  | 第 1 个额外语言描述 |
| `description_lang_2` | `VARCHAR(1024 CHAR)` |  | 第 2 个额外语言描述 |
| `synonyms` | `TEXT` |  | LF 分隔的同义词平铺字符串；不保存 JSON Map/Array |

约束：

1. Schema 层始终逐语言列展开，便于字段类型、Analyzer、查询过滤和运维观测独立配置；
2. `lang_1/lang_2` 是本体级可配置语言槽位，不把具体语言码写死进数据库 Schema；
3. `synonyms` 仍采用语言无关的 LF 平铺 String/TEXT，语言信息只在 OMS SynonymType 源模型中保留；
4. 空语言字段保持 NULL/空值，不写占位文本。
'''

p23 = re.compile(r'### 2\.3 `t_oag_\{ontology_id\}`[^\n]*\n.*?(?=\n### 2\.4 )', re.S)
current, n = p23.subn(new_23.rstrip(), current, count=1)
if n != 1:
    raise RuntimeError(f'2.3 replacement count={n}')

new_27 = r'''### 2.7 `t_oag_instance_{ontology_id}` Instance Value

实例索引保存**去重后的真实列值 + 内嵌同义词**。`synonyms` 用于召回和命中解释，但不建立独立 Instance Synonym 记录；真实查询过滤值始终以 `value` 为准。

| 字段 | 类型 | 非空 | 说明 |
|---|---|---:|---|
| `vector` | `DOUBLE[]` | ✔ | Instance Value 语义向量，1024 维 |
| `property_id` | `VARCHAR(512 CHAR)` | ✔ | 所属 Property.id |
| `object_type_id` | `VARCHAR(256 CHAR)` |  | Property 所属 ObjectType.id |
| `value` | `VARCHAR(4096 CHAR)` | ✔ | 去重后的真实标准列值；下游过滤条件使用该值 |
| `synonyms` | `TEXT` |  | 实例值同义词，LF 分隔平铺字符串；只作为召回/解释字段，不作为真实过滤值 |

业务唯一键继续使用：

```text
(normalized_value, property_id, object_type_id)
```

`synonyms` 不参与业务唯一键，避免同义词变化导致同一个真实 Instance Value 被误判为新业务记录。

Instance 不配置多语言 `display/description` 列；同义词统一使用与本体对象/Enum 相同的 LF 平铺表达：

```text
别名1
别名2
Alias-1
Alias-2
```

Dense Embedding 输入调整为：

```text
{value}
{synonyms}
```

其中 `value` 放在首行并作为主语义，`synonyms` 仅用于增强用户别名/黑话表达的 Dense 召回。OpenSearch `instanceLexical` 同时检索：

```text
value       → Exact / BM25
synonyms    → Exact / BM25
```

命中 synonym 时必须保留：

```text
matchedField = synonyms
matchedValue = 实际命中的实例同义词
value        = 真实标准实例值
```

Entity Linking 最终仍输出：

```text
sourceValue
→ canonical/actual value = value
→ Property
→ ObjectType
```

因此下游 Agent/LLM 可以使用 synonym 理解用户表达，但生成过滤条件时统一使用真实 `value`。

未来如需进一步节省空间，可演进为 value 表 + binding 表，但不改变 Entity Linking 和 `semanticExtensions.valueMappings` 的结果语义。
'''

p27 = re.compile(r'### 2\.7 `t_oag_instance_\{ontology_id\}` Instance Value\n.*?(?=\n### 2\.8 )', re.S)
current, n = p27.subn(new_27.rstrip(), current, count=1)
if n != 1:
    raise RuntimeError(f'2.7 replacement count={n}')

text = text[:start] + current + text[end:]

# Add an explicit V6.1 note near the top without rewriting historical source snapshots.
anchor = '> 整合原则：**信息完整性优先。V5.16 作为完整详细设计基线，V5.17 作为规范收敛与新增设计；重复内容可以分层归并，但任何具有独立语义的原始设计信息不得因重写而删除。PR #42 原附录内容已按主题合并回正文，不再作为独立附录。**'
note = anchor + '\n> V6.1 修正：**2.3 恢复本体对象 GaussVector 多语言字段逐列展开；2.7 为 Instance Value 恢复内嵌 `synonyms`，实例 Dense/Lexical 均可利用 synonym 召回，但真实过滤值始终使用 `value`。**'
if anchor not in text:
    raise RuntimeError('top integration anchor missing')
text = text.replace(anchor, note, 1)

# Safety checks: verify current normative block, not only historical copies.
check_start = text.index(start_marker)
check_end = text.index(end_marker, check_start)
check = text[check_start:check_end]
required = [
    '| `display_zh` | `VARCHAR(512 CHAR)`',
    '| `display_en` | `VARCHAR(512 CHAR)`',
    '| `display_lang_1` | `VARCHAR(512 CHAR)`',
    '| `display_lang_2` | `VARCHAR(512 CHAR)`',
    '| `description_zh` | `VARCHAR(1024 CHAR)`',
    '| `description_en` | `VARCHAR(1024 CHAR)`',
    '| `description_lang_1` | `VARCHAR(1024 CHAR)`',
    '| `description_lang_2` | `VARCHAR(1024 CHAR)`',
    '| `synonyms` | `TEXT` |  | 实例值同义词',
    '{value}\n{synonyms}',
    'matchedField = synonyms',
    'Instance Value + Synonyms',
]
for token in required:
    if token not in check:
        raise RuntimeError(f'missing required normative token: {token}')

for forbidden in [
    '| `display_zh/en/lang_1/lang_2`',
    '| `description_zh/en/lang_1/lang_2`',
    '实例索引只保存去重后的真实列值：',
]:
    if forbidden in check:
        raise RuntimeError(f'old normative representation remains: {forbidden}')

DOC.write_text(text, encoding='utf-8')
print('updated', DOC)
print('version V6.1')
print('2.3 expanded language columns: PASS')
print('2.7 instance synonyms: PASS')
