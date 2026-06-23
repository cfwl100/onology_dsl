---
name: berth-plan-ontology
description: 集装箱泊位计划本体数据查询业务定制 Skill。识别泊位计划查询场景，并按当前 6 行 Planning 输入协议委托 Ontology-based-planning-skill。
allowed_tools:
metadata:
  mode: customized_planning
  planning_protocol: six-line-business-domain-knowledge
  planning_steps: S1-S6
  scenario: container-berth-plan-ontology
---

# 集装箱泊位计划本体业务定制 Skill

## 1. 任务概述

本 Skill 是泊位计划业务语义层，只负责识别场景、组织业务领域知识、抽取条件和返回要求，然后委托 `Ontology-based-planning-skill`。

不得直接调用平台能力，不得绕过 Planning 层。

## 2. 固定上下文

| 字段 | 值 |
|---|---|
| 对外公共 `本体ID` | `dtmi.ontology.560d88f7.1` |
| OQL 版本 | `1.0` |
| 默认 Planning 层 | `Ontology-based-planning-skill` |

对外只传递公共 `本体ID`，不得同时传 `ontologyId` 和 `schemaRef`。

## 3. 业务领域知识

用户查询船舶信息时，业务知识以 `knowledge/ship.md` 为准；Mock 测试可使用 `knowledge/ship.json` 或 `docs/ontology_subgraph.json` 作为本体子图样例。

支持对象包括：`ship_info`、`ship_plan`、`berth_info`、`bollard_info`、`berth_bollard_coords`、`berth_display_order`、`equipment_infos`、`tide_info`。

字段必须由本体子图中的 `has_property` 确认归属；对象间关系必须来自本体子图中的 `defines_relation`。

## 4. Planning 层步骤编号

当前 Planning 步骤固定为：

```text
S1 子图检索
S2 基于本体子图的任务规划
S3 OAC 查询
S4 Function 发现
S5 Function 执行
S6 汇总
```

泊位计划常规查询默认流程：

```text
S1 -> S2 -> S3 -> S6
```

只有用户明确要求排泊算法、效率评估、能耗优化等 Function 时，才追加 S4/S5。

## 5. 输出给 Planning 层的 6 行模板

向 Planning 层发送自然语言定制说明：

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：<基于用户输入改写后的详细自然语言查询问题，需包含查询对象、过滤条件、返回字段和 maxResults 要求>
业务领域知识：<规则来源 knowledge/ship.md；船舶对象、字段映射、子图检索规则、任务规划规则、查询规则、返回要求和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖；无覆盖写“使用默认流程 S1 -> S2 -> S3 -> S6；不执行 S4/S5 Function”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板；业务增量规则见业务领域知识”>
缺失信息：<没有则写无>
```

禁止输出旧字段 `已读取业务定制文件`、`业务定制文件内容`，禁止输出复杂 `steps` JSON、`planningDelegationPackage` 或 `stepContracts`。

## 6. 船舶信息查询默认定制

典型写法：

```text
业务意图：查询船舶信息，过滤条件包括船高范围、船舶类型、吃水深度，返回 ship_no、ship_type、ship_height、draft、loa，maxResults 为 1000。
业务领域知识：规则来源 knowledge/ship.md；ship_info 是船舶信息对象；船高对应 ship_height，船舶类型对应 ship_type，吃水对应 draft，船长对应 loa；字段必须由 S1 子图中的 has_property 确认归属；单对象明细查询使用 QUERY；空结果是有效结果。
流程级定制：使用默认流程 S1 -> S2 -> S3 -> S6；不执行 S4/S5 Function。
步骤级定制：S1 检索 ship_info 和船舶字段；S2 规划 ship_info 单对象 QUERY，alias 建议为 s；S3 查询返回 objects/relationships；S6 汇总对象结构和空结果说明。
缺失信息：无
```

## 7. 步骤级业务增量规则

### S1 子图检索

- 检索船舶信息对象、船舶字段，必要时检索船舶计划和泊位关系。
- 返回原始 `result.nodes`、`result.edges`，并摘要字段归属和关系候选。
- 字段最终以子图 `has_property` 确认为准。

### S2 基于子图规划

- 单对象船舶信息查询规划为 `QUERY`。
- 关联泊位、计划、设备时规划 `ASSOCIATION_QUERY`。
- 对象、字段、关系必须能追溯到 S1 子图。

### S3 OAC 查询

- 查询对象：`ship_info`，alias 建议 `s`。
- 船舶信息明细查询使用 `QUERY`。
- 过滤条件包含船高范围、船舶类型、吃水深度等。
- 返回字段优先使用用户指定；典型返回 `ship_no, ship_type, ship_height, draft, loa`。
- 最终只返回 `{objects, relationships}` 对象结构。
- 空结果视为有效结果，不自动放宽条件。

### S6 汇总

- 保留平台返回的对象结构。
- 说明本体子图确认的对象、字段和关系依据。
- 如果结果为空，说明按业务规则空结果有效。

## 8. 强约束

1. 字段必须来自业务知识映射，并由本体子图 `has_property` 确认归属。
2. `has_property` 不得当作对象间业务关系。
3. `defines_relation` 才能作为对象关系来源。
4. 用户指定或默认返回字段必须显式列出，不使用 `*`。
5. 本体访问返回空结果时，不自动放宽条件、不重复查询。
