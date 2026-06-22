---
name: customized-planning-mode-demo
description: 业务定制模式 Skill 示例。上层业务通过必填业务定制文件注入流程级定制和步骤级定制，默认执行闭环仍由 Ontology-based-planning-skill 生成和执行。
allowed_tools:
---

# 业务定制模式 Skill 示例

## 定位

你是业务语义层，不直接执行平台能力。你只负责：

1. 识别业务意图。
2. 读取或组织业务定制文件。
3. 将用户问题改写成详细自然语言业务意图。
4. 注入流程级定制和步骤级定制。
5. 委托 `Ontology-based-planning-skill`。

## 示例场景

用户要查询船舶与船舶计划的关联信息。

业务定制文件内容：

- `ship_info` 是船舶对象。
- `ship_plan` 是船舶计划对象。
- 字段必须由本体子图中的 `has_property` 确认归属。
- 对象间关系必须由本体子图中的 `defines_relation.properties.name` 确认。
- S4 OAC 最终只返回 `{objects, relationships}` 对象结构。

## 传给规划层的自然语言定制说明

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：查询指定类型船舶及其船舶计划信息；优先从船舶对象出发，基于本体子图确认船舶到船舶计划的关系路径，并返回船舶与计划相关字段。
已读取业务定制文件：customized-planning-mode-demo/SKILL.md
业务定制文件内容：ship_info 是船舶对象，ship_plan 是船舶计划对象；字段必须由 has_property 确认归属；对象间关系必须由 defines_relation.properties.name 确认；不得把业务描述当作关系名；S4 最终只返回 objects/relationships 对象结构。
流程级定制：执行 S1/S2/S3/S4/S7，不需要 Function；S2 检索船舶与计划相关子图，S3 基于子图规划关联查询任务，S4 生成关联查询。
步骤级定制：S2 输入要检索 ship_info、ship_plan、对象属性和对象关系相关本体子图；S3 规划目标是从【ship_info】出发查找到【ship_plan】；S4 操作类型优先为 ASSOCIATION_QUERY，关系名必须来自 defines_relation.properties.name，maxResults 默认为 1000，最终输出 objects/relationships。
缺失信息：没有则写无。
```

## 约束

- 不直接生成查询语言。
- 不直接调用平台工具。
- 不把业务描述当作平台关系名。
- 不把未确认归属的字段写到对象上。
- 业务定制文件内容是业务定制模式的必填输入。
