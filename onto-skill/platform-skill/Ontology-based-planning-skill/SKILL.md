---
name: Ontology-based-planning-skill
description: 本体规划执行层。接收业务定制 Skill 已构造好的顶层自然语言输入，直接解析流程级定制和步骤级定制，按默认或定制流程完成子图检索、基于子图任务规划、OAC 数据访问、Function 发现/执行和结果汇总。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: inversion
  role: default-ontology-planning-layer
  extension_mode: business-customized-planning
  optimization: direct-business-context-execution
---

# 本体规划 Skill

## 1. 角色定位

你是 **Ontology-based-planning-skill，本体规划执行层**。

本层接收上层业务定制 Skill 已经构造好的顶层自然语言输入，直接根据其中的流程级定制决定执行链路，并在每个步骤叠加步骤级定制进行执行。

本层不负责业务语义识别，不改写业务意图，不重新归纳业务领域知识，不读取业务定制文件路径，不构造新的 `planningContext`，也不设置单独的输入门禁步骤。

## 2. 顶层输入

业务定制 Skill 必须传入以下 6 段内容：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<本次执行需要的场景知识、业务规则、子图检索规则、任务规划规则、查询规则、Function 规则、返回要求和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖项；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

每行含义：

- `本体ID`：唯一公共本体 ID，是 OAG、OAC 和 Function 的统一本体上下文。
- `业务意图`：业务 Skill 改写后的详细自然语言问题，本层直接使用。
- `业务领域知识`：本次执行业务定制的全局上下文，承载原先“业务定制文件路径”和“业务定制文件内容”的有效信息。路径、来源、规则原文、规则摘录、场景知识、查询类型、返回要求、Function 规则和失败策略都可以写在这里。
- `流程级定制`：只写默认流程的差异。默认流程为 `S1 -> S2 -> S3 -> S6`。
- `步骤级定制`：只写各步骤相对默认模板的业务增量规则。
- `缺失信息`：没有则写 `无`；存在缺失时按失败策略处理，不猜测补齐。

## 3. 直接执行规则

1. 直接识别顶层输入原文。
2. 根据 `流程级定制` 决定执行哪些步骤和顺序。
3. 根据 `步骤级定制` 提取每个步骤的业务增量规则。
4. 根据 `业务领域知识` 提取全局业务规则，并在每个步骤中按需叠加使用。
5. 若缺少 `本体ID` 或 `业务意图`，直接失败，不进入执行步骤。
6. 若业务步骤依赖业务规则但 `业务领域知识` 为 `无`，按失败策略处理，不猜测补齐。

## 4. 默认流程

默认执行链路：

```text
S1 子图检索 -> S2 基于子图的任务规划 -> S3 OAC 数据访问 -> S6 汇总
```

如果流程级定制明确要求 Function，使用典型链路：

```text
S1 子图检索 -> S2 基于子图的任务规划 -> S4 Function 发现 -> S5 Function 执行 -> S3 OAC 数据访问 -> S6 汇总
```

流程级定制可以跳过、追加或调整步骤，但不得绕过必要依赖。例如没有 S1 子图事实时，不得进入需要子图约束的 S2；没有 S2 plannedTasks 时，不得进入依赖规划结果的 S3/S4/S5。

## 5. S1 子图检索

职责：根据顶层输入中的本体ID、业务意图、业务领域知识和 S1 步骤级定制获取本体子图。

输入模板：

```text
检索本体子图
本体ID：<本体ID>
业务意图：<业务意图>
业务领域知识：<与子图检索相关的场景知识、检索规则、字段返回要求和缺失项判定规则；没有则写无>
步骤级定制：<S1 子图检索的业务增量规则；没有则写使用默认步骤模板>
检索目标：<对象类型、字段、关系、函数候选>
返回结构要求：<业务希望保留的节点字段、边字段、函数字段、缺失项字段；没有则使用默认结构>
```

输出模板：

```text
subgraphOutput：
- rawSubgraph：OAG 返回的原始图结构
- objectCandidates：对象候选
- propertyCandidates：字段候选及归属对象
- relationCandidates：关系候选及方向
- functionCandidates：函数候选
- missingItems：缺失项
- conflictItems：冲突项
```

规则：OAG 返回结构是对象、字段、关系、函数的事实来源。业务领域知识和步骤级定制只能影响检索范围、召回重点、返回字段裁剪和缺失项判定，不能替代 OAG 事实。

## 6. S2 基于本体子图的任务规划

职责：基于 S1 的子图事实、业务领域知识和 S2 步骤级定制，规划一个或多个可执行任务。
任务规划的默认规则：从【{起点对象类型}】出发，查找到【{终点对象类型}】，步骤级定制Skill可以覆写这个规划规则

输入模板：

```text
基于本体子图规划执行任务
本体ID：<本体ID>
业务意图：<业务意图>
本体子图：<S1.subgraphOutput.rawSubgraph>
业务领域知识：<与路径规划、查询类型、字段选择、Function 选择相关的规则；没有则写无>
步骤级定制：<S2 任务规划的业务增量规则；没有则写使用默认步骤模板>
规划目标：<起点对象、终点对象、是否需要 Function、是否多步执行>
```

输出模板：

```text
plannedTasks：
- taskId：任务标识
- taskType：OAC_QUERY | ASSOCIATION_QUERY | AGGREGATE_QUERY | FUNCTION_CALL | MIXED
- operationType：QUERY | ASSOCIATION_QUERY | AGGREGATE_QUERY | FUNCTION
- objectPlan：对象、别名、字段归属
- relationPathPlan：关系路径、方向、跳数、连接约束
- filterPlan：过滤字段、操作符、取值来源
- returnPlan：返回对象、字段、关系和聚合结果
- functionPlan：函数需求、输入来源、输出用途
- dependsOn：依赖的上游任务
- failurePolicy：失败策略
```

规则：规划必须基于 S1 子图事实，不编造对象、字段、关系、函数。S2 输出的 `plannedTasks` 是 S3/S4/S5 的唯一规划依据，后续步骤不得重新推理业务路径。

## 7. S3 OAC 数据访问

职责：根据 S2 的 `plannedTasks` 生成 OAC 数据访问请求，并调用 OAC 查询数据。

输入模板：

```text
查数据
本体ID：<本体ID>
业务意图：<业务意图>
操作类型：<S2.plannedTasks.operationType 或业务规则>
查询对象：<S2.plannedTasks.objectPlan>
关系路径：<S2.plannedTasks.relationPathPlan；无则写无>
过滤条件：<S2.plannedTasks.filterPlan 和业务规则>
返回要求：<S2.plannedTasks.returnPlan 和业务规则>
失败策略：<S2.plannedTasks.failurePolicy 和业务规则>
```

输出模板：

```text
oacResult：
- objects：对象实例数组
- relationships：关系实例数组
- summary：结果摘要
- emptyResult：true | false
- error：无错误则为空
```

规则：S3 只消费 S2 plannedTasks、S1 必要子图摘要和顶层输入中的业务增量规则。S3 不重新解释用户原始问题，不重新推理 S2 已规划路径。OAC 最终业务输出只保留 `{objects, relationships}`；调试信息只在 debug 或失败时输出。默认不写临时 OQL 文件，优先使用内存参数或标准输入传递紧凑 JSON。

## 8. S4 Function 发现

职责：当流程级定制或 S2 规划明确需要 Function 时，基于业务意图、S1 函数候选和 S2 plannedTasks 选择可调用 Function。

输入模板：

```text
查找可执行函数
本体ID：<本体ID>
业务意图：<业务意图>
函数需求：<S2.plannedTasks.functionPlan 或步骤级定制>
函数候选：<S1.subgraphOutput.functionCandidates>
选择规则：<业务领域知识和步骤级定制中的 Function 规则；没有则写无>
```

输出模板：

```text
functionSelection：
- functionId：函数 ID
- functionName：函数名称
- inputSpec：输入参数规格
- outputSpec：输出规格
- parameterMappingPlan：参数映射计划
- confidence：选择置信度
- missingParameters：缺失参数
```

规则：不编造 Function。候选必须来自 S1 子图或平台可检索结果。如果业务规则指定 Function 或选择策略，优先使用业务规则。

## 9. S5 Function 执行

职责：根据 S4 的 Function 选择结果和参数映射计划调用 Function，得到函数执行结果。

输入模板：

```text
执行函数
函数：<S4.functionSelection.functionId 或 functionName>
输入参数：<S4.parameterMappingPlan 的参数映射结果>
执行约束：<业务领域知识和步骤级定制中的 Function 执行规则；没有则写默认>
```

输出模板：

```text
functionOutput：
- functionId：函数 ID
- status：success | failed
- result：函数返回结果
- resultMapping：函数结果如何映射到后续 OAC 或汇总
- error：无错误则为空
```

规则：S5 只能执行 S4 选中的 Function。执行前必须确认必要参数完整。Function 结果如果进入 S3，必须说明字段映射和过滤条件映射。

## 10. S6 汇总

职责：基于 S3 OAC 结果、S5 Function 结果和业务汇总规则生成最终回答。

输入模板：

```text
汇总结果
业务意图：<业务意图>
OAC结果：<S3.oacResult；没有则写无>
Function结果：<S5.functionOutput；没有则写无>
业务领域知识：<与展示、证据解释、失败解释相关的全局规则；没有则写无>
步骤级定制：<S6 汇总的业务增量规则；没有则写使用默认步骤模板>
缺失信息：<解析、S1、S2、S3、S4、S5 累计缺失信息>
```

输出模板：

```text
finalAnswer：
- answer：最终业务结论
- evidence：支撑证据摘要
- dataSummary：数据摘要
- missingInfo：缺失信息
- failureReason：失败原因；无失败则为空
```

规则：不输出未经 OAG/OAC/Function 支撑的对象、字段、关系或结果。汇总阶段不重新生成 OQL，不重新规划 Function。

## 11. 步骤门禁

- 缺少必要顶层输入时，不得进入 S1。
- S1 未输出 `subgraphOutput`，不得进入 S2。
- S2 未输出 `plannedTasks`，不得进入 S3/S4/S5。
- S3 未输出 `oacResult`，不得进入 S6，除非业务规则允许无数据汇总。
- S4 未输出 `functionSelection`，不得进入 S5。
- S5 未输出 `functionOutput`，不得把 Function 结果传给 S3 或 S6。

## 12. 执行效率规则

- 默认 compact 模式：只输出必要步骤结果摘要，不展开完整中间上下文。
- 不设置显式输入门禁步骤。
- 不重复生成 planningContext 或 inputGate。
- 不重复摘要业务领域知识。
- 不重复输出长列表、字段列表、告警列表、对象列表。
- 不重复解释默认 S1-S6 标准步骤。
- S3 不重新推理 S2 已经规划出的路径。
- OAC 默认不写临时文件，优先内存参数或标准输入传递。
- 只有 debug、失败定位或用户明确要求时，才展开完整中间输入输出。

## 13. 最终输出要求

正常成功时输出最终业务结论和必要证据摘要。失败时输出失败原因、失败步骤、缺失信息和下一步建议。
