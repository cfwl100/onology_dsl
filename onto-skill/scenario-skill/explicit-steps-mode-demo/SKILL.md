---
name: explicit-steps-mode-demo
description: 显式步骤执行模式 Skill 示例。上层业务已经给出完整执行步骤，Ontology-based-planning-skill 只负责检查、绑定、委托执行和汇总；每个 OAG/OAC/Function 步骤仍必须使用自然语言输入模板。
allowed_tools:
---

# 显式步骤执行模式 Skill 示例

## 定位

你是上层业务 Skill 示例。当业务侧已经明确执行步骤时，可以直接构造 `steps` 传给 `Ontology-based-planning-skill`。

此模式适合：

- 业务 SOP 已经固定。
- 查询路径和返回目标已经明确。
- 希望规划层只做步骤检查、执行委托、结果绑定和汇总。

## 显式步骤规则

即使使用显式步骤，仍必须遵守：

- 对外只使用公共 `本体ID`，不要求同时填写 `ontologyId` 和 `schemaRef`。
- 每个 OAG、OAC、Function 步骤的 `input` 必须是对应模块的自然语言输入模板。
- OAC 步骤仍必须依赖 OAG 子图结果确认对象、字段、关系。
- Function 步骤仍必须基于 `result.functions` 或可信函数目标。

## 传给规划层的显式步骤输入示例

```json
{
  "intent": "按固定步骤查询船舶及船舶计划信息",
  "ontologyId": "dtmi.ontology.560d88f7.1",
  "steps": [
    {
      "stepId": "step1_search_subgraph",
      "actionType": "OAG",
      "input": "先找相关子图。\n本体ID：dtmi.ontology.560d88f7.1\n业务意图：查询船舶及其船舶计划信息，需要从船舶对象出发查找到船舶计划对象。\n业务定制文件：无。\n子图检索规则：检索 ship_info、ship_plan、对象属性和对象关系相关本体子图。\n检索目标：查找船舶对象、船舶计划对象、字段归属和对象间关系。\n子图返回结构要求：保留 result.seedNodes、result.nodes、result.edges、result.functions、result.actions 完整结构。\n期望输出：返回原始图结构 JSON，并摘要对象、字段归属和关系候选。",
      "expectedOutput": "返回 ship_info、ship_plan、属性字段和关系边"
    },
    {
      "stepId": "step2_plan_from_subgraph",
      "actionType": "SUBGRAPH_PLAN",
      "dependsOn": ["step1_search_subgraph"],
      "input": "基于本体子图规划执行任务。\n本体ID：dtmi.ontology.560d88f7.1\n业务意图：基于船舶到船舶计划的子图结构规划关联查询任务。\n本体子图结果：绑定 step1_search_subgraph 输出。\n业务定制规划规则文件：无。\n规划目标：从【ship_info】出发，查找到【ship_plan】。\n可用结构依据：使用子图确认的 objectType、property、has_property、defines_relation。\n业务规划规则：如果存在对象间关系，规划 ASSOCIATION_QUERY；否则返回缺失关系。\n期望输出：返回 OAC 计划步骤和所需查询依据。",
      "expectedOutput": "返回基于子图的关联查询任务规划"
    },
    {
      "stepId": "step3_query_data",
      "actionType": "OAC",
      "dependsOn": ["step2_plan_from_subgraph"],
      "input": "查数据\n本体ID：dtmi.ontology.560d88f7.1\n操作类型：ASSOCIATION_QUERY\n查询对象：来自子图的 ship_info 和 ship_plan。\n关系路径：使用 step2 规划出的 defines_relation.properties.name。\n过滤条件：如用户提供船舶类型或船舶编号，使用子图确认字段。\n返回要求：返回船舶和船舶计划相关字段，maxResults 为1000，空结果视为有效结果。\n执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。\n期望输出：返回操作类型判断、OQL JSON、校验结果、执行状态、数据结果或缺失项。",
      "expectedOutput": "返回船舶和船舶计划数据"
    },
    {
      "stepId": "step4_summary",
      "actionType": "SUMMARY",
      "dependsOn": ["step3_query_data"],
      "input": "汇总查询结果，保留平台返回字段，说明使用的本体ID、子图依据、OQL 执行状态和空结果情况。",
      "expectedOutput": "自然语言汇总结果"
    }
  ]
}
```

## 规划层职责

`Ontology-based-planning-skill` 收到上述输入后：

1. 检查每个 step 是否包含 `stepId`、`actionType`、`input`、`expectedOutput`。
2. 检查 OAG、OAC、Function 步骤是否使用自然语言输入模板。
3. 执行子图检索后解析子图。
4. 执行 OAC 前确认字段归属和关系来源。
5. 汇总时保留平台返回字段，不做字段归一化。

## 约束

- 显式 steps 不代表可以绕过子图校验。
- `OAC` 步骤仍必须使用子图中的对象、字段和关系。
- 查询结果为空时，不自动重复查询。
