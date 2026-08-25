# OAG 本体子图语义检索接口 extractedEntities / 实体提取设计方案

> 文档版本：V2.5  
> 更新日期：2026-08-25  
> 接口版本：v2  
> 上位方案：[OAG 本体锚点语义检索与向量索引设计方案](./OAG本体锚点语义检索与向量索引设计方案.md)

---

## 1. 文档目的

本文定义本体子图检索第 ① 步“实体提取（Entity Extraction）”的输入、输出和约束，并作为 `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search` 的 `extractedEntities` 正式结构规范。

本文同时给出可直接用于 LLM 的中英文实体提取 Prompt，确保接口 Schema、提取规则、Values 边界、运行时 Prompt 与服务端校验保持同一份权威定义。

本次结构收敛遵循一个核心原则：

> **`ExtractedEntity` 只保留 `ObjectType`、`Properties`、`Values` 三个字段。实体提取只负责识别“对象类型、对象属性和值”，不在本阶段绑定 Relationship，也不要求提前判断 Value 属于 Enum 还是 Instance。**

完整本体子图检索链路为：

```text
① Entity Extraction
   query → ObjectType / Properties / Values

② Entity Linking
   本体对象 / 枚举元素 / 实例元素
   → Exact/BM25 + Dense
   → Weighted RRF + 可选 LLM Fine Rank

③ Subgraph Retrieval Strategy
   minimal / khop / component
   → 生成 PathProbePlan
   → Loop 执行，可扩展业务策略

④ nGQL / Graph Algorithm Assembly
   PathProbePlan
   → 动态装配 nGQL 模板或图算法参数

⑤ Result Generation
   → ObjectType / Property / Relationship / RelationshipProperty
   → Function / Action
```

---

## 2. 接口角色与能力边界

### 2.1 接口地址

| 项目 | 定义 |
|---|---|
| Method | `POST` |
| Content-Type | `application/json` |
| URI | `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search` |
| 成功 HTTP 状态码 | `200` |

### 2.2 三种调用模式

| 模式 | query | extractedEntities | searchContext | 说明 |
|---|---:|---:|---:|---|
| 自然语言模式 | 有 | 无 | 可选 | OAG 从 `query` 自动执行实体提取 |
| 结构化模式 | 无 | 有 | 可选 | 业务 Skill 已完成实体提取，OAG 直接进入 Entity Linking |
| 组合模式 | 有 | 有 | 可选 | 结构化结果提供强提示，`query` 和 `searchContext` 用于补充与消歧，推荐模式 |

约束：

```text
query 和 extractedEntities 至少一个不为空
searchContext 不能单独满足该约束
```

### 2.3 实体提取阶段负责什么

实体提取负责：

1. 从用户问题识别 ObjectType 业务表达；
2. 识别属于该 ObjectType 的 Property，并保持从属关系；
3. 识别需要通过语义索引定位的业务值，输出到 `Values`；
4. 在归属未知时允许输出 value-only 实体；
5. 使用 `searchContext` 中的 few-shot、专家路径、领域术语、黑话和消歧规则辅助提取。

实体提取不负责：

1. 输出本体内部 ObjectType/Property ID；
2. 提前生成或绑定 Relationship；
3. 将 Value 强制分类为 Enum Value 或 Instance Value；
4. 把“超过 200”“本月”“总数”等条件直接翻译为 OQL/SQL/Cypher；
5. 决定 `minimal/khop/component` 路径算法；
6. 生成 nGQL。

Relationship 的发现与选择属于第 ③ 步子图检索策略。业务已有专家关系路径时，放入 `searchContext` 作为路径规划约束或优先级提示，不进入 `ExtractedEntity` Schema。

---

## 3. 请求参数

### 3.1 Header 与 Path

| 参数 | 位置 | 必选 | 类型 | 约束 | 说明 |
|---|---|---:|---|---|---|
| `tenantId` | Header | 是 | String | 1～256 字符 | 租户 ID |
| `traceId` | Header | 否 | String | 1～256 字符 | Trace ID；未传可由服务生成 |
| `ontologyId` | Path | 是 | String | 1～256 字符 | 本体 ID |

### 3.2 Body

| 参数 | 必选 | 类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `query` | 否 | String | 无 | 原始自然语言问题；与 `extractedEntities` 至少一个不为空 |
| `searchContext` | 否 | String | 无 | 动态搜索上下文；用于实体提取和后续语义消歧 |
| `extractedEntities` | 否 | `Array<ExtractedEntity>` | 无 | 结构化实体提取结果 |
| `adaptiveRetrieval` | 否 | Integer | `1` | 是否启用小本体全量返回策略 |
| `seedRetrievalMode` | 否 | String | `vector` | `vector` / `keyword` / `hybrid`；字段名为兼容历史 API，语义上控制 Entity Linking 检索模式 |
| `similarityThreshold` | 否 | Double | `0.6` | Dense 召回阈值 |
| `topk` | 否 | Integer | `3` | 每个语义单元最终保留候选数 |
| `graphExpansionStrategy` | 否 | String | `minimal` | `minimal` / `khop` / `component` |
| `hopLimit` | 否 | Integer | `3` | `khop` 最大深度 |
| `includeFunctions` | 否 | Integer | `0` | 是否扩展 Function |
| `includeActions` | 否 | Integer | `0` | 是否扩展 Action |

---

## 4. extractedEntities 正式结构

### 4.1 ExtractedEntity

`ExtractedEntity` **只定义三个顶层字段**：

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `ObjectType` | 否 | String | 无 | 对象类型名称、显示名、同义词或业务术语；value-only 场景可以省略 |
| `Properties` | 否 | `Array<String>` | `[]` | 当前 ObjectType 相关的 Property 名称；非空时必须同时存在 `ObjectType` |
| `Values` | 否 | `Array<ValueHint>` | `[]` | 需要语义检索的业务值；ObjectType/Property 归属未知时允许单独存在 |

每个 `ExtractedEntity` 至少满足下列之一：

```text
ObjectType 非空
或
Values 非空
```

不允许只有 `Properties` 而没有 `ObjectType`。

### 4.2 ValueHint

`Values` 统一承载“值语义提示”，不在实体提取阶段区分枚举值或实例值。

| 字段 | 必选 | 类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `Property` | 否 | String | 无 | 已知时填写所属 Property 的业务名称；未知时省略 |
| `Value` | 是 | String | 无 | 用户问题中需要语义定位的真实业务表达 |

示例：

```json
{
  "ObjectType": "Account",
  "Properties": ["accountStatus", "customerLevel"],
  "Values": [
    {"Property": "accountStatus", "Value": "在用"},
    {"Property": "customerLevel", "Value": "VIP"}
  ]
}
```

Entity Linking 阶段对 `Value` 同时考虑：

```text
枚举元素索引
  value / name / display / description / synonyms

实例元素索引
  真实去重 value
```

最终由索引记录中的 `property_id + object_type_id` 解析真实归属，而不是由 NER 根据字符串外形猜测。

### 4.3 value-only 结构

当问题只给出一个值而无法判断其对象和属性，例如：

```text
12JKS0885_IN_RSNM_KALIBATA3_MC
```

允许输出：

```json
{
  "Values": [
    {"Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"}
  ]
}
```

OAG 在 Entity Linking 阶段跨枚举元素/实例元素检索，并根据命中记录补齐 Property/ObjectType 归属。编码形态本身不能作为 Site、BaseStation、nativeId 等类型推断依据。

---

## 5. 实体提取规则

### 5.1 ObjectType

ObjectType 识别优先使用：

```text
业务对象名
显示名
别名/同义词
searchContext 中的术语映射
few-shot 中明确的对象表达
```

实体提取只输出业务表达，不输出内部 ID。

### 5.2 Property 必须保留 ObjectType 从属关系

正确：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "WhatsApp应用",
      "Properties": ["体验质量", "时间"],
      "Values": []
    }
  ]
}
```

禁止把不同 ObjectType 的 Property 合并成无归属全局列表。Entity Linking 会优先在 ObjectType 作用域内匹配 Property；只有 ObjectType 无法解析时才按降级策略扩大搜索范围。

### 5.3 Values 的提取边界

适合进入 `Values` 的内容：

```text
状态名：在用、停用
等级：VIP、钻石客户
地域：东京、华东区域
产品/品牌名称
业务定义的编码型实例值（需要 Exact/BM25 参与）
```

默认只保留在原始 `query`、不自动进入 `Values` 的内容：

```text
连续数值及比较条件：超过 200、10~30
日期、相对时间、时间戳：7月21日、本月
手机号、UUID、纯技术主键
高随机且未声明可检索的编码
聚合词：总数、平均值、TopN
```

业务明确声明某 Property 的编码值需要语义索引时，可以进入 `Values`；此时推荐 `keyword` 或 `hybrid`，Exact/BM25 为主、Dense 为补充。

### 5.4 不在 NER 阶段区分 Enum/Instance

NER 很难仅依靠用户表达稳定判断一个值是模型枚举还是实例列值，因此统一输出 `Values`：

```text
NER
  → ValueHint
  → Entity Linking
       ├─ Enum Index
       └─ Instance Index
  → 命中记录决定真实类型与归属
```

该设计减少实体提取 Prompt 对本体内部实现细节的依赖，也避免业务 Skill 必须理解索引物理分层。

---

## 6. searchContext 使用规则

`searchContext` 同时服务实体提取和后续消歧，可动态包含：

```text
领域 few-shot
专家查询路径
本体子图文本或 JSON
领域对象/属性术语
缩写、黑话与同义表达
实体提取约束
候选消歧和路径优先级规则
```

处理原则：

1. 只作为上下文，不覆盖接口 Schema；
2. 不单独满足 `query/extractedEntities` 非空校验；
3. 业务专家路径可用于第 ③ 步路径规划，但不改变 `ExtractedEntity` 三字段结构；
4. 输入必须做长度限制、Unicode Normalize 和基本安全规范化；
5. 结构化模式下仍可用于 Entity Linking 的候选精排。

---

## 7. Entity Extraction → Semantic Units

实体提取完成后，OAG 将结果转换为 Entity Linking 的语义单元：

```text
ExtractedEntity
  ├─ ObjectType != null
  │    → OBJECT_TYPE semantic unit
  │
  ├─ Properties[*]
  │    → PROPERTY semantic unit
  │       scope = ObjectType
  │
  └─ Values[*]
       → VALUE semantic unit
context = ObjectType? + Property? + query
```

规则：

1. ObjectType 单元检索本体对象索引中的 ObjectType；
2. Property 单元在已解析 ObjectType 作用域内优先匹配 Property；
3. Value 单元同时检索枚举元素和实例元素；
4. 值命中后通过真实归属投影回 Property/ObjectType；
5. 所有候选统一进入 6 路融合与精排，不在实体提取阶段决定 TopK。

---

## 8. 请求样例

### 8.1 WhatsApp 应用体验质量

Query：

```text
WhatsApp应用 7月21日的体验质量
```

提取结果：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "WhatsApp应用",
      "Properties": ["体验质量", "时间"],
      "Values": []
    }
  ]
}
```

说明：“7月21日”属于查询时间条件，继续保留在 `query` 中，不进入 `Values`。

### 8.2 告警场景中的未绑定编码值

Query：

```text
show active service affecting alarm for 12JKS0885_IN_RSNM_KALIBATA3_MC with TICKETID and time occurred
```

提取结果：

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

说明：问题中没有足够信息证明该编码属于 Site/BaseStation/nativeId，因此保持 value-only，由索引命中后解析真实归属。

### 8.3 同时包含枚举语义和实例语义的值

Query：

```text
查询在用状态的VIP客户账户
```

提取结果：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "Account",
      "Properties": ["accountStatus", "customerLevel"],
      "Values": [
        {"Property": "accountStatus", "Value": "在用"},
        {"Property": "customerLevel", "Value": "VIP"}
      ]
    }
  ],
  "seedRetrievalMode": "hybrid"
}
```

NER 不需要知道“在用”最终来自枚举索引还是“VIP”最终来自实例索引；Entity Linking 负责查询并根据索引记录判断。

### 8.4 带专家路径的组合模式

专家路径不写入 `ExtractedEntity`，而写入 `searchContext`：

```json
{
  "query": "本月个人客户中，信用额度超过200元的账户总数是多少？",
  "searchContext": "专家路径：IndividualCustomer -> PayRelation -> Account -> CreditLimitInstance。路径只用于后续候选消歧和子图路径规划。",
  "extractedEntities": [
    {"ObjectType": "IndividualCustomer", "Properties": ["id"], "Values": []},
    {"ObjectType": "PayRelation", "Properties": ["objectId", "accountId"], "Values": []},
    {"ObjectType": "Account", "Properties": ["accountId"], "Values": []},
    {"ObjectType": "CreditLimitInstance", "Properties": ["accountId", "initialAmount"], "Values": []}
  ],
  "graphExpansionStrategy": "minimal"
}
```

“本月”“超过 200”“总数”继续由原始 query 保存，后续查询生成阶段解释。

---

## 9. 校验与归一化规则

1. `tenantId`、`ontologyId` 必须存在且满足长度要求；
2. `query` 与 `extractedEntities` 至少一个不为空；
3. 每个 `ExtractedEntity` 至少存在非空 `ObjectType` 或非空 `Values`；
4. `Properties` 非空时必须存在 `ObjectType`；
5. `ValueHint.Value` 必须为非空字符串；
6. `ValueHint.Property` 非空且同一实体有 `ObjectType` 时，应同时出现在该实体 `Properties` 中；
7. 所有文本执行 trim、Unicode Normalize、去空和规范化去重；
8. 业务名称不能直接当作本体内部 ID；
9. value-only 不允许根据值的格式猜测 ObjectType/Property；
10. `similarityThreshold` 范围为 0～1；`topk/hopLimit >= 1`。

推荐归一化：

```text
Unicode NFKC
trim
连续空白折叠
大小写策略按 Analyzer/语言配置处理
数组稳定去重并保留首次出现顺序
```

---

## 10. OpenAPI Schema 核心定义

```yaml
components:
  schemas:
    SemanticSearchRequest:
      type: object
      anyOf:
        - required: [query]
        - required: [extractedEntities]
      properties:
        query:
          type: string
          minLength: 1
          maxLength: 1024
        searchContext:
          type: string
          minLength: 1
          maxLength: 32768
        extractedEntities:
          type: array
          minItems: 1
          items:
            $ref: '#/components/schemas/ExtractedEntity'
        adaptiveRetrieval:
          type: integer
          default: 1
          enum: [0, 1]
        seedRetrievalMode:
          type: string
          default: vector
          enum: [vector, keyword, hybrid]
        similarityThreshold:
          type: number
          minimum: 0
          maximum: 1
          default: 0.6
        topk:
          type: integer
          minimum: 1
          default: 3
        graphExpansionStrategy:
          type: string
          default: minimal
          enum: [minimal, khop, component]
        hopLimit:
          type: integer
          minimum: 1
          default: 3
        includeFunctions:
          type: integer
          default: 0
          enum: [0, 1]
        includeActions:
          type: integer
          default: 0
          enum: [0, 1]

    ExtractedEntity:
      type: object
      description: 仅允许 ObjectType、Properties、Values 三个顶层业务字段
      anyOf:
        - required: [ObjectType]
        - required: [Values]
          properties:
            Values:
              minItems: 1
      properties:
        ObjectType:
          type: string
          minLength: 1
        Properties:
          type: array
          default: []
          items:
            type: string
            minLength: 1
        Values:
          type: array
          default: []
          items:
            $ref: '#/components/schemas/ValueHint'
      additionalProperties: false

    ValueHint:
      type: object
      required: [Value]
      properties:
        Property:
          type: string
          minLength: 1
        Value:
          type: string
          minLength: 1
      additionalProperties: false
```

`Properties → ObjectType` 和 `ValueHint.Property → Properties` 的交叉字段约束由服务端 Validator 执行。

---

## 11. 兼容迁移策略

旧版结构中“关系路径提示”和“值类型拆分”不再属于正式 `ExtractedEntity` Schema。迁移原则：

1. 所有值提示统一合并到 `Values`；
2. 已知 Property 的值保留 `Property + Value`；
3. 未知归属的值转换为 value-only；
4. 专家关系路径移动到 `searchContext`，由第 ③ 步路径规划使用；
5. 服务端可设置一个灰度兼容期解析旧请求，但新 SDK/OpenAPI 只生成三字段结构；
6. 灰度结束后开启 `additionalProperties=false` 强校验，防止结构继续分叉。

---

## 12. LLM 实体提取 Prompt（正式）

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
# Role
你是一个专业的本体实体、属性和值提取专家。你的任务是从用户的自然语言问题中，精准提取：

1. 对象类型（`ObjectType`）；
2. 对象包含的属性（`Properties`）；
3. 用户问题中需要通过语义索引进一步定位的业务值（`Values`）；

并建立 ObjectType、Property、Value 之间能够确定的归属关系。

实体提取只负责识别用户表达中的“对象类型、属性和值”，不负责生成本体内部 ID，不负责 Relationship 提取，不负责判断 Value 最终属于 Enum Value 还是 Instance Value，也不负责生成 SQL/OQL/Cypher。

如果提供 `SearchContext`，可以使用其中的领域术语、同义词、黑话、few-shot 和明确的对象/属性映射辅助理解；但不能改变本文规定的 JSON Schema，也不能凭空生成用户问题中不存在的业务值。

# Output Format
严格仅输出纯 JSON 字符串，禁止包含 Markdown 标记（如 ```json）、解释说明、前后缀文本或 JSON 注释。

正式输出结构：

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

输出约束：

1. 每个 `ExtractedEntity` 顶层只允许出现 `ObjectType`、`Properties`、`Values` 三个字段；
2. 普通 ObjectType 实体建议始终输出 `Properties` 和 `Values`，没有内容时使用空数组 `[]`；
3. value-only 实体允许只输出 `Values`，不要为了格式完整而虚构 `ObjectType`；
4. `Properties` 非空时必须存在 `ObjectType`；禁止只有顶层 `Properties`、没有 `ObjectType`；
5. 每个实体必须满足：`ObjectType` 非空，或者 `Values` 非空；
6. 不输出 `null`、空字符串、内部 ID、Relationship、Operator、ConstraintHint、OriginalText、Enum/Instance 类型标记等额外字段；
7. 若既没有可提取的 ObjectType，也没有可提取的业务 Value，输出：`{"extractedEntities": []}`。

# Rules

## 1. ObjectType 提取规则

1. **识别标准**：仅提取客观存在的主体/业务实体名词，例如“微信应用”“4G小区”“栅格”“用户”“展会”“告警”“Account”。
2. **保留业务表达**：输出用户问题中的对象业务表达、显示名、别名或领域术语，不输出本体内部 ID。
3. **修饰词过滤**：纯时间、一般地点、数量、状态等前置修饰词通常不是 ObjectType。例如“2024年北京展会”中的核心 ObjectType 是“展会”；“高负荷小区”中的核心 ObjectType 是“小区”。
4. **避免指标前缀误拆**：复合指标/属性中的名词前缀属于 Property 的一部分，例如“数据包下行丢包率”中的“数据包”不能单独提取为 ObjectType。
5. **实体唯一性**：同一语义对象只保留一个最合适粒度。例如已提取“4G小区”时，不再额外提取“小区”。
6. **禁止从值形态猜对象类型**：不能因为一个字符串看起来像站点号、基站号、电话号码、UUID 或编码，就推断它属于 Site、BaseStation、User 等 ObjectType。

## 2. Property 提取规则

1. **识别标准**：提取依附于 ObjectType 的特征、指标、性能、状态维度、业务维度、测量维度或时间维度，例如“上行速率”“告警信息”“体验质量”“时间”“丢包率”“PRB利用率”“经纬度”“msisdn”“accountStatus”。
2. **归属必须明确**：Property 必须保留所属 ObjectType，不允许把多个 ObjectType 的 Properties 合并成一个无归属全局列表。
3. **词汇规范化**：属性表达带有纯泛化后缀“指标”“数据”“数值”等时，可去掉不影响语义的泛化后缀，例如“体验质量指标”提取为“体验质量”。
4. **路径/关联句式消歧**：在“从 A 到 B”“A 与 B 的关系”“A 到 B 的路径”等句式中，如果 B 实际是指标、维度或属性，则应作为 A 的 Property，而不是 ObjectType。
5. **长链集中属性对齐**：长链查询末尾集中出现多个属性时，要依据语义将每个 Property 分配给正确 ObjectType。
6. **没有属性时为空数组**：ObjectType 已识别但未提及任何 Property 时，`Properties` 输出 `[]`。

## 3. Values 提取规则

`Values` 用于承载需要在后续 Entity Linking 中通过枚举元素索引或实例元素索引进行定位的“业务值表达”。

### 3.1 应优先提取为 Value 的内容

当它们在问题中承担“筛选值、业务取值、对象实例取值”的语义时，优先进入 `Values`：

- 离散状态值：在用、停用、ACTIVE、严重、已恢复；
- 离散等级/类别：VIP、钻石客户、黄金客户、FORMAL；
- 作为业务属性取值使用的地域/区域：东京、华东区域、Region-A；
- 产品名、品牌名、套餐名、业务分类名；
- 用户明确输入、用于定位业务对象/属性的业务编码或实例值；
- `SearchContext` 明确声明需要通过语义索引检索的业务取值。

### 3.2 默认不要放入 Values 的内容

以下内容默认保留在原始 Query 中，由后续查询理解/条件生成阶段处理，不自动作为 Value：

- 连续数值及比较条件：`超过200`、`10~30`、`>= 80%`；
- 日期、相对时间、时间范围、时间戳：`7月21日`、`本月`、`昨天`、`2026-08-25`；
- 聚合/排序词：`总数`、`平均值`、`最大值`、`TopN`；
- 纯单位：`米`、`秒`、`Mbps`；
- 与查询目标无关的普通地点/时间修饰语；
- 仅凭外观判断为 UUID、手机号、纯技术主键、高随机编码，且问题/上下文没有表明它需要进行业务语义定位的内容。

但如果一个不透明编码/标识符**明确作为用户要查找的业务对象取值出现**，应保留为 Value；归属不确定时使用 value-only，不能根据编码格式猜测 ObjectType/Property。

### 3.3 Value 必须保留用户原始表达

`Value` 应尽量保持用户问题中的原始业务表达，不要在实体提取阶段转换为内部标准值、canonical value 或本体枚举值。

例如：

- 用户说“严重”，`Value` 保留“严重”，不要改写成 `CRITICAL`；
- 用户说“在用”，`Value` 保留“在用”，不要自行翻译成 `ACTIVE`；
- 用户输入 `12JKS0885_IN_RSNM_KALIBATA3_MC`，应原样保留大小写和字符。

标准值映射由后续 Entity Linking 根据真实索引记录完成。

### 3.4 Value 与 Property 的绑定规则

1. 如果用户问题或 `SearchContext` 能**明确确定** Value 所属 Property，则输出：

   `{"Property": "属性名", "Value": "业务值"}`

2. 如果 ObjectType 已知，但 Value 所属 Property 不确定，可以将 Value 放在该 ObjectType 的 `Values` 中，同时省略 `Property`：

   `{"Value": "业务值"}`

3. 如果 ObjectType 和 Property 都无法可靠确定，则单独输出 value-only 实体：

   `{"Values": [{"Value": "业务值"}]}`

4. 不要为了让每个 Value 都有 Property 而猜测 Property。
5. 如果填写了 `ValueHint.Property` 且同一条记录存在 `ObjectType`，该 Property 应同时出现在该实体的 `Properties` 数组中，保持结构一致。

### 3.5 value-only 规则

当用户提供了需要定位的真实业务值，但无法可靠判断其 ObjectType/Property 时，必须允许 value-only，而不是丢弃该值或虚构归属。

例如：

{
  "Values": [
    {
      "Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"
    }
  ]
}

后续 Entity Linking 会跨枚举元素索引和实例元素索引检索，再通过真实命中记录中的 Property/ObjectType 归属补齐信息。

### 3.6 不区分 Enum Value / Instance Value

实体提取阶段禁止输出或猜测：

- `EnumValue`；
- `InstanceValue`；
- `valueType`；
- `isEnum` / `isInstance`。

所有需要定位的值统一进入 `Values`。后续 Entity Linking 同时检索 Enum Index 和 Instance Index，由真实索引记录决定最终类型和归属。

## 4. 修饰词、状态词与 Value 的消歧

同一个词可能只是自然语言修饰语，也可能是 Property 的业务 Value，必须根据句法和语义角色判断。

- “所有高负荷小区的 RRC 连接成功率”：若没有明确 Property/上下文表明“高负荷”是可索引的离散业务值，默认仅视为修饰条件，不自动创建 Value；
- “小区的负荷状态为高负荷”：`负荷状态` 是 Property，`高负荷` 是 Value；
- “2024年北京展会期间”：`2024年` 和 `北京` 是事件上下文修饰，不自动进入 Values；
- “用户所属区域为东京”：`所属区域` 是 Property，`东京` 是 Value。

原则：**Value 是业务属性/实例的取值，不是所有形容词、地点词、时间词的集合。**

## 5. 路径、Relationship 与条件边界

1. Entity Extraction 不直接输出 Relationship 或 RelationshipProperty。
2. “从 A 到 B 的路径”“A 与 B 的关系”中，只有真实 ObjectType 才进入 ObjectType；指标/维度仍按 Property 处理。
3. 专家关系路径、方向约束和业务路径优先级如果存在于 `SearchContext`，只用于辅助理解和后续图规划，不增加 ExtractedEntity 字段。
4. 连续数值比较、日期范围、聚合、排序等条件不要转换为 ValueHint，也不要在本阶段生成 Operator/SQL/OQL/Cypher。

## 6. 去重与一致性规则

1. 相同 ObjectType 只保留一条实体记录，合并其 Properties 和 Values；
2. Properties 按首次出现顺序去重；
3. Values 按“Property（若有）+ Value 原文”去重；
4. 不同 ObjectType 下同名 Property 不得合并；
5. 同一个 Value 如果存在多个合理归属但当前无法消歧，不要复制到多个猜测 ObjectType 下，优先保留为 value-only，交给 Entity Linking 消歧；
6. 不补全用户未表达的对象、属性和值；`SearchContext` 只用于识别/消歧，不用于凭空扩写查询内容。

## 7. 输出前强制自检

输出 JSON 前逐项检查：

1. 顶层字段是否只有 `extractedEntities`；
2. 每个实体是否只包含 `ObjectType / Properties / Values`；
3. 是否存在只有 `Properties`、没有 `ObjectType` 的非法实体；
4. 是否遗漏用户明确用于筛选/定位的离散业务 Value；
5. 是否把日期、数值比较、聚合词错误放入 Values；
6. 是否根据编码外形猜测 ObjectType/Property；
7. 是否错误地区分 Enum/Instance；
8. `ValueHint.Property` 是否确有依据；
9. Value 是否保持用户原始表达；
10. JSON 是否可以直接解析且没有任何解释文字。

# Examples

## Example 1：原有 ObjectType + Properties 能力保持不变
Input: `查看下2024年北京展会期间，5G基站的上行速率和告警信息？`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "展会",
      "Properties": [],
      "Values": []
    },
    {
      "ObjectType": "5G基站",
      "Properties": ["上行速率", "告警信息"],
      "Values": []
    }
  ]
}

## Example 2：路径句式中的指标仍是 Property
Input: `从微信应用到体验质量指标和时间的路径？`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "微信应用",
      "Properties": ["体验质量", "时间"],
      "Values": []
    }
  ]
}

## Example 3：长链 ObjectType 与 Property 对齐
Input: `从微信应用到4G小区到栅格到用户到数据包下行丢包率、下行PRB平均利用率、栅格中心经纬度、msisdn的路径`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "微信应用",
      "Properties": ["数据包下行丢包率"],
      "Values": []
    },
    {
      "ObjectType": "4G小区",
      "Properties": ["下行PRB平均利用率"],
      "Values": []
    },
    {
      "ObjectType": "栅格",
      "Properties": ["栅格中心经纬度"],
      "Values": []
    },
    {
      "ObjectType": "用户",
      "Properties": ["msisdn"],
      "Values": []
    }
  ]
}

## Example 4：Property 已知的离散 Values
Input: `查询Account中accountStatus为在用且customerLevel为VIP的账户`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "Account",
      "Properties": ["accountStatus", "customerLevel"],
      "Values": [
        {
          "Property": "accountStatus",
          "Value": "在用"
        },
        {
          "Property": "customerLevel",
          "Value": "VIP"
        }
      ]
    }
  ]
}

## Example 5：地域是业务 Property 的 Value
Input: `查询所属区域为东京、客户等级为钻石客户的用户`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "用户",
      "Properties": ["所属区域", "客户等级"],
      "Values": [
        {
          "Property": "所属区域",
          "Value": "东京"
        },
        {
          "Property": "客户等级",
          "Value": "钻石客户"
        }
      ]
    }
  ]
}

## Example 6：不透明编码使用 value-only，不猜归属
Input: `查询 12JKS0885_IN_RSNM_KALIBATA3_MC 相关的告警`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "告警",
      "Properties": [],
      "Values": []
    },
    {
      "Values": [
        {
          "Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"
        }
      ]
    }
  ]
}

## Example 7：日期不进入 Values
Input: `WhatsApp应用 7月21日的体验质量`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "WhatsApp应用",
      "Properties": ["体验质量", "时间"],
      "Values": []
    }
  ]
}

## Example 8：连续数值比较不进入 Values
Input: `查询船高在10到30米之间的货轮`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "货轮",
      "Properties": ["船高"],
      "Values": []
    }
  ]
}

## Example 9：修饰词不强行提取为 Value
Input: `查询所有高负荷小区的RRC连接成功率是否达标？`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "小区",
      "Properties": ["RRC连接成功率"],
      "Values": []
    }
  ]
}

## Example 10：无本体业务实体和值
Input: `你好，请问今天天气怎么样？`

Output:
{"extractedEntities": []}

# Task
SearchContext:

Input:

Output:

---
````

### 12.3 English Version Prompt

````text
# Role
You are a professional ontology ObjectType, Property, and Value extraction expert. Your task is to accurately extract from a user's natural-language query:

1. Object types (`ObjectType`);
2. Properties belonging to those object types (`Properties`);
3. Business values that require semantic lookup in later Entity Linking (`Values`).

Establish only ownership relationships that can be determined reliably from the query and optional `SearchContext`.

Entity Extraction identifies business expressions for objects, properties, and values only. It MUST NOT generate internal ontology IDs, extract Relationships, classify a Value as Enum or Instance, or generate SQL/OQL/Cypher.

If `SearchContext` is provided, use its domain terminology, synonyms, jargon, few-shot examples, and explicit mappings only as interpretation/disambiguation context. It must not change the JSON schema or invent values that are absent from the user's query.

# Output Format
Output a pure JSON string only. Do NOT include Markdown fences, explanations, prefixes/suffixes, or JSON comments.

Formal structure:

{
  "extractedEntities": [
    {
      "ObjectType": "string",
      "Properties": ["property1", "property2"],
      "Values": [
        {
          "Property": "property1",
          "Value": "original business value"
        },
        {
          "Value": "business value with unresolved property"
        }
      ]
    },
    {
      "Values": [
        {
          "Value": "business value with unresolved ObjectType and Property"
        }
      ]
    }
  ]
}

Output constraints:

1. Each `ExtractedEntity` may contain only `ObjectType`, `Properties`, and `Values`.
2. For a normal ObjectType entity, output `Properties` and `Values`; use `[]` when empty.
3. A value-only entity may contain only `Values`; never invent an ObjectType just to complete the structure.
4. If top-level `Properties` is non-empty, `ObjectType` MUST exist.
5. Each entity must have either a non-empty `ObjectType` or non-empty `Values`.
6. Do not output nulls, empty strings, internal IDs, Relationships, Operator, ConstraintHint, OriginalText, or Enum/Instance classification fields.
7. If neither an ontology ObjectType nor a business Value can be extracted, output `{"extractedEntities": []}`.

# Rules

## 1. ObjectType Extraction

1. Extract objective business subject/entity nouns, such as `WeChat Application`, `4G Cell`, `Grid`, `User`, `Exhibition`, `Alarm`, or `Account`.
2. Preserve the user's business expression/display name/alias; do not output internal ontology IDs.
3. Ignore pure time/location/count/state modifiers when they only qualify the subject.
4. Do not split noun prefixes from compound metrics. For example, the `packet` part of `downlink packet loss rate` belongs to the Property expression.
5. Keep one most appropriate granularity for the same entity; do not emit both `4G Cell` and `Cell` for the same mention.
6. Never infer an ObjectType from the shape of a value such as a site code, phone number, UUID, or opaque identifier.

## 2. Property Extraction

1. Extract features, metrics, performance attributes, state dimensions, business dimensions, measurement dimensions, and time dimensions attached to an ObjectType.
2. Preserve ObjectType ownership; never merge Properties from different ObjectTypes into one global list.
3. Remove only semantically empty generic suffixes such as `metric`, `data`, or `value` when doing so preserves the original concept.
4. In path/relation phrasing, if a term is actually a metric or dimension, treat it as a Property rather than an ObjectType.
5. In long-chain queries with properties listed at the end, assign each Property to the correct ObjectType by semantics.
6. If no Property is mentioned for an ObjectType, output `Properties: []`.

## 3. Values Extraction

`Values` contains business value expressions that should be located later using Enum and/or Instance semantic indexes.

### 3.1 Prefer extracting as Values

When used as filter/business/instance values, prefer extracting:

- discrete statuses: `active`, `disabled`, `critical`, `recovered`;
- discrete levels/categories: `VIP`, `Diamond Customer`, `FORMAL`;
- regions used as business property values: `Tokyo`, `East China Region`, `Region-A`;
- product names, brand names, package names, business categories;
- explicit business codes/instance values used by the user to locate data;
- values explicitly declared as semantic-index values in `SearchContext`.

### 3.2 Do not extract as Values by default

Keep these in the original query for later condition/query understanding unless domain context explicitly says otherwise:

- continuous numeric comparisons/ranges: `over 200`, `10~30`, `>=80%`;
- dates, relative times, timestamps, time ranges: `July 21`, `this month`, `yesterday`;
- aggregation/sorting words: `count`, `average`, `maximum`, `TopN`;
- units such as `meter`, `second`, `Mbps`;
- ordinary time/location modifiers unrelated to a business property;
- UUIDs, phone numbers, pure technical keys, or highly random codes when the query/context does not indicate that they are business lookup values.

However, if an opaque identifier is clearly used as a business lookup value, preserve it as a Value. If ownership is uncertain, use value-only instead of guessing ObjectType/Property.

### 3.3 Preserve the original Value expression

Keep the user's original expression. Do not convert it to a canonical/internal value during Entity Extraction.

Examples:

- `critical` or a local-language synonym must not be rewritten into an internal enum code;
- `在用` must not be automatically changed to `ACTIVE`;
- preserve `12JKS0885_IN_RSNM_KALIBATA3_MC` exactly.

Canonical mapping is performed by downstream Entity Linking using actual index records.

### 3.4 Binding Value to Property

1. If the query or `SearchContext` clearly identifies the Property, output `{"Property":"...","Value":"..."}`.
2. If ObjectType is known but the Value's Property is uncertain, keep the Value under that ObjectType and omit `Property`.
3. If both ObjectType and Property are uncertain, emit a separate value-only entity: `{"Values":[{"Value":"..."}]}`.
4. Never guess a Property just to bind every Value.
5. If `ValueHint.Property` is provided and an ObjectType exists in the same entity, the same Property should also appear in the entity's `Properties` array.

### 3.5 Value-only

When a real business value is present but ownership cannot be reliably determined, do not drop it and do not invent ownership. Emit value-only and let Entity Linking resolve it through Enum/Instance indexes.

### 3.6 Do not classify Enum vs Instance

Never output `EnumValue`, `InstanceValue`, `valueType`, `isEnum`, or `isInstance`. All value hints go into `Values`. Downstream Entity Linking decides the real type and ownership from index hits.

## 4. Modifier vs Value Disambiguation

A word can be only a modifier or a real Property value. Decide by its semantic role:

- `high-load cells` → without an explicit Property/domain mapping, treat `high-load` as a query modifier, not automatically a Value;
- `loadStatus is high-load` → `loadStatus` is a Property and `high-load` is a Value;
- `during the 2024 Beijing Exhibition` → `2024` and `Beijing` are contextual modifiers, not Values by default;
- `users whose region is Tokyo` → `region` is a Property and `Tokyo` is a Value.

A Value is a business/property/instance value, not every adjective, location, or time expression.

## 5. Relationship and Condition Boundary

1. Do not output Relationship or RelationshipProperty.
2. In path/relation queries, only real business entities become ObjectTypes; metrics/dimensions remain Properties.
3. Expert relation/path hints in `SearchContext` are only context for later graph planning.
4. Do not translate continuous comparisons, date ranges, aggregation, or sorting into ValueHint, Operator, SQL, OQL, or Cypher in this stage.

## 6. Deduplication and Consistency

1. Keep one record for the same ObjectType and merge its Properties/Values.
2. Deduplicate Properties while preserving first-appearance order.
3. Deduplicate Values by `Property(if present) + original Value`.
4. Same-named Properties under different ObjectTypes must remain separate.
5. If one Value has multiple plausible owners and cannot be disambiguated now, prefer one value-only hint rather than duplicating it under guessed ObjectTypes.
6. Do not add objects, properties, or values not expressed by the user. `SearchContext` assists interpretation only.

## 7. Mandatory Pre-output Validation

Before emitting JSON, verify:

1. Top-level field is only `extractedEntities`.
2. Each entity contains only `ObjectType / Properties / Values`.
3. No entity has top-level Properties without ObjectType.
4. Explicit discrete business lookup/filter values have not been omitted.
5. Dates, numeric comparisons, and aggregation words were not incorrectly put into Values.
6. No ObjectType/Property was guessed from identifier shape.
7. No Enum/Instance classification was produced.
8. Every `ValueHint.Property` has actual evidence.
9. Values preserve the user's original expression.
10. The output is directly parseable JSON with no explanation text.

# Examples

## Example 1
Input: `Check the uplink rate and alarm information for 5G base stations during the 2024 Beijing Exhibition.`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "Exhibition",
      "Properties": [],
      "Values": []
    },
    {
      "ObjectType": "5G Base Station",
      "Properties": ["Uplink Rate", "Alarm Information"],
      "Values": []
    }
  ]
}

## Example 2
Input: `Query Accounts where accountStatus is active and customerLevel is VIP.`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "Account",
      "Properties": ["accountStatus", "customerLevel"],
      "Values": [
        {
          "Property": "accountStatus",
          "Value": "active"
        },
        {
          "Property": "customerLevel",
          "Value": "VIP"
        }
      ]
    }
  ]
}

## Example 3
Input: `Find alarms related to 12JKS0885_IN_RSNM_KALIBATA3_MC.`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "Alarm",
      "Properties": [],
      "Values": []
    },
    {
      "Values": [
        {
          "Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"
        }
      ]
    }
  ]
}

## Example 4
Input: `WhatsApp application QoE on July 21.`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "WhatsApp Application",
      "Properties": ["QoE", "Time"],
      "Values": []
    }
  ]
}

## Example 5
Input: `Query cargo ships with ship height between 10 and 30 meters.`

Output:
{
  "extractedEntities": [
    {
      "ObjectType": "Cargo Ship",
      "Properties": ["Ship Height"],
      "Values": []
    }
  ]
}

## Example 6
Input: `Hello, how is the weather today?`

Output:
{"extractedEntities": []}

# Task
SearchContext:

Input:

Output:
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

## 13. 最终设计决策

1. 实体提取是本体子图检索的第 ① 步，输出只描述对象、属性和值；
2. `ExtractedEntity` 顶层只保留 `ObjectType`、`Properties`、`Values`；
3. `Properties` 必须保持与 ObjectType 的从属关系；
4. `Values` 使用统一 `ValueHint`，NER 不区分 Enum/Instance；
5. Value 的真实类型、Property/ObjectType 归属由 Entity Linking 根据索引命中记录确定；
6. 归属未知时允许 value-only，禁止按编码形态猜测对象类型；
7. Relationship 不在实体提取阶段建模，由子图策略从本体拓扑中发现；
8. 专家关系路径通过 `searchContext` 传给后续路径规划；
9. 比较、时间、聚合等查询语义保留在原始 `query`；
10. 该结构直接生成 Entity Linking Semantic Units，与主方案中的本体对象/枚举元素/实例元素 6 路召回衔接。
