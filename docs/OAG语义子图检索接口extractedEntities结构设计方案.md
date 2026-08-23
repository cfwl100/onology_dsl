# OAG 本体子图语义检索接口 extractedEntities / 实体提取设计方案

> 文档版本：V2.4  
> 更新日期：2026-08-23  
> 接口版本：v2  
> 上位方案：[OAG 本体锚点语义检索与向量索引设计方案](./OAG本体锚点语义检索与向量索引设计方案.md)

---

## 1. 文档目的

本文定义本体子图检索第 ① 步“实体提取（Entity Extraction）”的输入、输出和约束，并作为 `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search` 的 `extractedEntities` 正式结构规范。

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

## 12. 最终设计决策

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
