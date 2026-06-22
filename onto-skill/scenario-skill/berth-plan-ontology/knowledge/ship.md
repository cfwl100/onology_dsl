# 船舶对象查询（ship_info）

## 目标

用于集装箱泊位计划本体数据查询场景下的船舶对象明细查询。

典型问题包括：

- 查询所有船舶信息。
- 按船舶编号查询船舶信息。
- 按船高、船舶类型、吃水深度等条件查询船舶信息。
- 查询船舶计划场景中与船舶对象相关的基础字段。

## 本体信息

- 对象名：`ship_info`
- 对象ID：`dtmi.560d88f7.object-type.c34b06da4da98133.1`
- Ontology-ID：`dtmi.ontology.560d88f7.1`
- schemaRef：`dtmi.ontology.560d88f7.1`

## 字段映射

本文件只描述船舶对象 `ship_info` 的业务字段映射。字段是否可用于最终查询，仍必须以本体子图中 `ship_info --has_property--> property` 的归属关系为准。

| 用户表达 | 平台字段 | 归属对象 | 用途 |
|---|---|---|---|
| 船舶编号、船号、船舶代码 | `ship_no` | `ship_info` | 返回字段、等值过滤、实例定位 |
| 船舶类型、船的类型 | `ship_type` | `ship_info` | 返回字段、等值过滤，例如“货轮” |
| 船高 | `ship_height` | `ship_info` | 返回字段、范围过滤，例如大于 10 小于 30 |
| 吃水深度、船的吃水深度 | `draft` | `ship_info` | 返回字段、等值或范围过滤 |
| 船长、总长、LOA | `loa` | `ship_info` | 返回字段 |

注意：子图中可能还存在 `ship_plan.vessel_type`。当用户询问“船舶类型”且查询对象是船舶信息时，必须优先使用 `ship_info.ship_type`；只有查询船舶计划对象时才考虑 `ship_plan.vessel_type`。

## 默认返回字段

当用户要求返回“船舶信息”，且没有进一步限制返回字段时，船舶对象默认返回以下字段：

```text
ship_no, ship_type, ship_height, draft, loa
```

如果用户明确指定返回字段，按用户指定字段返回，不额外扩展。

## 条件转换规则

| 用户条件 | OQL 条件 |
|---|---|
| 船高大于 10m | `ship_info.ship_height GT 10` |
| 船高小于 30m | `ship_info.ship_height LT 30` |
| 船舶类型是货轮 | `ship_info.ship_type EQ "货轮"` |
| 船的吃水深度是 10m | `ship_info.draft EQ 10` |

单位处理：用户输入中出现 `m`、`米` 等单位时，生成过滤条件时只保留数值部分，例如 `10m` → `10`。

## 端到端样例

用户问题：

```text
集装箱泊位计划本体数据查询场景，查询所有船高大于10m小于30m 且 船舶类型是货轮，船的吃水深度是10m的船舶信息？
```

业务定制输入应表达为：

```text
intent: ship_info_query
ontologyId: dtmi.ontology.560d88f7.1
schemaRef: dtmi.ontology.560d88f7.1
objectType: ship_info
alias: s
filters:
  - ship_height GT 10
  - ship_height LT 30
  - ship_type EQ 货轮
  - draft EQ 10
returns:
  - ship_no
  - ship_type
  - ship_height
  - draft
  - loa
maxResults: 1000
```

平台最终生成的 OQL 必须符合 `oql-query.schema.json`，当前 schema 要求 `version` 为 `2.0`，不得沿用历史样例中的 `1.0`。

## 调用规则

### 本体子图调用

调用本体子图查询时，必须传入：

```text
ontologyId = dtmi.ontology.560d88f7.1
```

本体子图检索问题保持自然语言，优先使用用户原始问题或业务 Skill 注入的自然语言检索问题。

### 本体访问调用

调用本体访问执行实例查询时，必须传入：

```text
schemaRef = dtmi.ontology.560d88f7.1
```

数据访问操作类型由 `Ontology-platform-unified-skill` 根据自然语言委托判断。本样例属于单对象明细查询，应路由为 `QUERY`。

## 强约束

1. 字段必须属于 `ship_info`，且必须能从本体子图的 `has_property` 关系确认归属。
2. 用户要求“船舶信息”时，默认返回 `ship_no, ship_type, ship_height, draft, loa`。
3. 不得把 `ship_plan.vessel_type` 当成 `ship_info.ship_type`。
4. 不得因为用户使用中文字段名就直接写入中文字段，必须映射到平台字段名。
5. 不得生成 `version: "1.0"` 的 OQL；OQL 版本以平台 schema 为准。
6. OAC 返回空结果是有效结果，不自动放宽条件或重复查询。
