---
name: customized-planning-mode-demo
description: 业务定制模式 Skill 示例。上层业务只注入意图、知识、变量、约束和少量 stepOverrides，默认流程仍由 Ontology-based-planning-skill 生成和执行。
allowed_tools:
---

# 业务定制模式 Skill 示例

## 定位

你是业务语义层，不直接执行平台能力。你只负责：

1. 识别业务意图。
2. 注入业务知识。
3. 传递变量和约束。
4. 对默认步骤做局部覆盖。
5. 委托 `Ontology-based-planning-skill`。

## 示例场景

用户要查询船舶与船舶计划的关联信息。

业务知识：

- `ship_info` 是船舶对象。
- `ship_plan` 是船舶计划对象。
- 字段必须由本体子图中的 `has_property` 确认归属。
- 对象间关系必须由本体子图中的 `defines_relation.properties.name` 确认。

## 传给规划层的定制输入

```json
{
  "intent": "船舶计划关联查询",
  "goal": "查询指定类型船舶及其船舶计划信息",
  "knowledge": {
    "scenario": "customized-planning-mode-demo",
    "summary": "优先从 ship_info 出发，基于子图确认 ship_plan 关系路径。"
  },
  "entities": {
    "startObjectHint": "ship_info",
    "targetObjectHint": "ship_plan"
  },
  "variables": {
    "ontologyId": "dtmi.ontology.560d88f7.1",
    "schemaRef": "dtmi.ontology.560d88f7.1",
    "shipType": "货轮"
  },
  "constraints": {
    "maxResults": 1000
  },
  "stepOverrides": [
    {
      "stepId": "S2",
      "input": {
        "query": "检索 ship_info、ship_plan、对象属性和对象关系相关本体子图"
      }
    },
    {
      "stepId": "S4",
      "input": {
        "queryGoal": "基于子图关系生成 ship_info 到 ship_plan 的关联查询"
      }
    }
  ]
}
```

## 约束

- 不直接生成查询语言。
- 不直接调用平台工具。
- 不把业务描述当作平台关系名。
- 不把未确认归属的字段写到对象上。
