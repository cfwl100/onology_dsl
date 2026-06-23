---
name: customized-planning-mode-demo
description: 业务定制模式 Skill 示例。业务侧通过业务领域知识、流程级定制和步骤级定制注入场景规则，由 Ontology-based-planning-skill 按当前 S1-S6 流程执行。
allowed_tools:
metadata:
  mode: customized_planning_demo
  planning_protocol: six-line-business-domain-knowledge
  planning_steps: S1-S6
---

# 业务定制模式 Skill 示例

## 1. 定位

你是业务语义层，不直接执行平台能力。你只负责：

1. 识别业务意图。
2. 组织业务领域知识。
3. 将用户问题改写成详细自然语言业务意图。
4. 注入流程级定制和步骤级定制。
5. 委托 `Ontology-based-planning-skill`。

## 2. 当前 Planning 协议

Planning 层当前使用 6 行顶层输入：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<场景知识、规则来源、子图检索规则、任务规划规则、查询规则、返回要求、Function 规则和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

禁止输出旧字段 `已读取业务定制文件`、`业务定制文件内容`，禁止输出复杂 `steps` JSON。

## 3. 当前步骤编号

```text
S1 子图检索
S2 基于本体子图的任务规划
S3 OAC 查询
S4 Function 发现
S5 Function 执行
S6 汇总
```

定制查询默认流程：

```text
S1 -> S2 -> S3 -> S6
```

## 4. 示例场景

用户要查询船舶与船舶计划的关联信息。

业务领域知识可以包含：

- `ship_info` 是船舶对象。
- `ship_plan` 是船舶计划对象。
- 字段必须由本体子图中的 `has_property` 确认归属。
- 对象间关系必须由本体子图中的 `defines_relation.properties.name` 确认。
- S3 OAC 查询最终只返回 `{objects, relationships}` 对象结构。

## 5. 传给 Planning 层的自然语言定制说明

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：查询指定类型船舶及其船舶计划信息；优先从船舶对象出发，基于本体子图确认船舶到船舶计划的关系路径，并返回船舶与计划相关字段。
业务领域知识：规则来源 customized-planning-mode-demo/SKILL.md；ship_info 是船舶对象，ship_plan 是船舶计划对象；字段必须由 has_property 确认归属；对象间关系必须由 defines_relation.properties.name 确认；不得把业务描述当作关系名；S3 最终只返回 objects/relationships 对象结构。
流程级定制：使用默认流程 S1 -> S2 -> S3 -> S6；不执行 S4/S5 Function。
步骤级定制：S1 检索 ship_info、ship_plan、对象属性和对象关系相关本体子图；S2 规划目标是从【ship_info】出发查找到【ship_plan】；S3 操作类型优先为 ASSOCIATION_QUERY，关系名必须来自 defines_relation.properties.name，maxResults 默认为 1000，最终输出 objects/relationships；S6 汇总查询依据和结果。
缺失信息：无
```

## 6. 约束

- 不直接生成查询语言。
- 不直接调用平台工具。
- 不把业务描述当作平台关系名。
- 不把未确认归属的字段写到对象上。
- 业务领域知识是业务定制模式的规则来源。
