from pathlib import Path
import sys

DOC = Path(sys.argv[1])
text = DOC.read_text(encoding='utf-8')


def replace_section(src: str, start: str, end: str, body: str) -> str:
    if start not in src or end not in src:
        raise SystemExit(f'section marker missing: {start!r} -> {end!r}')
    before, rest = src.split(start, 1)
    _, after = rest.split(end, 1)
    return before + body.rstrip() + '\n\n' + end + after


# Version and top-level design statement.
text = text.replace('> 版本：V5.10  ', '> 版本：V5.11  ', 1)
text = text.replace(
    'Synonym 是种子节点或枚举值的结构化字段而非独立物理行；',
    'SynonymType 在 OMS 中保留多语言源结构，OAG 物理索引中的 `synonyms` 统一为 LF 分隔的平铺字符串且不建立独立物理行；',
    1,
)

sec_21 = r'''## 2.1 数据模型：种子节点、枚举值、实例值与 Synonym

V5.11 的物理索引模型仍只保留三类业务记录，但 Synonym 明确区分 **OMS 源模型** 与 **OAG 检索模型**：

| 类型 | 物理实体 | Synonym 处理 | 本体归属字段 |
|---|---|---|---|
| 种子节点 | ObjectType / Property | `synonyms` 以 LF 分隔的平铺字符串内嵌 | 使用种子节点自身 `id`；Property→ObjectType 走拓扑 |
| 元数据元素 | Enum Value | `synonyms` 以 LF 分隔的平铺字符串内嵌 | `propertyId + objectTypeId` |
| 实例元素 | Instance Value | 不建立实例同义词记录 | `propertyid + objectTypeId` |

### 2.1.1 OMS SynonymType：保留多语言源结构

OMS 的 `synonym-type` 仍是建模资产，允许保留语言信息、显示名和描述。例如：

```json
{
  "id": "term-color-synonyms",
  "name": "color-synonyms",
  "display": {
    "zh": "颜色近义词",
    "en": "Color Synonyms"
  },
  "description": {
    "zh": "颜色相关术语的近义词定义",
    "en": "Synonyms for color-related terms"
  },
  "synonyms": {
    "zh": ["颜色", "色彩", "色泽", "色"],
    "en": ["Color", "Colour", "Hue", "Tint"]
  },
  "status": "ACTIVE"
}
```

源模型约束保持：

```text
synonyms 最多包含 3 个 language key
语言组合不固定
每种语言可包含多个同义词
language key 使用 BCP 47 风格，如 zh/en/es/es-MX/pt-BR
```

这些语言 key 用于 OMS 建模、治理和离线评测，不直接作为 OAG 热索引字段层级。

### 2.1.2 OAG `synonyms`：统一平铺为 String/TEXT

OAG 解析 ObjectType / Property / Enum Value 的 `refSynonymTypeId` 后，只提取 SynonymType 中真正参与检索的同义词值，并规范化为一个平铺字符串：

```text
颜色
色彩
色泽
色
Color
Colour
Hue
Tint
```

逻辑分隔符固定为 **LF**。在 JSON/CSV 传输中用字面量 `\n` 表达，例如：

```json
{
  "synonyms": "颜色\n色彩\n色泽\n色\nColor\nColour\nHue\nTint"
}
```

统一转换流程：

```text
SynonymType.synonyms(language → values[])
  ↓
语言块稳定排序
  ↓
语言内保持源数组顺序
  ↓
trim / Unicode normalize / 去空
  ↓
按规范化值去重并保留首次出现原文
  ↓
LF join
  ↓
OAG synonyms TEXT/String
```

稳定排序规则：`zh`、`en` 存在时优先，其余 language tag 按字典序排列；同一语言内保持 OMS 数组顺序。这样同一 SynonymType 在重复构建、FULL_REPLACE 和增量 UPSERT 时可得到确定性字符串。

> **关键边界：** OMS 保留“语言 → 同义词列表”的建模结构；GaussVector、OpenSearch、REST Batch 和 CSV 使用同一个平铺 `synonyms` 字段。OAG 不在热路径中重复反序列化 Synonym Map。

SynonymType 自身不建立独立向量记录。其 `name/display/description` 继续作为 OMS 管理元数据保留，但默认不复制到 `synonyms` 热索引字段，也不再通过 `synonyms_description` 重复拼入 Embedding；真正参与检索的是所属业务实体自身的 name/display/description 与平铺后的 synonym values。'''
text = replace_section(text, '## 2.1 数据模型：种子节点、枚举值、实例值与 Synonym', '## 2.2 三类物理索引与统一命名', sec_21)

sec_23 = r'''## 2.3 `t_ontoretrieval_{ontology_id}` GaussVector 表结构

种子节点表保留两个额外语言槽位，并增加平铺 `synonyms`。中文和英文仍保留固定列，另外最多支持 2 种 display/description 语言：

| 字段                   | 类型 | 非空 | 说明 |
|----------------------|---|--|---|
| `vector`             | `DOUBLE[]` | ✔ | 1024 维向量 |
| `type`               | `INT` |  | 0 ObjectType，1 Property |
| `id`                 | `VARCHAR(256 CHAR)` | ✔ | ObjectType / Property 全局唯一 ID |
| `parent_id`          | `VARCHAR(256 CHAR)` |  | 父元素 ID；当 type=1 时记录 Property 所属 ObjectType ID |
| `name`               | `VARCHAR(256 CHAR)` |  | 本体真实名称 |
| `display_zh`         | `VARCHAR(512 CHAR)` |  | 中文显示名 |
| `display_en`         | `VARCHAR(512 CHAR)` |  | 英文显示名 |
| `display_lang_1`     | `VARCHAR(512 CHAR)` |  | 第 1 个额外语言显示名 |
| `display_lang_2`     | `VARCHAR(512 CHAR)` |  | 第 2 个额外语言显示名 |
| `description_zh`     | `VARCHAR(1024 CHAR)` |  | 中文描述 |
| `description_en`     | `VARCHAR(1024 CHAR)` |  | 英文描述 |
| `description_lang_1` | `VARCHAR(1024 CHAR)` |  | 第 1 个额外语言描述 |
| `description_lang_2` | `VARCHAR(1024 CHAR)` |  | 第 2 个额外语言描述 |
| `synonyms`           | `TEXT` |  | LF 分隔的同义词平铺字符串；不保存 JSON Map/Array |

`synonyms` 逻辑值示例：

```text
小区
无线小区
Cell
Radio Cell
Celda
Celda de radio
```

传输表示：

```text
小区\n无线小区\nCell\nRadio Cell\nCelda\nCelda de radio
```

额外 display/description 最多 2 个语言槽位；“Synonym 最多 3 种语言”是 **OMS SynonymType 源模型约束**。平铺到 OAG 后不再保存 language key，因此热索引只校验 synonym 值本身，不再按语言字段拆列或拆对象。'''
text = replace_section(text, '## 2.3 `t_ontoretrieval_{ontology_id}` GaussVector 表结构', '## 2.4 种子节点向量化内容', sec_23)

sec_24 = r'''## 2.4 种子节点向量化内容

OAG 在内存中解析 ObjectType / Property 及其 SynonymType，先按 2.1.2 生成 canonical `synonyms` 字符串，再按以下顺序构建 Embedding 文本：

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

其中 `{synonyms}` 就是 LF 分隔后的同义词值列表。EmbeddingInputBuilder 可以直接把该字符串作为最后一个文本块追加，不再构造 `synonyms_value` / `synonyms_description` 两个中间字段。

这样可保证：

```text
OMS 静态构建
REST 动态导入
MinIO CSV 动态导入
        ↓
都使用同一种 synonyms 物理表达和 Embedding 规则
```

SynonymType 的 `name/display/description` 不再额外重复拼接到向量中，避免与所属 ObjectType / Property 自身的 name/display/description 形成重复语义权重。

空字段直接跳过，不写占位字符串。不要把 ObjectType 名称额外强制拼到 Property 向量开头；Property 自身语义、display、description、synonyms 已足够作为主表达。

当前 BGE-M3 向量维度继续沿用 1024。Embedding 批大小和重试次数属于 OAG 工程配置，不进入表 Schema。'''
text = replace_section(text, '## 2.4 种子节点向量化内容', '## 2.5 多语言槽位与 Synonym 语言规则', sec_24)

sec_25 = r'''## 2.5 多语言槽位与 Synonym 语言规则

### 2.5.1 Display / Description 最多 4 种语言

```text
固定语言：zh + en
额外语言：lang_1 + lang_2
总计最多 4 种
```

没有配置某个额外语言时，对应列为空。

### 2.5.2 Synonym：源模型保留语言，索引模型语言无关

Synonym 的语言规则只在 OMS 源模型层生效：

```text
OMS SynonymType.synonyms
  → 最多 3 个 language key
  → language key 不固定
  → 每种语言可有多个词
```

进入 OAG 后统一转换为：

```text
synonyms = term1<LF>term2<LF>term3...
```

因此 OAG 物理索引不再存在：

```text
synonyms.zh
synonyms.en
synonyms.es
synonyms.<language>
```

也不再通过 language key 对 synonym 做 Dense 过滤或 Lexical 硬过滤。`language_hint` 仍可作用于 display/description Analyzer 和查询理解，但 synonym 字段本身按语言无关文本检索。

如果未来确实需要“按语言返回 synonym”或线上语言级统计，应从 OMS SynonymType 源资产补充上下文，或新增独立冷元数据能力；不应重新把多语言 Map 放回高频检索记录。'''
text = replace_section(text, '## 2.5 多语言槽位与 Synonym 语言规则', '## 2.6 Property Vector 是否带 ObjectType', sec_25)

sec_27 = r'''## 2.7 `t_ontoretrieval_{ontology_id}` OpenSearch Index

OpenSearch 与 GaussVector 共享同一业务字段语义：

```text
type
id
name
display_zh
display_en
display_lang_1
display_lang_2
description_zh
description_en
description_lang_1
description_lang_2
synonyms
```

推荐映射：

| 字段 | OpenSearch 类型 | 说明 |
|---|---|---|
| `type` | `integer` | 0 ObjectType / 1 Property |
| `id` | `keyword` | 本体 ID |
| `name` | `keyword` + `text` | Exact / BM25 |
| `display_*` | `keyword` + `text` | 多语言显示名 |
| `description_*` | `text` | 多语言描述 |
| `synonyms` | `text` multi-field | 主字段按 LF 切成“整条 synonym token”做 Exact；`synonyms.bm25` 用普通 Analyzer 做 BM25 |

`synonyms` 不再映射为 dynamic object。推荐 Analyzer：

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

字段映射示意：

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

这样：

```text
Exact synonym
  → 查询 synonyms 主字段；一个 LF 行作为一个完整 token

BM25 synonym
  → 查询 synonyms.bm25；把平铺文本按普通全文规则召回
```

检索优先级：

```text
id/name/display exact
> synonyms line-exact
> name/display phrase/BM25
> synonyms.bm25
> description BM25
```

Synonym 命中统一返回：

```text
matched_field = synonyms
matched_value = 实际命中的某一行 synonym
```

Exact 命中可以直接定位匹配行；BM25 命中由 `SynonymMatchResolver` 对 `synonyms` 做一次 LF split，并用与检索一致的 normalizer 在候选行中选出最匹配的 `matched_value`。这一步是简单字符串处理，不再执行 JSON 反序列化。

不再使用扁平 `i18n_content`，也不再建立 `synonyms.*` dynamic template。'''
text = replace_section(text, '## 2.7 `t_ontoretrieval_{ontology_id}` OpenSearch Index', '## 2.8 `t_metadata_evidence_{ontology_id}`：Enum Value 模型与表结构', sec_27)

sec_28 = r'''## 2.8 `t_metadata_evidence_{ontology_id}`：Enum Value 模型与表结构

Metadata Evidence 只承载本体模型中定义的枚举值。

### 2.8.1 EnumType 源结构

```json
{
  "id": "ei.veh12.enum.Col35.1",
  "name": "Color",
  "display": {
    "en": "Color",
    "zh": "颜色"
  },
  "description": {
    "en": "Vehicle body color enumeration",
    "zh": "车身颜色枚举"
  },
  "status": "ACTIVE",
  "creatorByOntology": "vehicle",
  "valueType": "string",
  "refSynonymTypeId": "term-color-synonyms",
  "values": [
    {
      "id": "ei.veh12.enum.Col35.val.red8.1",
      "name": "red",
      "display": {
        "en": "Red",
        "zh": "红色"
      },
      "description": {
        "en": "Red color",
        "zh": "红色"
      },
      "value": "red",
      "order": 1,
      "refSynonymTypeId": "term-color-red-synonyms"
    },
    {
      "id": "ei.veh12.enum.Col35.val.blue9.1",
      "name": "blue",
      "display": {
        "en": "Blue",
        "zh": "蓝色"
      },
      "description": {
        "en": "Blue color",
        "zh": "蓝色"
      },
      "value": "blue",
      "order": 2,
      "refSynonymTypeId": "term-color-blue-synonyms"
    }
  ],
  "extensions": {}
}
```

真正进入 `t_metadata_evidence_{ontology_id}` 的粒度是 `values[]` 中的每个枚举值。

### 2.8.2 SynonymType 源结构与索引转换

OMS SynonymType 仍保留结构化多语言信息：

```json
{
  "id": "term-color-red-synonyms",
  "name": "color-red-synonyms",
  "display": {
    "zh": "红色近义词",
    "en": "Red Synonyms"
  },
  "description": {
    "zh": "红色相关术语",
    "en": "Synonyms for red"
  },
  "synonyms": {
    "zh": ["红", "赤色"],
    "en": ["Red"],
    "es": ["Rojo"]
  },
  "status": "ACTIVE"
}
```

OMS 源模型仍要求 `synonyms` 最多 3 个 language key，语言不固定。OAG 建索引时只把 synonym values 平铺：

```text
红
赤色
Red
Rojo
```

最终 `t_metadata_evidence_{ontology_id}.synonyms` 保存：

```text
红\n赤色\nRed\nRojo
```

其中不再包含 language key、JSON Object 或 Array。

### 2.8.3 Property 引用 Enum

```json
{
  "id": "prop:ont:vehicle:sp:bodyColor",
  "name": "bodyColor",
  "display": {
    "en": "Body Color",
    "zh": "车身颜色"
  },
  "description": {
    "en": "Vehicle body color",
    "zh": "车身颜色"
  },
  "dataType": "enum",
  "valueType": "string",
  "referenceEnumName": "Color",
  "referenceEnumId": "ei.vehicle.enum.Color.1",
  "extensions": {}
}
```

OAG 按：

```text
Property.referenceEnumId
  → EnumType.values[]
  → EnumValue.refSynonymTypeId
  → SynonymType.synonyms
  → SynonymFlattener
  → LF String
```

展开索引。

### 2.8.4 GaussVector 表结构

```text
t_metadata_evidence_{ontology_id}
```

| 字段                   | 类型 | 非空 | 说明 |
|----------------------|---|--|---|
| `vector`             | `DOUBLE[]` | ✔ | Enum Value 向量 |
| `type`               | `INT` |  | 固定表示 ENUM_VALUE |
| `propertyId`         | `VARCHAR(512 CHAR)` | ✔ | 引用该 Enum 的 Property.id |
| `objectTypeId`       | `VARCHAR(256 CHAR)` |  | Property 所属 ObjectType.id |
| `value`              | `VARCHAR(4096 CHAR)` |  | 真实枚举值 |
| `name`               | `VARCHAR(4096 CHAR)` |  | OMS 静态构建时可保存 `values[].name`；动态导入可为空 |
| `display_zh`         | `VARCHAR(512 CHAR)` |  | 中文 display |
| `display_en`         | `VARCHAR(512 CHAR)` |  | 英文 display |
| `display_lang_1`     | `VARCHAR(512 CHAR)` |  | 额外语言 1 display |
| `display_lang_2`     | `VARCHAR(512 CHAR)` |  | 额外语言 2 display |
| `description_zh`     | `TEXT` |  | 中文 description |
| `description_en`     | `TEXT` |  | 英文 description |
| `description_lang_1` | `TEXT` |  | 额外语言 1 description |
| `description_lang_2` | `TEXT` |  | 额外语言 2 description |
| `synonyms`           | `TEXT` |  | LF 分隔的 Enum Value 同义词平铺字符串 |

如果一个 EnumType 被多个 Property 复用，需要按实际引用 Property 展开记录。Evidence 不重新引入 `id/parent_id`；业务定位和数据库唯一性统一使用：

```text
objectTypeId + propertyId + normalized(value)
```

`values[].id` 仍可用于 OMS 源数据追踪和质量校验，但不作为 `t_metadata_evidence_{ontology_id}` 的持久化字段。'''
text = replace_section(text, '## 2.8 `t_metadata_evidence_{ontology_id}`：Enum Value 模型与表结构', '## 2.9 Enum Value 向量化规则', sec_28)

sec_29 = r'''## 2.9 Enum Value 向量化规则

每个 `values[]` 元素按以下内容生成一个向量：

```text
{value}
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

其中 `{synonyms}` 为当前 Enum Value 关联 SynonymType 经 2.1.2 规则平铺后的 LF String。动态 REST/CSV 导入不携带 `name` 时，EmbeddingInputBuilder 直接跳过该项；不允许用 `value` 复制填充 `name`。

向量顺序坚持：

```text
Value First
→ Name（存在时）/ Display
→ Description
→ Synonyms
```

不再构造 `synonyms_value` / `synonyms_description`，也不把 SynonymType 自身的 name/display/description 追加到向量文本。

不在向量文本开头追加 ObjectType / Property 文本；`propertyId + objectTypeId` 已提供确定性归属。'''
text = replace_section(text, '## 2.9 Enum Value 向量化规则', '## 2.10 `t_instance_evidence_{ontology_id}` 实例列值表结构', sec_29)

sec_213 = r'''## 2.13 Metadata / Instance OpenSearch Index

### `t_metadata_evidence_{ontology_id}`

核心字段与 GaussVector 一致：

```text
type
propertyId
objectTypeId
value
name
display_zh
display_en
display_lang_1
display_lang_2
description_zh
description_en
description_lang_1
description_lang_2
synonyms
```

Exact 优先：

```text
propertyId
objectTypeId
value.keyword
name.keyword
display_*.keyword
synonyms（synonym_line_analyzer，一行一个完整 synonym token）
```

BM25：

```text
name
display_*
description_*
synonyms.bm25
```

Metadata 的 `synonyms` 映射与 2.7 完全一致，不再使用 `synonyms.*.keyword` 或语言 dynamic object。

### `t_instance_evidence_{ontology_id}`

只需要：

```text
type          integer
propertyid    keyword
objectTypeId  keyword
value         keyword + text
language      keyword（可选）
```

Exact 主要搜索 `propertyid/objectTypeId/value.keyword`，BM25 搜索 `value`。'''
text = replace_section(text, '## 2.13 Metadata / Instance OpenSearch Index', '## 2.14 规范化规则', sec_213)

sec_214 = r'''## 2.14 规范化规则

规范化属于索引构建/查询处理逻辑，不增加额外持久化字段：

```text
trim
Unicode normalize
casefold（适用语言）
连续空白归一
全半角归一
```

`name/value/display/description` 保留原始业务文本。OMS 中原始 SynonymType 多语言结构继续由 OMS 维护；OAG 的 `synonyms` 保存规范化展开后的 canonical LF String。

SynonymFlattener 处理规则：

```text
CRLF / CR → LF
按 LF 切分
trim
去空行
按基础规范化值去重，保留首次出现原文
重新 LF join
```

OpenSearch 使用 2.7 的 line analyzer / BM25 multi-field；GaussVector 在 Embedding 前直接使用同一 canonical `synonyms`，避免不同存储各自做一套解析。'''
text = replace_section(text, '## 2.14 规范化规则', '## 2.15 language_hint 与语言槽位', sec_214)

sec_215 = r'''## 2.15 language_hint 与语言槽位

查询理解阶段仍可以输出：

```text
language_hint = BCP 47 language tag / mixed / und
```

物理存储分三种情况：

```text
种子节点 / Enum Value display、description
  → zh/en 固定 + lang_1/lang_2 两个 ontology 级语言槽位

SynonymType 源资产
  → OMS 中保留 language Map，最多 3 个 language key

OAG synonyms 热索引
  → 单个 LF 分隔 String，不保留 language key

Instance Value
  → 仅 value；language 为可选观测/Analyzer Hint
```

检索规则：

```text
display/description 可根据 language_hint 选择 Analyzer 或 Boost
synonyms 不按 language_hint 硬过滤，也不做 synonyms.<language> Boost
Dense 不按 language_hint 过滤
LLM 精排继续看到原始问题和所有候选
```

因此 `matched_field` 对 synonym 统一为 `synonyms`；如果需要知道该同义词在 OMS 中原本属于哪种语言，只能通过源 SynonymType 或离线标注补充，不能从热索引字段名反推。'''
text = replace_section(text, '## 2.15 language_hint 与语言槽位', '## 2.16 数据质量治理', sec_215)

sec_216 = r'''## 2.16 数据质量治理

OAG 元数据同步阶段必须先校验 OMS 源结构，再校验平铺后的热索引值。

### OMS SynonymType 源结构校验

```text
ObjectType / Property id 重复或缺失
name/display/description 格式非法
additionalLanguages 槽位配置不一致
SynonymType.synonyms language key 数 > 3
language key 非法或不符合约定的 BCP 47 风格
同一 language 内 synonym 重复
synonym 与 canonical name/display 完全重复
同一业务范围内 synonym 映射冲突
Enum Ref 不存在
Enum values[].id/value 源数据重复
Enum Value.refSynonymTypeId 不存在
Property.referenceEnumId 不存在
Parent ObjectType 缺失
```

### OAG 平铺 synonyms 校验

```text
统一 CRLF/CR 为 LF
禁止空 synonym 行进入索引
去除首尾空白
规范化后重复 synonym 只保留第一次出现的原文
禁止 JSON Object / JSON Array 形式写入 synonyms 热字段
字段总长度和 synonym 数量受服务配置保护
```

动态 REST/CSV 已经不携带 language key，因此只能执行平铺值质量校验，不能在 OAG API 层声称“校验动态 synonyms 最多 3 种语言”。该限制属于 OMS SynonymType 源建模约束。

冲突处理原则：不能静默覆盖，必须可观测；严重结构错误阻断当前记录或当前批次入库。

DataSync 实例值额外检查：

```text
空 value
超长 value
unique_value_count
同一 objectTypeId + propertyid 下重复 value
高基数
无意义随机串
非法 UTF-8
```'''
text = replace_section(text, '## 2.16 数据质量治理', '## 2.17 增量索引与幂等', sec_216)

sec_217 = r'''## 2.17 增量索引与幂等

三类表按各自稳定业务键做幂等 UPSERT / DELETE：

```text
种子节点：id
Enum Value：objectTypeId + propertyId + normalized(value)
Instance Value：objectTypeId + propertyid + normalized(value)
```

同一业务键重复 UPSERT 必须覆盖当前记录而不是新增重复向量；`synonyms` 以 canonical LF String 整字段覆盖，不执行 Map merge。DELETE 必须同时删除 GaussVector 与 OpenSearch 中对应记录。

不在记录中保留：

```text
content_hash
model_version
source_version
updated_at
```

版本和构建信息统一放到 OAG 的 Import Job / Generation 元数据，不进入每条向量记录。

Embedding 模型升级时：

```text
创建新的 Generation
→ 全量重新 Embedding
→ Verify
→ 原子发布
```

如果未来需要“内容未变化则跳过 Embedding”，可以作为 OAG 内部缓存优化实现，但不扩展业务表 Schema。'''
text = replace_section(text, '## 2.17 增量索引与幂等', '## 2.18 GaussVector 索引算法', sec_217)

# Necessary cross-chapter consistency updates caused by the new physical synonym representation.
text = text.replace('命中：bodyColor 对应 Enum Value 的 synonyms.zh = 色泽', '命中：bodyColor 对应 Enum Value 的 synonyms 中的“色泽”')
text = text.replace('matched_field = synonyms.zh', 'matched_field = synonyms')
text = text.replace('matched_field = synonyms.<language>', 'matched_field = synonyms')
text = text.replace('"matched_field": "synonyms.zh"', '"matched_field": "synonyms"')
text = text.replace('"matched_field": "synonyms.es"', '"matched_field": "synonyms"')
text = text.replace('如果用户命中 `synonyms.*`', '如果用户命中 `synonyms`')
text = text.replace('如果用户命中 `synonyms.*`，记录仍按所属 ObjectType/Property/Enum Value 的规则投影。', '如果用户命中 `synonyms`，记录仍按所属 ObjectType/Property/Enum Value 的规则投影。')

# SearchHit examples: output uses the same flattened representation as the index.
text = text.replace(
'''  "synonyms": {
    "zh": ["小区"],
    "en": ["Cell", "Radio Cell"],
    "es": ["Celda"]
  },''',
'''  "synonyms": "小区\\nCell\\nRadio Cell\\nCelda",''')
text = text.replace(
'''  "synonyms": {
    "zh": ["红", "红色"],
    "en": ["Red"],
    "es": ["Rojo"]
  },''',
'''  "synonyms": "红\\n红色\\nRed\\nRojo",''')

# Final decision/evaluation text.
text = text.replace('**认为 synonyms 语言必须固定 zh/en/es。** Synonyms 最多 3 种语言，但组合不固定。', '**把 OAG synonyms 热字段重新设计成语言 Map。** 最多 3 种语言是 OMS SynonymType 源模型约束；OAG 热索引统一使用 LF 平铺 String。')
text = text.replace('**`synonyms` 最多支持 3 种语言，三种语言不固定，每种语言可有多个词。**', '**OMS SynonymType 的 `synonyms` 最多 3 个非固定 language key；OAG 物理 `synonyms` 统一平铺为 LF String，不保存 language key。**')
text = text.replace('**种子节点向量化使用 name + 4语言 display/description + synonyms_value + synonyms_description。**', '**种子节点向量化使用 name + 4语言 display/description + 平铺 synonyms。**')
text = text.replace('**Enum Value 向量化使用 value + name + 4语言 display/description + synonyms_value + synonyms_description。**', '**Enum Value 向量化使用 value + 可选 name + 4语言 display/description + 平铺 synonyms。**')
text = text.replace('SynonymLanguageAccuracy', 'SynonymSourceLanguageAccuracy（离线标注）')
text = text.replace('SynonymLanguageRecall@K', 'SynonymSourceLanguageRecall@K（离线标注）')
text = text.replace('`synonyms` 最多 3 种语言且语言不固定，因此必须按实际 language key 分桶统计，不能只看 display/description 的四个语言槽位。', '`synonyms` 的 language key 只存在于 OMS SynonymType 源资产；语言级评测必须使用带源语言标签的离线测试集分桶，不能从 OAG 平铺热索引字段反推语言。')
text = text.replace('ObjectType/Property 及 Enum Value 的 Synonym 内嵌在 `synonyms` 字段中，中文/英文之外最多再支持两个 display/description 语言槽位，Synonym 最多三种非固定语言；Seed/Enum 向量包含 name/display/description/synonyms，Instance 向量只包含 value。', 'ObjectType/Property 及 Enum Value 的 Synonym 在 OMS 中保留最多三个非固定 language key，进入 OAG 后统一平铺为 LF 分隔的 `synonyms` String；中文/英文之外最多再支持两个 display/description 语言槽位；Seed/Enum 向量直接包含平铺 synonyms，Instance 向量只包含 value。')

# Chapter 3 already uses the flat protocol; align static build wording with the new chapter 2 template.
text = text.replace(
    '动态导入不再接收 `name`，EmbeddingInputBuilder 拼接 `value + display_* + description_* + synonyms`；静态 OMS 构建仍可使用第 2.9 节中存在的 `name`。',
    '动态导入不再接收 `name`，EmbeddingInputBuilder 拼接 `value + display_* + description_* + synonyms`；静态 OMS 构建按第 2.9 节在 `name` 存在时追加该字段。两种路径都直接消费同一个 LF 平铺 `synonyms`。'
)

DOC.write_text(text, encoding='utf-8')

# Validation.
text = DOC.read_text(encoding='utf-8')
ch2 = text.split('# 2. 数据模型与索引结构', 1)[1].split('# 3. 索引构建与 DataSync Bulk Import', 1)[0]
required = [
    '> 版本：V5.11',
    'OMS SynonymType：保留多语言源结构',
    'OAG `synonyms`：统一平铺为 String/TEXT',
    'LF 分隔的同义词平铺字符串',
    '{synonyms}',
    'synonym_line_analyzer',
    'SynonymFlattener',
    'matched_field = synonyms',
    'Instance Value：objectTypeId + propertyid + normalized(value)',
]
missing = [x for x in required if x not in text]
if missing:
    raise SystemExit(f'missing required V5.11 content: {missing}')
forbidden_ch2 = [
    'JSON 序列化的多语言同义词 Map',
    '`synonyms` | `object`',
    'synonyms.*.keyword',
    '{synonyms_value}',
    '{synonyms_description}',
    'synonyms\n  → language Map',
]
found = [x for x in forbidden_ch2 if x in ch2]
if found:
    raise SystemExit(f'stale synonym model remains in chapter 2: {found}')
forbidden_all = [
    'matched_field = synonyms.<language>',
    '"matched_field": "synonyms.zh"',
    '"matched_field": "synonyms.es"',
]
found_all = [x for x in forbidden_all if x in text]
if found_all:
    raise SystemExit(f'stale matched_field remains: {found_all}')
if text.count('# 2. 数据模型与索引结构') != 1 or text.count('# 3. 索引构建与 DataSync Bulk Import') != 1:
    raise SystemExit('chapter boundary damaged')
if text.count('```') % 2 != 0:
    raise SystemExit('unbalanced markdown fences')
print('V5.11 synonym flat-index patch applied and validated')
