# 标准步骤输入输出模板库

本文档定义 Planning 层通用的 S1/S2/S3/S4/S5/S6 标准步骤模板。业务 Skill 不应在运行时重复展开这些模板全文，只需要在步骤级定制中写业务增量规则。

## 1. 使用原则

默认执行态使用 compact 模式。

- `业务领域知识`：承载全局业务规则、字段语义、路径约束、返回要求和失败策略。
- `流程级定制`：只描述相对默认流程 `S1 -> S2 -> S3 -> S6` 的差异。
- `步骤级定制`：只描述 S1/S2/S3/S4/S5/S6 的业务增量规则。
- `inputRefs`：引用上游步骤输出或变量，不重复复制上游结果全文。
- `expectedOutputRef`：引用标准输出类型，不重复展开输出结构说明。

只有在 debug、校验失败、执行失败、缺少对象/字段/关系/函数/参数规格，或用户明确要求完整 stepTrace 时，才展开本文档中的模板全文。

## 2. 标准模板索引

| 步骤 | 阶段 | actionType | 标准输出 |
|---|---|---|---|
| `S1` | 子图检索 | `OAG` | `subgraphOutput` |
| `S2` | 基于子图任务规划 | `SUBGRAPH_PLAN` | `plannedTasks` |
| `S3` | OAC 数据访问 | `OAC` | `objectStructure` |
| `S4` | Function 发现 | `FUNCTION_DISCOVERY` | `functionSelection` |
| `S5` | Function 执行 | `FUNCTION_CALL` | `functionOutput` |
| `S6` | 汇总 | `SUMMARY` | `finalAnswer` |

## 3. S1 标准模板：子图检索

### 标准输入

```text
先找相关子图。
本体ID：<公共本体ID>
业务意图：<详细自然语言问题，用于检索对象、属性、关系、函数候选>
业务领域知识：<与子图检索相关的对象、字段、关系、函数候选规则>
步骤级定制：<S1 子图检索业务增量；没有则使用默认模板>
检索目标：<需要检索哪些对象、属性、关系、函数候选；不得提前编造平台字段名>
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
- 多方向检索结果冲突：保留 OAG 原始结果并交由 S2/S3 判断。

## 4. S2 标准模板：基于子图任务规划

### 标准输入

```text
基于本体子图规划执行任务。
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<路径规则、对象选择规则、查询类型规则、Function 前后置规则>
本体子图结果：<S1.subgraphOutput 引用>
步骤级定制：<S2 任务规划业务增量；没有则使用默认模板>
规划目标：<单对象、关系路径、聚合、Function 或组合任务>
期望输出：plannedTasks
```

### 标准输出：plannedTasks

```text
plannedTasks:
- taskId
- taskType：OAC_QUERY / ASSOCIATION_QUERY / AGGREGATE_QUERY / FUNCTION_CALL / MIXED
- operationType：QUERY / ASSOCIATION_QUERY / AGGREGATE / FUNCTION
- objectPlan：对象和 alias 计划
- relationPathPlan：关系路径计划
- filterPlan：过滤条件计划，长列表使用变量引用或文件输入
- returnPlan：返回字段计划
- dependsOn：依赖的上游任务
- failurePolicy
```

### 标准失败策略

- 无法从子图得到合法对象或关系：停止依赖步骤，返回 missing。
- 多条路径均可用：按业务规则优先级选择，不在 S3 重推理。
- S2 输出的 `plannedTasks` 是 S3/S4/S5 的唯一任务计划输入。

## 5. S3 标准模板：OAC 数据访问

### 标准输入

```text
查数据
本体ID：<公共本体ID，平台侧作为 schemaRef 来源>
业务意图：<详细自然语言问题>
业务领域知识：<与 OAC 查询相关的过滤、返回、聚合、空结果和失败处理规则>
步骤级定制：<S3 OAC 数据访问业务增量；没有则使用默认模板>
操作类型：<来自 S2.plannedTasks.operationType>
查询对象：<来自 S2.plannedTasks.objectPlan>
关系路径：<来自 S2.plannedTasks.relationPathPlan；仅关系查询需要>
过滤条件：<来自 S2.plannedTasks.filterPlan；长列表最终生成 OQL 时才展开>
返回要求：<来自 S2.plannedTasks.returnPlan>
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

- S3 不重新解释用户原始问题或业务知识全文。
- S3 只消费 S1.subgraphOutput、S2.plannedTasks、业务领域知识和步骤级增量规则。
- OQL 校验失败时只返回失败摘要；仅 debug 或失败定位时展开 OQL 和完整模板。
- 复杂 OQL 或长数组优先使用 UTF-8 JSON 文件，并通过 `--input <json文件>` 校验和执行。
- 短小 JSON 且确认 Shell 引号安全时，才可使用 `--oac-json`。
- 真实执行前必须确认 `SERVICE_NAMESPACE` 和 `TENANT_ID` 等服务环境变量已配置。

## 6. S4 标准模板：Function 发现

### 标准输入

```text
发现函数。
本体ID：<公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么需要函数能力>
业务领域知识：<与 Function 选择相关的业务规则、优先级、输入输出要求>
步骤级定制：<S4 Function 发现业务增量；没有则使用默认模板>
函数来源：<OAG result.functions 或业务规则指定目标>
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

- 没有函数候选：返回 missing，不进入 S5。
- 多个函数候选：按业务规则排序；仍无法确定时返回歧义项。

## 7. S5 标准模板：Function 执行

### 标准输入

```text
执行函数。
functionSelection：<S4 输出引用>
参数规格：<参数规格查询结果>
上下文参数：<变量、OAC 结果或上游步骤输出引用>
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

## 8. S6 标准模板：汇总

### 标准输入

```text
汇总结果。
业务意图：<详细自然语言问题>
业务领域知识：<最终结论、证据组织、空结果解释、失败解释规则>
步骤级定制：<S6 汇总业务增量；没有则使用默认模板>
输入来源：<上游步骤摘要、objectStructure、functionOutput、missingOrConflict>
期望输出：finalAnswer
```

### 标准输出：finalAnswer

```text
finalAnswer:
- answer：最终业务结论
- evidence：支撑证据摘要
- dataSummary：数据摘要
- missingInfo：缺失信息
- failureReason：失败原因；无失败则为空
```

### 标准失败策略

- S6 不重新执行上游步骤。
- S6 不重新展开长列表。
- S6 不把 OQL、validation、operationDecision 混入 OAC 最终对象结构。
