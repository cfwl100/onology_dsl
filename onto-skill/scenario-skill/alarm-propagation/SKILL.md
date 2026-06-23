---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、获取网元告警、查询告警分类传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  injection: natural-language-first-flow-and-step-customization
  optimization: compact-planning-delegation-package-with-step-template-ref
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
2. **步骤级定制**：每个步骤使用哪个标准步骤模板、哪个业务契约、哪些变量、哪些依赖、哪些失败策略。

业务定制文件内容必填。流程级定制和步骤级定制优先级最高，可以覆盖 `Ontology-based-planning-skill` 和 `Ontology-platform-unified-skill` 中默认的流程、模板、输出格式和执行规则。

覆盖的是 Skill 默认规则和模板；如果平台返回缺少业务要求的对象、字段、关系、函数或参数规格，必须输出缺失或冲突说明，不得编造平台事实。

## 3. 一次性委托包与引用型步骤契约

为减少 opencode 运行中的重复解释、重复压缩和长上下文展开，本 Skill 必须使用一次性委托包 `planningDelegationPackage`。

### 3.1 生成原则

1. 当前意图只读取一次对应业务定制文件。
2. 只生成一次 `planningDelegationPackage`，后续禁止再次完整展开相同的业务意图、流程级定制和步骤级定制。
3. 长告警列表只在 `variables` 中完整保存一次，其他位置只通过变量名引用。
4. `业务意图` 必须是压缩后的详细自然语言任务，不能反复粘贴完整告警列表。
5. `流程级定制` 和 `步骤级定制` 只写规则摘要、规则编号、标准模板编号、业务契约编号和变量引用，禁止重复粘贴 evidence.md 全文。
6. `stepContracts` 默认必须使用**标准模板 + 业务增量契约**的引用模式，只列出 `stepTemplateRef / contractRef / variablesRef / inputRefs / dependsOn / expectedOutputRef / failurePolicyRef`。
7. S2/S3/S4/S5/S6/S7 的标准输入、标准输出、标准执行规则和标准失败策略来自 Planning 标准模板库 `references/standard-step-templates.md`，默认运行不展开全文。
8. evidence 场景的方向、对象、字段、路径、过滤条件、返回要求等业务差异来自 `knowledge/evidence.md` 中的 `contractRef`，默认运行只引用编号。
9. Planning 层收到 `planningDelegationPackage` 后，应直接复用变量区、方向计划、引用型 stepContracts 和规则摘要；除非缺失或冲突，不要求二次整理同一业务文件全文。
10. S4 OAC 默认不得写 `temp_oql*.json`、`oql_same_site.json`、`oql_*.json` 临时文件；必须通过 `--oac-json` 或 `--input -` 在内存或 stdin 中传递 OQL。

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
  步骤级定制：<按 S2/S3/S4/S7 写 stepTemplateRef、contractRef 和变量引用；不重复展开长列表>
  stepContracts：<按方向生成引用型 S2/S3/S4/S7 契约；禁止默认展开模板全文>
  缺失信息：<无法确认的信息；没有则写无>
```

### 3.4 引用型 stepContracts 默认格式

`stepContracts` 是让 Planning 层真正体现 S2/S3/S4 输入输出模板的强制交付物。默认采用标准模板 + 业务契约双引用，避免重复输出模板全文。

每个待执行方向必须独立生成一组 stepContracts：

```text
stepContracts:
  - stepId：S2_<directionKey>_subgraph
    actionType：OAG
    stepTemplateRef：standard.S2.oag
    contractRef：evidence.<directionKey>.S2.subgraph
    variablesRef：[neName_<directionKey>, alarmNames_<directionKey>, returnFields_ne, returnFields_alarm, messageType_<directionKey>]
    expectedOutputRef：subgraphOutput
    dependsOn：[]
    failurePolicyRef：evidence.common.fail.stop_on_empty_subgraph

  - stepId：S3_<directionKey>_plan
    actionType：SUBGRAPH_PLAN
    stepTemplateRef：standard.S3.subgraphPlan
    contractRef：evidence.<directionKey>.S3.plan
    inputRefs：[S2_<directionKey>_subgraph.subgraphOutput, variables, directionPlans.<directionKey>]
    expectedOutputRef：plannedTasks
    dependsOn：[S2_<directionKey>_subgraph]
    failurePolicyRef：evidence.common.fail.stop_on_unplannable_subgraph

  - stepId：S4_<directionKey>_oac
    actionType：OAC
    stepTemplateRef：standard.S4.oac
    contractRef：evidence.<directionKey>.S4.oac
    inputRefs：[variables, S2_<directionKey>_subgraph.subgraphOutput, S3_<directionKey>_plan.plannedTasks]
    variablesRef：[neName_<directionKey>, alarmNames_<directionKey>, returnFields_ne, returnFields_alarm, messageType_<directionKey>]
    expectedOutputRef：objectStructure
    dependsOn：[S3_<directionKey>_plan]
    failurePolicyRef：evidence.common.fail.valid_empty_result_no_retry

  - stepId：S7_<directionKey>_summary
    actionType：SUMMARY
    stepTemplateRef：standard.S7.summary
    contractRef：evidence.<directionKey>.S7.summary
    inputRefs：[S2_<directionKey>_subgraph.record, S3_<directionKey>_plan.record, S4_<directionKey>_oac.record]
    expectedOutputRef：directionEvidenceSummary
    dependsOn：[S4_<directionKey>_oac]
    failurePolicyRef：evidence.common.fail.summary_only_no_rerun
```

默认运行严禁在 `stepContracts` 中展开完整 `input` 和 `expectedOutput` 模板。完整模板只在以下情况展开：

- 用户明确要求 `debug`、`full trace`、`展示完整步骤输入输出`。
- stepTemplateRef 或 contractRef 校验失败。
- S2/S3/S4 任一步骤缺少必要变量、关系、字段、函数或参数规格。
- 平台执行失败并需要定位失败原因。

### 3.5 OQL 无临时文件规则

OAC 查询步骤只允许在内存或 stdin 中传递 OQL。默认调用方式使用通用 shell 形式描述，不绑定 PowerShell：

```sh
python scripts/validate_oql.py --oac-json '<compact-json>'
python scripts/execute_oac_operation.py --oac-json '<compact-json>' --message-type '<message_type>'
```

当 JSON 过长或 shell 转义风险较高时，使用 stdin：

```sh
printf '%s' '<compact-json>' | python scripts/validate_oql.py --input -
printf '%s' '<compact-json>' | python scripts/execute_oac_operation.py --input - --message-type '<message_type>'
```

禁止默认写 `temp_oql*.json`、`oql_same_site.json`、`oql_*.json`。只有用户明确要求保存、`traceMode=debug`、失败复现或 stdin 不可用时，才允许写文件；写文件时必须使用 `--input <file>`，不得使用旧参数 `--oql_file`。

### 3.6 重复上下文禁止项

严格禁止：

- 在 `业务意图`、`流程级定制`、`步骤级定制`、`stepContracts` 中重复粘贴同一份长告警列表。
- 在 `stepContracts` 中默认展开 S2/S3/S4/S7 的完整标准模板或业务模板。
- 同时传 `业务定制文件全文` 和 `业务定制摘要` 的大段重复内容。
- 在多个方向共享同一个告警列表变量，除非用户明确说明相同。
- 已生成 `planningDelegationPackage` 后，再次重新组织相同 evidence.md 规则。
- 为“确认、优化、换一种说法”重复生成新的委托包。
