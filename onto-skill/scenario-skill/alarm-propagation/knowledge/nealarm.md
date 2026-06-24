# 获取网元告警

本文是 `alarm-propagation` 中“查询网元告警”意图的业务领域知识文件，采用当前六步格式组织。业务 Skill 读取本文后，将必要内容注入 Planning 顶层输入的 `业务领域知识`、`流程级定制`、`步骤级定制` 和 `缺失信息` 中。

## 0. 全局业务领域知识

目标：识别指定网元是否存在当前或活动告警，并返回告警对象结构。

核心知识：

- 告警和异常事件不同，查询告警时不要查询 `AbnormalStatus`。
- `alarm.alarmName` 表示告警类型，不是单条告警唯一标识。
- 单条或指定告警实例应优先使用 `alarm.identifier` 过滤。
- 查询某网元告警时，直接使用 `ne.name` 作为过滤条件，不需要先查询网元 ID。
- 如果子图中存在可信告警查询函数候选，可以在流程级定制中启用函数步骤；否则走 OAC 查询。

网元层级：

| 层级 | 含义 | ne_layer |
|---|---|---|
| CN | 核心路由 Core Network | 30 |
| AN | 汇聚路由 Aggregation Network | 20 |
| EN | 接入路由 Edge Network | 10 |

告警返回字段必须全部来自 `alarm` 对象：

```text
ownerVid, severity, alarmName, identifier, firstOccurrence, lastOccurrence, clearTime, node
```

## 1. 流程级定制

默认流程：

```text
S1 -> S2 -> S3 -> S6
```

如果业务领域知识明确要求使用可信告警查询函数，可采用：

```text
S1 -> S2 -> S4 -> S5 -> S6
```

空结果表示当前未发现匹配告警，不自动换路径、不自动扩大查询范围。

## 2. S1 子图检索

输入模板：

```text
检索本体子图
本体ID：<本体ID>
业务意图：查询指定网元的当前或活动告警
业务领域知识：告警对象、网元对象、ne.name 过滤规则、告警字段返回要求、函数候选规则
步骤级定制：查询网元告警的子图检索规则
检索目标：从 ne 对象出发，查找关联 alarm 对象的路径、字段、关系和函数候选
返回结构要求：保留 ne、alarm、字段归属、关系路径、函数候选、缺失项
```

输出模板：

```text
subgraphOutput：
- rawSubgraph：OAG 返回的原始图结构
- objectCandidates：ne、alarm
- propertyCandidates：ne.name、alarm 的必返字段
- relationCandidates：ne 到 alarm 的可达关系路径
- functionCandidates：告警查询相关函数候选
- missingItems：缺失对象、字段、关系或函数
```

执行规则：

- 通过 OAG 子图确认 ne 到 alarm 的关系路径。
- 子图中没有 alarm 对象或告警字段时，停止后续查询并进入 S6 输出缺失信息。

## 3. S2 基于本体子图的任务规划

输入模板：

```text
基于本体子图规划执行任务
本体ID：<本体ID>
业务意图：查询指定网元的告警
本体子图：<S1.subgraphOutput.rawSubgraph>
业务领域知识：ne.name 直接过滤、告警返回字段、函数候选策略、空结果策略
步骤级定制：查询网元告警的任务规划规则
规划目标：确认使用 OAC 查询还是函数候选，并规划返回 alarm 对象字段
```

规划规则：

- 没有可信函数候选时，规划 S3 OAC 查询。
- OAC 查询过滤条件使用 `ne.name = <网元名称>`。
- 用户明确要求指定告警实例时，使用 `alarm.identifier` 过滤。
- `alarmName` 仅用于告警类型过滤，不用于唯一实例定位。

输出模板：

```text
plannedTasks：
- taskType：OAC_QUERY 或 FUNCTION_CALL
- operationType：QUERY / ASSOCIATION_QUERY / FUNCTION
- objectPlan：ne、alarm
- relationPathPlan：来自 S1 子图的 ne 到 alarm 路径
- filterPlan：ne.name 或 alarm.identifier / alarm.alarmName
- returnPlan：alarm 的 8 个返回字段
- functionPlan：可选函数候选和参数来源
- failurePolicy：空结果有效，不自动扩大范围
```

## 4. S3 OAC 查询

输入模板：

```text
查数据
本体ID：<本体ID>
操作类型：来自 S2.plannedTasks
查询对象：来自 S2.plannedTasks.objectPlan
关系路径：来自 S2.plannedTasks.relationPathPlan
过滤条件：ne.name = <网元名称>；如用户指定告警实例，则 alarm.identifier = <identifier>
返回要求：返回 alarm 的 8 个必返字段；message_type=alarm
期望输出：只返回对象结构 {objects, relationships}
```

输出模板：

```json
{
  "objects": [],
  "relationships": []
}
```

失败策略：

- 空结果表示未发现匹配告警。
- 禁止空结果后自动扩大查询范围。
- 禁止遗漏 alarm 的必返字段。

## 5. S4/S5 函数候选与函数结果

默认策略：没有可信函数候选时不走 S4/S5。

函数候选使用规则：

- 只使用 S1 子图返回的函数候选。
- 函数输入必须来自用户问题、业务领域知识或上游步骤结果。
- 函数输出必须能映射到告警对象字段或 S6 汇总结构。
- 函数候选缺失或输入不完整时，使用 S3 OAC 查询路径。

## 6. S6 汇总

输入模板：

```text
汇总网元告警查询结果
业务意图：<业务意图>
业务领域知识：告警字段含义、空结果解释、展示要求
上游结果：S3.oacResult 或 S5.functionOutput
```

输出模板：

```text
finalAnswer：
- queryTarget：查询网元
- alarmStatus：FOUND | NOT_FOUND | MISSING_INFO | FAILED
- alarmCount：告警数量
- alarms：告警对象摘要
- missingItems：缺失项
- nextAction：是否需要补充信息
```

汇总规则：

- 非空结果表示发现告警。
- 空结果表示未发现匹配告警。
- 必须说明使用的是 OAC 查询还是函数候选。
- 不重新执行上游步骤。

## 7. 禁止项

- 禁止查询 `AbnormalStatus` 替代 `alarm`。
- 禁止先查网元 ID 再查告警，除非 OAG 子图事实证明必须这样做。
- 禁止把 `alarmName` 当作告警唯一标识。
- 禁止遗漏 alarm 的 8 个返回字段。
- 禁止编造 OAG 未返回的关系或函数。
