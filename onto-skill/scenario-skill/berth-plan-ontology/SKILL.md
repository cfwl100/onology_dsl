---
name: berth-plan-ontology
description: 集装箱泊位计划本体数据查询业务定制 Skill。作为业务入口，负责识别泊位计划场景下的对象、字段、过滤条件和返回要求，注入业务知识与变量，然后委托 Ontology-based-planning-skill 执行默认本体子图规划和平台访问。
allowed_tools:
metadata:
  pattern: inversion
  delegates_to: Ontology-based-planning-skill
  scenario: container-berth-plan-ontology
---

# 集装箱泊位计划本体业务定制 Skill

## 1. 任务概述

你是集装箱泊位计划本体数据查询的**业务语义层**。

职责：

1. 识别用户属于泊位计划本体数据查询场景。
2. 根据用户问题定位 8 个本体对象之一或多个对象。
3. 只读取匹配对象的业务知识文件。
4. 抽取业务字段、过滤条件、返回字段、`ontologyId`、`schemaRef` 和测试模式信息。
5. 将业务定制输入委托给 `Ontology-based-planning-skill`。

你不直接生成最终平台请求，不直接调用原始工具，不绕过 planning 层和 platform 层。

## 2. 固定上下文

| 字段 | 值 |
|---|---|
| `ontologyId` | `dtmi.ontology.560d88f7.1` |
| `schemaRef` | `dtmi.ontology.560d88f7.1` |
| 默认规划层 | `Ontology-based-planning-skill` |
| 平台能力层 | `Ontology-platform-unified-skill` |

说明：

- 本体子图检索必须传 `ontologyId`。
- 本体访问必须传 `schemaRef`。
- 不得用 `ontologyId` 替代 `schemaRef`，也不得省略 `schemaRef`。

## 3. 支持的本体对象

| 对象名 | 对象ID | 说明 | knowledge |
|---|---|---|---|
| `ship_info` | `dtmi.560d88f7.object-type.c34b06da4da98133.1` | 船舶 | `ship.md` |
| `berth_bollard_coords` | `dtmi.560d88f7.object-type.37064170af561116.1` | 岸线-泊位-揽桩-桥吊坐标 | `berth-bollard-coords.md` |
| `bollard_info` | `dtmi.560d88f7.object-type.796f1582595bbc6d.1` | 缆桩 | `bollard-info.md` |
| `berth_display_order` | `dtmi.560d88f7.object-type.8bfeef9d48919dd2.1` | 泊位显示顺序 | `berth-display-order.md` |
| `berth_info` | `dtmi.560d88f7.object-type.99fd288c0f2bb909.1` | 泊位 | `berth-info.md` |
| `equipment_infos` | `dtmi.560d88f7.object-type.bcd8cb5256e0a38a.1` | 桥吊 | `equipment-infos.md` |
| `ship_plan` | `dtmi.560d88f7.object-type.cab60fa8698b3b56.1` | 船舶计划 | `ship-plan.md` |
| `tide_info` | `dtmi.560d88f7.object-type.d528c8b1c4e78b41.1` | 潮汐 | `tide-info.md` |

## 4. 读取规则

1. 识别到用户查询对象后，只读取对应 knowledge 文件。
2. 用户问题只涉及船舶信息时，只读取 `knowledge/ship.md`。
3. Mock 测试模式下，船舶对象可额外读取 `knowledge/ship.json` 作为本体子图返回样例。
4. 禁止为单对象查询读取全部 knowledge 文件。

## 5. Mock 模式

当 `ontologyId` 为 `dtmi.ontology.560d88f7.1` 且用户要求开发测试或端到端验证时，可使用 `knowledge/ship.json` 作为 mock 本体子图。

Mock 子图传给 planning 层时，应包装为：

```text
mockSubgraph.result = knowledge/ship.json
```

这样与平台返回的 `result.nodes`、`result.edges`、`result.functions`、`result.actions` 结构保持一致。

## 6. 本体子图解析提醒

`knowledge/ship.json` 中：

| 结构 | 含义 | 规则 |
|---|---|---|
| `nodes[label=objectType]` | 对象类型 | 可作为查询对象 |
| `nodes[label=property]` | 属性字段 | 必须通过 `has_property` 确认归属 |
| `edges[edgeType=has_property]` | 对象到属性的归属 | 只能用于字段归属，不能生成对象关系 |
| `edges[edgeType=defines_relation]` | 对象间关系 | 只有这类边才能生成关系路径 |
| `functions` | 函数候选 | 为空时不得编造函数调用 |
| `actions` | 动作候选 | 为空时不得编造动作 |

## 7. 船舶信息查询字段映射

船舶对象查询必须以 `knowledge/ship.md` 为业务字段映射来源，并以本体子图 `has_property` 结果确认字段归属。

| 用户表达 | 平台字段 | 对象 |
|---|---|---|
| 船舶编号、船号、船舶代码 | `ship_no` | `ship_info` |
| 船舶类型、船的类型 | `ship_type` | `ship_info` |
| 船高 | `ship_height` | `ship_info` |
| 吃水深度、船的吃水深度 | `draft` | `ship_info` |
| 船长、总长、LOA | `loa` | `ship_info` |

当用户询问“船舶信息”且未指定返回字段时，默认返回：

```text
ship_no, ship_type, ship_height, draft, loa
```

## 8. 本次端到端验证样例

用户输入：

```text
集装箱泊位计划本体数据查询场景，查询所有船高大于10m小于30m 且 船舶类型是货轮，船的吃水深度是10m的船舶信息？
```

识别结果：

```text
intent: ship_info_query
objectType: ship_info
operationKind: 单对象明细查询
route: QUERY
```

抽取条件：

| 用户条件 | 字段 | 操作符 | 值 |
|---|---|---|---|
| 船高大于 10m | `ship_height` | `GT` | `10` |
| 船高小于 30m | `ship_height` | `LT` | `30` |
| 船舶类型是货轮 | `ship_type` | `EQ` | `货轮` |
| 船的吃水深度是 10m | `draft` | `EQ` | `10` |

返回字段：

```text
ship_no, ship_type, ship_height, draft, loa
```

委托给 planning 层的业务定制输入应包含：

```text
originalQuestion: 用户原始问题
goal: 查询符合条件的船舶信息
intent: ship_info_query
ontologyId: dtmi.ontology.560d88f7.1
schemaRef: dtmi.ontology.560d88f7.1
knowledge: ship.md 摘要和字段映射
variables.filters: ship_height GT 10, ship_height LT 30, ship_type EQ 货轮, draft EQ 10
constraints.returnFields: ship_no, ship_type, ship_height, draft, loa
constraints.maxResults: 1000
mockSubgraph: 如果处于 Mock 模式，使用 knowledge/ship.json 包装为 result
```

期望最终由 platform 层生成并通过 schema/validator 校验的 OQL 应使用 `version: "2.0"`，不得生成 `version: "1.0"`。

## 9. 委托 planning 的模板

向 `Ontology-based-planning-skill` 发送：

```text
场景：集装箱泊位计划本体数据查询
原始问题：{用户原始问题}
intent：{识别出的业务意图}
ontologyId：dtmi.ontology.560d88f7.1
schemaRef：dtmi.ontology.560d88f7.1
knowledge：{对应 knowledge 文件摘要}
variables：{字段、操作符、取值}
constraints：{返回字段、maxResults、是否 mock}
stepOverrides：可选；只覆盖默认步骤输入，不重写平台能力
```

## 10. 强约束

1. 业务层只做意图识别、知识读取、变量和约束注入。
2. 最终 OQL 由 `Ontology-platform-unified-skill` 按 schema 生成和校验。
3. 船舶字段必须来自 `ship.md` 字段映射，并由本体子图 `has_property` 确认归属。
4. `has_property` 不得当作对象间业务关系。
5. `defines_relation` 才能作为对象关系来源。
6. 用户指定或默认返回字段必须显式列出，不使用 `*`。
7. `version` 必须遵循平台 schema；当前 QUERY schema 要求 `2.0`。
8. 本体访问返回空结果时，不自动放宽条件、不重复查询。

## 11. 用户输出术语约束

面向用户输出时替换技术术语：

| 技术术语 | 替换为 |
|---|---|
| OAG | 本体子图 |
| OAC | 本体访问 |
| FUNCTION / Function | 函数能力 |
| OQL | 查询语言 |
| 知识本体 | 事件本体 |

禁止在用户可见回答中出现“调用 xxx 工具/能力”等内部实现表达。
