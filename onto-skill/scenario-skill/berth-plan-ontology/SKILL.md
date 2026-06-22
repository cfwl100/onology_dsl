---
name: berth-plan-ontology
description: 集装箱泊位计划本体数据查询业务定制 Skill。作为业务入口，识别泊位计划场景的对象、字段、条件和返回要求，并委托 Ontology-based-planning-skill。
allowed_tools:
metadata:
  pattern: inversion
  delegates_to: Ontology-based-planning-skill
  scenario: container-berth-plan-ontology
---

# 集装箱泊位计划本体业务定制 Skill

## 1. 任务概述

本 Skill 是业务语义层，只负责识别场景、读取对应业务知识、抽取变量和约束，然后委托 `Ontology-based-planning-skill`。

不得直接生成最终平台请求，不得绕过 planning 层和 platform 层。

## 2. 固定上下文

| 字段 | 值 |
|---|---|
| `ontologyId` | `dtmi.ontology.560d88f7.1` |
| `schemaRef` | `dtmi.ontology.560d88f7.1` |
| OQL 初始版本 | `1.0` |
| 默认规划层 | `Ontology-based-planning-skill` |
| 平台能力层 | `Ontology-platform-unified-skill` |

本体子图检索使用 `ontologyId`，本体访问使用 `schemaRef`，最终 OQL 使用 `version: "1.0"`。

## 3. 对象路由

用户查询船舶信息时，只读取 `knowledge/ship.md`；Mock 测试可额外读取 `knowledge/ship.json` 作为本体子图返回样例。

支持对象包括：`ship_info`、`ship_plan`、`berth_info`、`bollard_info`、`berth_bollard_coords`、`berth_display_order`、`equipment_infos`、`tide_info`。

## 4. 子图解析提醒

本体子图结构遵循 `docs/ontology_subgraph.json`：

- `nodes[label=objectType]` 表示对象类型。
- `nodes[label=property]` 表示属性字段。
- `edges[edgeType=has_property]` 只能确认对象字段归属。
- `edges[edgeType=defines_relation]` 才能生成对象关系路径。
- `functions` 为空时不得编造函数调用。
- `actions` 为空时不得编造动作。

## 5. 船舶信息查询基线

船舶信息查询的业务字段映射以 `knowledge/ship.md` 为准，并必须由本体子图 `has_property` 确认归属。

端到端验证中的船舶信息明细查询应路由为 `QUERY`，对象为 `ship_info`，alias 为 `s`。

典型条件抽取：

```text
ship_height GT 10
ship_height LT 30
ship_type EQ 用户指定船舶类型
draft EQ 10
```

默认返回字段：

```text
ship_no, ship_type, ship_height, draft, loa
```

## 6. 委托模板

向 planning 层发送：

```text
场景：集装箱泊位计划本体数据查询
原始问题：{用户原始问题}
intent：{识别出的业务意图}
ontologyId：dtmi.ontology.560d88f7.1
schemaRef：dtmi.ontology.560d88f7.1
knowledge：{对应 knowledge 文件摘要}
variables：{字段、操作符、取值}
constraints：{返回字段、maxResults、是否 mock、version=1.0}
```

## 7. 强约束

1. 字段必须来自业务知识映射，并由本体子图 `has_property` 确认归属。
2. `has_property` 不得当作对象间业务关系。
3. `defines_relation` 才能作为对象关系来源。
4. 用户指定或默认返回字段必须显式列出，不使用 `*`。
5. 最终 OQL 必须使用 `version: "1.0"`。
6. 本体访问返回空结果时，不自动放宽条件、不重复查询。