# 标准步骤输入输出模板库

本文档定义 Planning 层通用的 S2/S3/S4/S5/S6/S7 标准步骤模板。业务 Skill 不应在运行时重复展开这些模板全文，只需要在步骤级定制中通过 `stepTemplateRef` 引用，并通过业务规则引用或 `contractRef` 指向业务定制文件中的增量规则。

## 1. 使用原则

默认执行态使用 compact 模式。

- `stepTemplateRef`：引用本文档中的标准输入、输出、执行规则和失败策略。
- `contractRef`：引用业务定制文件中的业务增量规则，例如方向、对象、字段、路径、过滤条件、返回要求。
- `variablesRef`：引用变量区中的变量，长列表只在变量区保存一次。
- `inputRefs`：引用上游步骤输出或变量，不重复复制上游结果全文。
- `expectedOutputRef`：引用标准输出类型，不重复展开输出结构说明。

只有在 debug、校验失败、执行失败、缺少对象/字段/关系/函数/参数规格，或用户明确要求完整 stepTrace 时，才展开本文档中的模板全文。

## 2. 标准模板索引

| stepTemplateRef | 阶段 | actionType | 标准输出 |
|---|---|---|---|
| `standard.S2.oag` | S2 子图检索 | `OAG` | `subgraphOutput` |
| `standard.S3.subgraphPlan` | S3 基于子图任务规划 | `SUBGRAPH_PLAN` | `plannedTasks` |
| `standard.S4.oac` | S4 OAC 数据访问 | `OAC` | `objectStructure` |
| `standard.S5.functionDiscovery` | S5 Function 发现 | `FUNCTION_DISCOVERY` | `functionSelection` |
| `standard.S6.functionCall` | S6 Function 执行 | `FUNCTION_CALL` | `functionOutput` |
| `standard.S7.summary` | S7 汇总 | `SUMMARY` | `finalSummary` |

## 3. S2 标准模板：standard.S2.oag

### 标准输入

```text
先找相关子图。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题，用于检索对象、属性、关系、函数候选>
业务定制文件：<已读取的子图检索规则文件或场景知识文件；业务定制模式必填>
子图检索规则：<来自 contractRef 的业务增量规则>
检索目标：<需要检索哪些对象、属性、关系、函数候选；不得提前编造平台字段名>
子图返回结构要求：<保留 result.seedNodes / nodes / edges / functions / actions 中哪些内容>
期望输出：subgraphOutput
```

### 标准输出：subgraphOutput

```text
subgraphOutput:
- subgraphRawResult：OAG 原始 result 结构引用
- objectCandidates：对象候选摘要
- propertyOwnership：字段归属摘要
- relationCandidates：关系候选摘要
- functionCandidates：函数候选摘要
- missingOrConflict：缺失或冲突项
```

### 标准失败策略

- 子图为空：按业务失败策略处理，默认停止后续依赖步骤。
- 对象、字段、关系缺失：返回 missing，不编造。
- 同一方向多次检索结果冲突：保留 OAG 原始结果并交由 S3 判断。

## 4. S3 标准模板：standard.S3.subgraphPlan

### 标准输入

```text
基于本体子图规划执行任务。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题>
本体子图结果：<S2.subgraphOutput 引用>
变量区：<planningContext.variables 引用>
业务规划规则：<来自 contractRef 的业务增量规则>
规划目标：<单对象、关系路径、聚合、Function 或组合任务>
期望输出：plannedTasks
```

### 标准输出：plannedTasks

```text
plannedTasks:
- taskId
- actionType：QUERY / ASSOCIATION_QUERY / AGGREGATE / FUNCTION_DISCOVERY / FUNCTION_CALL / SUMMARY
- operation：OAC 操作类型或 Function 操作类型
- objectPlan：对象和 alias 计划
- relationPlan：关系路径计划
- filterPlan：过滤条件计划，长列表使用 variablesRef
- returnPlan：返回字段计划
- inputRefs：下游步骤输入引用
- outputRef：下游可消费输出引用
- planningBasis：来自 subgraphOutput 和 contractRef 的依据摘要
- failurePolicyRef
```

### 标准失败策略

- 无法从子图得到合法对象或关系：停止依赖步骤，返回 missing。
- 多条路径均可用：按业务规则引用的优先级选择，不在 S4 重推理。
- S3 输出的 `plannedTasks` 是 S4 的唯一任务计划输入。

## 5. S4 标准模板：standard.S4.oac

### 标准输入

```text
查数据
本体ID：<公共本体ID，平台侧作为 schemaRef 来源>
操作类型：<来自 S3.plannedTasks.operation>
查询对象：<来自 S3.plannedTasks.objectPlan>
关系路径：<来自 S3.plannedTasks.relationPlan；仅关系查询需要>
过滤条件：<来自 S3.plannedTasks.filterPlan；长列表最终生成 OQL 时才展开>
返回要求：<来自 S3.plannedTasks.returnPlan>
执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。
期望输出：objectStructure
```

### 标准输出：objectStructure

```json
{
  "objects": [],
  "relationships": []
}
```

### 标准失败策略

- S4 不重新解释用户原始问题或业务定制文件全文。
- S4 只消费 variables、S2.subgraphOutput、S3.plannedTasks 和业务增量规则。
- OQL 校验失败时只返回失败摘要；仅 debug 或失败定位时展开 OQL 和完整模板。
- 默认不写临时 OQL 文件，优先使用 `--oac-json` 或 `--input -`。

## 6. S5 标准模板：standard.S5.functionDiscovery

### 标准输入

```text
发现函数。
本体ID：<公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么需要函数能力>
函数来源：<OAG result.functions 或业务规则引用指定目标>
函数选择依据：<description、name、业务规则或上下文>
期望输出：functionSelection
```

### 标准输出：functionSelection

```text
functionSelection:
- selectedFunctionId
- selectedOntologyId
- selectedPhysicalNameCandidate
- selectionBasis
- missingOrConflict
```

### 标准失败策略

- 没有函数候选：返回 missing，不进入 S6。
- 多个函数候选：按业务规则排序；仍无法确定时返回歧义项。

## 7. S6 标准模板：standard.S6.functionCall

### 标准输入

```text
调用函数。
functionSelection：<S5 输出引用>
参数规格：<get_params_spec 返回结果>
上下文参数：<variables、OAC 结果或上游步骤输出引用>
参数缺失策略：<来自业务规则或默认 missing>
期望输出：functionOutput
```

### 标准输出：functionOutput

```text
functionOutput:
- functionId
- physicalName
- params
- callStatus
- rawResult
- missingOrConflict
```

### 标准失败策略

- 未获取参数规格：不调用函数。
- 缺少必填参数：返回 missing，不猜测。
- 未解析到 physicalName：不调用函数。

## 8. S7 标准模板：standard.S7.summary

### 标准输入

```text
汇总结果。
输入来源：<上游 StepExecutionRecord 摘要、objectStructure、functionOutput、missingOrConflict>
汇总要求：<来自业务规则引用的业务展示要求>
期望输出：finalSummary
```

### 标准输出：finalSummary

```text
finalSummary:
- resultSummary
- objects / relationships 摘要或引用
- functionResult 摘要或引用
- missingOrConflict
- evidenceBasis
- noRerunGuarantee
```

### 标准失败策略

- S7 不重新执行上游步骤。
- S7 不重新展开长列表。
- S7 不把 OQL、validation、operationDecision 混入 OAC 最终对象结构。
