---
name: berth-plan-ontology
description: 集装箱泊位计划本体数据查询业务定制 Skill。作为业务入口，识别泊位计划场景的对象、字段、条件和返回要求，并以流程级定制和步骤级定制方式委托 Ontology-based-planning-skill。
allowed_tools:
metadata:
  pattern: inversion
  delegates_to: Ontology-based-planning-skill
  scenario: container-berth-plan-ontology
---

# 集装箱泊位计划本体业务定制 Skill

## 1. 任务概述

本 Skill 是业务语义层，只负责识别场景、读取对应业务定制文件、抽取业务条件和返回要求，然后委托 `Ontology-based-planning-skill`。

不得直接生成最终平台请求，不得绕过 planning 层和 platform 层。

## 2. 固定上下文

| 字段 | 值 |
|---|---|
| 对外公共 `本体ID` | `dtmi.ontology.560d88f7.1` |
| OQL 初始版本 | `1.0` |
| 默认规划层 | `Ontology-based-planning-skill` |
| 平台能力层 | `Ontology-platform-unified-skill` |

对外只传递公共 `本体ID`。Planning 层会把该 ID 传给下层本体子图检索，并在生成本体访问步骤时将其作为 OQL `schemaRef` 来源。

## 3. 对象路由

用户查询船舶信息时，只读取 `knowledge/ship.md`；Mock 测试可额外读取 `knowledge/ship.json` 或 `docs/ontology_subgraph.json` 作为本体子图返回样例。

支持对象包括：`ship_info`、`ship_plan`、`berth_info`、`bollard_info`、`berth_bollard_coords`、`berth_display_order`、`equipment_infos`、`tide_info`。

## 4. 子图结构约束

本体子图结构遵循 `docs/ontology_subgraph.json`：

- `result.seedNodes[]` 表示命中的种子节点。
- `result.nodes[label=objectType]` 表示对象类型。
- `result.nodes[label=property]` 表示属性字段。
- `result.edges[edgeType=has_property]` 只能确认对象字段归属。
- `result.edges[edgeType=defines_relation]` 才能生成对象关系路径。
- `result.functions[]` 为空时不得编造函数调用。
- `result.actions[]` 为空时不得编造动作。

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

向 planning 层发送自然语言定制说明：

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：<基于用户输入改写后的详细自然语言查询问题，需包含查询船舶信息、船高范围、船舶类型、吃水深度、返回字段和 maxResults 要求>
已读取业务定制文件：knowledge/ship.md
业务定制文件内容：船舶字段映射以 ship.md 为准；字段必须由本体子图 has_property 确认归属；关系只来自 defines_relation；最终 OQL 使用 version=1.0；S4 最终只返回 objects/relationships 对象结构。
流程级定制：执行 S1/S2/S3/S4/S7，不需要 Function；S2 先检索船舶信息相关本体子图，S3 基于子图规划单对象 QUERY 查询任务，S4 生成、校验并执行 OQL。
步骤级定制：S2 需要返回 ship_info 及 ship_no、ship_type、ship_height、draft、loa 等字段归属；S3 规划对象为 ship_info、alias 建议为 s；S4 操作类型为 QUERY，过滤条件和返回字段按 ship.md 及用户问题生成；空结果不重试；最终输出 objects/relationships。
缺失信息：没有则写无。
```

## 7. 流程级定制规则

- 船舶明细查询默认执行 S1/S2/S3/S4/S7。
- 不规划 S5/S6 Function，除非用户明确要求调用业务算法。
- 如果用户只问模型字段或对象定义，可以在 S3 后结束。
- 如果用户要求关联泊位、缆桩、设备等对象，则 S3 应规划 ASSOCIATION_QUERY 路径任务。

## 8. 步骤级定制规则

### S2 子图检索

- 检索目标：船舶信息对象、船舶字段、必要时检索船舶计划和泊位关系。
- 返回结构要求：保留完整 `result.nodes`、`result.edges`，并摘要输出字段归属和关系候选。
- 不得提前编造字段；字段最终以子图 `has_property` 确认为准。

### S3 基于子图规划

- 单对象船舶信息查询规划为 `QUERY`。
- 关联泊位、计划、设备时才规划 `ASSOCIATION_QUERY`。
- 规划时必须说明对象、字段、关系分别来自哪个子图节点或边。

### S4 OAC 查询

- 查询对象：`ship_info`，alias 建议 `s`。
- 操作类型：船舶信息明细查询为 `QUERY`。
- 过滤条件：船高范围、船舶类型、吃水深度等，单位 m/米 去掉后保留数值字符串。
- 返回要求：用户指定字段优先；典型返回 `ship_no, ship_type, ship_height, draft, loa`。
- 输出要求：最终只返回 `{objects, relationships}` 对象结构；不把 operationDecision、oql、validation 作为最终输出字段。
- 空结果视为有效结果，不自动放宽条件重试。

## 9. 强约束

1. 业务定制文件 `knowledge/ship.md` 是业务定制模式必填输入。
2. 字段必须来自业务知识映射，并由本体子图 `has_property` 确认归属。
3. `has_property` 不得当作对象间业务关系。
4. `defines_relation` 才能作为对象关系来源。
5. 用户指定或默认返回字段必须显式列出，不使用 `*`。
6. 最终 OQL 必须使用 `version: "1.0"`。
7. 本体访问返回空结果时，不自动放宽条件、不重复查询。
