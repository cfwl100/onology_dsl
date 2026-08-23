from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8').replace('\r\n', '\n')

# -----------------------------------------------------------------------------
# 1. Formal document header: keep current version/date, remove merge/review trail.
# -----------------------------------------------------------------------------
header_re = re.compile(
    r'^# OAG 本体锚点语义检索与向量索引设计方案\n\n---\n\n'
    r'> 版本：V6\.1（全量整合版）  \n'
    r'> 日期：2026-08-23  \n'
    r'> 来源：.*?\n'
    r'> 整合原则：.*?\n'
    r'> V6\.1 修正：.*?\n\n---\n',
    re.S,
)
header_new = '''# OAG 本体锚点语义检索与向量索引设计方案

---

> 版本：V6.1  
> 日期：2026-08-23  
> 文档定位：OAG 本体语义索引管理、混合语义检索、本体对象投影与子图构建的正式设计规范。  
> 设计范围：覆盖索引模型与构建、OAC/MinIO 数据接入、Entity Extraction / Entity Linking、Lexical + Dense 混合召回、Weighted RRF、LLM 精排、PathProbePlan、nGQL/图算法执行以及最终结果返回。

---
'''
text, n = header_re.subn(header_new, text, count=1)
if n != 1:
    raise RuntimeError(f'formal header replacement count={n}')

text = text.replace(
    '阅读规则：每章的“V5.17 规范收敛与新增设计”用于说明当前推荐行为；“V5.16 完整详细设计”保留原有实现、接口、DDL、兼容方案、算法、错误处理、评测和灰度信息。若出现历史路径与当前收敛规范并存，明确标注为历史/兼容信息，当前执行以 V5.17/PR #42 收敛规则为准。',
    '阅读规则：本文按“核心设计 + 详细设计与实现”组织。核心设计定义当前规范，详细设计补充接口、DDL、算法、错误处理、性能、评测、兼容和灰度要求；同一主题如存在多处说明，应保持字段、接口和执行语义一致。'
)

# Remove chapter 0 revision/source/review records completely.
text, n = re.subn(
    r'\n---\n\n## 0\. 版本来源、信息完整性与规范优先级\n.*?(?=\n---\n\n# 1\. 设计目标、术语与总体架构)',
    '',
    text,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError(f'chapter 0 removal count={n}')

# Formal wrapper headings; remove version-evolution wording.
text = re.sub(r'## ([1-7])\.0 V5\.17 规范收敛与新增设计（完整保留）', r'## \1.0 核心设计', text)
text = re.sub(r'## ([1-7])\.1 V5\.16 完整详细设计（信息基线，完整保留）', r'## \1.1 详细设计与实现', text)

# Remove PR review-only blocks; substantive decisions already exist in core/detail chapters.
for start_marker, end_marker in [
    ('## 1.2 PR #42 检视结论在总体架构中的收敛', '# 2. 数据模型与语义索引结构'),
    ('## 3.100 PR #42 检视规范：数据接入、容量、文件身份、Checkpoint、性能与错误处理', '# 4. 实体提取、Entity Linking 与 6 路混合召回'),
    ('## 7.100 PR #42 检视规范：配置、可观测性、验收、修订规则与最终决策', '# 8. 全量信息覆盖与维护原则'),
]:
    s = text.find(start_marker)
    if s < 0:
        raise RuntimeError(f'missing review start marker: {start_marker}')
    e = text.find(end_marker, s)
    if e < 0:
        raise RuntimeError(f'missing review end marker: {end_marker}')
    # Preserve the next top-level chapter marker except for chapter 8, which is removed below.
    text = text[:s] + text[e:]

# Remove chapter 8 maintenance/meta chapter completely.
text, n = re.subn(r'\n# 8\. 全量信息覆盖与维护原则\n.*\Z', '\n', text, count=1, flags=re.S)
if n != 1:
    raise RuntimeError(f'chapter 8 removal count={n}')

# -----------------------------------------------------------------------------
# 2. Formalize 2.6 Enum schema: expand all language columns explicitly.
# -----------------------------------------------------------------------------
sec26_re = re.compile(
    r'### 2\.6 `t_oag_enum_\{ontology_id\}` Enum Value\n.*?(?=\n### 2\.7 `t_oag_instance_\{ontology_id\}` Instance Value)',
    re.S,
)
sec26_new = '''### 2.6 `t_oag_enum_{ontology_id}` Enum Value

真正入索引的粒度是 `EnumType.values[]` 的每一个枚举值；一个 EnumType 被多个 Property 复用时按实际 Property 引用展开。

表结构保持与原有设计一致，**各语言字段逐列展开**，中文、英文为固定字段，另外最多保留 2 个可演进语言槽位：

| 字段 | 类型 | 非空 | 说明 |
|---|---|---:|---|
| `vector` | `DOUBLE[]` | ✔ | Enum Value 1024 维语义向量 |
| `value` | `VARCHAR(4096 CHAR)` |  | 真实标准枚举值 |
| `property_id` | `VARCHAR(512 CHAR)` | ✔ | 引用该 Enum 的 Property.id |
| `object_type_id` | `VARCHAR(256 CHAR)` |  | Property 所属 ObjectType.id |
| `display_zh` | `VARCHAR(512 CHAR)` |  | 中文 display |
| `display_en` | `VARCHAR(512 CHAR)` |  | 英文 display |
| `display_lang_1` | `VARCHAR(512 CHAR)` |  | 第 1 个额外语言 display |
| `display_lang_2` | `VARCHAR(512 CHAR)` |  | 第 2 个额外语言 display |
| `description_zh` | `TEXT` |  | 中文 description |
| `description_en` | `TEXT` |  | 英文 description |
| `description_lang_1` | `TEXT` |  | 第 1 个额外语言 description |
| `description_lang_2` | `TEXT` |  | 第 2 个额外语言 description |
| `synonyms` | `TEXT` |  | LF 分隔的 Enum Value 同义词平铺字符串 |

业务唯一键：

```text
objectTypeId + propertyId + normalized(value)
```

`synonyms` 不参与业务唯一键；同义词变化通过相同业务键覆盖当前记录。

向量化顺序：

```text
{value}
{display_zh}
{display_en}
{display_lang_1}
{display_lang_2}
{description_zh}
{description_en}
{description_lang_1}
{description_lang_2}
{synonyms}
```

约束：

1. Schema 层按语言逐列展开，不使用 `display_zh/en/lang_1/lang_2`、`description_zh/en/lang_1/lang_2` 这类合并表示；
2. `lang_1/lang_2` 为 ontology 级可配置语言槽位；
3. `value` 是权威真实过滤值；display/description/synonyms 只负责召回、排序与解释；
4. Synonym 仍统一使用 LF 平铺 String/TEXT，不建立独立 Enum Synonym 物理记录。
'''
text, n = sec26_re.subn(sec26_new.rstrip(), text, count=1)
if n != 1:
    raise RuntimeError(f'2.6 replacement count={n}')

# -----------------------------------------------------------------------------
# 3. Make the detailed Instance design consistent with the restored synonyms.
# -----------------------------------------------------------------------------
# 2.1 logical model table
text = text.replace(
    '| 实例元素   | Instance Value        | 不建立实例同义词记录                 | `propertyid + objectTypeId`           |',
    '| 实例元素   | Instance Value        | `synonyms` 以内嵌 LF 平铺字段保存；不建立独立同义词记录 | `propertyid + objectTypeId`           |'
)

# 2.2 detail overview
text = text.replace(
    '| 实例元素   | `t_oag_instance_{ontology_id}` | OAG，业务服务 提供数据 | Instance Value        |',
    '| 实例元素   | `t_oag_instance_{ontology_id}` | OAG，业务服务 提供数据 | Instance Value + Synonyms |'
)

# 2.10 detailed table: singular synonym -> plural canonical field
text = text.replace(
    '| `synonym`        | `VARCHAR(4096 CHAR)` |     | 真实列值的同义词                  |',
    '| `synonyms`       | `TEXT`               |     | 实例值同义词，LF 分隔平铺字符串；仅用于召回与解释 |'
)
text = text.replace(
    '实例索引保存去重后的真实列值，每条记录直接携带所属 Property 和 ObjectType。',
    '实例索引保存去重后的真实列值及其内嵌同义词，每条记录直接携带所属 Property 和 ObjectType。`synonyms` 不建立独立物理行，真实过滤值始终使用 `value`。'
)

# 2.12 detailed Instance embedding
text = text.replace(
    '实例列值 Dense 内容严格只使用：\n\n```text\n{value}\n```\n\n这样 Instance Dense 表达始终由真实业务值主导；Property/ObjectType 归属直接由记录中的 `propertyid + objectTypeId` 提供。',
    '实例列值 Dense 内容使用：\n\n```text\n{value}\n{synonyms}\n```\n\n`value` 必须放在首行并作为主语义；`synonyms` 仅增强别名、黑话和业务俗称召回。Property/ObjectType 归属直接由记录中的 `propertyid + objectTypeId` 提供，禁止额外拼接 Property/ObjectType 名称或描述。'
)

# 2.13 detailed OpenSearch Instance fields
old_instance_os = '''#### `t_oag_instance_{ontology_id}`

只需要：

```text
type          integer
propertyid    keyword
objectTypeId  keyword
value         keyword + text
```

Exact 主要搜索 `propertyid/objectTypeId/value.keyword`，BM25 搜索 `value`.'''
new_instance_os = '''#### `t_oag_instance_{ontology_id}`

核心字段：

```text
type          integer
propertyid    keyword
objectTypeId  keyword
value         keyword + text
synonyms      text multi-field
```

Exact 主要搜索 `propertyid/objectTypeId/value.keyword` 和 `synonyms` 的整行 synonym token；BM25 搜索 `value` 与 `synonyms.bm25`。命中 synonym 时返回 `matched_field=synonyms`、`matched_value=实际命中同义词`，真实过滤值仍返回 `value`.'''
if old_instance_os in text:
    text = text.replace(old_instance_os, new_instance_os)
else:
    # punctuation in source may use Chinese full stop / no trailing period; use regex fallback
    text, n = re.subn(
        r'#### `t_oag_instance_\{ontology_id\}`\n\n只需要：\n\n```text\ntype\s+integer\npropertyid\s+keyword\nobjectTypeId\s+keyword\nvalue\s+keyword \+ text\n```\n\nExact 主要搜索 `propertyid/objectTypeId/value\.keyword`，BM25 搜索 `value`。',
        new_instance_os,
        text,
        count=1,
    )
    if n != 1:
        raise RuntimeError('detailed instance OpenSearch block not found')

# 2.15 language model description
text = text.replace(
    'Instance Value\n  → 仅 value；language 为可选观测/Analyzer Hint',
    'Instance Value\n  → value + LF 平铺 synonyms；不配置 display/description 多语言列，language 仅作为可选观测/Analyzer Hint'
)

# 3.6 current summary Instance schema
text = text.replace(
    'object_type_id\nproperty_id\nvalue\noperation      # INCREMENTAL 时 UPSERT/DELETE',
    'object_type_id\nproperty_id\nvalue\nsynonyms       # optional，LF 平铺同义词\noperation      # INCREMENTAL 时 UPSERT/DELETE'
)

# 3.6.2 detailed CSV
text = text.replace(
    'propertyid,objectTypeId,value,language,op',
    'propertyid,objectTypeId,value,synonyms,op'
)
text = text.replace(
    '| `synonym`        | `VARCHAR(4096 CHAR)` | 真实列值的同义词            |',
    '| `synonyms`       | `synonyms`           | 实例值同义词；CSV 中使用 `\\n` 转义表达 LF 分隔 |'
)
text = text.replace(
    'prop:subscriber:subLevel,obj:subscriber:Subscriber,VIP,und,UPSERT\nprop:subscriber:subLevel,obj:subscriber:Subscriber,GOLD,und,UPSERT',
    'prop:subscriber:subLevel,obj:subscriber:Subscriber,VIP,"重要客户\\nVIP客户",UPSERT\nprop:subscriber:subLevel,obj:subscriber:Subscriber,GOLD,"黄金客户\\nGold Customer",UPSERT'
)

# OpenAPI InstanceValueRecord and example
text = text.replace(
    '        value: { type: string, maxLength: 4096 }\n        language: { type: string, default: und }\n        op:',
    '        value: { type: string, maxLength: 4096 }\n        synonyms:\n          type: string\n          description: 实例值同义词平铺字符串，逻辑分隔符为 LF；REST JSON 使用 \\n 转义\n        op:'
)
text = text.replace(
    '            value: VIP\n            language: und\n            op: UPSERT',
    '            value: VIP\n            synonyms: "重要客户\\nVIP客户"\n            op: UPSERT'
)

# 3.10 detailed pipeline
text = text.replace(
    '唯一业务范围：`objectTypeId + propertyid + normalized(value)`。Embedding 严格复用第 2.12 节：`{value}`。',
    '唯一业务范围：`objectTypeId + propertyid + normalized(value)`。Embedding 复用第 2.12 节：`{value}` + `{synonyms}`；`synonyms` 不参与业务唯一键。'
)

# 4.x / 5.x detailed search result and runtime sequence consistency
text = text.replace('└─ Instance Value（value 命中）', '└─ Instance Value（value/synonyms 命中）')
text = text.replace('D->>OS: value Exact/BM25\n      D->>GV: Dense(value only)', 'D->>OS: value/synonyms Exact/BM25\n      D->>GV: Dense(value + synonyms)')

# 7 core decisions consistency
text = text.replace('5. ObjectType/Property/Enum 的同义词进入 OAG 后统一为 LF `synonyms`；', '5. ObjectType/Property/Enum/Instance 的同义词进入 OAG 后统一为 LF `synonyms`；')
text = text.replace('6. Instance 向量严格只使用真实 `value`；', '6. Instance 向量使用真实 `value` + 内嵌 `synonyms`，其中 `value` 为主语义和唯一真实过滤值；')

# Detailed anti-patterns/final decisions consistency
text = text.replace(
    '4. **为实例值额外建立独立同义词记录。** Instance Evidence 只保存去重后的真实 value。\n5. **实例向量拼接 Property/描述/同义词。** Instance Dense 严格只使用 `{value}`。',
    '4. **为实例值额外建立独立同义词记录。** Instance 同义词必须内嵌在真实 value 记录的 `synonyms` 字段中。\n5. **实例向量拼接 Property/ObjectType/描述。** Instance Dense 只使用 `{value}` + `{synonyms}`，不注入归属对象文本。'
)
text = text.replace(
    '8. **Synonym 不建立独立物理行；Instance Evidence 只保存真实实例值。**',
    '8. **Synonym 不建立独立物理行；Instance 记录保存真实实例值及内嵌 `synonyms`。**'
)
text = text.replace(
    '13. **Instance Value 向量化严格只使用 `{value}`。**',
    '13. **Instance Value 向量化使用 `{value}` + `{synonyms}`，真实过滤值仍只使用 `value`。**'
)
text = text.replace(
    'Seed/Enum 向量直接包含平铺 synonyms，Instance 向量只包含 value。',
    'Seed/Enum/Instance 向量均可包含平铺 synonyms，其中 Instance 以 value 为首行主语义且不拼接 Property/ObjectType/description。'
)

# Remove explicit review/revision/history wording in remaining formal text.
replacements = {
    'V5.7 不要求一次性替换现有链路，而是在现有类和接口上渐进演进：': '当前设计不要求一次性替换现有链路，而是在现有类和接口上渐进演进：',
    'V5.7 保留。': '当前设计保留。',
    'V5.15 将检索数据模型统一为三个业务层次：': '检索数据模型统一为三个业务层次：',
    '**历史方案（保留演进信息，不作为当前最终规范）：** ': '',
    '**历史兼容描述：** ': '**兼容说明：** ',
    '历史兼容默认值': '兼容默认值',
    '历史版本曾为 `VARCHAR(1024)`，当前通过升级脚本扩展为 TEXT': '数据库类型统一使用 TEXT',
    ' -- 历史版本为 VARCHAR(1024)，V5.16 检视后升级为 TEXT JSON': ' -- TEXT JSON Checkpoint',
    '原方案描述了每个 Chunk 的：': 'Chunk 运行期包含以下状态信息：',
    '本轮设计不引入该表。': '本设计不引入该表。',
    '本轮评审将当前产品规格收敛为：': '当前产品容量规格定义为：',
    '检视后，原先：': '外部协议统一为：',
}
for a, b in replacements.items():
    text = text.replace(a, b)

# Remove the obsolete old OAC_QUERY/AUTO historical config/table block but retain DataSeek alignment paragraph.
text, _ = re.subn(
    r'#### 数据源访问模式、容量规格与 DataSeek 对齐结论\n\n(?:.*?)(?=与 DataSeek/NL2SQL 的对齐采用统一语义值逻辑模型：)',
    '#### DataSeek / NL2SQL 语义值模型对齐\n\n',
    text,
    count=1,
    flags=re.S,
)

# Remove obsolete compatibility sentence that reintroduces old direct-return routes.
text = re.sub(
    r'\n\*\*兼容说明：\*\* 三种数据交付方式曾在进入 OAG 前区分 OMS、OAC 小批/分页和 MinIO 大文件；.*?流水线。\n',
    '\n',
    text,
    count=1,
    flags=re.S,
)

# Normalize first-import detailed baseline to current protocol.
text = text.replace(
    '| Software | ≤ 10,000 | OAC Query | 分页读取 + Embedding Batch + 双存储 Bulk，可单任务完成 |\n| SEC / IOH | ≤ 1,000,000 | MinIO Bulk | 文件切 Chunk、Embedding Worker 池、GaussVector/OpenSearch 独立 Bulk Writer、Checkpoint 恢复 |',
    '| Software | ≤ 10,000 源侧用户 | MinIO + `LIGHTWEIGHT_BULK` | Streaming/Chunk/Checkpoint 启用，较少 Worker 和较小队列 |\n| SEC / IOH | ≤ 1,000,000 源侧用户 | MinIO + `RECOVERABLE_BULK` | Streaming、Chunk、Embedding Worker 池、双 Writer、Backpressure、Checkpoint 恢复 |'
)

# Remove review/meta phrases that should not appear in a formal design.
for phrase in ['PR #42', '附录 A', '检视意见', '检视规范', '检视结论', '本轮检视', 'V6.1 修正']:
    text = text.replace(phrase, '')

# -----------------------------------------------------------------------------
# 4. Structural cleanup and final validation.
# -----------------------------------------------------------------------------
# Avoid excessive separators created by block removal.
text = re.sub(r'(\n---\n){3,}', '\n---\n\n', text)
text = re.sub(r'\n{4,}', '\n\n\n', text)

# Ensure current authoritative 2.3/2.6/2.7 fields are explicit.
required = [
    '### 2.3 `t_oag_{ontology_id}` GaussVector 表结构',
    '| `display_zh` | `VARCHAR(512 CHAR)`',
    '| `description_lang_2` | `VARCHAR(1024 CHAR)`',
    '### 2.6 `t_oag_enum_{ontology_id}` Enum Value',
    '| `display_zh` | `VARCHAR(512 CHAR)` |  | 中文 display |',
    '| `display_en` | `VARCHAR(512 CHAR)` |  | 英文 display |',
    '| `display_lang_1` | `VARCHAR(512 CHAR)` |  | 第 1 个额外语言 display |',
    '| `display_lang_2` | `VARCHAR(512 CHAR)` |  | 第 2 个额外语言 display |',
    '| `description_zh` | `TEXT` |  | 中文 description |',
    '| `description_en` | `TEXT` |  | 英文 description |',
    '| `description_lang_1` | `TEXT` |  | 第 1 个额外语言 description |',
    '| `description_lang_2` | `TEXT` |  | 第 2 个额外语言 description |',
    '### 2.7 `t_oag_instance_{ontology_id}` Instance Value',
    '| `synonyms` | `TEXT` |  | 实例值同义词',
    '{value}\n{synonyms}',
    'semanticExtensions.valueMappings',
    'PathProbePlan',
    'instanceDataSourceMode: OAC',
]
for token in required:
    if token not in text:
        raise RuntimeError(f'missing required token: {token}')

for forbidden in [
    '| `display_zh/en/lang_1/lang_2`',
    '| `description_zh/en/lang_1/lang_2`',
    '## 0. 版本来源',
    'PR #42',
    '检视规范',
    '检视结论',
    'V5.16 完整详细设计',
    'V5.17 规范收敛',
    '# 8. 全量信息覆盖与维护原则',
    'V6.1 修正',
]:
    if forbidden in text:
        raise RuntimeError(f'formalization residue remains: {forbidden}')

DOC.write_text(text.rstrip() + '\n', encoding='utf-8')
print('formalized:', DOC)
print('enum expanded languages: PASS')
print('instance synonyms consistency: PASS')
print('revision/review records removed: PASS')
print('chars:', len(text), 'lines:', text.count('\\n') + 1)
