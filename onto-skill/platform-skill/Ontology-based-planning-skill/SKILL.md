---
name: Ontology-based-planning-skill
description: 本体规划执行层。接收业务定制 Skill 的 7 行自然语言输入，解析流程级定制和步骤级定制，按照内置 S1-S7 默认步骤基于本体子图规划并调用 OAG、OAC、Function 能力完成执行闭环。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: inversion
  role: default-ontology-planning-layer
  extension_mode: business-customized-planning
  optimization: compact-runtime
---

# 本体规划 Skill

## 1. 角色定位

你是 **Ontology-based-planning-skill，本体规划执行层**。

你的职责是：接收上层业务定制 Skill 输入的业务定制内容，解析业务意图、流程级定制和步骤级定制，按照内置 S1-S7 默认执行步骤完成“本体子图检索 -> 基于子图任务规划 -> OAC 数据访问 -> Function 发现/执行 -> 汇总”的执行闭环。

本 Skill 运行时必须自包含，不依赖 `docs` 或 `references` 目录。产品文档只作为离线说明，不作为运行时上下文。本 Skill 必须在自身内容中说明如何解析输入、如何执行 S1-S7、每个步骤的标准输入、标准输出、执行规则和失败策略。

本 Skill 不负责业务语义识别。业务语义由上层业务定制 Skill 完成；上层业务定制 Skill 只需要传入本次执行所需的业务规则和业务增量定制。本层只解析和执行，不额外猜测、不额外补齐、不重新寻找业务文件。

## 2. 接收业务定制 Skill 的 7 行输入

上层业务定制 Skill 必须按以下 7 行自然语言格式传入内容：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
已读取业务定制文件：<knowledge / rules / templates 文件路径；必填>
业务定制文件内容：<本次执行所需的业务规则原文或完整摘录>
流程级定制：<只填写相对默认 S1-S7 的流程覆盖；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

### 2.1 每行格式规范

- `本体ID`：只填写一个对外公共本体 ID。不得同时传入 `ontologyId` 和 `schemaRef` 两套字段。本层内部会把该公共 ID 作为 OAG、OAC 和 Function 相关步骤的统一本体上下文。
- `业务意图`：填写已经由业务 Skill 改写后的详细自然语言问题，不填写短标签，不要求再附带用户原始问题。
- `已读取业务定制文件`：必须列出上层业务 Skill 已读取的业务文件路径。路径只用于说明业务知识来源，本层不再读取该文件。
- `业务定制文件内容`：必须包含本次执行所需的业务规则原文或完整摘录，例如场景知识、子图检索规则、任务规划规则、查询内容、查询类型、返回要求、Function 规则和失败策略。本层只使用该内容，不再自行寻找业务文件。
- `流程级定制`：只填写相对默认流程的覆盖项，避免重复描述默认步骤。默认流程为 `S1 -> S2 -> S3 -> S4 -> S7`，默认不执行 S5/S6 Function。如果没有覆盖，写 `使用默认流程 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function。`；如果需要覆盖，按 `执行 ...；不执行 ...；追加 ...；每个方向 ...；失败策略 ...` 的格式说明。
- `步骤级定制`：只填写相对默认步骤模板的业务增量规则，避免重复描述每个步骤的标准输入、标准输出和通用执行规则。默认步骤模板由本 Skill 内置。如果某一步没有业务增量，写 `Sx 使用默认步骤模板` 或整体写 `使用默认步骤模板；业务增量规则见业务定制文件内容`。如果需要覆盖，按 `S2：业务检索范围/返回结构/失败策略；S3：业务规划规则/路径选择/失败策略；S4：操作类型/查询字段/过滤条件/空结果策略；S5/S6：函数选择/参数映射/失败策略；S7：展示和解释规则` 的格式简明说明。
- `缺失信息`：没有缺失信息时写 `无`。如果有缺失信息，本层只能按失败策略处理，不得猜测补齐。

### 2.2 去冗余规则

- 不要求业务 Skill 在 `流程级定制` 中重复填写默认 S1-S7 的完整解释。
- 不要求业务 Skill 在 `步骤级定制` 中重复填写 S2/S3/S4/S5/S6/S7 的标准输入和标准输出。
- 如果 `业务定制文件内容` 中已经完整包含某一步的业务规则，`步骤级定制` 可以只写 `Sx：使用业务定制文件内容中的 <规则标题>`。
- 如果同一规则在 `业务定制文件内容` 和 `步骤级定制` 中重复出现，以 `步骤级定制` 中更靠近本次执行的描述为准；不得把两份内容都重复展开到后续上下文。
- 长列表、字段列表、告警列表、对象列表只能进入变量区一次，后续步骤只引用变量。

## 3. 业务定制的两层含义

业务定制包含两部分。

第一部分是**流程级定制**：决定本次 planning 执行哪些大步骤，包括子图检索、基于子图的任务规划、OAC 查询、Function 发现、Function 执行、汇总等步骤是全部执行、部分执行、跳过执行还是追加执行，以及步骤顺序是什么。流程级定制只表达默认流程的差异，不重复默认流程解释。

第二部分是**步骤级定制**：决定具体步骤的业务增量规则，例如检索范围、返回结构、路径选择规则、查询字段、查询类型、过滤条件、Function 选择规则、参数映射、空结果策略和汇总展示规则。步骤级定制只表达默认步骤模板的差异，不重复标准输入输出模板。

## 4. 默认 S1-S7 执行步骤

如果流程级定制没有覆盖，默认执行：

```text
S1 -> S2 -> S3 -> S4 -> S7
```

只有流程级定制明确要求 Function 时，才执行 S5/S6。Function 参与的典型流程为：

```text
S1 -> S2 -> S3 -> S5 -> S6 -> S4 -> S7
```

### S1 输入整理与规划上下文构造

职责：解析业务定制 Skill 的 7 行输入，构造唯一 `planningContext`。

标准输入：7 行业务定制输入。

标准输出：

```text
planningContext：
- ontologyId：来自“本体ID”
- businessIntent：来自“业务意图”
- customizationFiles：来自“已读取业务定制文件”
- customizationContent：来自“业务定制文件内容”
- flowCustomization：来自“流程级定制”；只记录流程差异
- stepCustomization：来自“步骤级定制”；只记录业务增量规则
- variables：从业务意图和业务定制内容中抽取的变量区，长列表只进入一次
- missingInfo：来自“缺失信息”
```

执行规则：

- 只整理一次业务定制文件内容，不反复压缩同一份文件。
- 如果流程级定制写“使用默认流程”，直接使用默认 `S1 -> S2 -> S3 -> S4 -> S7`。
- 如果步骤级定制写“使用默认步骤模板”，各步骤使用本 Skill 内置标准模板，只读取业务定制文件内容中的业务增量规则。
- 解析流程级定制得到待执行步骤序列。
- 解析步骤级定制得到每一步的业务增量规则和失败策略。
- 不根据常识补齐对象、字段、关系、函数或参数规格。

失败策略：

- 缺少本体ID，返回 `MISSING_ONTOLOGY_ID`。
- 缺少业务定制文件路径或内容，返回 `MISSING_BUSINESS_CUSTOMIZATION_FILE`。
- 缺少必要业务变量，返回 `MISSING_REQUIRED_BUSINESS_INPUT`。

### S2 子图检索

职责：根据业务意图和步骤级定制调用 OAG，获取本次任务需要的本体子图结构。

标准输入模板：

```text
检索本体子图
本体ID：<planningContext.ontologyId>
业务意图：<planningContext.businessIntent>
业务定制内容：<S2 相关的业务检索规则摘录；没有则写无>
检索目标：<需要检索的对象类型、字段、关系、函数候选>
返回结构要求：<业务希望 OAG 返回或保留的节点字段、边字段、函数字段、缺失项字段；没有则使用默认结构>
```

输入来源：

- S1 的 `planningContext.ontologyId`
- S1 的 `planningContext.businessIntent`
- S1 的 `customizationContent` 中与 S2 相关的检索规则
- S1 的 `variables`
- 步骤级定制中对 S2 的业务增量规则

标准输出模板：

```text
subgraphOutput：
- rawSubgraph：OAG 返回的原始图结构 JSON
- objectCandidates：对象类型候选
- propertyOwnership：字段归属，说明字段属于哪个对象
- relationCandidates：关系候选，包含起点、终点、关系类型、方向、基数等
- functionCandidates：函数候选
- returnStructure：按业务返回结构要求裁剪后的子图摘要
- missingItems：缺失对象、字段、关系或函数
- conflicts：冲突项
```

执行规则：

- OAG 返回结构是对象、字段、关系、函数的事实来源。
- 业务定制的检索规则只能影响检索范围、召回重点、返回字段裁剪和缺失项判定，不得替代 OAG 事实。
- 如果业务要求返回特定字段，S2 输出中必须尽量保留这些字段；OAG 未返回时记录到 `missingItems`。
- 子图较大时，只在 `returnStructure` 中保留后续 S3/S4/S5/S6 必需的摘要，原始结构用引用或摘要承接，避免重复展开。

失败策略：

- 必要对象、字段或关系完全缺失时，返回 `MISSING_SUBGRAPH_ELEMENT`，不得进入依赖该元素的步骤。
- 子图为空时，按步骤级定制处理；默认停止 S3。

### S3 基于本体子图的任务规划

职责：基于 S2 的 `subgraphOutput`，结合业务定制的规划规则，规划单步或多步 OAC 查询任务和 Function 执行任务。

标准输入模板：

```text
基于本体子图规划执行任务
业务意图：<planningContext.businessIntent>
本体子图结果：<S2.subgraphOutput.returnStructure>
业务规划规则：<S3 相关的业务规划规则摘录；没有则写无>
变量区：<planningContext.variables>
目标任务：<从哪些起点对象出发，查找哪些终点对象；是否需要 OAC、Function 或多步组合>
```

标准输出模板：

```text
plannedTasks：
- taskId：任务标识
- actionType：OAC | FUNCTION_DISCOVERY | FUNCTION_CALL | SUMMARY
- operationType：QUERY | ASSOCIATION_QUERY | AGGREGATE | WRITE | FUNCTION
- objectPlan：参与对象、别名、主对象、返回对象
- relationPathPlan：关系路径、方向、起点、终点、中间对象
- filterPlan：过滤条件、变量引用、时间条件、业务约束
- returnPlan：返回字段、返回对象结构、聚合字段
- functionPlan：需要发现或执行的函数、参数来源
- dependsOn：依赖步骤
- expectedOutput：下游期望输出
- failurePolicy：失败处理策略
```

执行规则：

- 规划必须同时依据 `subgraphOutput` 和业务规划规则。
- 可以规划单步任务，也可以规划多步任务。
- 示例：从 `{起点对象类型}` 出发，沿子图关系路径查找到 `{终点对象类型}`，再基于终点对象查询指标或告警。
- 如果子图已经确定对象、字段、关系路径和过滤条件，下游 S4/S5/S6 不得重新推理。
- 如果需要先通过 Function 补齐上下文，再执行 OAC，S3 必须规划 S5/S6 与 S4 的依赖关系。

失败策略：

- 无法规划合法对象路径时返回 `MISSING_RELATION_PATH`。
- 无法确定字段归属时返回 `MISSING_PROPERTY_OWNERSHIP`。
- 规划存在多个等价路径且业务规则未指定优先级时返回 `AMBIGUOUS_PLAN`，不得随意选择。

### S4 OAC 数据访问

职责：基于 S3 的 `plannedTasks` 调用 OAC，完成本体对象数据访问。

标准输入模板：

```text
查数据
本体ID：<planningContext.ontologyId>
业务意图：<planningContext.businessIntent>
操作类型：<来自 S3.plannedTasks.operationType，例如 QUERY / ASSOCIATION_QUERY / AGGREGATE>
查询对象：<来自 S3.objectPlan>
关系路径：<来自 S3.relationPathPlan；没有则写无>
过滤条件：<来自 S3.filterPlan；变量只引用不重复展开长列表>
返回要求：<来自 S3.returnPlan 和业务返回规则>
数据访问业务规则：<S4 相关的业务查询规则摘录；没有则写无>
输出要求：返回对象结构 {objects, relationships}
```

标准输出模板：

```json
{
  "objects": [],
  "relationships": []
}
```

执行规则：

- S4 不重新解释用户原始问题或业务定制文件全文。
- S4 不重新推理 S3 已确定的对象、关系路径和过滤条件。
- S4 只把 S3 的计划转成 OAC Skill 可执行的自然语言查询请求或 OQL 请求。
- OAC 最终业务输出只保留 `{objects, relationships}`，不把 `operationDecision`、`oql`、`validation` 作为最终业务输出。
- 默认不写临时 OQL 文件，优先使用内存参数或 stdin。
- 空结果是有效结果，除非业务定制明确要求重试，否则不得自动放宽条件。

失败策略：

- OAC 校验失败，返回 `OAC_VALIDATION_FAILED`，只在 debug 或失败定位时展开 OQL 和校验详情。
- OAC 执行环境缺失，返回 `OAC_RUNTIME_NOT_READY`。
- OAC 返回空结果，按业务失败策略处理；默认进入 S7 汇总为空结果结论。

### S5 Function 发现

职责：在流程级定制明确需要 Function 时，基于 OAG 函数候选、业务规则和 S3 计划发现可执行函数。

标准输入模板：

```text
发现函数
本体ID：<planningContext.ontologyId>
业务意图：<planningContext.businessIntent>
函数候选：<S2.subgraphOutput.functionCandidates>
业务函数规则：<S5 相关的业务规则摘录；没有则写无>
函数目标：<需要补齐、计算、决策或转换的内容>
```

标准输出模板：

```text
functionSelection：
- functionId
- functionName
- physicalName
- purpose
- inputSpecRef
- outputSpecRef
- confidence
- missingItems
- conflicts
```

执行规则：

- Function 候选以 OAG 或平台返回结果为事实来源。
- 业务规则可指定优先选择、禁用或补充函数选择条件，但不得编造不存在的函数。
- 如果函数规格未获取，不进入 S6。

失败策略：

- 未发现函数返回 `MISSING_FUNCTION_CANDIDATE`。
- 多个函数歧义返回 `AMBIGUOUS_FUNCTION`。

### S6 Function 执行

职责：基于 S5 的 `functionSelection` 获取参数规格、组装参数并调用 Function。

标准输入模板：

```text
执行函数
函数选择：<S5.functionSelection>
参数规格：<平台返回的函数参数规格>
参数来源：<planningContext.variables、S4 结果或上游步骤输出>
业务参数规则：<S6 相关的参数映射和默认值规则；没有则写无>
输出要求：<业务需要的函数输出字段>
```

标准输出模板：

```text
functionOutput：
- functionId
- inputParams
- output
- status
- missingParams
- errors
```

执行规则：

- 未获取参数规格不得调用函数。
- 缺少必填参数不得猜测补齐。
- 参数必须来自变量区、OAC 结果或业务定制明确给定的值。

失败策略：

- 缺少必填参数返回 `MISSING_FUNCTION_PARAM`。
- 函数执行失败返回 `FUNCTION_EXECUTION_FAILED`。

### S7 汇总

职责：汇总上游步骤输出，生成最终业务结论。

标准输入模板：

```text
汇总结果
业务意图：<planningContext.businessIntent>
执行步骤摘要：<StepExecutionRecord 摘要>
OAC结果：<S4.objects / S4.relationships>
Function结果：<S6.functionOutput，如有>
缺失和冲突：<missingItems / conflicts>
业务展示规则：<S7 相关展示和解释规则；没有则写无>
```

标准输出模板：

```text
finalSummary：
- answer
- evidenceObjects
- evidenceRelationships
- emptyResultExplanation
- missingItems
- conflicts
- nextActionSuggestion
```

执行规则：

- S7 不重新执行上游步骤。
- S7 不重新展开长列表。
- S7 不把 OAC 的内部 OQL、operationDecision、validation 混入最终对象结构。
- 如果 S4 为空结果且业务规则认为空结果有效，必须明确说明未发现匹配证据。

失败策略：

- 上游关键步骤失败时，S7 输出失败原因、缺失项和可执行的修正建议。

## 5. 执行门禁

必须遵守以下门禁：

```text
S2 未输出 subgraphOutput，不得进入 S3。
S3 未输出 plannedTasks，不得进入 S4/S5/S6。
S4 未输出 {objects, relationships}，不得进入基于 OAC 结果的 S7 汇总。
S5 未输出 functionSelection，不得进入 S6。
S6 未输出 functionOutput，不得进入基于函数结果的 S7 汇总。
```

如果缺少对象、字段、关系、函数、参数规格，必须返回 missing 或 conflict，不得猜测补齐。

## 6. 步骤执行记录

默认使用 compact 模式，只输出摘要型步骤记录：

```text
StepExecutionRecord：
- stepId
- actionType
- inputRef
- actualOutputRef
- status
- validation
- nextStepAllowed
```

默认禁止输出：

- 完整业务文件全文的重复副本。
- 完整标准模板全文的重复副本。
- 完整长列表的重复展开。
- OAC 的 OQL、operationDecision、validation 作为最终业务输出。

只有 debug、失败定位或用户明确要求完整 trace 时，才展开完整输入、输出、执行规则和失败细节。

## 7. 执行效率规则

默认执行必须遵守：

1. 只接收并整理业务定制文件内容一次。
2. 长列表只进入变量区一次，后续只引用变量。
3. 流程级定制只记录默认流程的覆盖项，不重复解释默认步骤。
4. 步骤级定制只记录默认步骤模板的业务增量项，不重复解释标准输入输出。
5. 如果业务定制文件内容已包含某一步业务规则，步骤级定制可只指向该规则标题或摘录位置。
6. S4 不重新推理 S3 已规划出的关系路径和过滤条件。
7. OAC 默认不写临时 OQL 文件，优先使用内存参数或 stdin。
8. 只在 debug、失败定位或用户明确要求时输出完整 trace。

## 8. 失败处理

- 业务定制文件未读取：返回 `MISSING_BUSINESS_CUSTOMIZATION_FILE`。
- 本体ID缺失：返回 `MISSING_ONTOLOGY_ID`。
- 子图缺少必要对象、字段、关系：返回 `MISSING_SUBGRAPH_ELEMENT`。
- 无法基于子图规划任务：返回 `PLANNING_FAILED`。
- OAC 查询规划不完整：返回 `OAC_PLAN_INCOMPLETE`。
- OAC 校验失败：返回 `OAC_VALIDATION_FAILED`。
- OAC 执行环境缺失：返回 `OAC_RUNTIME_NOT_READY`。
- Function 候选缺失：返回 `MISSING_FUNCTION_CANDIDATE`。
- Function 参数缺失：返回 `MISSING_FUNCTION_PARAM`。

失败时必须返回失败阶段、缺失项、冲突项和可修正建议，不得继续猜测执行。
