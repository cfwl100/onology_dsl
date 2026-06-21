---
name: explicit-steps-mode-demo
description: 显式步骤执行模式 Skill 示例。上层业务已经给出完整执行步骤，Ontology-based-planning-skill 只负责检查、绑定、委托执行和汇总。
allowed_tools:
---

# 显式步骤执行模式 Skill 示例

## 定位

你是上层业务 Skill 示例。当业务侧已经明确执行步骤时，可以直接构造 `steps` 传给 `Ontology-based-planning-skill`。

此模式适合：

- 业务 SOP 已经固定。
- 查询路径和返回目标已经明确。
- 希望规划层只做步骤检查、执行委托、结果绑定和汇总。

## 传给规划层的显式步骤输入

```json
{
  "intent": "显式船舶计划查询",
  "goal": "按固定步骤查询船舶及船舶计划信息",
  "variables": {
    "ontologyId": "dtmi.ontology.560d88f7.1",
    "schemaRef": "dtmi.ontology.560d88f7.1"
  },
  "steps": [
    {
      "stepId": "step1_search_subgraph",
      "actionType": "OAG",
      "input": {
        "query": "先找相关子图：从 ship_info 出发，查找到 ship_plan",
        "ontologyId": "dtmi.ontology.560d88f7.1"
      },
      "expectedOutput": "返回 ship_info、ship_plan、属性字段和关系边"
    },
    {
      "stepId": "step2_query_data",
      "actionType": "OAC",
      "dependsOn": ["step1_search_subgraph"],
      "input": {
        "queryGoal": "查数据：查询 ship_info 及其关联 ship_plan 信息",
        "schemaRef": "dtmi.ontology.560d88f7.1",
        "maxResults": 1000
      },
      "expectedOutput": "返回船舶和船舶计划数据"
    },
    {
      "stepId": "step3_summary",
      "actionType": "SUMMARY",
      "dependsOn": ["step2_query_data"],
      "input": {
        "summaryGoal": "汇总查询结果，保留平台返回字段"
      },
      "expectedOutput": "自然语言汇总结果"
    }
  ]
}
```

## 规划层职责

`Ontology-based-planning-skill` 收到上述输入后：

1. 检查每个 step 是否包含 `stepId`、`actionType`、`input`、`expectedOutput`。
2. 执行 `step1_search_subgraph` 后解析子图。
3. 执行 `step2_query_data` 前确认字段归属和关系来源。
4. 执行 `step3_summary` 时保留平台返回字段，不做字段归一化。

## 约束

- 显式 steps 不代表可以绕过子图校验。
- `OAC` 步骤仍必须使用子图中的对象、字段和关系。
- 查询结果为空时，不自动重复查询。
