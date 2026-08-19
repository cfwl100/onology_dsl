# OAG 本体子图语义检索接口 v2 设计规范

> 文档版本：V2.0  
> 更新日期：2026-08-19  
> 接口版本：v2  
> 参考：[OAG 本体锚点语义检索与向量索引设计方案](./OAG本体锚点语义检索与向量索引设计方案.md)

## 1. 文档目的

本文定义 OAG 本体子图语义检索接口 v2 的正式接口契约，包括：

- 接口地址和调用方式；
- Header、Path 和 Body 参数；
- `extractedEntities` 结构；
- ObjectType、Property、Relationship、RelationshipProperty、Enum Value 和 Instance Value 的检索规则；
- 自适应检索与子图扩展策略；
- 成功响应、失败响应和 OpenAPI Schema；
- 旧版 `extractedEntities` 字符串结构的兼容策略。

## 2. 接口概述

### 2.1 接口描述

本体子图语义检索接口 v2。接口以自然语言问题 `query`、业务侧提取好的实体 `extractedEntities`，或者两者的组合作为检索输入，在指定本体中检索语义相关元素并构建本体子图。

当只传递 `query` 时，OAG 从自然语言问题中提取 ObjectType、Property、Relationship、RelationshipProperty、Enum Value 和 Instance Value 等语义提示。

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
6. 按请求扩展 Function 和 Action。

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

| 模式 | query | extractedEntities | 处理方式 |
|---|---:|---:|---|
| 自然语言模式 | 有 | 无 | OAG 从 `query` 提取语义提示并检索 |
| 结构化模式 | 无 | 有 | OAG 直接使用业务 Skill 提取结果检索 |
| 组合模式 | 有 | 有 | `extractedEntities` 提供专家路径和强类型提示，`query` 提供完整语义上下文 |

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

## 6. extractedEntities 结构

### 6.1 设计原则

业务 Skill 根据用户问题和专家经验通常只能获得对象、属性、关系和值的业务名称，无法可靠获得本体内部 ID。因此请求结构只表达业务语义，不包含 ObjectType、Property、Relationship 或目标对象的 ID 字段。

`extractedEntities` 不承载比较操作、时间范围和聚合操作，也不定义 `OriginalText`、`Operator` 或 `ConstraintHint`。

业务问题中的完整条件继续保留在 `query` 中。

### 6.2 ExtractedEntity

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `ObjectType` | 是 | String | 无 | 对象类型名称、显示名、同义词或业务术语 |
| `Properties` | 否 | `Array<String>` | `[]` | 当前对象相关的 Property 名称列表 |
| `Relationships` | 否 | `Array<RelationshipHint>` | `[]` | 从当前对象出发的 Relationship 路径提示 |
| `EnumValues` | 否 | `Array<EnumValueHint>` | `[]` | 当前对象属性相关的枚举值提示 |
| `InstanceValues` | 否 | `Array<InstanceValueHint>` | `[]` | 当前对象属性相关的实例列值提示 |

### 6.3 RelationshipHint

| 字段 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `Relationship` | 是 | String | 无 | 关系名称、显示名、同义词或业务术语 |
| `Direction` | 否 | String | `OUT` | 可取 `OUT`、`IN`、`BOTH` |
| `TargetObjectType` | 是 | String | 无 | 目标 ObjectType 名称；源 ObjectType 由所属 `ExtractedEntity` 确定 |
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

不应放入 `InstanceValues`：

```text
连续数值
日期和时间戳
手机号
UUID
纯技术主键
高随机编码
```

上述不适合向量化的内容继续保留在原始 `query` 中。

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
  "extractedEntities": [
    {
      "ObjectType": "IndividualCustomer",
      "Properties": [
        "id"
      ],
      "Relationships": [
        {
          "Relationship": "OWNS",
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

## 10. OAG 处理流程

### 10.1 输入处理

1. 校验 Header、Path 和 Body 参数；
2. 校验 `query` 和 `extractedEntities` 至少一个不为空；
3. 对所有名称和值执行 trim、Unicode Normalize 和去空；
4. 对重复 ObjectType、Property、Relationship、Enum Value 和 Instance Value 做规范化去重；
5. 根据调用模式生成语义检索单元。

### 10.2 检索路由

| 输入元素 | 检索对象 | 处理方式 |
|---|---|---|
| `ObjectType` | ObjectType 种子节点 | 检索 `name/display/description/synonyms` |
| `Properties` | Property 种子节点 | 检索 `name/display/description/synonyms` |
| `Relationships` | Relationship 和拓扑 | 解析关系名称，用于路径校验、候选排序和子图扩展 |
| `RelationshipHint.Properties` | RelationshipProperty | 检索关系属性名称，并保留在命中边的元数据中 |
| `EnumValues` | Enum Value | 检索 `value/name/display/description/synonyms` |
| `InstanceValues` | Instance Value | 使用真实业务 `value` 检索实例值索引 |

### 10.3 Property 上下文

当 Enum Value 或 Instance Value 中存在 `Property`：

1. 同时检索 Property 名称和值；
2. 将 Property 名称作为候选分组和精排上下文；
3. 不把业务名称直接当作内部 ID；
4. 使用索引命中记录的真实归属完成种子节点投影。

当 `Property` 不存在时，OAG 可以跨 Property 检索该值，再结合 `query`、ObjectType 和专家关系路径进行消歧。

### 10.4 关系路径

`Relationships` 是专家路径提示，不是已经解析的本体关系。OAG 应：

1. 按关系名称、显示名或同义词解析 Relationship；
2. 使用源 ObjectType、`Direction` 和 `TargetObjectType` 校验关系候选；
3. 使用 `Properties` 解析 RelationshipProperty；
4. 将正确关系作为子图构建路径提示；
5. 未匹配时不创造关系，将其记录为未解析提示并按配置降级。

### 10.5 种子节点投影与子图构建

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

## 11. 响应参数

### 11.1 顶层响应

| 参数名称 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---:|---|---|---|
| `resultCode` | 是 | String | 无 | 业务响应码；成功返回 `200`，失败返回具体错误码 |
| `resultMessage` | 是 | String | 无 | 成功返回 `success`，失败返回错误信息 |
| `result` | 是 | Object | 无 | 最终语义检索结果、本体子图和执行元数据；失败时可以为 `null` |

### 11.2 result 结构

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

### 11.3 成功响应示例

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

## 12. 错误处理

### 12.1 HTTP 状态码

| HTTP 状态码 | 场景 |
|---:|---|
| `200` | 检索成功，包括合法的空匹配结果 |
| `400` | 参数格式错误、枚举值非法、`query` 和 `extractedEntities` 同时为空 |
| `404` | 指定租户或本体不存在 |
| `429` | 服务限流或并发超过限制 |
| `500` | 服务内部错误 |
| `503` | 向量库、关键词索引或图存储暂不可用 |

### 12.2 失败响应示例

```json
{
  "resultCode": "INVALID_REQUEST",
  "resultMessage": "query and extractedEntities cannot both be empty",
  "result": null
}
```

## 13. OpenAPI 3.0.3 定义

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
      required: [ObjectType]
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
      required: [Relationship, TargetObjectType]
      properties:
        Relationship:
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

## 14. 校验规则

1. `tenantId` 和 `ontologyId` 必须存在且满足长度要求。
2. `query` 和 `extractedEntities` 至少一个不为空。
3. `query` 去除首尾空白后长度必须为 1～1024。
4. 每个 `ExtractedEntity` 必须包含非空 `ObjectType`。
5. 每个 Relationship 必须包含 `Relationship` 和 `TargetObjectType`。
6. Enum Value 和 Instance Value 必须包含非空 `Value`。
7. `similarityThreshold` 必须在 0～1 之间。
8. `topk` 和 `hopLimit` 必须大于等于 1。
9. 所有枚举型参数必须使用定义值。
10. 所有输入名称和值在检索前统一执行 trim、Unicode Normalize 和规范化去重。
11. 业务输入只作为检索提示，不能直接作为本体内部 ID 使用。

## 15. 兼容策略

### 15.1 原有结构兼容

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

### 15.2 字符串形式迁移

原接口文档将 `extractedEntities` 标注为 String，但示例实际为 JSON 对象。v2 正式 Schema 使用 `Array<ExtractedEntity>`。

如果现网调用方将整个结构作为转义 JSON 字符串传入，建议服务端在迁移期同时支持：

```text
结构化 Array<ExtractedEntity>
字符串形式的 legacy extractedEntities
```

迁移完成后废弃字符串形式，避免二次 JSON 解析和类型不一致。

## 16. 最终设计决策

1. 规范 URI 为 `/v2/onto-retrieval/{ontologyId}/subgraph/semantic-search`。
2. `query` 和 `extractedEntities` 至少一个不为空，推荐同时传递。
3. `extractedEntities` 正式类型为 `Array<ExtractedEntity>`，不再定义为 String。
4. 业务侧只传递对象、属性、关系和值的业务名称，不传递本体内部 ID。
5. `Relationships` 支持方向、目标 ObjectType 和 RelationshipProperty 名称列表。
6. 新增 `EnumValues` 和 `InstanceValues`，分别检索枚举值索引和实例值索引。
7. 不定义 `OriginalText`、`Operator` 和 `ConstraintHint`。
8. 比较条件、时间范围、聚合方式和单位继续保留在原始 `query` 中。
9. `adaptiveRetrieval` 默认开启，默认规模阈值为 100。
10. `seedRetrievalMode` 支持 `vector`、`keyword` 和 `hybrid`。
11. `graphExpansionStrategy` 支持 `minimal`、`khop` 和 `component`。
12. `includeFunctions` 和 `includeActions` 默认均为 0。
13. `includeDimAndIndicator` 不属于 v2 有效请求 Schema。
14. 成功响应统一返回 `resultCode/resultMessage/result`。
15. `retrievalResults` 表达完整语义命中，`seedNodes/nodes/edges` 表达本体子图结果。
