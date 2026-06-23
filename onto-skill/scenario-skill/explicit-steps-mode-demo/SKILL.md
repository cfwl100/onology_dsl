---
name: explicit-steps-mode-demo
description: 显式流程定制模式 Skill 示例。业务侧明确流程级和步骤级定制，仍按当前 6 行 Planning 输入协议委托 Ontology-based-planning-skill。
allowed_tools:
metadata:
  mode: explicit_flow_demo
  planning_protocol: six-line-business-domain-knowledge
  planning_steps: S1-S6
---

# 显式流程定制模式 Skill 示例

## 1. 定位

你是上层业务 Skill 示例。业务侧已经明确流程和每步业务规则时，仍然使用 6 行自然语言顶层模板交给 `Ontology-based-planning-skill`。

不要构造 JSON steps。

## 2. 当前 Planning 输入

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<场景知识、规则来源、子图检索规则、任务规划规则、查询规则、返回要求、Function 规则和失败策略；没有则写无>
流程级定制：<明确步骤顺序、跳过和追加；无覆盖写“使用默认流程”>
步骤级定制：<逐步说明相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

## 3. 当前步骤编号

```text
S1 子图检索
S2 基于本体子图的任务规划
S3 OAC 查询
S4 Function 发现
S5 Function 执行
S6 汇总
```

## 4. 示例

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：查询船舶及其船舶计划信息；从船舶对象出发，基于本体子图确认船舶到船舶计划的关系路径，并返回船舶与计划相关字段。
业务领域知识：ship_info 是船舶对象，ship_plan 是船舶计划对象；字段必须由 has_property 确认归属；对象间关系必须由 defines_relation.properties.name 确认；空结果视为有效结果。
流程级定制：使用流程 S1 -> S2 -> S3 -> S6；不使用 S4/S5 Function。
步骤级定制：S1 检索 ship_info、ship_plan、字段归属和对象关系子图；S2 规划从 ship_info 到 ship_plan 的关联查询任务；S3 使用 ASSOCIATION_QUERY，关系名来自 defines_relation.properties.name，返回 objects/relationships；S6 汇总子图依据、查询依据和结果。
缺失信息：无
```

## 5. 约束

- 显式流程定制不能绕过子图校验。
- S3 使用 S1/S2 确认的对象、字段和关系。
- Function 只在业务领域知识或流程级定制明确要求时进入 S4/S5。
- 结果为空时，不自动放宽条件。
