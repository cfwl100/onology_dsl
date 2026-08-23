from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8')

start_marker = '# 2. 数据模型与语义索引结构'
end_marker = '# 3. 语义索引管理：构建、数据接入、任务、MinIO 与一致性'
assert text.count(start_marker) == 1, f'unexpected chapter 2 marker count: {text.count(start_marker)}'
assert text.count(end_marker) == 1, f'unexpected chapter 3 marker count: {text.count(end_marker)}'
start = text.index(start_marker)
end = text.index(end_marker)

chapter2 = r'''# 2. 数据模型与语义索引结构

本章只定义 OAG 语义索引的**数据模型、向量化规则、全文索引规则和物理存储结构**。索引构建任务、MinIO、Checkpoint、FULL_REPLACE / INCREMENTAL 等生命周期机制统一在第 3 章定义。

整体按照三类稳定语义实体组织：

```text
本体对象：ObjectType / Property
枚举元素：Enum Value
实例元素：Instance Value
```

三类数据分别建立 GaussVector 向量索引和 OpenSearch 全文索引；两种存储使用同一业务语义和稳定业务键，在检索层统一归一化为 SearchHit。

---

## 2.1 总体索引模型

### 2.1.1 三类物理索引与统一命名

| 逻辑类型 | GaussVector 表 | OpenSearch Index | Owner | 索引粒度 | 稳定业务键 |
|---|---|---|---|---|---|
| 本体对象 | `t_oag_{ontology_id}` | `t_oag_{ontology_id}` | OAG | 1 个 ObjectType / Property 1 条记录 | `id` |
| 枚举元素 | `t_oag_enum_{ontology_id}` | `t_oag_enum_{ontology_id}` | OAG | 1 个 Property 下的 1 个 Enum Value 1 条记录 | `object_type_id + property_id + normalized(value)` |
| 实例元素 | `t_oag_instance_{ontology_id}` | `t_oag_instance_{ontology_id}` | OAG；业务侧提供源数据 | 1 个 Property 下去重后的 1 个 Instance Value 1 条记录 | `object_type_id + property_id + normalized(value)` |

三类数据保持物理隔离，主要原因：

```text
数据规模不同
更新频率不同
ANN 算法和参数不同
数据 Owner / 来源不同
TopK / similarityThreshold 不同
容量与分表策略不同
```

### 2.1.2 统一索引处理链路

```text
OMS / OAC / Business Data
        ↓
Schema / Ontology Mapping
        ↓
Normalize + Synonym Flatten + Dedup
        ↓
┌──────────────────────────┬──────────────────────────┐
│ EmbeddingInputBuilder    │ LexicalDocumentBuilder   │
│ BGE-M3 / 1024 dim        │ Exact / BM25             │
└────────────┬─────────────┴─────────────┬────────────┘
             ↓                           ↓
        GaussVector                 OpenSearch
             └────────────┬──────────────┘
                          ↓
                 SearchHit Normalizer
```

统一原则：

1. GaussVector 和 OpenSearch 必须使用同一条业务记录的相同 `id / property_id / object_type_id / value / synonyms` 语义；
2. Dense 与 Lexical 的差异只体现在索引方式和查询方式，不允许形成两套业务数据模型；
3. 同一业务键重复导入只能覆盖原记录，不能产生重复向量或重复全文文档；
4. Enum / Instance 可以成为最终语义检索结果，但不直接成为 Core Graph 路径算法顶点。

### 2.1.3 Core Graph 与语义索引边界

```text
语义索引负责：
ObjectType / Property / Enum Value / Instance Value 的语义定位

Core Graph 负责：
ObjectType / Property / Relationship 的拓扑连接
```

Enum / Instance 命中后，通过 `property_id + object_type_id` 投影回 Property / ObjectType，再进入子图算法。Synonym 只作为所属业务记录的检索字段，不建立独立图节点或独立物理索引记录。

---

## 2.2 公共建模与检索规则

### 2.2.1 多语言字段规则

本体对象和 Enum Value 的 Display / Description 使用固定槽位：

```text
固定语言：zh + en
额外语言：lang_1 + lang_2
总计最多 4 种语言
```

对应物理字段：

```text
display_zh
display_en
display_lang_1
display_lang_2

description_zh
description_en
description_lang_1
description_lang_2
```

规则：

- `lang_1 / lang_2` 是 ontology 级可配置语言槽位，不把具体小语种语言码写死到数据库 Schema；
- 未配置的语言槽位保持 NULL / 空值；
- Instance Value 不配置 `display_* / description_*` 多语言列；
- 不通过不断增加 `display_xx / description_xx` 列扩展语言数量。

### 2.2.2 OMS SynonymType 到 OAG `synonyms` 的统一表达

OMS 继续保留结构化、多语言 SynonymType：

```json
{
  "id": "term-color-synonyms",
  "synonyms": {
    "zh": ["颜色", "色彩", "色泽"],
    "en": ["Color", "Colour"],
    "es": ["Color"]
  }
}
```

OMS 源模型约束：

```text
synonyms 最多 3 个 language key
language key 不固定
每个 language 可包含多个 synonym
language key 使用 BCP 47 风格，例如 zh / en / es / es-MX / pt-BR
```

进入 OAG 后不保存 language Map，而统一平铺成 LF String：

```text
颜色
色彩
色泽
Color
Colour
```

转换规则：

```text
SynonymType.synonyms(language → values[])
  ↓
zh / en 存在时优先，其余 language tag 按字典序
  ↓
语言内保持源数组顺序
  ↓
trim / Unicode normalize / 去空
  ↓
按规范化值去重，保留第一次出现的原文
  ↓
LF join
  ↓
synonyms TEXT/String
```

传输到 JSON / CSV 时可使用字面量 `\n`：

```json
{
  "synonyms": "颜色\n色彩\n色泽\nColor\nColour"
}
```

关键边界：

1. OMS 保留多语言源结构，OAG 热索引只保留 LF 平铺 String；
2. GaussVector / OpenSearch / REST Batch / CSV 使用同一个 `synonyms` 物理表达；
3. SynonymType 不建立独立向量记录或独立全文记录；
4. SynonymType 自身的 `name / display / description` 不重复拼入所属实体 Embedding；
5. OAG 不建立 `synonyms.zh / synonyms.en / synonyms.<language>` dynamic object。

### 2.2.3 文本规范化规则

规范化属于索引构建和查询处理逻辑，不额外增加 `normalized_*` 持久化字段：

```text
trim
Unicode normalize
casefold（适用语言）
连续空白归一
全半角归一
```

`name / value / display / description` 保留原始业务文本；规范化值只用于去重、业务键比较、Exact 匹配和幂等判断。

`SynonymFlattener` 额外执行：

```text
CRLF / CR → LF
按 LF split
trim
去空行
按规范化值去重并保留首次出现原文
重新 LF join
```

### 2.2.4 OpenSearch `synonyms` 公共 Analyzer

ObjectType / Property / Enum / Instance 的 `synonyms` 统一使用“整行 Exact + 普通 BM25”双模式：

```yaml
analysis:
  tokenizer:
    synonym_line_tokenizer:
      type: pattern
      pattern: '\\n+'
  analyzer:
    synonym_line_analyzer:
      type: custom
      tokenizer: synonym_line_tokenizer
      filter: [lowercase, asciifolding]
```

字段映射：

```yaml
synonyms:
  type: text
  analyzer: synonym_line_analyzer
  search_analyzer: synonym_line_analyzer
  fields:
    bm25:
      type: text
      analyzer: standard
```

语义：

```text
synonyms 主字段
  → 一个 LF 行作为一个完整 synonym token
  → 用于 synonym line-exact

synonyms.bm25
  → 普通全文 Analyzer
  → 用于 synonym BM25
```

Synonym 命中统一保留：

```text
matched_field = synonyms
matched_value = 实际命中的 synonym 行
```

Exact 可直接定位命中行；BM25 命中由 `SynonymMatchResolver` 对原始 `synonyms` 做 LF split，再使用与检索一致的 normalizer 选择最匹配的 `matched_value`，不执行 JSON 反序列化。

### 2.2.5 `language_hint` 与语言检索规则

Query Understanding 可以输出：

```text
language_hint = BCP 47 language tag / mixed / und
```

使用规则：

```text
display / description
  → 可根据 language_hint 选择 Analyzer 或 Boost

synonyms
  → 不按 language_hint 硬过滤
  → 不做 synonyms.<language> Boost

Dense
  → 不按 language_hint 硬过滤

LLM Rerank
  → 始终看到原始 Query 与全部候选
```

由于 OAG `synonyms` 已经平铺，线上不能从字段名反推出 synonym 的源语言；需要语言级统计时，应使用 OMS SynonymType 或离线标注数据。

---

## 2.3 本体对象索引：ObjectType / Property

本体对象使用同一张物理表，通过 `type` 区分 ObjectType 和 Property。

### 2.3.1 GaussVector / OpenSearch 数据结构

```text
t_oag_{ontology_id}
```

| 字段 | GaussVector 类型 | OpenSearch 类型 | 非空 | 说明 |
|---|---|---|---:|---|
| `vector` | `DOUBLE[]` | - | ✔ | BGE-M3 1024 维向量，仅 GaussVector 保存 |
| `type` | `INT` | `integer` |  | 0 ObjectType；1 Property |
| `id` | `VARCHAR(256 CHAR)` | `keyword` | ✔ | ObjectType / Property 全局唯一 ID，也是业务键 |
| `parent_id` | `VARCHAR(256 CHAR)` | `keyword` |  | Property 所属 ObjectType.id；ObjectType 可空 |
| `name` | `VARCHAR(256 CHAR)` | `keyword + text` |  | 本体真实名称，支持 Exact / BM25 |
| `display_zh` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 中文显示名 |
| `display_en` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 英文显示名 |
| `display_lang_1` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 第 1 个额外语言显示名 |
| `display_lang_2` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 第 2 个额外语言显示名 |
| `description_zh` | `VARCHAR(1024 CHAR)` | `text` |  | 中文描述 |
| `description_en` | `VARCHAR(1024 CHAR)` | `text` |  | 英文描述 |
| `description_lang_1` | `VARCHAR(1024 CHAR)` | `text` |  | 第 1 个额外语言描述 |
| `description_lang_2` | `VARCHAR(1024 CHAR)` | `text` |  | 第 2 个额外语言描述 |
| `synonyms` | `TEXT` | `text multi-field` |  | LF 分隔同义词；主字段 Exact，`.bm25` 全文检索 |

Schema 必须逐语言列展开，不使用 `display_zh/en/lang_1/lang_2` 或 `description_zh/en/lang_1/lang_2` 这种合并字段定义。

### 2.3.2 向量化内容和规则

Embedding 文本固定按以下顺序拼接：

```text
{name}
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

规则：

1. 使用 BGE-M3，向量维度 1024；
2. 空字段直接跳过，不写占位字符串；
3. `{synonyms}` 使用 2.2.2 生成的 canonical LF String；
4. SynonymType 自身 `name / display / description` 不重复加入 Embedding；
5. Property 不额外强制拼接所属 ObjectType 名称，避免父对象语义重复注入；
6. Embedding Batch、重试等属于第 3 / 7 章工程配置，不进入 Schema。

### 2.3.3 全文索引内容和规则

OpenSearch 检索字段：

```text
Exact / Filter:
  id
  type
  parent_id
  name.keyword
  display_*.keyword
  synonyms

BM25 / Phrase:
  name
  display_*
  description_*
  synonyms.bm25
```

推荐优先级：

```text
id / name / display exact
> synonyms line-exact
> name / display phrase/BM25
> synonyms.bm25
> description BM25
```

Property 检索时使用 `type=1 + parent_id=<ObjectType.id>` 约束所属 ObjectType 范围，避免跨 ObjectType 错挂 Property。

### 2.3.4 索引存储具体实现

GaussVector：

```text
ANN：GsIVFFLAT
Distance：COSINE
适用规模：约 1*10^4 ～ 2*10^6
IVF_NLIST 推荐初值：4 * sqrt(N)
N = 当前物理表实际记录数
```

OpenSearch：

```text
_id = id
业务过滤字段：type / parent_id
全文字段：name / display_* / description_* / synonyms
```

GaussVector 与 OpenSearch 都以 `id` 做幂等覆盖和删除定位。

### 2.3.5 注意事项

- Property → ObjectType 优先使用 `parent_id`，并由 GraphTopologyCache / `has_property` 做拓扑校验；
- `synonyms` 是所属 ObjectType / Property 的内嵌字段，不建立独立 synonym 记录；
- 不再使用扁平 `i18n_content`，也不建立 `synonyms.*` dynamic template；
- `name / display / description / synonyms` 负责语义召回，`id / parent_id / type` 负责确定性身份和归属。

---

## 2.4 枚举元素索引：Enum Value

`t_oag_enum_{ontology_id}` 只承载本体模型中真正定义的 Enum Value，不承载 EnumType 管理对象本身。

### 2.4.1 数据来源与 GaussVector / OpenSearch 数据结构

索引展开链路：

```text
Property.referenceEnumId
  → EnumType.values[]
  → EnumValue.value
  → EnumValue.refSynonymTypeId
  → SynonymType.synonyms
  → SynonymFlattener
  → t_oag_enum_{ontology_id}
```

真正入索引的粒度是 `EnumType.values[]` 的每一个枚举值。如果同一个 EnumType 被多个 Property 复用，必须按照实际引用 Property 展开为多条归属明确的记录。

```text
t_oag_enum_{ontology_id}
```

| 字段 | GaussVector 类型 | OpenSearch 类型 | 非空 | 说明 |
|---|---|---|---:|---|
| `vector` | `DOUBLE[]` | - | ✔ | Enum Value 1024 维向量，仅 GaussVector 保存 |
| `value` | `VARCHAR(4096 CHAR)` | `keyword + text` |  | 真实标准枚举值，是权威过滤值 |
| `property_id` | `VARCHAR(512 CHAR)` | `keyword` | ✔ | 引用该 Enum 的 Property.id |
| `object_type_id` | `VARCHAR(256 CHAR)` | `keyword` |  | Property 所属 ObjectType.id |
| `display_zh` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 中文 display |
| `display_en` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 英文 display |
| `display_lang_1` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 第 1 个额外语言 display |
| `display_lang_2` | `VARCHAR(512 CHAR)` | `keyword + text` |  | 第 2 个额外语言 display |
| `description_zh` | `TEXT` | `text` |  | 中文 description |
| `description_en` | `TEXT` | `text` |  | 英文 description |
| `description_lang_1` | `TEXT` | `text` |  | 第 1 个额外语言 description |
| `description_lang_2` | `TEXT` | `text` |  | 第 2 个额外语言 description |
| `synonyms` | `TEXT` | `text multi-field` |  | LF 分隔的 Enum Value 同义词 |

业务唯一键：

```text
object_type_id + property_id + normalized(value)
```

`values[].id` 可用于 OMS 源数据追踪和质量校验，但不作为 `t_oag_enum_{ontology_id}` 持久化字段。SearchHit 层的 `recordType=ENUM_VALUE` 由 Normalizer 统一补充，不要求为此增加物理 `type` 字段。

### 2.4.2 向量化内容和规则

每个 Enum Value 独立生成一个向量：

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

规则：

1. **Value First**：真实 `value` 始终放在首行；
2. Display / Description / Synonyms 用于增强自然语言和多语言召回；
3. `{synonyms}` 使用 LF 平铺 String；
4. 不再构造 `synonyms_value / synonyms_description`；
5. 不追加 SynonymType 自身 `name / display / description`；
6. 不在向量前追加 ObjectType / Property 文本，归属由 `property_id + object_type_id` 确定；
7. 空字段跳过，不写占位值。

### 2.4.3 全文索引内容和规则

OpenSearch 检索字段：

```text
Exact / Filter:
  property_id
  object_type_id
  value.keyword
  display_*.keyword
  synonyms

BM25 / Phrase:
  value
  display_*
  description_*
  synonyms.bm25
```

推荐优先级：

```text
value exact
> display exact
> synonyms line-exact
> value / display phrase/BM25
> synonyms.bm25
> description BM25
```

命中 display / synonym 时，最终结果仍必须返回真实 `value`；`matched_field / matched_value` 只用于说明用户实际命中了哪一种表达。

### 2.4.4 索引存储具体实现

GaussVector：

```text
ANN：GsIVFFLAT
Distance：COSINE
推荐规模：约 1*10^4 ～ 2*10^6
IVF_NLIST 推荐初值：4 * sqrt(N)
```

数据库唯一性和 OpenSearch `_id` 均基于：

```text
object_type_id + property_id + normalized(value)
```

同一业务键再次 UPSERT 时覆盖原记录，包括 `display / description / synonyms / vector`；同义词变化不会生成新的 Enum 记录。

### 2.4.5 注意事项

- `value` 是唯一权威业务过滤值，display / description / synonyms 只负责召回、排序和解释；
- 一个 EnumType 被多个 Property 引用时必须展开，不能只按 EnumType/value 全局去重；
- Enum synonym 不建立独立记录；
- Enum / Property / ObjectType 的归属信息必须在入库前完成 Ontology Mapping 校验；
- 物理 Schema 按语言字段逐列展开，不能重新合并成多语言 JSON 对象。

---

## 2.5 实例元素索引：Instance Value

Instance 索引保存去重后的真实业务列值及其内嵌同义词，不保存整行业务数据。

### 2.5.1 数据范围与 GaussVector / OpenSearch 数据结构

入库粒度：

```text
同一个 Property / ObjectType 作用域内
按 normalized(value) 去重
每个真实 Instance Value 保存 1 条记录
```

例如 5000 万条 Subscriber 数据中，如果 `subLevel` 最终只有 `VIP / GOLD / SILVER / NORMAL` 四个唯一值，则该 Property 最终只保存 4 条实例语义索引记录。

```text
t_oag_instance_{ontology_id}
```

| 字段 | GaussVector 类型 | OpenSearch 类型 | 非空 | 说明 |
|---|---|---|---:|---|
| `vector` | `DOUBLE[]` | - | ✔ | Instance Value 1024 维向量，仅 GaussVector 保存 |
| `value` | `VARCHAR(4096 CHAR)` | `keyword + text` | ✔ | 去重后的真实标准列值，是权威过滤值 |
| `synonyms` | `TEXT` | `text multi-field` |  | 实例值同义词，LF 分隔；用于召回与解释 |
| `property_id` | `VARCHAR(512 CHAR)` | `keyword` | ✔ | 所属 Property.id |
| `object_type_id` | `VARCHAR(256 CHAR)` | `keyword` |  | Property 所属 ObjectType.id |

业务唯一键：

```text
object_type_id + property_id + normalized(value)
```

`synonyms` 不参与业务唯一键。SearchHit 层的 `recordType=INSTANCE_VALUE` 由 Normalizer 统一补充，不要求增加物理 `type` 字段。

### 2.5.2 向量化内容和规则

Instance Dense 只使用真实值及其同义词：

```text
{value}
{synonyms}
```

规则：

1. `value` 必须放在首行并作为主语义；
2. `synonyms` 只增强别名、黑话、业务俗称的 Dense 召回；
3. 不拼接 Property / ObjectType 名称、display、description，归属由结构字段确定；
4. Instance 不配置 `display_* / description_*` 多语言字段；
5. 对 Struct 等组合值，使用规范化后的可读 `value` 表达作为 `{value}`，不额外注入父对象文本。

### 2.5.3 全文索引内容和规则

OpenSearch 检索字段：

```text
Exact / Filter:
  property_id
  object_type_id
  value.keyword
  synonyms

BM25:
  value
  synonyms.bm25
```

推荐优先级：

```text
value exact
> synonyms line-exact
> value BM25
> synonyms.bm25
```

命中 synonym 时统一返回：

```text
matched_field = synonyms
matched_value = 实际命中的实例同义词
value         = 真实标准实例值
```

下游过滤条件和 `semanticExtensions.valueMappings[].canonicalValue` 始终使用 `value`，不能使用 synonym 作为真实过滤值。

### 2.5.4 索引存储具体实现

#### 当前实现

当前版本使用单张 `t_oag_instance_{ontology_id}`，同一个规范化值如果属于多组 Property / ObjectType，允许保存多条物理记录：

```text
(value=A, property=P1, objectType=O1)
(value=A, property=P2, objectType=O2)
```

这样可以避免 `property_id / object_type_id` 数组化带来的更新放大和索引过滤复杂度。

GaussVector ANN：

```text
中小规模：GsIVFFLAT + COSINE
千万 / 亿级：GsDiskANN
```

OpenSearch `_id` 与 GaussVector 幂等键均由：

```text
object_type_id + property_id + normalized(value)
```

确定。

#### 容量与分表演进

当前正式方案：

```text
单表 + 产品规格约束
```

达到单表容量或性能上限后，优先评估水平拆分；按 ObjectType 分表作为备选，不能在没有容量数据时提前制造大量物理表。

如果未来明确要求“同一个 value 只保存一份向量”，演进为值表 + 归属映射表：

```text
t_oag_instance_value_{ontology_id}
  value_id
  normalized_value UNIQUE
  value
  synonyms
  vector

        1 : N
          ↓

t_oag_instance_binding_{ontology_id}
  value_id
  property_id
  object_type_id
  UNIQUE(value_id, property_id, object_type_id)
```

查询链路：

```text
Value 表 Exact/BM25/Dense
  → value_id
  → Binding 批量展开 property_id / object_type_id
  → Entity Linking / RRF / LLM 消歧
```

存储演进不能改变上层 Entity Linking 和 `semanticExtensions.valueMappings` 的结果语义。

### 2.5.5 注意事项：索引准入与高基数控制

Instance Value 进入语义索引的基础准入条件：

```text
instance_index_enabled =
  property.capability == "DIMENSION"
  AND datatype_eligible
  AND value_shape_eligible
  AND cardinality_eligible
```

默认不建议向量化：

```text
UUID
手机号
纯技术主键
时间戳
日期
连续数值
高随机编码
```

适合向量化：

```text
产品名称
品牌名称
客户等级
区域名称
业务状态
自然语言标签
人可理解的业务分类
```

高基数自由文本进入单独 Document / RAG Index，不进入 Instance Value Resolver。

DataSync / 业务服务可以源侧预去重，但 OAG 写入前仍必须按 `object_type_id + property_id + normalized(value)` 再次去重并执行幂等 UPSERT。

---

## 2.6 三类索引统一存储与治理

### 2.6.1 幂等 UPSERT / DELETE 与 Generation

三类索引的稳定键：

```text
本体对象：id
Enum Value：object_type_id + property_id + normalized(value)
Instance Value：object_type_id + property_id + normalized(value)
```

统一规则：

1. GaussVector 和 OpenSearch 使用同一稳定业务键；
2. 重复 UPSERT 必须覆盖原记录，不能追加重复向量或全文文档；
3. `synonyms` 以 canonical LF String 整字段覆盖，不做语言 Map merge；
4. DELETE 必须同时删除 GaussVector 与 OpenSearch 中对应记录；
5. OpenSearch 使用稳定业务键生成确定性 `_id`；
6. 双写一致性、Chunk 重放和 Publish 由第 3 章统一保证。

每条索引记录不额外保存：

```text
content_hash
model_version
source_version
updated_at
```

版本、模型和构建信息统一由 Import Job / Generation 管理。Embedding 模型升级时：

```text
创建新 Generation
→ 全量重新 Embedding
→ Verify
→ 原子 Publish
```

### 2.6.2 数据质量治理

OMS / OAG 建索引前至少校验：

```text
ObjectType / Property id 重复或缺失
name / display / description 格式非法
additionalLanguages 槽位配置不一致
SynonymType.synonyms language key 数 > 3
language key 非法或不符合 BCP 47 约定
同一 language 内 synonym 重复
synonym 与 canonical name/display 完全重复
同一业务范围内 synonym 映射冲突
Enum Ref 不存在
Enum values[].id / value 源数据重复
Enum Value.refSynonymTypeId 不存在
Property.referenceEnumId 不存在
Parent ObjectType 缺失
```

OAG `synonyms` 热字段额外校验：

```text
CRLF / CR 统一为 LF
禁止空 synonym 行
去除首尾空白
规范化后重复 synonym 只保留第一次出现的原文
禁止 JSON Object / JSON Array 写入 synonyms
字段总长度和 synonym 数量受服务配置保护
```

动态 REST / CSV 已经不携带 language key，因此只能校验平铺值，不能在 OAG API 层声明“动态 synonyms 最多 3 种语言”；该约束属于 OMS SynonymType 源模型。

Instance 额外检查：

```text
空 value
超长 value
unique_value_count
同一 object_type_id + property_id 下重复 value
高基数
无意义随机串
非法 UTF-8
```

严重结构错误必须阻断当前记录或批次，不能静默覆盖；冲突必须可观测。

### 2.6.3 本体归属、检索结果与拓扑投影

```text
ObjectType
  → id 直接定位

Property
  → parent_id
  → GraphTopologyCache / has_property 双重校验

Enum Value / Instance Value
  → property_id + object_type_id 直接记录归属
```

SearchHit 在进入 RRF 前必须保留：

```text
recordType
id / propertyId / objectTypeId / value
matched_field
matched_value
channel
rank / rawScore
```

其中 `recordType` 是检索归一化字段，不要求所有物理表都持久化 `type`。

SeedNodeProjector 规则：

```text
ObjectType      → ObjectType
Property        → Property + 所属 ObjectType
Enum Value      → Property + 所属 ObjectType
Instance Value  → Property + 所属 ObjectType
```

Enum / Instance 作为最终语义证据和 ValueMapping 来源保留，但不直接成为最短路径、K-hop、Connected Component 的拓扑顶点。

### 2.6.4 存储选型汇总

| 类型 | Dense 主内容 | Lexical 主内容 | GaussVector ANN | 主要过滤字段 |
|---|---|---|---|---|
| 本体对象 | name + display + description + synonyms | id/name/display/description/synonyms | `GsIVFFLAT + COSINE` | `type / parent_id` |
| Enum Value | value + display + description + synonyms | value/display/description/synonyms | `GsIVFFLAT + COSINE` | `object_type_id / property_id` |
| Instance Value | value + synonyms | value/synonyms | 中小规模 `GsIVFFLAT`；千万/亿级 `GsDiskANN` | `object_type_id / property_id` |

### 2.6.5 关键注意事项

1. **三类稳定实体、三套物理索引**，不要把 Enum/Instance 混入本体对象表；
2. **Dense 与 Lexical 共用同一业务数据模型**，不能维护两套字段语义；
3. **多语言字段按列展开**：固定 zh/en + lang_1/lang_2；Instance 不配置 display/description 多语言列；
4. **Synonym 内嵌而不独立建记录**，OAG 中统一为 LF String；
5. **Enum/Instance 的真实过滤值始终是 `value`**，synonym/display 只能用于召回和解释；
6. **Instance 向量只使用 value + synonyms**，不拼 Property/ObjectType 文本；
7. **业务唯一键不包含 synonyms**，同义词变化只能覆盖现有业务记录；
8. **ANN 参数按表规模独立配置**，实例表不能机械复用本体对象表的 ANN 参数；
9. **Property 作用域必须由 parent_id / object_type_id 约束**，避免跨对象错误链接；
10. **版本信息放 Generation / Import Job**，不向每条向量记录扩散运维字段。

---

'''

new_text = text[:start] + chapter2 + text[end:]

# 第 2 章重编号后，同步修正文档其他章节中的旧章节引用。
new_text = re.sub(r'第\s*2\.8\s*/\s*2\.10\s*节', '第 2.4.1 / 2.5.1 节', new_text)
new_text = re.sub(r'第\s*2\.12\s*节', '第 2.5.2 节', new_text)

old_reading_rule = '阅读规则：本文按“核心设计 + 详细设计与实现”组织。核心设计定义当前规范，详细设计补充接口、DDL、算法、错误处理、性能、评测、兼容和灰度要求；同一主题如存在多处说明，应保持字段、接口和执行语义一致。'
new_reading_rule = '阅读规则：第 2 章按“总体规则 → 本体对象 → 枚举元素 → 实例元素 → 统一治理”组织，其他章节保留“核心设计 + 详细设计与实现”；同一主题只保留一处权威定义，接口、DDL、算法与运行规则引用该定义。'
if old_reading_rule in new_text:
    new_text = new_text.replace(old_reading_rule, new_reading_rule, 1)

# 结构校验：章节编号必须连续且无旧版重复包装。
new_start = new_text.index(start_marker)
new_end = new_text.index(end_marker)
new_chapter = new_text[new_start:new_end]
required_headings = [
    '## 2.1 总体索引模型',
    '## 2.2 公共建模与检索规则',
    '## 2.3 本体对象索引：ObjectType / Property',
    '## 2.4 枚举元素索引：Enum Value',
    '## 2.5 实例元素索引：Instance Value',
    '## 2.6 三类索引统一存储与治理',
]
for heading in required_headings:
    assert new_chapter.count(heading) == 1, f'missing/duplicate heading: {heading}'

for obsolete in [
    '## 2.0 核心设计',
    '## 2.1 详细设计与实现',
    '### 2.7 ',
    '### 2.8 ',
    '### 2.9 ',
    '### 2.10 ',
    '### 2.11 ',
    '### 2.12 ',
    '### 2.13 ',
    '### 2.14 ',
    '### 2.15 ',
    '### 2.16 ',
    '### 2.17 ',
    '### 2.18 ',
]:
    assert obsolete not in new_chapter, f'obsolete chapter structure remains: {obsolete}'

required_terms = [
    '`display_zh`', '`display_en`', '`display_lang_1`', '`display_lang_2`',
    '`description_zh`', '`description_en`', '`description_lang_1`', '`description_lang_2`',
    '`synonyms`', 'BGE-M3', '1024', 'synonym_line_analyzer', 'SynonymMatchResolver',
    'GsIVFFLAT', 'GsDiskANN', 'COSINE', 'value_id', 't_oag_instance_binding_{ontology_id}',
    'semanticExtensions.valueMappings', 'property.capability == "DIMENSION"',
]
for term in required_terms:
    assert term in new_chapter, f'required design detail lost: {term}'

# 旧的第 2 章细分编号不应再被后续章节引用。
suffix = new_text[new_end:]
stale_refs = re.findall(r'第\s*2\.(?:7|8|9|10|11|12|13|14|15|16|17|18)(?:\.\d+)?(?:\s*/\s*2\.\d+(?:\.\d+)?)?\s*节', suffix)
assert not stale_refs, f'stale chapter 2 references remain: {stale_refs}'

assert len(new_chapter.splitlines()) > 450, 'chapter 2 unexpectedly short; possible information loss'
assert new_text.count(end_marker) == 1

DOC.write_text(new_text, encoding='utf-8')
print(f'chapter2 lines: {len(new_chapter.splitlines())}')
print('chapter2 restructure validation: PASS')
