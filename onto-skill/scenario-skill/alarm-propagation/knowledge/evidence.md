# 验证传播证据

## 目标

根据获取到的传播关系知识，验证实例层是否存在支持传播链的告警证据。

## 核心经验性知识

- 业务路径在本体中名称为 `businesspath`。
- 告警的 `alarmName` 实际上是告警类型。
- 告警的唯一标识符是 `identifier`。

## 证据检查方向

验证传播证据时，检查哪些方向由**用户输入**决定。

每个方向的目的：

1. **同站点**：找到网元，与它同站点的其他网元的告警。
2. **对端网元**：找到网元，与它通过对端链路相连的其他网元的告警。
3. **业务路径**：找到网元，与它同属一个业务路径的其他网元的告警。

动态规划原则：

- 用户输入“三步[同站点、对端网元、业务路径]” → 规划并执行 3 个方向。
- 用户输入“两步[同站点、对端网元]” → 规划并执行 2 个方向。
- 用户输入“同站点” → 只规划并执行 1 个方向。
- 用户输入为 0 步，或未指定，直接结束当前会话并输出 `未指定规划方向`，禁止臆测执行。
- 必须按照用户输入顺序，按顺序执行不同方向的规划。

## 运行效率优化：一次性委托包、变量绑定与引用型步骤契约

传播证据验证必须使用一次性 `planningDelegationPackage`。默认运行采用 `traceMode=compact`。

### 变量绑定规则

用户输入中的长告警列表必须只保存一次，写入 `variables`：

```text
variables:
  alarmNames_same_site: [同站点方向完整告警类型列表]
  alarmNames_peer_ne: [对端网元方向完整告警类型列表]
  alarmNames_service_path: [业务路径方向完整告警类型列表]
```

后续所有流程级定制、步骤级定制、stepContracts、S3 plannedTask 和 S4 查询模板只能引用变量名：

```text
终点 alarm.alarmName ∈ ${alarmNames_same_site}
```

只有在最终生成本体访问查询语言时，才允许把 `${alarmNames_same_site}` 展开为完整 `values` 列表。

### 委托包必填内容

传播证据验证委托 Planning 层时，应传递紧凑委托包：

```text
planningDelegationPackage:
  本体ID：network@1.0
  traceMode：compact
  业务意图：验证用户指定方向上的告警传播证据；每个方向独立检索子图、独立规划、独立查询；长告警列表见 variables。
  已读取业务定制文件：knowledge/evidence.md
  业务定制摘要：保留方向决定、串行、每方向独立子图检索、禁止合并、禁止 Function/Port/Link、返回字段、message_type、空结果不重试规则。
  variables：<各方向网元名、完整告警列表、返回字段、message_type>
  directionPlans：<每个方向一条，包含 directionKey、neNameRef、alarmNamesRef、messageType、requiredFlow>
  流程级定制：按 directionPlans 串行执行；每方向执行 S2/S3/S4/S7；本意图不调用 Function。
  步骤级定制：S2/S3/S4/S7 只引用 contractRef；完整模板保留在本文件的契约目录中。
  stepContracts：<每个方向生成引用型契约，禁止默认展开完整 input 模板>
```

### 引用型 stepContracts 默认规则

每个用户指定方向必须生成独立的四个步骤契约，但默认只传引用，不展开完整模板。

```text
stepContracts:
  - stepId：S2_<directionKey>_subgraph
    actionType：OAG
    contractRef：evidence.<directionKey>.S2.subgraph
    variablesRef：[neName_<directionKey>, alarmNames_<directionKey>, returnFields_ne, returnFields_alarm, messageType_<directionKey>]
    expectedOutputRef：subgraphOutput
    dependsOn：[]
    failurePolicyRef：evidence.common.fail.stop_on_empty_subgraph

  - stepId：S3_<directionKey>_plan
    actionType：SUBGRAPH_PLAN
    contractRef：evidence.<directionKey>.S3.plan
    inputRefs：[S2_<directionKey>_subgraph.subgraphOutput, variables, directionPlans.<directionKey>]
    expectedOutputRef：plannedTasks
    dependsOn：[S2_<directionKey>_subgraph]
    failurePolicyRef：evidence.common.fail.stop_on_unplannable_subgraph

  - stepId：S4_<directionKey>_oac
    actionType：OAC
    contractRef：evidence.<directionKey>.S4.oac
    inputRefs：[variables, S2_<directionKey>_subgraph.subgraphOutput, S3_<directionKey>_plan.plannedTasks]
    variablesRef：[neName_<directionKey>, alarmNames_<directionKey>, returnFields_ne, returnFields_alarm, messageType_<directionKey>]
    expectedOutputRef：objectStructure
    dependsOn：[S3_<directionKey>_plan]
    failurePolicyRef：evidence.common.fail.valid_empty_result_no_retry

  - stepId：S7_<directionKey>_summary
    actionType：SUMMARY
    contractRef：evidence.<directionKey>.S7.summary
    inputRefs：[S2_<directionKey>_subgraph.record, S3_<directionKey>_plan.record, S4_<directionKey>_oac.record]
    expectedOutputRef：directionEvidenceSummary
    dependsOn：[S4_<directionKey>_oac]
    failurePolicyRef：evidence.common.fail.summary_only_no_rerun
```

默认运行禁止在 `stepContracts` 中展开完整 `input` 与 `expectedOutput`。完整模板仅在 debug、失败定位或用户明确要求完整 trace 时展开。

### 契约目录：contractRef 对应的完整模板

以下模板是 Planning 层和步骤执行时的依据。默认运行只引用 `contractRef`，不要复制全文到 stepContracts。

#### evidence.common.fail.stop_on_empty_subgraph

子图为空时停止该方向，输出空结果说明，不自动换方向，不重复检索。

#### evidence.common.fail.stop_on_unplannable_subgraph

无法基于子图规划时停止该方向，输出缺失对象、字段、关系或函数信息，不重新解释本文件全文。

#### evidence.common.fail.valid_empty_result_no_retry

OAC 返回空对象结构是有效结果，不自动放宽条件，不换路径，不重复查询。

#### evidence.common.fail.summary_only_no_rerun

汇总只使用上游 StepExecutionRecord 和结果引用，不重新执行上游步骤。

#### evidence.<directionKey>.S2.subgraph

S2 子图检索模板：

```text
先找相关子图。
本体ID：network@1.0
业务意图：验证 <directionName> 方向传播证据。
业务定制文件：knowledge/evidence.md
子图检索规则：每个方向独立检索一次；使用本文件固定 query；禁止合并多个方向；禁止重复检索。
检索目标：从网元出发，查找 <directionName> 方向可到达的其他网元及其告警；返回对象、属性、关系和函数候选。
子图返回结构要求：保留 result.seedNodes、nodes、edges、functions、actions；摘要必须包含对象候选、字段归属、关系候选。
```

S2 输出必须为 `subgraphOutput`，包含：`subgraphRawResult`、`nodes`、`edges`、`functions`、`objectCandidates`、`propertyOwnership`、`relationCandidates`、`missing/risks`。

#### evidence.<directionKey>.S3.plan

S3 任务规划模板：

```text
基于本体子图规划执行任务。
本体ID：network@1.0
业务意图：验证 <directionName> 方向传播证据。
本体子图结果：${S2_<directionKey>_subgraph.actualOutput.subgraphOutput}
变量区：neNameRef=${neName_<directionKey>}，alarmNamesRef=${alarmNames_<directionKey>}，returnFields_ne=${returnFields_ne}，returnFields_alarm=${returnFields_alarm}
方向计划：${directionPlans.<directionKey>}
业务规划规则：禁止 Function；禁止 Port/Link；关系名必须来自 defines_relation.properties.name；字段必须通过 has_property 确认归属；过滤条件引用 alarmNamesRef，不展开长列表。
```

S3 输出必须为 `plannedTasks`，包含：`flowDecision`、`variablesRef`、`steps`、`skippedSteps`、`overriddenDefaults`、`missing/risks`，并必须生成一个 `S4_<directionKey>_oac` 步骤。

#### evidence.<directionKey>.S4.oac

S4 OAC 数据访问模板：

```text
查数据
本体ID：network@1.0
操作类型：ASSOCIATION_QUERY
查询对象：来自 S3_<directionKey>_plan.plannedTasks，不得重新推断
关系路径：来自 S3_<directionKey>_plan.plannedTasks，关系名必须来自 defines_relation.properties.name
过滤条件：起点 ne.name = ${neName_<directionKey>}；终点 alarm.alarmName ∈ ${alarmNames_<directionKey>}；对端网元方向需要增加 peer ne.name != ${neName_<directionKey>}；业务路径方向需要增加 businesspath.aDeviceName = ${neName_<directionKey>}
返回要求：返回 returnFields_ne 和 returnFields_alarm；message_type=${messageType_<directionKey>}；空结果是有效结果
执行要求：先生成并校验查询语言；通过后再执行；结果为空不重试、不换路径、不放宽条件。
期望输出：只返回对象结构 {objects, relationships}；不输出 operationDecision、oql、validation。
```

S4 输出必须为：

```json
{
  "objects": [],
  "relationships": []
}
```

#### evidence.<directionKey>.S7.summary

S7 汇总模板：

```text
汇总 S2/S3/S4 的 StepExecutionRecord 和 S4 对象结构结果。
输出该方向证据结果、空结果说明、缺失项、使用变量引用和执行状态。
不得重新执行 S2/S3/S4。
```

### 禁止重复展开

严格禁止：

- 在业务意图、流程级定制、步骤级定制、stepContracts 中重复粘贴完整告警列表。
- 在默认运行中把契约目录中的完整 S2/S3/S4/S7 模板复制到 stepContracts。
- 在同一次会话中重复读取并压缩本文件。
- 已生成 `planningDelegationPackage` 后，再重新组织一份相同含义的委托说明。
- 为了“确认、优化、换一种说法”重复生成委托包。
- 有引用型 stepContracts 时，再让 Planning 层自由重写 S2/S3/S4 模板。

## 验证传播证据查询逻辑

核心逻辑：从网元出发，查找同站点/对端/业务路径的其他网元的告警。

输入：

- 用户输入可能包含多个方向，每个方向有独立配置。
- 每个方向的配置：
  - 网元名称 `ne.name`，必填。
  - 终点告警类别，必填；该方向要筛选的告警类型列表。

关键点：

- 不同方向的网元名称和告警列表可能不同，必须独立处理。
- 规划时需要为每个方向生成独立的执行计划。
- `alarmName` 是告警类别，不是唯一标识符。
- 长告警列表只在 `variables` 中保存一次，后续通过变量引用传递。
- 每个方向的 S2/S3/S4/S7 输入输出必须体现在引用型 stepContracts 和 StepExecutionRecord 摘要中。

## 关系名动态获取

关系名从本体子图的 `edges.properties.name` 动态获取，不固定在代码或配置中。

- `businesspath` 是对象类型，不是关系边。
- 关系名 `pathThrough` 必须从本体子图的 `edges.properties.name` 获取。
- 如果本体子图返回的边名称不是 `pathThrough`，必须使用返回的实际名称。

## 查询约束

- 当方向为 `同站点` 时，查询路径禁止 site 经过 ne 连接 alarm，除非本体子图没有直接 site 到 alarm 的关系且业务规则明确允许走可达路径。
- 当方向为 `对端网元` 以及 `业务路径` 时，查询路径必须经过 ne 再连接 alarm。

## OAG 调用规则

1. 每个方向必须独立调用一次 OAG，禁止在一个 OAG 调用中同时查询多个方向。
2. 方向唯一键：
   - 同站点：`same_site`
   - 对端网元：`peer_ne`
   - 业务路径：`service_path`
3. 同一方向只能调用一次，禁止为了“确认、优化、换一种说法”而重复调用。
4. 获取到某方向的 OAC 结果后，后续必须直接使用，禁止重新查询。
5. 禁止使用模板以外的自由 query。

## 固定 OAG query 模板

### 同站点

```text
查找网元通过站点关联到其他网元及这些网元告警的本体子图。
```

### 对端网元

```text
查找网元通过对端链路关联到其他网元及这些网元告警的本体子图。
```

### 业务路径

```text
查找网元通过业务路径关联到其他网元及这些网元告警的本体子图。
```

## OAC 查询内容

每个方向最终都应查询：

```text
起点网元 -> 中间对象/关系 -> 其他网元 -> 告警
```

过滤条件必须包含：

- 起点网元：`ne.name = ${neName_<directionKey>}`。
- 终点告警类型：`alarm.alarmName IN ${alarmNames_<directionKey>}`。
- 对端网元方向需要排除自身：`peerNe.name != ${neName_<directionKey>}`。
- 业务路径方向需要使用业务路径设备名：`businesspath.aDeviceName = ${neName_<directionKey>}`。

## 输出字段

### 网元返回字段

```text
srcSpaceVid, name, className, domain, networkType
```

### 告警返回字段

```text
node, ownerVid, severity, alarmName, identifier, firstOccurrence, lastOccurrence, clearTime
```

## message_type

- 同站点：`same_site_active_alarms`
- 对端网元：`peer_ne_active_alarms`
- 业务路径：`service_path_active_alarms`

## 禁止项

- 本意图禁止调用 Function。
- 禁止查询 Port、Link。
- 禁止合并多个方向到一个 OAG/OAC 步骤。
- 禁止自动补充用户未指定方向。
- 禁止空结果后自动放宽条件、换路径或重试。
- 禁止在默认运行中输出完整 contract 模板；默认只输出引用。
