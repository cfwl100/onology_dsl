---
name: default-planning-mode-demo
description: 默认规划模式业务 Skill 示例。用于演示上层业务 Skill 不提供完整 steps，也不提供复杂业务定制，只传入公共本体ID和详细业务意图，由 Ontology-based-planning-skill 走默认本体子图规划流程。
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
2. 将用户问题改写成详细自然语言业务意图。
3. 提供公共 `本体ID`。
4. 委托 `Ontology-based-planning-skill` 走默认规划流程。

你不生成完整 steps，不直接生成查询语言，不直接调用平台能力，不提前臆造对象、字段或关系。

## 传给本体规划层的输入

当用户请求“查询船高大于 10 的货轮”时，构造如下自然语言输入并委托给 `Ontology-based-planning-skill`：

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：查询船舶信息，过滤条件为船高大于10且船舶类型为货轮；希望返回船舶类型和船高，maxResults 为1000；请先检索相关本体子图，再基于子图确认对象、字段归属和是否需要数据访问。
缺失信息：没有则写无。
```

说明：

- `本体ID` 是对外公共本体标识，planning 层会把它传给子图检索，并在数据访问时作为 `schemaRef` 来源。
- `业务意图` 是详细自然语言任务，不是短标签。
- “船高”“船舶类型”“返回字段”等只是用户期望，最终必须通过本体子图的 `has_property` 确认字段归属后才能进入查询语言。

## 委托规则

必须将上述输入交给 `Ontology-based-planning-skill`。

规划层会默认执行：

1. 读取输入并整理上下文。
2. 使用业务意图检索本体子图。
3. 基于本体子图规划执行任务。
4. 从子图中识别 `objectType`、`property`、`has_property`、`defines_relation`。
5. 如需要数据访问，生成 OAC 委托输入。
6. 校验字段归属和关系来源。
7. 委托 `Ontology-platform-unified-skill` 完成平台能力调用。

## 禁止事项

- 禁止跳过本体子图检索直接拼查询语言。
- 禁止把 `has_property` 当成对象间关系。
- 禁止把未通过 `has_property` 确认归属的字段写入对象。
- 禁止自行臆造关系名、字段名或函数参数。
- 禁止要求业务侧同时填写 ontologyId 和 schemaRef。
