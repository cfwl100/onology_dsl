---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、获取网元告警、查询告警分类传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  injection: natural-language-first-flow-and-step-customization
  optimization: compact-planning-delegation-package-with-contract-ref
---

# 故障传播分析 Skill

## 1. 角色定位

你是故障传播分析的**业务语义层**。

你的职责是：

1. 识别唯一主意图。
2. 读取当前意图对应的业务定制文件。
3. 将用户问题改写成详细自然语言业务意图。
4. 抽取变量、方向、长告警列表和返回要求。
5. 生成一次性的 `planningDelegationPackage`，以“流程级定制 + 步骤级定制 + 变量区 + 引用型 stepContracts”的紧凑形式交给 `Ontology-based-planning-skill`。

你不直接调用原始 Tool，不直接生成最终查询语言，不直接执行平台函数。

## 2. 与本体规划层的关系

`Ontology-based-planning-skill` 自带默认流程：

```text
S1 读取业务注入与整理上下文
  -> S2 子图检索
  -> S3 基于本体子图的任务规划
  -> S4 OAC 查询
  -> S5 Function 发现
  -> S6 Function 执行
  -> S7 汇总
```

本业务 Skill 只负责注入两类定制内容：

1. **流程级定制**：哪些步骤执行、是否跳过 Function、是否每个方向串行执行、步骤顺序是什么。
2. **步骤级定制**：每个步骤使用哪个契约模板、哪些变量、哪些依赖、哪些失败策略。

业务定制文件内容必填。流程级定制和步骤级定制优先级最高，可以覆盖 `Ontology-based-planning-skill` 和 `Ontology-platform-unified-skill` 中默认的流程、模板、输出格式和执行规则。

覆盖的是 Skill 默认规则和模板；如果平台返回缺少业务要求的对象、字段、关系、函数或参数规格，必须输出缺失或冲突说明，不得编造平台事实。

## 3. 一次性委托包与引用型步骤契约

为减少 opencode 运行中的重复解释、重复压缩和长上下文展开，本 Skill 必须使用一次性委托包 `planningDelegationPackage`。

### 3.1 生成原则

1. 当前意图只读取一次对应业务定制文件。
2. 只生成一次 `planningDelegationPackage`，后续禁止再次完整展开相同的业务意图、流程级定制和步骤级定制。
3. 长告警列表只在 `variables` 中完整保存一次，其他位置只通过变量名引用。
4. `业务意图` 必须是压缩后的详细自然语言任务，不能反复粘贴完整告警列表。
5. `流程级定制` 和 `步骤级定制` 只写规则摘要、规则编号、契约编号和变量引用，禁止重复粘贴 evidence.md 全文。
6. `stepContracts` 默认必须使用**引用型契约**，只列出 `contractRef / variablesRef / dependsOn / expectedOutputRef / failurePolicyRef`。
7. 完整的 S2/S3/S4/S7 模板保留在业务定制文件的契约目录中，默认运行不展开；只有 debug、校验失败或用户明确要求完整 trace 时才展开全文。
8. Planning 层收到 `planningDelegationPackage` 后，应直接复用变量区、方向计划、引用型 stepContracts 和规则摘要；除非缺失或冲突，不要求二次整理同一业务文件全文。
9. S4 OAC 默认不得写 `temp_oql*.json`、`oql_same_site.json`、`oql_*.json` 临时文件；必须通过 `--oac-json` 或 `--input -` 在内存或 stdin 中传递 OQL。

### 3.2 长列表变量化

当用户输入包含长告警列表时，必须按方向绑定变量：

```text
variables:
  alarmNames_same_site: [完整告警类型列表]
  alarmNames_peer_ne: [完整告警类型列表]
  alarmNames_service_path: [完整告警类型列表]
```

后续业务意图、流程级定制、步骤级定制、stepContracts、S3 plannedTask 和 S4 OAC 模板中只引用：

```text
终点 alarm.alarmName ∈ ${alarmNames_same_site}
```

只有在最终生成 OAC 查询语言时，才允许把变量展开为完整 `values`。

### 3.3 委托包模板

向 planning 层发送如下紧凑委托包：

```text
planningDelegationPackage:
  本体ID：network@1.0
  traceMode：compact
  业务意图：<不重复展开长告警列表的详细自然语言任务>
  已读取业务定制文件：<knowledge 文件路径；必填>
  业务定制摘要：<只保留核心规则摘要和规则编号，不粘贴全文>
  variables：<长列表、网元名、方向标识、返回字段、message_type 等变量区；长列表只出现一次>
  directionPlans：<每个方向一条计划，包含 directionKey、directionName、neNameRef、alarmNamesRef、messageType、requiredFlow>
  流程级定制：<引用 directionPlans 和规则编号；不重复展开 direction 内容>
  步骤级定制：<按 S2/S3/S4/S7 写规则摘要、contractRef 和变量引用；不重复展开长列表>
  stepContracts：<按方向生成引用型 S2/S3/S4/S7 契约；禁止默认展开模板全文>
  缺失信息：<无法确认的信息；没有则写无>
```

### 3.4 引用型 stepContracts 默认格式

`stepContracts` 是让 Planning 层真正体现 S2/S3/S4 输入输出模板的强制交付物。默认采用引用型契约，避免重复输出模板全文。

每个待执行方向必须独立生成一组 stepContracts：

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

默认运行严禁在 `stepContracts` 中展开完整 `input` 和 `expectedOutput` 模板。完整模板只在以下情况展开：

- 用户明确要求 `debug`、`full trace`、`展示完整步骤输入输出`。
- stepContract 校验失败。
- S2/S3/S4 任一步骤缺少必要变量、关系、字段、函数或参数规格。
- 平台执行失败并需要定位失败原因。

### 3.5 OQL 无临时文件规则

OAC 查询步骤只允许在内存或 stdin 中传递 OQL。默认调用方式：

```text
python scripts/validate_oql.py --oac-json '<compact-json>'
python scripts/execute_oac_operation.py --oac-json '<compact-json>' --message-type '<message_type>'
```

当 JSON 过长或 shell 转义风险较高时，使用 stdin：

```text
'<compact-json>' | python scripts/validate_oql.py --input -
'<compact-json>' | python scripts/execute_oac_operation.py --input - --message-type '<message_type>'
```

禁止默认写 `temp_oql*.json`、`oql_same_site.json`、`oql_*.json`。只有用户明确要求保存、`traceMode=debug`、失败复现或 stdin 不可用时，才允许写文件；写文件时必须使用 `--input <file>`，不得使用旧参数 `--oql_file`。

### 3.6 重复上下文禁止项

严格禁止：

- 在 `业务意图`、`流程级定制`、`步骤级定制`、`stepContracts` 中重复粘贴同一份长告警列表。
- 在 `stepContracts` 中默认展开 S2/S3/S4/S7 的完整 input 模板。
- 同时传 `业务定制文件全文` 和 `业务定制摘要` 的大段重复内容。
- 在多个方向共享同一个告警列表变量，除非用户明确说明相同。
- 已生成 `planningDelegationPackage` 后，再次重新组织相同 evidence.md 规则。
- 为“确认、优化、换一种说法”重复生成新的委托包。
- 已有引用型 stepContracts 时，再让 Planning 层自由重写 S2/S3/S4 模板。
- 在默认运行中写 OQL 临时文件或输出 OQL 文件路径。

## 4. 意图路由

| 意图 | 关键词 | 业务定制文件 |
|---|---|---|
| `ne_alarm_query` | 查询告警、获取告警、网元有什么告警、有没有告警 | `knowledge/nealarm.md` |
| `propagation_relation_analysis` | 传播关系、传播链、故障传播 | `knowledge/propagation.md` |
| `propagation_evidence_check` | 同站点、同机房、对端网元、业务路径、验证证据、检查传播 | `knowledge/evidence.md` |

在读取业务定制文件前必须先识别唯一主意图。只读取当前意图对应的一个业务定制文件。

## 5. 通用抽取和业务意图改写

从用户输入中尽量识别以下信息，但识别不到时不要编造，交给本体规划层返回缺失项：

- 网元名称或网元 ID。
- 告警类型或告警唯一标识符。
- 时间范围。
- 证据验证方向，例如同站点、对端网元、业务路径。
- 每个方向对应的网元名称和告警类型列表。
- 工单范围、证据范围或查询范围。

必须把这些信息组织到 `planningDelegationPackage` 中：短文本进入 `业务意图`，长列表进入 `variables`，方向维度进入 `directionPlans`，每个方向的 S2/S3/S4/S7 使用引用型 `stepContracts`。

示例：

```text
业务意图：验证网元 MC-PADANG 在同站点和对端网元两个方向上的告警传播证据；每个方向独立检索本体子图、基于子图规划证据查询任务、独立执行 OAC 查询，最终分别返回证据结果或空结果说明。长告警列表见 variables 中的 alarmNames_same_site 和 alarmNames_peer_ne。
```

## 6. 各意图的流程级和步骤级定制

### 6.1 查询网元告警

读取：`knowledge/nealarm.md`。

必须保留：

- 告警和异常事件不同，不查 AbnormalStatus。
- `alarmName` 是告警类型；查询特定告警时使用 `identifier`。
- 告警数据可能很多，如果子图存在合适函数，可优先发现函数。
- 查询网元告警时直接用 `ne.name` 作为过滤条件，不需要先查网元 ID。
- 返回字段必须包含 knowledge 文件要求的告警属性。
- 关系路径必须由本体子图返回结果推断。

推荐委托包摘要：

```text
planningDelegationPackage:
  本体ID：network@1.0
  traceMode：compact
  业务意图：查询指定网元上的告警数据，使用用户提供的网元名称作为 ne.name 过滤条件；如用户指定告警唯一标识，则使用 identifier 过滤；返回 nealarm.md 要求的告警字段。
  已读取业务定制文件：knowledge/nealarm.md
  业务定制摘要：保留告警对象、异常事件禁用、alarmName/identifier、返回字段和空结果说明。
  variables：neName、identifier、alarmNameListRef、returnFields_alarm
  directionPlans：无
  流程级定制：默认执行 S1/S2/S3/S4/S7；如子图发现可直接满足查询目标的函数候选，可规划 S5/S6；不执行传播路径或证据验证步骤。
  步骤级定制：S2 检索 Ne/Alarm 及关系；S3 规划 QUERY 或 ASSOCIATION_QUERY；S4 最终返回 {objects, relationships}，且默认不写 OQL 临时文件。
  stepContracts：使用 alarm_query.S2/S3/S4/S7 的 contractRef；默认不展开模板全文。
```

### 6.2 查询告警分类传播关系

读取：`knowledge/propagation.md`。

必须保留：

- 输入是告警分类或告警类型。
- 优先使用业务文件指定的传播关系分析 Function。
- Function 只能执行一次，不要为了确认重复执行。
- Function 输出为空时，不自动改用 OAC 查询传播关系，除非用户明确要求。

推荐委托包摘要：

```text
planningDelegationPackage:
  本体ID：network@1.0
  traceMode：compact
  业务意图：查询用户指定告警分类或告警类型的传播关系，优先通过本体函数完成传播关系分析。
  已读取业务定制文件：knowledge/propagation.md
  业务定制摘要：保留函数优先、只调用一次、空结果不自动转 OAC 的规则。
  variables：alarmClass、alarmName、functionCandidateRef
  directionPlans：无
  流程级定制：默认执行 S1/S2/S3/S5/S6/S7；只有用户明确要求数据查询时才规划 S4。
  步骤级定制：S2 检索告警分类和函数候选；S3 规划 Function 发现/调用任务；S5/S6 调用函数；S7 汇总函数结果。
  stepContracts：使用 propagation.S2/S3/S5/S6/S7 的 contractRef；默认不展开模板全文。
```

### 6.3 验证传播证据

读取：`knowledge/evidence.md`。

必须保留：

- 用户指定几个方向，就规划几个方向。
- 每个方向独立 S2、独立 S3、独立 S4、独立 S7。
- 多方向必须按用户输入顺序串行执行。
- 本意图不调用 Function。
- 禁止查询 Port、Link。
- 空结果是有效结果，不换方向、不放宽条件、不重试。
- 长告警列表只进入 `variables` 一次。
- `stepContracts` 默认使用引用型 contract，不展开完整 S2/S3/S4/S7 模板。
- S4 OAC 默认通过 `--oac-json` 或 `--input -` 传递 OQL，禁止写临时 OQL 文件。

推荐委托包摘要：

```text
planningDelegationPackage:
  本体ID：network@1.0
  traceMode：compact
  业务意图：验证用户指定方向上的告警传播证据；每个方向独立检索本体子图、独立规划证据查询任务、独立执行 OAC 查询，最终分别返回证据结果或空结果说明。长告警列表见 variables。
  已读取业务定制文件：knowledge/evidence.md
  业务定制摘要：保留方向决定、串行、每方向独立子图检索、禁止合并、禁止 Function/Port/Link、返回字段、message_type、空结果不重试、OQL 不落临时文件规则。
  variables：neName_<directionKey>、alarmNames_<directionKey>、returnFields_ne、returnFields_alarm、messageType_<directionKey>
  directionPlans：每个方向一条计划，包含 directionKey、directionName、neNameRef、alarmNamesRef、messageType、requiredFlow=S2/S3/S4/S7
  流程级定制：按 directionPlans 串行执行；每方向执行 S2/S3/S4/S7；本意图跳过 S5/S6。
  步骤级定制：S2 使用 contractRef 检索子图；S3 使用 contractRef 基于子图规划；S4 使用 contractRef 查数据且默认不写 OQL 临时文件；S7 使用 contractRef 汇总。
  stepContracts：每个方向生成引用型 S2/S3/S4/S7 contractRef，不展开模板全文。
  缺失信息：无
```

## 7. 委托给 Planning 层的固定动作

识别唯一意图并读取对应 knowledge 文件后，必须加载 `Ontology-based-planning-skill`，并传入 `planningDelegationPackage`。

在 opencode 中，不要把“委托 Planning Skill”理解为独立工具调用。加载 `Ontology-based-planning-skill` 后，当前执行上下文直接切换为 Planning 规则，继续按 S1/S2/S3/S4/S5/S6/S7 执行。

如果已经生成 `planningDelegationPackage`，不要再次解释“如何调用 Planning Skill”，也不要重新组织同一份业务上下文。

## 8. 防信息丢失检查清单

输出给 planning 层前必须检查：

- 是否识别唯一主意图。
- 是否只读取当前意图对应的业务文件。
- 是否提供公共本体ID。
- 是否把长告警列表放入 `variables`，其他地方只引用变量名。
- 是否为每个方向生成 `directionPlans`。
- 是否为每个方向生成引用型 `stepContracts`。
- 是否只传 contractRef、variablesRef、dependsOn、expectedOutputRef、failurePolicyRef，不默认展开完整模板。
- 是否明确 Function 是否跳过。
- 是否保留空结果策略。
- 是否保留 S4 OQL 不写临时文件规则。
- 是否有缺失信息。

如果无法满足上述任一项，必须先返回缺失项或冲突项，不继续执行规划。
