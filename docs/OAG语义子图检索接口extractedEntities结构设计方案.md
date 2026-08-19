# OAG 本体子图语义检索接口 v2 设计规范

> 文档版本：V2.2  
> 更新日期：2026-08-19  
> 接口版本：v2  
> 参考：[OAG 本体锚点语义检索与向量索引设计方案](./OAG本体锚点语义检索与向量索引设计方案.md)

## 1. 文档目的

本文定义 OAG 本体子图语义检索接口 v2 的正式接口契约，包括：

- 接口地址和调用方式；
- Header、Path 和 Body 参数；
- `entityExtractContext` 动态实体提取上下文；
- `extractedEntities` 结构；
- ObjectType、Property、Relationship、RelationshipProperty、Enum Value 和 Instance Value 的检索规则；
- 自适应检索与子图扩展策略；
- 成功响应、失败响应和 OpenAPI Schema；
- 旧版 `extractedEntities` 字符串结构的兼容策略。

## 2. 接口概述

### 2.1 接口描述

本体子图语义检索接口 v2。接口以自然语言问题 `query`、业务侧提取好的实体 `extractedEntities`，或者两者的组合作为检索输入，在指定本体中检索语义相关元素并构建本体子图。

当只传递 `query` 时，OAG 可以结合可选的 `entityExtractContext`，从自然语言问题中提取 ObjectType、Property、Relationship、RelationshipProperty、Enum Value 和 Instance Value 等语义提示。

当传递 `extractedEntities` 时，OAG 使用业务 Skill 根据原始问题和专家查询路径生成的结构化提示查找种子节点、枚举值和实例值，并按照指定策略构建本体子图。

返回结果包括：

```text
ObjectType
Property
Relationship
RelationshipProperty
Function
Action
命中的 Enum Value / Instance Value 语义结果
```

### 2.2 能力边界

接口负责：

1. 自然语言语义提取或结构化实体接收；
2. 种子节点、枚举值和实例值检索；
3. 关键词、向量或混合召回；
4. 检索结果向 ObjectType/Property 种子节点投影；
5. `minimal`、`khop` 或 `component` 子图构建；
6. 使用业务动态注入的 few-shot、专家子图和领域术语辅助实体提取；
7. 按请求扩展 Function 和 Action。

接口不负责：

1. 将“超过 200 元”“本月”等条件转换为底层查询表达式；
2. 执行 OQL、SQL、Cypher 或数据源查询；
3. 由业务侧提供或推断本体内部 ID；
4. 索引数据导入、更新或删除。

## 3. 接口基本信息

| 项目 | 定义 |
|---|---|
| 接口名称 | 本体子图语义检索接口 v2 |
| Method | `POST` |
| Content-Type | `application/json` |
| 规范 URI | `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search` |
| 成功 HTTP 状态码 | `200` |

### 3.1 URI 规范化说明

原始接口描述中的 URL 为：

```text
/v2/onto-retrieval/subgraph/semantic-search
```

但同时将 `ontologyId` 定义为必选 Path 参数。Path 参数必须在 URI 中存在对应占位符，因此本规范统一为：

```text
/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search
```

对应 Spring 接口建议为：

```java
@PostMapping("/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search")
```

## 4. 调用模式

接口支持三种输入模式：

| 模式 | query | extractedEntities | entityExtractContext | 处理方式 |
|---|---:|---:|---:|---|
| 自然语言模式 | 有 | 无 | 可选 | OAG 结合 `query` 和提取上下文生成语义提示并检索 |
| 结构化模式 | 无 | 有 | 不生效 | OAG 直接使用业务 Skill 提取结果检索 |
| 组合模式 | 有 | 有 | 可选 | `extractedEntities` 提供专家路径和强类型提示，`query` 和提取上下文用于补充提取、消歧和排序 |

约束：

```text
query 和 extractedEntities 至少一个不为空
```

组合模式为推荐方式。OAG 不使用 `query` 覆盖业务侧明确提供的结构，但可以使用 `query` 完成候选消歧、排序和语义完整性判断。

## 5. 请求参数

### 5.1 Header 和 Path 参数

| 参数名称 | 参数位置 | 必选 | 数据类型 | 默认值 | 约束 | 说明 |
|---|---|---:|---|---|---|---|
| `tenantId` | header | 是 | String | 无 | 1～256 字符 | 租户 ID |
| `traceId` | header | 否 | String | 无 | 1～256 字符 | 调用链 Trace ID；未传时可由服务生成 |
| `ontologyId` | path | 是 | String | 无 | 1～256 字符 | 本体 ID |

### 5.2 Body 参数

| 参数名称 | 必选 | 数据类型 | 默认值 | 约束 | 说明 |
|---|---:|---|---|---|---|
| `query` | 否 | String | 无 | 1～1024 字符 | 自然语言问题；与 `extractedEntities` 至少一个不为空 |
| `entityExtractContext` | 否 | String | 无 | 建议 1～32768 字符 | 实体提取上下文；业务可动态注入 few-shot、专家查询路径、本体子图、领域术语和其他提取提示；仅在 OAG 执行或补充实体提取时生效 |
| `extractedEntities` | 否 | `Array<ExtractedEntity>` | 无 | 非空时 `minItems: 1` | 业务 Skill 根据原始问题和专家查询路径生成的结构化检索提示；与 `query` 至少一个不为空 |
| `adaptiveRetrieval` | 否 | Integer | `1` | `0` 或 `1` | 是否启用自适应检索 |
| `seedRetrievalMode` | 否 | String | `vector` | `vector`、`keyword`、`hybrid` | 种子节点及其语义证据检索模式 |
| `similarityThreshold` | 否 | Double | `0.6` | 0～1 | 向量相似度阈值，仅对 `vector` 和 `hybrid` 有效 |
| `topk` | 否 | Integer | `3` | `minimum: 1` | 相似度阈值内每个语义单元保留的前 k 个候选 |
| `graphExpansionStrategy` | 否 | String | `minimal` | `minimal`、`khop`、`component` | 子图扩展策略 |
| `hopLimit` | 否 | Integer | `3` | `minimum: 1` | `khop` 策略下的最大扩散深度 |
| `includeFunctions` | 否 | Integer | `0` | `0` 或 `1` | 是否返回相关 Function |
| `includeActions` | 否 | Integer | `0` | `0` 或 `1` | 是否返回相关 Action |

### 5.3 废弃参数

`includeDimAndIndicator` 不属于 v2 有效请求 Schema，不在新接口中继续定义。

### 5.4 entityExtractContext 使用规则

`entityExtractContext` 是实体提取阶段的业务上下文，可以包含：

```text
领域 few-shot 示例
专家查询路径
本体子图文本或 JSON
领域对象、属性和关系术语
业务缩写和黑话说明
实体提取补充提示
```

处理边界：

1. 仅在 OAG 需要从 `query` 执行或补充实体提取时使用；
2. 不单独满足“`query` 和 `extractedEntities` 至少一个不为空”的校验条件；
3. 不直接作为种子节点、枚举值或实例值的检索 Query；
4. 不覆盖接口 Schema、系统级实体提取规则和服务安全约束；
5. 业务传入内容应被视为不可信上下文，并执行长度限制和输入规范化；
6. 结构化模式下如果 OAG 不再执行实体提取，该字段不生效。

## 6. extractedEntities 结构

### 6.1 设计原则

业务 Skill 根据用户问题和专家经验通常只能获得对象、属性、关系和值的业务名称，无法可靠获得本体内部 ID。因此请求结构只表达业务语义，不包含 ObjectType、Property、Relationship 或目标对象的 ID 字段。

`extractedEntities` 不承载比较操作、时间范围和聚合操作，也不定义 `OriginalText`、`Operator` 或 `ConstraintHint`。

业务问题中的完整条件继续保留在 `query` 中。

当问题中只出现实例值、但没有足够信息判断其 ObjectType 或 Property 归属时，允许生成 value-only 的 `ExtractedEntity`。OAG 必须先跨 ObjectType/Property 检索该值，命中后再使用索引记录补齐真实归属，禁止根据值的外形猜测对象类型。

### 6.2 ExtractedEntity

`Relationships` 与 `ObjectType`、`Properties` 平级。关系记录必须显式包含源 ObjectType 和目标 ObjectType，不再依赖所在 `ExtractedEntity` 隐式推断源端。

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `ObjectType` | 否 | String | 无 | 对象类型名称、显示名、同义词或业务术语；仅包含未绑定 Enum/Instance Value 时可以省略 |
| `Properties` | 否 | `Array<String>` | `[]` | 当前对象相关的 Property 名称列表；存在该字段时必须同时存在 `ObjectType` |
| `Relationships` | 否 | `Array<RelationshipHint>` | `[]` | 与 ObjectType 平级的 Relationship 路径提示；每条记录显式声明源、目标 ObjectType |
| `EnumValues` | 否 | `Array<EnumValueHint>` | `[]` | 枚举值提示；ObjectType/Property 归属未知时允许单独存在 |
| `InstanceValues` | 否 | `Array<InstanceValueHint>` | `[]` | 实例列值提示；ObjectType/Property 归属未知时允许单独存在 |

每个 `ExtractedEntity` 至少包含以下一种非空内容：

```text
ObjectType
Relationships
EnumValues
InstanceValues
```

### 6.3 RelationshipHint

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `Relationship` | 是 | String | 无 | 关系名称、显示名、同义词或业务术语 |
| `SourceObjectType` | 是 | String | 无 | 关系源 ObjectType 名称 |
| `TargetObjectType` | 是 | String | 无 | 关系目标 ObjectType 名称 |
| `Direction` | 否 | String | `OUT` | 可取 `OUT`、`IN`、`BOTH` |
| `Properties` | 否 | `Array<String>` | `[]` | 需要检索或返回的 RelationshipProperty 名称列表 |

### 6.4 EnumValueHint

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `Property` | 否 | String | 无 | 枚举值所属 Property 名称；无法确定时可以省略 |
| `Value` | 是 | String | 无 | 枚举值、显示名、同义词或用户使用的业务表达 |

OAG 使用 `Value` 检索 Enum Value 的：

```text
value
name
display
description
synonyms
```

命中 Enum Value 后，由 OAG 根据索引记录的真实归属投影为 Property 和 ObjectType 种子节点。业务侧不提供该归属的内部 ID。

### 6.5 InstanceValueHint

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `Property` | 否 | String | 无 | 实例值所属 Property 名称；无法确定时可以省略 |
| `Value` | 是 | String | 无 | 实例数据中适合语义检索的真实业务列值 |

适合放入 `InstanceValues`：

```text
VIP
东京
华东区域
钻石客户
产品名称
品牌名称
```

默认不应由通用规则自动放入 `InstanceValues`：

```text
连续数值
日期和时间戳
手机号
UUID
纯技术主键
高随机编码
```

上述不适合向量化的内容继续保留在原始 `query` 中。

如果业务上下文明确确认某个编码是需要检索的实例值，则可以放入 `InstanceValues`，但应优先使用 `keyword` 或 `hybrid` 模式进行 Exact/关键词匹配，不依赖编码字符串的向量语义。业务明确标注优先于通用形态判断，但不能据此猜测该值所属的 ObjectType 或 Property。

### 6.6 通用结构示例

```json
{
  "extractedEntities": [
    {
      "ObjectType": "ObjectType1",
      "Properties": [
        "Property1",
        "Property2"
      ],
      "Relationships": [
        {
          "Relationship": "RELATIONSHIP_NAME",
          "SourceObjectType": "ObjectType1",
          "Direction": "OUT",
          "TargetObjectType": "ObjectType2",
          "Properties": [
            "RelationshipProperty1"
          ]
        }
      ],
      "EnumValues": [
        {
          "Property": "EnumProperty",
          "Value": "EnumValue"
        }
      ],
      "InstanceValues": [
        {
          "Property": "InstanceProperty",
          "Value": "InstanceValue"
        }
      ]
    }
  ]
}
```

## 7. 检索参数语义

### 7.1 adaptiveRetrieval

| 值 | 语义 |
|---:|---|
| `0` | 不启用自适应检索，始终按 `seedRetrievalMode` 和 `graphExpansionStrategy` 检索 |
| `1` | 启用自适应检索 |

当 `adaptiveRetrieval=1`：

```text
本体规模 <= 自适应阈值
  → 返回全量本体核心子图
  → 不再执行基于种子节点的图扩展

本体规模 > 自适应阈值
  → 按 seedRetrievalMode 检索候选
  → 按 graphExpansionStrategy 构建子图
```

默认阈值为 100 个节点，统计口径为：

```text
ObjectType + Property + Relationship + RelationshipProperty
```

阈值属于服务端配置，不由业务请求动态修改。

### 7.2 seedRetrievalMode

| 值 | 处理方式 |
|---|---|
| `vector` | 使用向量索引执行语义召回 |
| `keyword` | 使用关键词、Exact 或 BM25 召回 |
| `hybrid` | 同时执行关键词和向量召回，并进行融合排序 |

Enum Value 和 Instance Value 是种子节点的语义证据：OAG 先在对应索引中检索值，再投影到所属 Property/ObjectType 种子节点。因此 `seedRetrievalMode` 同时决定这些语义证据使用的检索通道。

### 7.3 similarityThreshold

`similarityThreshold` 只过滤向量召回结果：

```text
vector
  → 生效

hybrid
  → 对其中的向量通道生效

keyword
  → 不生效
```

关键词 Exact 命中不应被向量阈值过滤。

### 7.4 topk

`topk` 表示相似度阈值内每个语义单元最终保留的前 k 个候选，不等同于底层每个检索通道的内部召回数量。OAG 可以使用更大的内部 TopK 完成融合和精排，最终输出数量受 `topk` 控制。

### 7.5 graphExpansionStrategy

| 策略 | 语义 |
|---|---|
| `minimal` | 构建覆盖全部种子节点的最小连通子图 |
| `khop` | 以多个种子节点为起点执行多源 BFS；最大深度由 `hopLimit` 控制 |
| `component` | 返回种子节点所属的全连通分量 |

`hopLimit` 仅在 `graphExpansionStrategy=khop` 时参与路径深度控制，其他策略可以接收该字段但不使用。

### 7.6 includeFunctions 和 includeActions

在本体核心子图构建完成后：

```text
includeFunctions = 1
  → 扩展与核心子图相关的 Function

includeActions = 1
  → 扩展与核心子图相关的 Action
```

Function 和 Action 默认不作为主检索种子参与路径算法。

## 8. 业务专家经验请求样例

### 8.1 用户问题

> 本月个人客户中，信用额度超过 200 元的账户总数是多少？

### 8.2 查询路径

```text
IndividualCustomer ──[OWNS]──→ PayRelation ──[BELONGS_TO]──→ Account ──[HAS]──→ CreditLimitInstance

IndividualCustomer: id
PayRelation: objectId → accountId
Account: accountId
CreditLimitInstance: accountId、本月、initialAmount > 200
```

### 8.3 HTTP 请求

```http
POST /v2/onto-retrieval/dtmi.ontology.example.1/subgraph/semantic-search HTTP/1.1
Content-Type: application/json
tenantId: tenant-a
traceId: 8b8ce86f0f934b0d
```

```json
{
  "query": "本月个人客户中，信用额度超过200元的账户总数是多少？",
  "entityExtractContext": "专家查询路径：IndividualCustomer通过OWNS关联PayRelation，PayRelation通过BELONGS_TO关联Account，Account通过HAS关联CreditLimitInstance。",
  "extractedEntities": [
    {
      "ObjectType": "IndividualCustomer",
      "Properties": [
        "id"
      ],
      "Relationships": [
        {
          "Relationship": "OWNS",
          "SourceObjectType": "IndividualCustomer",
          "Direction": "OUT",
          "TargetObjectType": "PayRelation",
          "Properties": []
        }
      ],
      "EnumValues": [],
      "InstanceValues": []
    },
    {
      "ObjectType": "PayRelation",
      "Properties": [
        "objectId",
        "accountId"
      ],
      "Relationships": [
        {
          "Relationship": "BELONGS_TO",
          "SourceObjectType": "PayRelation",
          "Direction": "OUT",
          "TargetObjectType": "Account",
          "Properties": []
        }
      ],
      "EnumValues": [],
      "InstanceValues": []
    },
    {
      "ObjectType": "Account",
      "Properties": [
        "accountId"
      ],
      "Relationships": [
        {
          "Relationship": "HAS",
          "SourceObjectType": "Account",
          "Direction": "OUT",
          "TargetObjectType": "CreditLimitInstance",
          "Properties": []
        }
      ],
      "EnumValues": [],
      "InstanceValues": []
    },
    {
      "ObjectType": "CreditLimitInstance",
      "Properties": [
        "accountId",
        "initialAmount"
      ],
      "Relationships": [],
      "EnumValues": [],
      "InstanceValues": []
    }
  ],
  "adaptiveRetrieval": 0,
  "seedRetrievalMode": "vector",
  "similarityThreshold": 0.6,
  "topk": 3,
  "graphExpansionStrategy": "minimal",
  "hopLimit": 3,
  "includeFunctions": 0,
  "includeActions": 0
}
```

### 8.4 样例说明

该问题中的 `EnumValues` 和 `InstanceValues` 为空是正确的：

1. “个人客户”已由专家路径明确为 `IndividualCustomer`，不是枚举值。
2. `CreditLimitInstance` 是 ObjectType，不是实例列值。
3. “200”是连续数值，不进入 Instance Value 向量索引。
4. “本月”是相对时间，不进入 Instance Value 向量索引。
5. “超过”和“总数”属于条件与聚合语义，由原始 `query` 保留。

OAG 根据结构化提示检索相关 ObjectType、Property 和 Relationship，构建支持后续查询生成的本体子图。

## 9. EnumValues 和 InstanceValues 请求样例

```json
{
  "query": "查询在用状态的VIP客户账户",
  "extractedEntities": [
    {
      "ObjectType": "Account",
      "Properties": [
        "accountStatus",
        "customerLevel"
      ],
      "Relationships": [],
      "EnumValues": [
        {
          "Property": "accountStatus",
          "Value": "在用"
        }
      ],
      "InstanceValues": [
        {
          "Property": "customerLevel",
          "Value": "VIP"
        }
      ]
    }
  ],
  "seedRetrievalMode": "hybrid"
}
```

OAG 对该请求分别执行：

```text
Account / accountStatus / customerLevel
  → 种子节点索引

在用
  → Enum Value 索引

VIP
  → Instance Value 索引
```

Enum/Instance 命中后投影为 Property 和 ObjectType，再参与本体子图构建。

## 10. entityExtractContext 与实体提取示例

实体提取结果必须保留 ObjectType 与 Property 的从属关系：Property 放在所属 ObjectType 对应的 `Properties` 数组中，禁止把不同对象的 Property 合并成无归属的全局列表。

以下示例统一使用接口 Schema 规定的 `ObjectType`、`Properties`、`Relationships`、`EnumValues` 和 `InstanceValues` 字段名。可选空数组可以省略，但完整示例中显式保留，便于说明结构层级。

### 10.1 WhatsApp 应用体验质量

#### Query

```text
WhatsApp应用 7月21日的体验质量
```

#### entityExtractContext 示例

```text
应用体验质量问数场景：
- “WhatsApp应用”识别为 ObjectType。
- “体验质量”和“时间”识别为 WhatsApp应用 的 Property。
- 日期值保留在原始 query 中，不作为 Instance Value 进行向量检索。
```

#### 最新实体提取结果

```json
{
  "extractedEntities": [
    {
      "ObjectType": "WhatsApp应用",
      "Properties": [
        "体验质量",
        "时间"
      ],
      "Relationships": [],
      "EnumValues": [],
      "InstanceValues": []
    }
  ]
}
```

从属关系：

```text
WhatsApp应用
  ├─ 体验质量
  └─ 时间
```

“7月21日”是时间条件，继续保留在 `query` 中，不进入 `InstanceValues`。

### 10.2 未绑定实例值的活跃业务影响告警

#### Query

```text
show active service affecting alarm for 12JKS0885_IN_RSNM_KALIBATA3_MC with TICKETID and time occurred
```

#### entityExtractContext 示例

```text
告警查询场景：
- alarm 对应 ALARM。
- TICKETID 和 time occurred 分别映射为 ALARM 的“告警TICKET ID”和“告警发生时间”属性。
- 12JKS0885_IN_RSNM_KALIBATA3_MC 是需要检索的 Instance Value。
- 问题中没有 Site、基站或 nativeId 信息，不得根据实例值的编码形态推断 ObjectType 或 Property。
- 未提供确定的本体关系名称时，不创造 Relationship。
```

#### 最新实体提取结果

```json
{
  "extractedEntities": [
    {
      "ObjectType": "ALARM",
      "Properties": [
        "告警TICKET ID",
        "告警发生时间"
      ],
      "Relationships": [],
      "EnumValues": [],
      "InstanceValues": []
    },
    {
      "Relationships": [],
      "EnumValues": [],
      "InstanceValues": [
        {
          "Value": "12JKS0885_IN_RSNM_KALIBATA3_MC"
        }
      ]
    }
  ]
}
```

从属关系：

```text
ALARM
  ├─ 告警TICKET ID
  └─ 告警发生时间

未绑定 Instance Value
  └─ 12JKS0885_IN_RSNM_KALIBATA3_MC
```

该结果不包含 `Site`、`BaseStation`、`nativeId` 或其他基站信息。`12JKS0885_IN_RSNM_KALIBATA3_MC` 作为未绑定 Instance Value 进入检索，由 OAG 跨 ObjectType/Property 查找真实归属；命中之前不得人为补充所属对象或属性。

该值具有明显的编码形态，推荐：

```json
{
  "seedRetrievalMode": "hybrid"
}
```

其中 Exact/关键词通道优先保证编码值准确匹配，向量通道只作为补充召回。

## 11. OAG 处理流程

### 11.1 输入处理

1. 校验 Header、Path 和 Body 参数；
2. 校验 `query` 和 `extractedEntities` 至少一个不为空；
3. 当需要实体提取时，将 `entityExtractContext` 作为受限的业务上下文与 `query` 一起输入实体提取组件；
4. 对所有名称和值执行 trim、Unicode Normalize 和去空；
5. 对重复 ObjectType、Property、Relationship、Enum Value 和 Instance Value 做规范化去重；
6. 根据调用模式生成语义检索单元。

### 11.2 检索路由

| 输入元素 | 检索对象 | 处理方式 |
|---|---|---|
| `ObjectType` | ObjectType 种子节点 | 检索 `name/display/description/synonyms` |
| `Properties` | Property 种子节点 | 检索 `name/display/description/synonyms` |
| `Relationships` | Relationship 和拓扑 | 解析关系名称，用于路径校验、候选排序和子图扩展 |
| `RelationshipHint.Properties` | RelationshipProperty | 检索关系属性名称，并保留在命中边的元数据中 |
| `EnumValues` | Enum Value | 检索 `value/name/display/description/synonyms` |
| `InstanceValues` | Instance Value | 使用真实业务 `value` 检索实例值索引 |

### 11.3 Property 上下文

当 Enum Value 或 Instance Value 中存在 `Property`：

1. 同时检索 Property 名称和值；
2. 将 Property 名称作为候选分组和精排上下文；
3. 不把业务名称直接当作内部 ID；
4. 使用索引命中记录的真实归属完成种子节点投影。

当 `Property` 不存在但 `ObjectType` 已知时，OAG 在该 ObjectType 的相关 Property 范围内检索该值。

当 `ObjectType` 和 `Property` 都不存在时，该值属于未绑定值。OAG 应跨 ObjectType/Property 检索 Enum/Instance 索引，命中后再根据索引记录补齐真实归属。对于编码型值，优先使用 Exact/关键词通道，禁止根据编码格式推断 Site、基站或其他对象类型。

### 11.4 关系路径

`Relationships` 是专家路径提示，不是已经解析的本体关系。OAG 应：

1. 按关系名称、显示名或同义词解析 Relationship；
2. 使用 `SourceObjectType`、`Direction` 和 `TargetObjectType` 校验关系候选；
3. 使用 `Properties` 解析 RelationshipProperty；
4. 将正确关系作为子图构建路径提示；
5. 未匹配时不创造关系，将其记录为未解析提示并按配置降级。

### 11.5 种子节点投影与子图构建

```text
ObjectType / Property 命中
  → 直接形成种子节点

Enum Value / Instance Value 命中
  → 投影到所属 Property
  → 补齐所属 ObjectType
  → 形成图构建种子节点

全部种子节点
  → minimal / khop / component
  → 本体核心子图
  → Function / Action 扩展
```

## 12. 响应参数

### 12.1 顶层响应

| 参数名称 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `resultCode` | 是 | String | 无 | 业务响应码；成功返回 `200`，失败返回具体错误码 |
| `resultMessage` | 是 | String | 无 | 成功返回 `success`，失败返回错误信息 |
| `result` | 是 | Object | 无 | 最终语义检索结果、本体子图和执行元数据；失败时可以为 `null` |

### 12.2 result 结构

| 字段 | 数据类型 | 说明 |
|---|---|---|
| `retrievalResults` | Array | 完整语义命中结果，包括 Seed、Enum Value 和 Instance Value |
| `seedNodes` | Array | 从语义命中结果投影得到的 ObjectType/Property 图构建种子节点 |
| `nodes` | Array | 本体子图节点，主要承载 ObjectType 和 Property |
| `edges` | Array | 本体子图关系；RelationshipProperty 作为关系元数据返回 |
| `semanticExtensions` | Object | 命中值的同义词、枚举域等可选语义上下文 |
| `capabilityExtensions` | Object | 按请求返回的 Function 和 Action |
| `metadata` | Object | 检索模式、图策略、连通性、截断和未解析信息 |

返回元素映射：

| 业务元素 | 响应位置 |
|---|---|
| ObjectType、Property | `seedNodes`、`nodes`、`retrievalResults` |
| Relationship、RelationshipProperty | `edges` |
| Enum Value、Instance Value | `retrievalResults`、`semanticExtensions` |
| Function、Action | `capabilityExtensions` |

### 12.3 成功响应示例

```json
{
  "resultCode": "200",
  "resultMessage": "success",
  "result": {
    "retrievalResults": [],
    "seedNodes": [],
    "nodes": [],
    "edges": [],
    "semanticExtensions": {},
    "capabilityExtensions": {
      "functions": [],
      "actions": []
    },
    "metadata": {
      "retrievalMode": "vector",
      "graphStrategy": "minimal",
      "connected": true,
      "truncated": false,
      "unresolvedSemanticUnits": [],
      "unconnectedSeedNodeIds": []
    }
  }
}
```

`retrievalResults` 是完整语义命中的权威字段；`seedNodes`、`nodes` 和 `edges` 表达图构建结果。

## 13. 错误处理

### 13.1 HTTP 状态码

| HTTP 状态码 | 场景 |
|---:|---|
| `200` | 检索成功，包括合法的空匹配结果 |
| `400` | 参数格式错误、枚举值非法、`query` 和 `extractedEntities` 同时为空 |
| `404` | 指定租户或本体不存在 |
| `429` | 服务限流或并发超过限制 |
| `500` | 服务内部错误 |
| `503` | 向量库、关键词索引或图存储暂不可用 |

### 13.2 失败响应示例

```json
{
  "resultCode": "INVALID_REQUEST",
  "resultMessage": "query and extractedEntities cannot both be empty",
  "result": null
}
```

## 14. OpenAPI 3.0.3 定义

```yaml
openapi: 3.0.3
info:
  title: OAG Ontology Subgraph Semantic Search API
  version: 2.0.0

paths:
  /v2/onto-retrieval/{ontologyId}/subgraph/semantic-search:
    post:
      operationId: semanticSearchSubgraphV2
      summary: 本体子图语义检索接口 v2
      parameters:
        - $ref: '#/components/parameters/TenantId'
        - $ref: '#/components/parameters/TraceId'
        - $ref: '#/components/parameters/OntologyId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SemanticSearchRequest'
      responses:
        '200':
          description: 检索成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SemanticSearchResponse'
        '400':
          description: 请求参数错误
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SemanticSearchResponse'
        '404':
          description: 本体不存在
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SemanticSearchResponse'
        '429':
          description: 请求被限流
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SemanticSearchResponse'
        '500':
          description: 服务内部错误
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SemanticSearchResponse'
        '503':
          description: 依赖服务暂不可用
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SemanticSearchResponse'

components:
  parameters:
    TenantId:
      name: tenantId
      in: header
      required: true
      schema:
        type: string
        minLength: 1
        maxLength: 256
    TraceId:
      name: traceId
      in: header
      required: false
      schema:
        type: string
        minLength: 1
        maxLength: 256
    OntologyId:
      name: ontologyId
      in: path
      required: true
      schema:
        type: string
        minLength: 1
        maxLength: 256

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
        entityExtractContext:
          type: string
          minLength: 1
          maxLength: 32768
          description: 业务动态注入的实体提取上下文，可包含 few-shot、专家查询路径、本体子图和领域术语
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
          format: double
          default: 0.6
          minimum: 0
          maximum: 1
        topk:
          type: integer
          default: 3
          minimum: 1
        graphExpansionStrategy:
          type: string
          default: minimal
          enum: [minimal, khop, component]
        hopLimit:
          type: integer
          default: 3
          minimum: 1
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
      anyOf:
        - required: [ObjectType]
        - required: [Relationships]
          properties:
            Relationships:
              minItems: 1
        - required: [EnumValues]
          properties:
            EnumValues:
              minItems: 1
        - required: [InstanceValues]
          properties:
            InstanceValues:
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
        Relationships:
          type: array
          default: []
          items:
            $ref: '#/components/schemas/RelationshipHint'
        EnumValues:
          type: array
          default: []
          items:
            $ref: '#/components/schemas/EnumValueHint'
        InstanceValues:
          type: array
          default: []
          items:
            $ref: '#/components/schemas/InstanceValueHint'

    RelationshipHint:
      type: object
      required: [Relationship, SourceObjectType, TargetObjectType]
      properties:
        Relationship:
          type: string
          minLength: 1
        SourceObjectType:
          type: string
          minLength: 1
        Direction:
          type: string
          default: OUT
          enum: [OUT, IN, BOTH]
        TargetObjectType:
          type: string
          minLength: 1
        Properties:
          type: array
          default: []
          items:
            type: string
            minLength: 1

    EnumValueHint:
      type: object
      required: [Value]
      properties:
        Property:
          type: string
          minLength: 1
        Value:
          type: string
          minLength: 1

    InstanceValueHint:
      type: object
      required: [Value]
      properties:
        Property:
          type: string
          minLength: 1
        Value:
          type: string
          minLength: 1

    SemanticSearchResponse:
      type: object
      required: [resultCode, resultMessage, result]
      properties:
        resultCode:
          type: string
        resultMessage:
          type: string
        result:
          type: object
          nullable: true
          allOf:
            - $ref: '#/components/schemas/SemanticSearchResult'

    SemanticSearchResult:
      type: object
      properties:
        retrievalResults:
          type: array
          items:
            type: object
            additionalProperties: true
        seedNodes:
          type: array
          items:
            type: object
            additionalProperties: true
        nodes:
          type: array
          items:
            type: object
            additionalProperties: true
        edges:
          type: array
          items:
            type: object
            additionalProperties: true
        semanticExtensions:
          type: object
          additionalProperties: true
        capabilityExtensions:
          type: object
          properties:
            functions:
              type: array
              items:
                type: object
                additionalProperties: true
            actions:
              type: array
              items:
                type: object
                additionalProperties: true
        metadata:
          type: object
          additionalProperties: true
```

## 15. 校验规则

1. `tenantId` 和 `ontologyId` 必须存在且满足长度要求。
2. `query` 和 `extractedEntities` 至少一个不为空。
3. `entityExtractContext` 不能单独满足第 2 条校验；非空时长度不超过 32768 字符。
4. `query` 去除首尾空白后长度必须为 1～1024。
5. 每个 `ExtractedEntity` 至少包含非空 `ObjectType`、`Relationships`、`EnumValues` 或 `InstanceValues` 中的一种。
6. 出现 `Properties` 时必须同时提供 `ObjectType`，Property 必须归属于该 ObjectType。
7. 每个 Relationship 必须包含 `Relationship`、`SourceObjectType` 和 `TargetObjectType`。
8. Relationship 所在实体如果同时提供 `ObjectType`，该值应与 `SourceObjectType` 一致；源和目标对象应出现在本次 `extractedEntities` 的 ObjectType 列表中。
9. Enum Value 和 Instance Value 必须包含非空 `Value`。
10. Enum/Instance Value 未提供 ObjectType 和 Property 时，按未绑定值进行跨 ObjectType/Property 检索，不得通过值的格式猜测归属。
11. `similarityThreshold` 必须在 0～1 之间。
12. `topk` 和 `hopLimit` 必须大于等于 1。
13. 所有枚举型参数必须使用定义值。
14. 所有输入名称和值在检索前统一执行 trim、Unicode Normalize 和规范化去重。
15. 业务输入只作为检索提示，不能直接作为本体内部 ID 使用。

## 16. 兼容策略

### 16.1 原有结构兼容

以下已有结构仍是合法的 v2 请求：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "ObjectType1",
      "Properties": [
        "Property1"
      ]
    }
  ]
}
```

`Relationships`、`EnumValues` 和 `InstanceValues` 均为可选字段，默认空数组。

### 16.2 字符串形式迁移

原接口文档将 `extractedEntities` 标注为 String，但示例实际为 JSON 对象。v2 正式 Schema 使用 `Array<ExtractedEntity>`。

如果现网调用方将整个结构作为转义 JSON 字符串传入，建议服务端在迁移期同时支持：

```text
结构化 Array<ExtractedEntity>
字符串形式的 legacy extractedEntities
```

迁移完成后废弃字符串形式，避免二次 JSON 解析和类型不一致。

## 17. 最终设计决策

1. 规范 URI 为 `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search`。
2. `query` 和 `extractedEntities` 至少一个不为空，推荐同时传递。
3. `extractedEntities` 正式类型为 `Array<ExtractedEntity>`，不再定义为 String。
4. 业务侧只传递对象、属性、关系和值的业务名称，不传递本体内部 ID。
5. `Relationships` 与 `ObjectType/Properties` 平级，每条关系显式声明 `SourceObjectType` 和 `TargetObjectType`。
6. `Relationships` 支持方向和 RelationshipProperty 名称列表。
7. 新增 `entityExtractContext`，用于业务动态注入 few-shot、专家路径、本体子图和领域术语。
8. 新增 `EnumValues` 和 `InstanceValues`，分别检索枚举值索引和实例值索引。
9. 不定义 `OriginalText`、`Operator` 和 `ConstraintHint`。
10. 比较条件、时间范围、聚合方式和单位继续保留在原始 `query` 中。
11. ObjectType 和 Property 使用嵌套结构表达明确的从属关系。
12. ObjectType/Property 归属未知的 Enum/Instance Value 可以作为 value-only 实体输入，由 OAG 检索后解析归属。
13. 编码型实例值优先使用 `keyword` 或 `hybrid` 模式，不根据编码形态推断对象类型。
14. `adaptiveRetrieval` 默认开启，默认规模阈值为 100。
15. `seedRetrievalMode` 支持 `vector`、`keyword` 和 `hybrid`。
16. `graphExpansionStrategy` 支持 `minimal`、`khop` 和 `component`。
17. `includeFunctions` 和 `includeActions` 默认均为 0。
18. `includeDimAndIndicator` 不属于 v2 有效请求 Schema。
19. 成功响应统一返回 `resultCode/resultMessage/result`。
20. `retrievalResults` 表达完整语义命中，`seedNodes/nodes/edges` 表达本体子图结果。
