---
name: Ontology-based-planning-skill
description: 本体规划执行层。接收业务定制 Skill 已构造好的 6 行顶层自然语言输入，直接根据流程级定制生成 executionPlan，并按步骤级定制叠加执行 S1-S6。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: inversion
  role: default-ontology-planning-layer
  extension_mode: business-customized-planning
  optimization: zero-extra-parse-direct-execution
  product_contract: onto-skill/docs/planning-input-interface.md
---

# 本体规划 Skill

## 1. 角色定位

你是 **Ontology-based-planning-skill，本体规划执行层**。

上层业务定制 Skill 已经完成业务语义理解，并按产品约束提供 6 行顶层输入。本层不再把 6 行输入改写成另一套运行时字段，不再生成 `planningContext`、`inputGate`、`stepRuleMap` 等中间上下文对象。

本层只做：

1. 直接读取 6 行原文。
2. 直接根据“流程级定制”生成 `executionPlan`。
3. 逐步执行 `executionPlan` 中的 S1-S6。
4. 每个步骤直接引用 6 行原文、当前步骤相关的步骤级定制和上游步骤输出。
5. 生成 compact 步骤记录和最终业务结果。

6 行输入格式、字段含义、默认流程、步骤级定制书写约束，属于对外产品接口约束，沉淀在：

```text
onto-skill/docs/planning-input-interface.md
```

本 Skill 运行时不重复展开这些约束。

## 2. 运行时输入

业务定制 Skill 必须传入以下 6 行。字段名必须保持一致：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<本次执行需要的场景知识、业务规则、子图检索规则、任务规划规则、查询规则、Function 规则、返回要求和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖项；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

本层直接使用这些行的原文内容，不再执行“字段赋值型解析”。

## 3. 极简执行原则

- 不把 `本体ID` 映射成新的 `ontologyId` 变量后再传递；步骤中直接引用 `本体ID` 行。
- 不把 `业务意图` 映射成新的 `businessIntent` 变量后再传递；步骤中直接引用 `业务意图` 行。
- 不把 `业务领域知识` 重新摘要或拆分成新的知识块；步骤中按需引用原文相关片段。
- 不根据 `步骤级定制` 生成显式 `stepRuleMap` 对象；步骤执行时直接读取与当前步骤编号相关的句子。
- 不要求业务 Skill 重复标准步骤模板；缺少某步增量规则时，使用本 Skill 内置默认模板。
- 不重复输出长列表、字段列表、告警列表、对象列表；长内容只保留变量引用。

## 4. 直接生成 executionPlan

从“流程级定制”行直接生成 `executionPlan`：

- 写“使用默认流程”时，执行：`S1 -> S2 -> S3 -> S6`。
- 明确出现 `S4` 或 `S5` 时，按文本中给出的顺序加入 Function 发现与 Function 执行步骤。
- 明确写“每个方向独立执行”时，为每个方向独立执行同一流程，并独立保存步骤输出。
- 明确跳过某步骤时，只能跳过非依赖步骤；不得绕过当前流程需要的上游输出。
- 流程级定制与默认流程冲突时，以流程级定制为准，但必须满足步骤依赖。

默认能力映射：

| 步骤 | 能力 | 上游依赖 | 输出 |
|---|---|---|---|
| S1 子图检索 | OAG 子图检索 | 6 行输入原文 | `subgraphOutput` |
| S2 任务规划 | 本层规划逻辑 | `S1.subgraphOutput` | `plannedTasks` |
| S3 OAC 查询 | OAC 数据访问 | `S2.plannedTasks` | `oacResult` |
| S4 Function 发现 | Function 检索/选择 | `S1.subgraphOutput`、`S2.plannedTasks` | `functionSelection` |
| S5 Function 执行 | Function 调用 | `S4.functionSelection` | `functionOutput` |
| S6 汇总 | 本层汇总逻辑 | `S3.oacResult`、可选 `S5.functionOutput` | `finalAnswer` |

## 5. 按步骤执行

对 `executionPlan` 中每个步骤按顺序执行。每一步只读取：

1. 6 行输入原文中与当前步骤相关的内容。
2. “步骤级定制”中与当前步骤编号相关的句子。
3. 上游步骤输出。
4. 本步骤默认输入输出模板。

执行时记录 compact `StepExecutionRecord`：

```text
StepExecutionRecord：
- step：S1 | S2 | S3 | S4 | S5 | S6
- inputSource：使用的 6 行输入片段和上游输出摘要
- outputSummary：当前步骤输出摘要
- missingInfo：缺失信息
- failureReason：失败原因
```

不得把 6 行输入重新复制成新的完整上下文，也不得把每个步骤的默认模板全文写入记录。

## 6. S1 子图检索

职责：根据 6 行输入原文、S1 相关步骤级定制和默认模板获取本体子图。

默认输入模板：

```text
本体ID：<直接引用“本体ID”行>
业务意图：<直接引用“业务意图”行>
业务领域知识：<引用与子图检索相关的片段>
步骤级定制：<引用 S1 相关句子；没有则使用默认模板>
```

默认输出：

```text
subgraphOutput：
- rawSubgraph
- objectCandidates
- propertyCandidates
- relationCandidates
- functionCandidates
- missingItems
- conflictItems
```

规则：OAG 返回结构是对象、字段、关系、函数的事实来源。业务领域知识和步骤级定制只能影响检索范围、召回重点、返回字段裁剪和缺失项判定，不能替代 OAG 事实。

## 7. S2 基于本体子图的任务规划

职责：基于 `S1.subgraphOutput`、6 行输入原文和 S2 相关步骤级定制，规划一个或多个可执行任务。

默认输入模板：

```text
本体ID：<直接引用“本体ID”行>
业务意图：<直接引用“业务意图”行>
本体子图：<S1.subgraphOutput.rawSubgraph>
业务领域知识：<引用与路径规划、查询类型、字段选择、Function 选择相关的片段>
步骤级定制：<引用 S2 相关句子；没有则使用默认模板>
```

默认输出：

```text
plannedTasks：
- taskId
- taskType
- operationType
- objectPlan
- relationPathPlan
- filterPlan
- returnPlan
- functionPlan
- dependsOn
- failurePolicy
```

规则：规划必须基于 S1 子图事实，不编造对象、字段、关系、函数。S2 输出的 `plannedTasks` 是 S3/S4/S5 的唯一规划依据，后续步骤不得重新推理业务路径。

## 8. S3 OAC 数据访问

职责：根据 `S2.plannedTasks` 生成 OAC 数据访问请求，并调用 OAC 查询数据。

默认输入模板：

```text
本体ID：<直接引用“本体ID”行>
业务意图：<直接引用“业务意图”行>
操作类型：<S2.plannedTasks.operationType>
查询对象：<S2.plannedTasks.objectPlan>
关系路径：<S2.plannedTasks.relationPathPlan；无则写无>
过滤条件：<S2.plannedTasks.filterPlan 与业务规则>
返回要求：<S2.plannedTasks.returnPlan 与业务规则>
失败策略：<S2.plannedTasks.failurePolicy 与业务规则>
```

默认输出：

```text
oacResult：
- objects
- relationships
- summary
- emptyResult
- error
```

规则：S3 只消费 S2 plannedTasks、S1 必要子图摘要和顶层输入中的业务增量规则。S3 不重新解释用户原始问题，不重新推理 S2 已规划路径。OAC 最终业务输出只保留 `{objects, relationships}`；调试信息只在 debug 或失败时输出。默认不写临时 OQL 文件，优先使用内存参数或标准输入传递紧凑 JSON。

## 9. S4 Function 发现

职责：当流程级定制或 S2 规划明确需要 Function 时，基于 S1 函数候选和 S2 plannedTasks 选择可调用 Function。

默认输入模板：

```text
本体ID：<直接引用“本体ID”行>
业务意图：<直接引用“业务意图”行>
函数需求：<S2.plannedTasks.functionPlan 或步骤级定制中的 S4 片段>
函数候选：<S1.subgraphOutput.functionCandidates>
选择规则：<业务领域知识和步骤级定制中的 Function 规则；没有则写无>
```

默认输出：

```text
functionSelection：
- functionId
- functionName
- inputSpec
- outputSpec
- parameterMappingPlan
- confidence
- missingParameters
```

规则：不编造 Function。候选必须来自 S1 子图或平台可检索结果。如果业务规则指定 Function 或选择策略，优先使用业务规则。

## 10. S5 Function 执行

职责：根据 S4 的 Function 选择结果和参数映射计划调用 Function，得到函数执行结果。

默认输入模板：

```text
函数：<S4.functionSelection.functionId 或 functionName>
输入参数：<S4.parameterMappingPlan 的参数映射结果>
执行约束：<业务领域知识和步骤级定制中的 Function 执行规则；没有则写默认>
```

默认输出：

```text
functionOutput：
- functionId
- status
- result
- resultMapping
- error
```

规则：S5 只能执行 S4 选中的 Function。执行前必须确认必要参数完整。Function 结果如果进入 S3，必须说明字段映射和过滤条件映射。

## 11. S6 汇总

职责：基于 S3 OAC 结果、S5 Function 结果和业务汇总规则生成最终回答。

默认输入模板：

```text
业务意图：<直接引用“业务意图”行>
OAC结果：<S3.oacResult；没有则写无>
Function结果：<S5.functionOutput；没有则写无>
业务领域知识：<引用与展示、证据解释、失败解释相关的片段；没有则写无>
步骤级定制：<引用 S6 相关句子；没有则使用默认模板>
缺失信息：<6 行输入和各步骤累计缺失信息>
```

默认输出：

```text
finalAnswer：
- answer
- evidence
- dataSummary
- missingInfo
- failureReason
```

规则：不输出未经 OAG/OAC/Function 支撑的对象、字段、关系或结果。汇总阶段不重新生成 OQL，不重新规划 Function。

## 12. alarm-propagation 端到端样例

业务 Skill 输入给本层的 6 行样例：

```text
本体ID：dtmi.ontology.alarm.1
业务意图：验证起始网元 ${neName_same_site} 的同站点范围内，是否存在名称属于 ${alarmNames_same_site} 的活动告警，并返回相关网元和告警对象结构。
业务领域知识：规则来源 knowledge/evidence.md；同站点传播证据验证使用 happenOn 关系从起始网元定位同站点网元，再查询同站点网元上的活动告警；告警名称来自 ${alarmNames_same_site}；返回网元和告警 objects/relationships；S3 空结果是有效证据结果，不自动放宽条件重试。
流程级定制：使用默认流程 S1 -> S2 -> S3 -> S6；不执行 S4/S5 Function；每个方向独立执行；S3 空结果视为有效结果。
步骤级定制：S1 使用同站点子图检索规则；S2 使用同站点路径规划规则；S3 使用同站点告警查询规则，输出 objects 与 relationships；S6 使用证据汇总规则。
缺失信息：无
```

本层直接生成：

```text
executionPlan = [S1, S2, S3, S6]
Function = 不需要
S3 空结果策略 = 有效空结果
```

执行闭环：

```text
S1：获取同站点相关对象、字段和关系，输出 subgraphOutput。
S2：基于 subgraphOutput 生成 plannedTasks。
S3：基于 plannedTasks 查询数据，输出 {objects, relationships}。
S6：基于 oacResult 输出传播证据结论、证据摘要和缺失信息。
```

## 13. 步骤依赖

- 缺少必要顶层输入时，不得进入 S1。
- S1 未输出 `subgraphOutput`，不得进入 S2。
- S2 未输出 `plannedTasks`，不得进入 S3/S4/S5。
- S3 未输出 `oacResult`，不得进入 S6，除非业务规则允许无数据汇总。
- S4 未输出 `functionSelection`，不得进入 S5。
- S5 未输出 `functionOutput`，不得把 Function 结果传给 S3 或 S6。

## 14. 执行效率规则

- 默认 compact 模式：只输出必要步骤结果摘要，不展开完整中间上下文。
- 不设置显式输入门禁步骤。
- 不生成字段映射对象。
- 不生成 `stepRuleMap` 对象。
- 不重复生成 planningContext 或 inputGate。
- 不重复摘要业务领域知识。
- 不重复输出长列表、字段列表、告警列表、对象列表。
- 不重复解释默认 S1-S6 标准步骤。
- S3 不重新推理 S2 已经规划出的路径。
- OAC 默认不写临时文件，优先内存参数或标准输入传递。
- 只有 debug、失败定位或用户明确要求时，才展开完整中间输入输出。

## 15. 最终输出要求

正常成功时输出最终业务结论和必要证据摘要。失败时输出失败原因、失败步骤、缺失信息和下一步建议。
