# OAG 子图检索返回结构设计

## 1. 概述

本文档描述 OAG（Open Ontology Graph）子图检索功能的最终返回数据结构定义和 JSON 示例。

### 1.1 API 接口
### 1.2 返回格式

所有接口统一返回 `RestResponse<T>` 格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { /* 实际数据 */ }
}
```

---

## 2. 完整返回结构（GraphSearchResponse）

### 2.1 结构定义

**核心类**: `GraphSearchResponse`

| 字段 | 类型 | 描述 |
|------|------|------|
| `seedNodes` | `List<SeedNodes>` | 种子节点列表（检索入口节点） |
| `nodes` | `List<GraphObject>` | 图节点列表 |
| `edges` | `List<GraphEdge>` | 图边列表 |
| `functions` | `List<Functions>` | 函数列表 |
| `actions` | `List<Actions>` | 操作列表 |
| `semanticExtensions` | `SemanticExtensions` | 语义扩展；保存“用户原始值 → 标准真实值 → Property → ObjectType”的确定性映射，辅助下游 Agent/LLM 生成过滤条件和查询语句 |

---

### 2.2 子结构定义

#### SeedNodes（种子节点）

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 节点标识，格式：`ObjectType:Cell` |
| `name` | String | 节点名称 |
| `score` | float | 召回分数（0~1） |
| `llmDrawEntityName` | String | LLM 绘制用的实体名称 |

#### GraphObject（图节点对象）

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 节点唯一标识 |
| `label` | String | 节点标签/类型（如 ObjectType、PropertyType） |
| `properties` | `Map<String, Object>` | 节点属性映射 |

**Properties 常见属性**:

| 属性 Key | 描述 |
|----------|------|
| `name` | 节点名称 |
| `display` | 多语言显示（JSON 格式：`{"zh":"小区","en":"Cell"}`） |
| `description` | 节点描述（多语言 JSON 格式） |

#### GraphEdge（图边对象）

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 边唯一标识 |
| `sourceId` | String | 源节点 ID |
| `targetId` | String | 目标节点 ID |
| `edgeType` | String | 边类型（如 associate、compose、inherit） |
| `properties` | Object | 边属性 |

#### Functions（函数）

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 函数唯一标识 |
| `label` | String | 函数标签 |
| `properties` | `Map<String, Object>` | 函数属性 |

#### Actions（操作）

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 操作唯一标识 |
| `label` | String | 操作标签 |
| `properties` | `Map<String, Object>` | 操作属性 |

#### SemanticExtensions（语义扩展）

`semanticExtensions` 不改变 `nodes/edges` 的本体拓扑，而是把 Entity Linking 最终确认的 Enum Value / Instance Value 转换成下游可直接消费的值归属映射。

```text
SemanticExtensions
└── valueMappings[]
    ├── semanticUnitId
    ├── sourceValue
    ├── canonicalValue
    ├── valueType
    ├── objectType
    │   ├── id
    │   └── name
    ├── property
    │   ├── id
    │   └── name
    ├── matchedField
    ├── matchedValue
    ├── matchedBy
    └── confidence
```

##### SemanticExtensions

| 字段 | 类型 | 必选 | 描述 |
|------|------|------|------|
| `valueMappings` | `List<ValueMapping>` | 是 | Enum/Instance 的最终值映射；没有值命中时返回空数组 |

##### ValueMapping

| 字段 | 类型 | 必选 | 描述 |
|------|------|------|------|
| `semanticUnitId` | String | 否 | 产生该映射的语义单元 ID，用于和 `retrievalResults` 对齐 |
| `sourceValue` | String | 是 | 用户问题或 `extractedEntities.Values[].Value` 中的原始表达 |
| `canonicalValue` | String | 是 | OAG Entity Linking 最终确认的真实标准值；下游生成过滤条件时使用。它直接来自最终 Enum/Instance `retrievalResults[].value`，不是额外维护的 canonical 字典 |
| `valueType` | String | 是 | `ENUM_VALUE` / `INSTANCE_VALUE` |
| `objectType` | `ObjectRef` | 是 | 真实值所属 ObjectType |
| `property` | `ObjectRef` | 是 | 真实值所属 Property |
| `matchedField` | String | 否 | 实际命中的索引字段，例如 `value` / `synonyms` |
| `matchedValue` | String | 否 | 实际命中文本；同义词命中时保留用户命中的 synonym |
| `matchedBy` | String | 否 | `EXACT` / `SYNONYM` / `LEXICAL` / `DENSE` |
| `confidence` | float | 否 | 映射置信度，范围 `[0,1]` |

##### ObjectRef

| 字段 | 类型 | 必选 | 描述 |
|------|------|------|------|
| `id` | String | 是 | 本体真实 ID |
| `name` | String | 是 | 本体真实名称 |

设计约束：

1. `sourceValue` 用于解释用户原始表达；`canonicalValue + property + objectType` 用于查询条件/查询语句生成。
2. `canonicalValue` 必须是索引中的真实 Enum/Instance Value，不能返回 display、synonym 或 LLM 生成的新值。
3. Enum synonym 命中时，例如 `sourceValue=严重`，标准值可以是 `canonicalValue=CRITICAL`。
4. Instance Value 经过规范化或实体链接后，`sourceValue` 与 `canonicalValue` 可以相同，也可以不同。
5. 同一个 `sourceValue` 存在多个合法归属时允许返回多个 `ValueMapping`，按 `confidence` 降序；OAG 不为保证唯一而强行猜测。
6. 只为最终选中的 `ENUM_VALUE/INSTANCE_VALUE` 生成映射；纯 ObjectType/Property 命中不生成 `valueMappings`。
7. 下游 Agent/LLM 不应使用 `sourceValue` 猜过滤字段，也不应把 `matchedValue` 当真实过滤值；实际过滤值统一使用 `canonicalValue`。

---

### 2.3 JSON 示例

下面示例同时包含一个实例值映射和一个枚举同义词映射。`semanticExtensions.valueMappings` 直接表达：

```text
用户原始值
  → 标准真实值
  → Property
  → ObjectType
```

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "seedNodes": [
      {
        "id": "ObjectType:Site",
        "name": "Site",
        "score": 0.9812,
        "llmDrawEntityName": "Site"
      },
      {
        "id": "ObjectType:Alarm",
        "name": "Alarm",
        "score": 0.9731,
        "llmDrawEntityName": "Alarm"
      }
    ],
    "nodes": [
      {
        "id": "obj:site:Site",
        "label": "ObjectType",
        "properties": {
          "name": "Site",
          "display": "{\"zh\":\"站点\",\"en\":\"Site\"}",
          "description": "{\"zh\":\"网络站点\",\"en\":\"Network site\"}"
        }
      },
      {
        "id": "prop:site:nativeId",
        "label": "PropertyType",
        "properties": {
          "name": "nativeId",
          "display": "{\"zh\":\"站点原生标识\",\"en\":\"Native ID\"}"
        }
      },
      {
        "id": "obj:alarm:Alarm",
        "label": "ObjectType",
        "properties": {
          "name": "Alarm",
          "display": "{\"zh\":\"告警\",\"en\":\"Alarm\"}"
        }
      },
      {
        "id": "prop:alarm:severity",
        "label": "PropertyType",
        "properties": {
          "name": "severity",
          "display": "{\"zh\":\"严重级别\",\"en\":\"Severity\"}"
        }
      }
    ],
    "edges": [
      {
        "id": "edge_site_alarm",
        "sourceId": "obj:site:Site",
        "targetId": "obj:alarm:Alarm",
        "edgeType": "associate",
        "properties": {
          "businessSemanticType": "associate"
        }
      },
      {
        "id": "edge_site_native_id",
        "sourceId": "obj:site:Site",
        "targetId": "prop:site:nativeId",
        "edgeType": "compose",
        "properties": {}
      },
      {
        "id": "edge_alarm_severity",
        "sourceId": "obj:alarm:Alarm",
        "targetId": "prop:alarm:severity",
        "edgeType": "compose",
        "properties": {}
      }
    ],
    "functions": [],
    "actions": [],
    "semanticExtensions": {
      "valueMappings": [
        {
          "semanticUnitId": "u1",
          "sourceValue": "12JKS0885_IN_RSNM_KALIBATA3_MC",
          "canonicalValue": "12JKS0885_IN_RSNM_KALIBATA3_MC",
          "valueType": "INSTANCE_VALUE",
          "objectType": {
            "id": "obj:site:Site",
            "name": "Site"
          },
          "property": {
            "id": "prop:site:nativeId",
            "name": "nativeId"
          },
          "matchedField": "value",
          "matchedValue": "12JKS0885_IN_RSNM_KALIBATA3_MC",
          "matchedBy": "EXACT",
          "confidence": 1.0
        },
        {
          "semanticUnitId": "u2",
          "sourceValue": "严重",
          "canonicalValue": "CRITICAL",
          "valueType": "ENUM_VALUE",
          "objectType": {
            "id": "obj:alarm:Alarm",
            "name": "Alarm"
          },
          "property": {
            "id": "prop:alarm:severity",
            "name": "severity"
          },
          "matchedField": "synonyms",
          "matchedValue": "严重",
          "matchedBy": "SYNONYM",
          "confidence": 0.99
        }
      ]
    }
  }
}
```

下游 Agent/LLM 可以直接得到确定性过滤语义：

```text
Site.nativeId = "12JKS0885_IN_RSNM_KALIBATA3_MC"
Alarm.severity = "CRITICAL"
```

其中 `sourceValue` 只用于理解用户原始表达，真正生成查询条件时使用 `canonicalValue`。

---

## 3. 简化返回结构（RetrievalResponseData）

对于部分场景，经过 `graphSearchInfo` 方法转换后，返回简化版本。

### 3.1 结构定义

| 字段 | 类型 | 描述 |
|------|------|------|
| `nodes` | `List<NodeVo>` | 节点列表 |
| `edges` | `List<EdgeVo>` | 边列表 |

### 3.2 NodeVo

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 节点 ID |
| `name` | String | 节点名称 |
| `type` | String | 节点类型 |
| `displayName` | String | 显示名称（已解析多语言） |
| `description` | String | 节点描述（已解析多语言） |

### 3.3 EdgeVo

| 字段 | 类型 | 描述 |
|------|------|------|
| `source` | String | 源节点 ID |
| `target` | String | 目标节点 ID |
| `label` | String | 边标签/类型 |
| `rank` | String | 边排序/权重 |

### 3.4 JSON 示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "nodes": [
      {
        "id": "node_001",
        "name": "Cell",
        "type": "ObjectType",
        "displayName": "小区",
        "description": "小区实体，用于表示无线网络中的小区"
      },
      {
        "id": "node_002",
        "name": "UE",
        "type": "ObjectType",
        "displayName": "终端",
        "description": "用户终端设备"
      }
    ],
    "edges": [
      {
        "source": "node_001",
        "target": "node_002",
        "label": "associate",
        "rank": "1"
      }
    ]
  }
}
```

---

## 4. 指标检索返回结构（MetricSearchResponse）

### 4.1 结构定义

| 字段 | 类型 | 描述 |
|------|------|------|
| `seedNodes` | `List<SeedNodes>` | 种子节点 |
| `nodes` | `List<GraphObject>` | 图节点 |
| `edges` | `List<GraphEdge>` | 图边 |

### 4.2 JSON 示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "seedNodes": [
      {
        "id": "Indicator:KPI001",
        "name": "PRB Utilization Rate",
        "score": 0.98,
        "llmDrawEntityName": "PRB利用率"
      }
    ],
    "nodes": [
      {
        "id": "indicator_001",
        "label": "Indicator",
        "properties": {
          "name": "PRB Utilization Rate",
          "display": "{\"zh\":\"PRB利用率\",\"en\":\"PRB Utilization Rate\"}",
          "unit": "%",
          "valueRange": "0-100"
        }
      },
      {
        "id": "dimension_001",
        "label": "Dimension",
        "properties": {
          "name": "Cell",
          "display": "{\"zh\":\"小区\",\"en\":\"Cell\"}"
        }
      }
    ],
    "edges": [
      {
        "id": "edge_m001",
        "sourceId": "indicator_001",
        "targetId": "dimension_001",
        "edgeType": "dimension",
        "properties": {}
      }
    ]
  }
}
```

---
