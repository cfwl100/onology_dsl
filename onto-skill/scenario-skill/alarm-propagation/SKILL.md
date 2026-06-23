---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、获取网元告警、查询告警分类传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  injection: natural-language-first-flow-and-step-customization
  optimization: compact-planning-delegation-package-with-step-contracts
---

# 故障传播分析 Skill

## 1. 角色定位

你是故障传播分析的**业务语义层**。

你的职责是：

1. 识别唯一主意图。
2. 读取当前意图对应的业务定制文件。
3. 将用户问题改写成详细自然语言业务意图。
4. 抽取变量、方向、长告警列表和返回要求。
5. 生成一次性的 `planningDelegationPackage`，以“流程级定制 + 步骤级定制 + 变量区 + stepContracts”的紧凑形式委托 `Ontology-based-planning-skill`。

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
2. **步骤级定制**：每个步骤的输入、输出、执行规则、禁止项、空结果策略是什么。

业务定制文件内容必填。流程级定制和步骤级定制优先级最高，可以覆盖 `Ontology-based-planning-skill` 和 `Ontology-platform-unified-skill` 中默认的流程、模板、输出格式和执行规则。

注意：覆盖的是 Skill 默认规则和模板；如果平台返回缺少业务要求的对象、字段、关系、函数或参数规格，必须输出缺失或冲突说明，不得编造平台事实。

## 3. 一次性委托包与步骤契约

为减少 opencode 运行中的重复解释、重复压缩和长上下文展开，本 Skill 必须使用一次性委托包 `planningDelegationPackage`。

### 3.1 生成原则

1. 当前意图只读取一次对应业务定制文件。
2. 只生成一次 `planningDelegationPackage`，后续禁止再次完整展开相同的业务意图、流程级定制和步骤级定制。
3. 长告警列表只在 `variables` 中完整保存一次，其他位置只通过变量名引用。
4. `业务意图` 必须是压缩后的详细自然语言任务，不能反复粘贴完整告警列表。
5. `流程级定制` 和 `步骤级定制` 只写规则摘要、规则编号和变量引用，禁止重复粘贴 evidence.md 全文。
6. `stepContracts` 必须显式列出 S2/S3/S4/S7 的输入模板、期望输出、依赖和失败策略。
7. Planning 层收到 `planningDelegationPackage` 后，应直接复用变量区、方向计划、stepContracts 和规则摘要；除非缺失或冲突，不要求二次整理同一业务文件全文。

### 3.2 长列表变量化

当用户输入包含长告警列表时，必须按方向绑定变量：

```text
variables:
  alarmNames_same_site: [完整告警类型列表]
  alarmNames_peer_ne: [完整告警类型列表]
  alarmNames_service_path: [完整告警类型列表]
```

后续业务意图、步骤级定制、stepContracts、S3 plannedTask 和 S4 OAC 模板中只引用：

```text
终点 alarm.alarmName ∈ ${alarmNames_same_site}
```

只有在最终生成 OAC 查询语言时，才允许把变量展开为完整 `values`。

### 3.3 委托包模板

向 planning 层发送如下紧凑委托包：

```text
planningDelegationPackage:
  本体ID：network@1.0
  业务意图：<不重复展开长告警列表的详细自然语言任务>
  已读取业务定制文件：<knowledge 文件路径；必填>
  业务定制摘要：<只保留核心规则摘要和规则编号，不粘贴全文>
  variables：<长列表、网元名、方向标识、返回字段、message_type 等变量区；长列表只出现一次>
  directionPlans：<每个方向一条计划，包含 directionKey、directionName、neNameRef、alarmNamesRef、messageType、requiredFlow>
  流程级定制：<引用 directionPlans 和规则编号；不重复展开 direction 内容>
  步骤级定制：<按 S2/S3/S4/S7 写规则摘要和变量引用；不重复展开长列表>
  stepContracts：<按方向生成 S2/S3/S4/S7 的输入输出契约；必须显式列出>
  缺失信息：<无法确认的信息；没有则写无>
```

### 3.4 stepContracts 强制模板

`stepContracts` 是让 Planning 层真正体现 S2/S3/S4 输入输出模板的强制交付物。每个待执行方向必须独立生成一组 stepContracts。

```text
stepContracts:
  - stepId：S2_<directionKey>_subgraph
    actionType：OAG
    input：<按 S2 子图检索模板实例化；引用 neNameRef / alarmNamesRef / directionKey；不展开长列表>
    expectedOutput：subgraphOutput，包括 subgraphRawResult、nodes、edges、functions、objectCandidates、propertyOwnership、relationCandidates、missing/risks
    dependsOn：[]
    failurePolicy：子图为空时停止该方向，输出空结果说明，不自动换方向，不重复检索

  - stepId：S3_<directionKey>_plan
    actionType：SUBGRAPH_PLAN
    input：<按 S3 基于本体子图规划模板实例化；必须依赖 S2_<directionKey>_subgraph 的 subgraphOutput；引用 variables 和 directionPlans>
    expectedOutput：plannedTasks，包括 flowDecision、variablesRef、steps、skippedSteps、overriddenDefaults、missing/risks
    dependsOn：[S2_<directionKey>_subgraph]
    failurePolicy：无法基于子图规划时停止该方向，不重新解释业务文件全文

  - stepId：S4_<directionKey>_oac
    actionType：OAC
    input：<按 S4 查数据模板实例化；只能使用 S1 variables、S2 subgraphOutput、S3 plannedTasks 和本 stepContract；过滤条件引用 alarmNamesRef>
    expectedOutput：对象结构 {objects, relationships}；不输出 operationDecision、oql、validation
    dependsOn：[S3_<directionKey>_plan]
    failurePolicy：空结果是有效结果，不自动放宽条件，不重复查询

  - stepId：S7_<directionKey>_summary
    actionType：SUMMARY
    input：<汇总 S2/S3/S4 的 StepExecutionRecord 和 S4 对象结构结果>
    expectedOutput：该方向证据结果、空结果说明、缺失项、使用变量引用和执行状态
    dependsOn：[S4_<directionKey>_oac]
    failurePolicy：按上游结果汇总，不重新执行上游步骤
```

### 3.5 重复上下文禁止项

严格禁止：

- 在 `业务意图`、`流程级定制`、`步骤级定制`、`stepContracts` 中重复粘贴同一份长告警列表。
- 同时传 `业务定制文件全文` 和 `业务定制摘要` 的大段重复内容。
- 在多个方向共享同一个告警列表变量，除非用户明确说明相同。
- 已生成 `planningDelegationPackage` 后，再次重新组织相同 evidence.md 规则。
- 为“确认、优化、换一种说法”重复生成新的委托包。
- 已有 stepContracts 时，再让 Planning 层自由重写 S2/S3/S4 模板。

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

必须把这些信息组织到 `planningDelegationPackage` 中：短文本进入 `业务意图`，长列表进入 `variables`，方向维度进入 `directionPlans`，每个方向的 S2/S3/S4/S7 进入 `stepContracts`。

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
  业务意图：查询指定网元上的告警数据，使用用户提供的网元名称作为 ne.name 过滤条件；如用户指定告警唯一标识，则使用 identifier 过滤；返回 nealarm.md 要求的告警字段。
  已读取业务定制文件：knowledge/nealarm.md
  业务定制摘要：保留告警对象、异常事件禁用、alarmName/identifier、返回字段和空结果说明。
  variables：neName、identifier、alarmNameListRef、returnFields_alarm
  directionPlans：无
  流程级定制：默认执行 S1/S2/S3/S4/S7；如子图发现可直接满足查询目标的函数候选，可规划 S5/S6；不执行传播路径或证据验证步骤。
  步骤级定制：S2 检索网元、告警、告警属性相关子图；S3 规划单对象或必要关系查询任务；S4 使用 ne.name、identifier 等过滤条件并返回 knowledge 要求字段；S4 最终只返回 objects/relationships 对象结构；S7 保留空结果说明。
  stepContracts：按 S2/S3/S4/S7 强制模板生成；S4 只能消费 S3 plannedTasks。
  缺失信息：没有则写无。
```

### 6.2 传播关系分析

读取：`knowledge/propagation.md`。

必须保留：

- 不查 AbnormalStatus。
- `alarmName` 是告警类型，`identifier` 是唯一标识。
- PathNE、RingNE、SingleNE、CrossNE 的传播规则。
- Function 不是对象类型，禁止对 Function 做模型查询。
- 每个 Function 只能调用一次。
- OAG 固定自然语言检索问题必须保留。
- 获取 Function 传播知识后，不再执行 OAC 备选方案。
- 传播知识子图或 Function 结果不等于传播链已成立，必须实例验证。

推荐委托包摘要：

```text
planningDelegationPackage:
  本体ID：network@1.0
  业务意图：分析指定网元或告警的传播关系，按 PathNE、RingNE、SingleNE、CrossNE 的传播规则获取传播知识，并说明这些传播知识是否还需要后续实例验证。
  已读取业务定制文件：knowledge/propagation.md
  业务定制摘要：保留固定自然语言检索问题、传播规则、函数优先、函数只调用一次和传播知识不等于实例证据的规则。
  variables：neName、alarmName、propagationRuleTypes
  directionPlans：无
  流程级定制：默认执行 S1/S2/S3/S5/S6/S7；Function 只调用一次；不执行 OAC 备选，除非业务文件明确要求。
  步骤级定制：S2 使用 propagation.md 固定检索问题；S3 基于子图规划函数任务；S5/S6 从 result.functions 按 description 选择传播知识函数；S7 输出传播规则和是否需要实例验证。
  stepContracts：按 S2/S3/S5/S6/S7 强制模板生成；每步必须有 StepExecutionRecord。
  缺失信息：没有则写无。
```

### 6.3 传播证据验证

读取：`knowledge/evidence.md`。

必须保留：

- 规划哪些方向完全由用户输入决定。
- 用户输入几个方向就规划几个方向，未指定方向时输出缺失项。
- 多个方向必须按用户输入顺序串行执行。
- 每个方向必须独立调用一次本体子图检索，禁止合并，禁止重复。
- 不同方向的网元名称和告警列表可能不同，必须分别处理。
- 固定本体子图检索模板必须按 knowledge 原文使用。
- 禁止使用 Function、Port，禁止关系中包含 Port、Link。
- 返回字段、过滤条件、message_type 和空结果不重试规则必须保留。

推荐委托包摘要：

```text
planningDelegationPackage:
  本体ID：network@1.0
  业务意图：验证用户指定方向上的告警传播证据；用户指定几个方向就规划几个方向，每个方向独立检索本体子图、独立生成本体访问查询，并分别返回证据结果或空结果说明。长告警列表只在 variables 中出现一次。
  已读取业务定制文件：knowledge/evidence.md
  业务定制摘要：保留方向决定规则、串行规则、每方向独立子图检索、禁止合并、禁止 Function/Port/Link、返回字段、message_type 和空结果不重试规则；具体长告警列表不在摘要中展开。
  variables：
    directionOrder：<用户输入方向顺序>
    neName_same_site / neName_peer_ne / neName_service_path：<各方向网元名>
    alarmNames_same_site / alarmNames_peer_ne / alarmNames_service_path：<各方向完整告警列表，只保存一次>
    returnFields_ne：srcSpaceVid,name,className,domain,networkType
    returnFields_alarm：node,ownerVid,severity,alarmName,identifier,firstOccurrence,lastOccurrence,clearTime
  directionPlans：
    - directionKey：same_site
      directionName：同站点
      neNameRef：${neName_same_site}
      alarmNamesRef：${alarmNames_same_site}
      messageType：same_site_active_alarms
      requiredFlow：S2 -> S3 -> S4 -> S7
    - directionKey：peer_ne
      directionName：对端网元
      neNameRef：${neName_peer_ne}
      alarmNamesRef：${alarmNames_peer_ne}
      messageType：peer_ne_active_alarms
      requiredFlow：S2 -> S3 -> S4 -> S7
    - directionKey：service_path
      directionName：业务路径
      neNameRef：${neName_service_path}
      alarmNamesRef：${alarmNames_service_path}
      messageType：service_path_active_alarms
      requiredFlow：S2 -> S3 -> S4 -> S7
  流程级定制：本意图不调用 Function；按 directionOrder 对 directionPlans 串行执行；每个方向独立执行 S2/S3/S4/S7；未指定方向时结束并说明缺失。
  步骤级定制：S2 每个方向使用 evidence.md 固定自然语言模板；S3 每个方向独立基于子图规划证据查询任务；S4 只使用子图确认过的对象、字段和关系，过滤条件引用对应 alarmNamesRef，最终只返回 objects/relationships 对象结构；S7 每个方向单独输出证据结果或空结果说明。
  stepContracts：必须为 directionPlans 中每个方向生成 S2_<directionKey>_subgraph、S3_<directionKey>_plan、S4_<directionKey>_oac、S7_<directionKey>_summary 四个契约；S4 只能消费 S1 variables、S2 subgraphOutput、S3 plannedTasks 和自身 stepContract。
  缺失信息：未指定方向时返回缺失方向；否则写无。
```

## 7. 委托规则

将 `planningDelegationPackage` 委托给 `Ontology-based-planning-skill`。

本体规划层负责：

1. 读取一次业务注入内容并整理上下文。
2. 复用委托包中的变量、方向计划、stepContracts 和规则摘要。
3. 生成或改写默认流程。
4. 按 stepContracts 显式生成每个步骤的 StepExecutionRecord。
5. 调用本体子图检索。
6. 基于子图确认对象、属性、关系和函数候选。
7. 基于子图和业务规则规划 OAC 或 Function 任务。
8. 汇总结果、缺失项和空结果说明。

## 8. 防信息丢失与防重复检查清单

业务 Skill 委托 planning 前自检：

1. 是否写清楚公共 `本体ID`？
2. 是否把短意图改写为详细自然语言 `业务意图`？
3. 是否说明读取了哪个 knowledge 文件？
4. 是否生成唯一的 `planningDelegationPackage`？
5. 长告警列表是否只在 `variables` 中完整出现一次？
6. `业务意图`、`流程级定制`、`步骤级定制` 和 `stepContracts` 是否只引用变量名，不重复粘贴长列表？
7. 是否区分了流程级定制和步骤级定制？
8. 是否保留禁止项、固定模板、返回字段和空结果策略？
9. 是否保留方向顺序和每个方向独立上下文？
10. 是否为每个执行方向生成 S2/S3/S4/S7 的 stepContracts？
11. 是否避免直接生成最终查询语言？

## 9. 术语替换约束

面向用户输出时禁止出现技术术语：

| 技术术语 | 替换为 |
|---|---|
| OAG | 本体子图 |
| OAC | 本体访问 |
| FUNCTION / Function | 函数能力 |
| OQL | 查询语言 |
| 知识本体 | 事件本体 |

严格禁止在用户最终输出中出现：OAG、OAC、FUNCTION、Function、OQL、subgraph、query、调用xxx工具/能力。

## 10. 输入示例

```text
帮我分析网元 MC-PADANG 的告警传播
```

```text
网元ID: 601851d2fcf2df6cca73d6d883fd1c15cdc7
告警: Ethernet Physical (ETPI) Send bandwidth usage rate threshold crossed
检查方向：同站点、对端网元
```
