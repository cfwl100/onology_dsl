---
name: default-planning-mode-demo
description: 默认规划模式业务 Skill 示例。用于演示上层业务 Skill 不提供完整 steps，只传入业务目标、ontologyId、schemaRef 和少量实体变量，由 Ontology-based-planning-skill 使用默认本体子图规划流程生成执行步骤。
allowed_tools:
---

# 默认规划模式业务 Skill 示例

## 使用场景

当业务侧只知道用户目标，但还没有定制 SOP 或完整执行步骤时，使用本示例模式。

典型请求：

- 查询船舶类型为货轮且船高大于 10 的船舶信息。
- 查询船舶及其船舶计划。
- 找到和船舶相关的对象、字段和关系，并完成默认查询规划。

## 职责边界

你是上层业务 Skill 示例，只负责提供最小业务上下文：

1. 识别用户目标。
2. 提取对象、实体、过滤条件、返回要求。
3. 注入 `ontologyId` 和 `schemaRef`。
4. 委托 `Ontology-based-planning-skill` 走默认规划流程。

你不生成完整 steps，不直接生成查询语言，不直接调用平台能力。

## 传给本体规划层的输入

当用户请求“查询船高大于 10 的货轮”时，构造如下语义请求并委托给 `Ontology-based-planning-skill`：

```json
{
  "goal": "查询满足条件的船舶信息",
  "intent": "默认本体查询规划",
  "entities": {
    "startObjectHint": "ship_info"
  },
  "variables": {
    "ontologyId": "dtmi.ontology.560d88f7.1",
    "schemaRef": "dtmi.ontology.560d88f7.1",
    "filters": [
      {
        "field": "ship_height",
        "operator": "GT",
        "value": 10
      },
      {
        "field": "ship_type",
        "operator": "EQ",
        "value": "货轮"
      }
    ]
  },
  "constraints": {
    "returnFields": ["ship_type", "ship_height"],
    "maxResults": 1000
  }
}
```

## 委托规则

必须将上述输入交给 `Ontology-based-planning-skill`。

规划层会默认执行：

1. 归一化语义请求。
2. 检索本体子图。
3. 从子图中识别 `objectType`、`property`、`has_property`、`defines_relation`。
4. 生成数据访问步骤。
5. 校验字段归属和关系来源。
6. 委托 `Ontology-platform-unified-skill` 完成平台能力调用。

## 禁止事项

- 禁止跳过本体子图检索直接拼查询语言。
- 禁止把 `has_property` 当成对象间关系。
- 禁止把未通过 `has_property` 确认归属的字段写入对象。
- 禁止自行臆造关系名、字段名或函数参数。
