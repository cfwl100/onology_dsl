# OAG 语义子图检索接口 extractedEntities 结构设计方案

> 版本：V1.0  
> 日期：2026-08-19  
> 适用接口：`POST /v2/onto-retrieval/subgraph/semantic-search`  
> 参考：[OAG 本体锚点语义检索与向量索引设计方案](./OAG本体锚点语义检索与向量索引设计方案.md)

## 1. 背景

语义子图检索接口同时支持两类输入：

- 原始自然语言问题 `query`；
- 业务 Skill 根据原始问题和专家查询路径提取的 `extractedEntities`。

原有接口将 `extractedEntities` 定义为 `String`，但示例实际表达的是结构化 JSON，并且只描述了 ObjectType 和 Property，无法明确表达枚举值、实例值及专家路径中的关系方向。

本方案将 `extractedEntities` 调整为结构化数组，并增加：

- `Relationships`：表达专家经验中的查询路径；
- `EnumValues`：表达 OMS 静态建模的枚举值；
- `InstanceValues`：表达实例数据中适合语义检索的真实业务列值。

## 2. 设计边界

### 2.1 业务侧只提供可获得的信息

业务 Skill 根据用户问题和专家经验通常只能获得对象、属性、关系和值的业务名称，无法可靠获得本体内部 ID。因此请求结构中不包含：

```text
ObjectTypeId
PropertyId
RelationshipId
TargetObjectTypeId
其他本体元素 ID
```

本体 ID 由 OAG 检索并解析，在检索结果和本体子图中返回。

### 2.2 query 与 extractedEntities 职责分离

`query` 保留完整问题语义，包括：

```text
比较条件
时间范围
聚合方式
数量、金额和单位
```

`extractedEntities` 只表达可用于 OAG 检索和子图构建的语义提示：

```text
ObjectType
Property
Relationship
Enum Value
Instance Value
```

因此 `extractedEntities` 不定义：

```text
OriginalText
Operator
ConstraintHint
```

例如，“本月个人客户中，信用额度超过 200 元的账户总数是多少？”中的“本月”“超过 200 元”“总数”继续保留在 `query` 中；`extractedEntities` 只表达相关对象、属性和关系路径。

### 2.3 extractedEntities 是检索提示，不是最终本体结果

业务 Skill 输出的名称可能是：

- 本体英文名称；
- 中文或其他语言显示名；
- 同义词、业务术语或专家习惯用语；
- 用户问题中的实例值表达。

OAG 需要对这些内容执行关键词、向量或混合检索，不应把输入名称直接当作已经确认的本体元素。

## 3. 请求参数调整

### 3.1 extractedEntities 参数

| 参数名称 | 参数位置 | 必选 | 数据类型 | 默认值 | 说明 |
|---|---|---:|---|---|---|
| `extractedEntities` | body | 否 | `Array<ExtractedEntity>` | 无 | 业务 Skill 根据原始问题和专家查询路径生成的结构化检索提示；`query` 和 `extractedEntities` 至少一个不为空 |

建议业务 Skill 同时传递 `query` 和 `extractedEntities`：

- `query` 为 OAG 提供完整语义上下文；
- `extractedEntities` 为 OAG 提供专家路径和强类型检索提示；
- 当两者存在语义冲突时，OAG 将 `extractedEntities` 作为候选约束和 Boost 依据，但仍需根据真实本体索引完成解析。

### 3.2 ExtractedEntity

| 字段 | 数据类型 | 必选 | 默认值 | 说明 |
|---|---|---:|---|---|
| `ObjectType` | String | 是 | 无 | 对象类型名称、显示名、同义词或业务术语 |
| `Properties` | Array\<String> | 否 | `[]` | 与当前对象相关的属性名称列表 |
| `Relationships` | Array\<RelationshipHint> | 否 | `[]` | 从当前对象出发的关系路径提示 |
| `EnumValues` | Array\<EnumValueHint> | 否 | `[]` | 与当前对象属性相关的枚举值提示 |
| `InstanceValues` | Array\<InstanceValueHint> | 否 | `[]` | 与当前对象属性相关的实例列值提示 |

### 3.3 RelationshipHint

| 字段 | 数据类型 | 必选 | 默认值 | 说明 |
|---|---|---:|---|---|
| `Relationship` | String | 是 | 无 | 关系名称、显示名、同义词或业务术语 |
| `Direction` | String | 否 | `OUT` | 关系方向，可取 `OUT`、`IN`、`BOTH` |
| `TargetObjectType` | String | 是 | 无 | 目标对象类型名称；源对象由所属 `ExtractedEntity.ObjectType` 确定 |

### 3.4 EnumValueHint

| 字段 | 数据类型 | 必选 | 默认值 | 说明 |
|---|---|---:|---|---|
| `Property` | String | 否 | 无 | 枚举值所属属性名称；无法确定时可以省略 |
| `Value` | String | 是 | 无 | 枚举值、显示名、同义词或用户使用的业务表达 |

`EnumValues` 表达 OMS 静态建模的枚举项，例如账户状态、客户类型、产品类型等。OAG 使用 `Value` 检索枚举值的 `value/name/display/description/synonyms`，再根据命中记录内部的 `propertyId + objectTypeId` 投影为 Property 和 ObjectType 种子节点。

### 3.5 InstanceValueHint

| 字段 | 数据类型 | 必选 | 默认值 | 说明 |
|---|---|---:|---|---|
| `Property` | String | 否 | 无 | 实例值所属属性名称；无法确定时可以省略 |
| `Value` | String | 是 | 无 | 实例数据中适合语义检索的真实业务列值 |

适合放入 `InstanceValues` 的值包括：

```text
VIP
东京
华东区域
钻石客户
某产品名称
```

以下值不应作为 Instance Value 向量检索提示：

```text
连续数值
日期和时间戳
手机号
UUID
纯技术主键
高随机编码
```

这些内容继续保留在原始 `query` 中，由后续查询规划和条件生成环节处理。

## 4. 推荐 JSON 结构

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
          "TargetObjectType": "ObjectType2"
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

## 5. 业务专家经验样例

### 5.1 用户问题

> 本月个人客户中，信用额度超过 200 元的账户总数是多少？

### 5.2 查询路径

```text
IndividualCustomer ──[OWNS]──→ PayRelation ──[BELONGS_TO]──→ Account ──[HAS]──→ CreditLimitInstance

IndividualCustomer: id
PayRelation: objectId → accountId
Account: accountId
CreditLimitInstance: accountId、本月、initialAmount > 200
```

### 5.3 Skill 生成的完整请求

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
          "TargetObjectType": "PayRelation"
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
          "TargetObjectType": "Account"
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
          "TargetObjectType": "CreditLimitInstance"
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

### 5.4 样例说明

该问题中的 `EnumValues` 和 `InstanceValues` 为空是正确的：

1. “个人客户”已经由专家路径明确为 `IndividualCustomer`，不是枚举值。
2. `CreditLimitInstance` 虽然名称中包含 `Instance`，但它是 ObjectType，不是实例列值。
3. “200”是连续数值，不进入实例值向量索引。
4. “本月”是相对时间，不进入实例值向量索引。
5. “超过”和“总数”属于条件与聚合语义，由原始 `query` 保留，不进入 `extractedEntities`。

OAG 根据 `extractedEntities` 检索 `IndividualCustomer`、`PayRelation`、`Account`、`CreditLimitInstance`、相关 Property 和 Relationship，并返回支持后续查询生成的本体子图。

## 6. EnumValues 和 InstanceValues 非空示例

以下示例只用于说明新增字段的表达方式：

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
  ]
}
```

OAG 对该输入分别执行：

```text
Account / accountStatus / customerLevel
  → 种子节点索引

在用
  → Enum Value 索引

VIP
  → Instance Value 索引
```

## 7. OAG 检索处理规则

| 输入元素 | 检索对象 | 处理方式 |
|---|---|---|
| `ObjectType` | ObjectType 种子节点 | 检索 `name/display/description/synonyms` |
| `Properties` | Property 种子节点 | 检索 `name/display/description/synonyms` |
| `Relationships` | 本体关系和拓扑 | 解析关系名称，并用于路径校验、候选 Boost 和子图扩展 |
| `EnumValues` | Enum Value | 检索 `value/name/display/description/synonyms` |
| `InstanceValues` | Instance Value | 仅使用真实业务 `value` 检索实例值索引 |

### 7.1 Property 上下文处理

当 `EnumValueHint.Property` 或 `InstanceValueHint.Property` 存在时：

1. OAG 同时检索 Property 名称和值；
2. Property 名称作为候选分组和排序上下文；
3. 不把业务输入的 Property 名称直接当作 `propertyId`；
4. 最终使用枚举或实例索引命中记录内部的 `propertyId + objectTypeId` 建立确定归属。

当 `Property` 不存在时，OAG 可以跨 Property 检索该值，再结合原始 `query`、ObjectType 上下文和专家关系路径进行精排。

### 7.2 关系路径处理

`Relationships` 不是业务侧提供的本体 ID，而是专家路径提示。OAG 应：

1. 按关系名称、显示名或同义词解析 Relationship；
2. 使用当前 `ObjectType`、`Direction` 和 `TargetObjectType` 校验候选关系；
3. 将匹配关系作为子图构建的路径提示；
4. 未匹配时不创造关系，记录为未解析提示并按配置降级为普通子图检索。

### 7.3 检索结果投影

Enum Value 或 Instance Value 命中后，OAG 按索引记录中的真实归属完成投影：

```text
Enum/Instance 检索命中
  → Property 种子节点
  → ObjectType 种子节点
  → 与其他种子节点执行 minimal / khop / component 子图构建
```

业务请求不需要也不允许构造这些内部 ID。

## 8. OpenAPI Schema 建议

```yaml
ExtractedEntity:
  type: object
  required:
    - ObjectType
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
  required:
    - Relationship
    - TargetObjectType
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

EnumValueHint:
  type: object
  required:
    - Value
  properties:
    Property:
      type: string
      minLength: 1
    Value:
      type: string
      minLength: 1

InstanceValueHint:
  type: object
  required:
    - Value
  properties:
    Property:
      type: string
      minLength: 1
    Value:
      type: string
      minLength: 1
```

`SemanticSearchRequest.extractedEntities` 调整为：

```yaml
extractedEntities:
  type: array
  minItems: 1
  items:
    $ref: '#/components/schemas/ExtractedEntity'
```

## 9. 兼容与校验建议

### 9.1 兼容策略

现有调用方如果已经传递以下结构，可以继续工作：

```json
{
  "extractedEntities": [
    {
      "ObjectType": "ObjectType1",
      "Properties": ["Property1"]
    }
  ]
}
```

新增数组均为可选字段，默认空数组，不影响已有业务 Skill。

如果现网实际把整个 JSON 作为转义字符串传入，建议在过渡期同时兼容：

```text
结构化 Array<ExtractedEntity>
JSON 字符串形式的 legacy extractedEntities
```

完成调用方升级后，废弃字符串形式。

### 9.2 校验规则

1. `query` 和 `extractedEntities` 至少一个不为空。
2. `ExtractedEntity.ObjectType` 不为空。
3. Relationship 必须同时包含 `Relationship` 和 `TargetObjectType`。
4. Enum Value 和 Instance Value 必须包含非空 `Value`。
5. 所有字符串在检索前统一执行 trim、Unicode Normalize 和去空。
6. 对重复 ObjectType、Property、Relationship 和 Value 做规范化去重。
7. 输入名称只作为检索提示，不能作为内部 ID 使用。

## 10. 最终设计决策

1. `extractedEntities` 从 `String` 调整为 `Array<ExtractedEntity>`。
2. 业务侧只传递对象、属性、关系和值的业务名称，不传递任何本体 ID。
3. 新增 `Relationships`、`EnumValues` 和 `InstanceValues`。
4. Enum Value 使用 `Property + Value` 表达，`Property` 无法确定时可省略。
5. Instance Value 使用 `Property + Value` 表达，`Property` 无法确定时可省略。
6. 不定义 `OriginalText`、`Operator` 和 `ConstraintHint`。
7. 比较条件、时间范围、聚合方式和单位继续保留在原始 `query` 中。
8. 连续数值、日期、时间戳和技术主键不进入 Instance Value 向量检索。
9. OAG 根据业务名称执行检索，在内部解析真实 `id/propertyId/objectTypeId`。
10. Enum/Instance 命中后投影为 Property 和 ObjectType 种子节点，再构建本体子图。
