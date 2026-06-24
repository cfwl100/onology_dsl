# 验证传播证据

本文是 `alarm-propagation` 的业务领域知识文件，采用 `Ontology-based-planning-skill` 当前六步协议组织。业务 Skill 读取本文后，应将必要内容注入 Planning 顶层输入的 `业务领域知识`、`流程级定制`、`步骤级定制` 和 `缺失信息` 中。

## 0. 全局业务领域知识

### 0.1 目标

根据用户指定的传播证据检查方向，在实例层验证是否存在支持传播链的活动告警证据。

### 0.2 业务事实

- 业务路径在本体中的对象类型名称为 `businesspath`。
- 告警的 `alarmName` 表示告警类型。
- 告警的唯一标识符是 `identifier`。
- 每个方向必须独立检索子图、独立规划、独立查询、独立汇总。
- 长告警列表必须变量化保存，后续步骤只引用变量名，只有最终生成 OAC 查询参数时才允许展开完整列表。

### 0.3 证据检查方向

| directionKey | 方向名称 | 目的 |
|---|---|---|
| `same_site` | 同站点/同机房 | 找到起始网元同站点的其他网元，并查询这些网元上的活动告警。 |
| `peer_ne` | 对端网元 | 找到与起始网元通过对端链路相连的其他网元，并查询这些网元上的活动告警。 |
| `service_path` | 业务路径 | 找到与起始网元同属业务路径的其他网元，并查询这些网元上的活动告警。 |

### 0.4 方向选择规则

- 用户输入“三步[同站点、对端网元、业务路径]”时，按用户顺序规划并执行三个方向。
- 用户输入“两步[同站点、对端网元]”时，按用户顺序规划并执行两个方向。
- 用户输入“同站点/同机房”时，只执行 `same_site`。
- 用户未指定方向时，输出缺失信息 `未指定规划方向`，禁止臆测执行。

### 0.5 变量要求

```text
alarmNames_same_site = [同站点方向完整告警类型列表]
alarmNames_peer_ne = [对端网元方向完整告警类型列表]
alarmNames_service_path = [业务路径方向完整告警类型列表]
neName_same_site = <同站点方向起始网元名称>
neName_peer_ne = <对端网元方向起始网元名称>
neName_service_path = <业务路径方向起始网元名称>
returnFields_ne = [srcSpaceVid, name, className, domain, networkType]
returnFields_alarm = [node, ownerVid, severity, alarmName, identifier, firstOccurrence, lastOccurrence, clearTime]
```

## 1. 流程级定制

### 1.1 默认流程

传播证据验证默认不调用 Function，单个方向使用：

```text
S1 -> S2 -> S3 -> S6
```

多方向查询时，按用户指定方向顺序串行执行，每个方向独立执行 `S1 -> S2 -> S3 -> S6`，不得共享中间结果，除非用户明确要求复用。

### 1.2 Function 策略

本意图默认不执行 `S4/S5 Function`。只有业务领域知识明确要求 Function 补齐路径、参数或上下文时，才允许追加：

```text
S1 -> S2 -> S4 -> S5 -> S3 -> S6
```

### 1.3 空结果策略

S3 OAC 查询返回空对象结构是有效结果，不自动放宽条件、不换路径、不重试，直接进入 S6 汇总。

## 2. S1 子图检索

### 2.1 输入模板

```text
检索本体子图
本体ID：network@1.0
业务意图：验证 <directionName> 方向传播证据
业务领域知识：本文全局业务领域知识、方向规则、变量要求、禁止项
步骤级定制：使用 <directionKey> 方向子图检索规则
检索目标：从起始网元出发，查找 <directionName> 方向可达的其他网元及其告警相关对象、字段、关系和函数候选
返回结构要求：保留 result.seedNodes、nodes、edges、functions、actions；摘要必须包含对象候选、字段归属、关系候选、函数候选、缺失项和风险项
```

### 2.2 方向检索规则

| directionKey | 固定 OAG query |
|---|---|
| `same_site` | 查找网元通过站点关联到其他网元及这些网元告警的本体子图。 |
| `peer_ne` | 查找网元通过对端链路关联到其他网元及这些网元告警的本体子图。 |
| `service_path` | 查找网元通过业务路径关联到其他网元及这些网元告警的本体子图。 |

### 2.3 输出模板

```text
subgraphOutput：
- rawSubgraph：OAG 返回的原始图结构
- objectCandidates：ne、alarm、site、businesspath 等对象候选
- propertyCandidates：对象字段及归属对象
- relationCandidates：关系候选、方向、路径约束
- functionCandidates：函数候选；本意图默认不使用
- missingItems：缺失对象、字段、关系
- conflictItems：路径冲突或字段归属冲突
```

### 2.4 执行规则

- 每个方向只能调用一次 OAG。
- 禁止在一个 OAG 调用中合并多个方向。
- 禁止使用模板以外的自由 query。
- 子图为空时停止该方向后续步骤，并在 S6 输出缺失说明。

## 3. S2 基于本体子图的任务规划

### 3.1 输入模板

```text
基于本体子图规划执行任务
本体ID：network@1.0
业务意图：验证 <directionName> 方向传播证据
本体子图：<S1.subgraphOutput.rawSubgraph>
业务领域知识：本文方向规则、查询约束、输出字段、message_type 和失败策略
步骤级定制：使用 <directionKey> 方向路径规划规则
规划目标：从起点网元出发，经过 <directionName> 相关对象或关系，查找到其他网元及其告警
```

### 3.2 规划规则

- 必须基于 S1 子图事实规划，不得凭经验写死关系名。
- 关系名必须来自 `edges.properties.name` 或等价的子图返回关系事实。
- 字段必须通过子图中的属性归属确认。
- `businesspath` 是对象类型，不是关系边。
- `pathThrough` 只作为候选名称，必须以子图实际返回关系名为准。
- 禁止规划 Port、Link 查询路径。
- 每个方向必须生成一个 S3 OAC 查询任务。

### 3.3 方向路径约束

- `same_site`：查询同站点其他网元及其告警。禁止无业务依据地走 `site -> alarm` 直连路径；优先从站点关联到其他网元，再连接告警。
- `peer_ne`：查询路径必须经过其他网元再连接告警，并排除起始网元自身。
- `service_path`：查询路径必须经过 `businesspath` 和其他网元再连接告警，业务路径设备名约束使用 `businesspath.aDeviceName = ${neName_service_path}`。

### 3.4 输出模板

```text
plannedTasks：
- taskId：S3_<directionKey>_oac
- taskType：ASSOCIATION_QUERY
- operationType：ASSOCIATION_QUERY
- objectPlan：起点网元、方向中间对象、其他网元、告警
- relationPathPlan：来自 S1 子图的关系路径
- filterPlan：起点网元、告警类型、方向附加条件
- returnPlan：returnFields_ne、returnFields_alarm、objects、relationships
- functionPlan：默认无
- failurePolicy：空结果有效，不自动重试
```

### 3.5 失败策略

无法基于子图规划合法路径时，停止该方向 S3，输出缺失对象、字段、关系或路径冲突，不重新解释业务知识全文。

## 4. S3 OAC 查询

### 4.1 输入模板

```text
查数据
本体ID：network@1.0
操作类型：ASSOCIATION_QUERY
查询对象：来自 S2.plannedTasks.objectPlan
关系路径：来自 S2.plannedTasks.relationPathPlan
过滤条件：来自 S2.plannedTasks.filterPlan
返回要求：返回 returnFields_ne 和 returnFields_alarm；message_type=<messageType_<directionKey>>；空结果是有效结果
执行要求：先生成并校验查询语言；通过后执行；默认不写临时 OQL 文件
期望输出：只返回对象结构 {objects, relationships}
```

### 4.2 固定过滤条件

- 起点网元：`ne.name = ${neName_<directionKey>}`。
- 终点告警类型：`alarm.alarmName IN ${alarmNames_<directionKey>}`。
- 对端网元方向：增加 `peerNe.name != ${neName_peer_ne}`。
- 业务路径方向：增加 `businesspath.aDeviceName = ${neName_service_path}`。

### 4.3 输出字段

网元字段：

```text
srcSpaceVid, name, className, domain, networkType
```

告警字段：

```text
node, ownerVid, severity, alarmName, identifier, firstOccurrence, lastOccurrence, clearTime
```

message_type：

| directionKey | message_type |
|---|---|
| `same_site` | `same_site_active_alarms` |
| `peer_ne` | `peer_ne_active_alarms` |
| `service_path` | `service_path_active_alarms` |

### 4.4 输出模板

```json
{
  "objects": [],
  "relationships": []
}
```

### 4.5 失败策略

- 查询结果为空是有效结果。
- 禁止空结果后自动放宽条件、换路径或重试。
- 禁止输出 OQL、validation 或 operationDecision，除非 debug 模式明确要求。

## 5. S4/S5 Function 发现与执行

### 5.1 默认策略

本意图默认不执行 Function。

```text
S4：跳过，原因：流程级定制声明不执行 Function。
S5：跳过，原因：S4 无 Function 选择结果。
```

### 5.2 允许启用条件

只有业务领域知识明确要求 Function 补齐查询参数、路径上下文或其他输入，并且 S1 子图返回了可信函数候选时，才允许执行 S4/S5。

### 5.3 失败策略

Function 候选缺失或参数不完整时，只停止 Function 分支，不影响不依赖 Function 的 S3/S6。

## 6. S6 汇总

### 6.1 输入模板

```text
汇总传播证据
业务意图：<业务意图>
业务领域知识：证据判断、空结果解释、方向顺序和展示要求
步骤级定制：使用证据汇总规则
上游结果：S1 子图摘要、S2 规划摘要、S3 OAC 对象结构、可选 S5 Function 输出
```

### 6.2 汇总规则

- 每个方向输出独立证据结论。
- 如果 S3 返回非空 objects/relationships，说明存在该方向相关告警证据。
- 如果 S3 返回空对象结构且业务规则声明空结果有效，输出“未发现该方向传播证据”。
- 必须列出使用的方向、起始网元变量、告警列表变量、message_type、缺失项和执行状态。
- 不重新执行 S1/S2/S3。

### 6.3 输出模板

```text
finalAnswer：
- directionKey：方向唯一键
- directionName：方向名称
- evidenceStatus：FOUND | NOT_FOUND | MISSING_INFO | FAILED
- evidenceSummary：证据摘要或空结果说明
- objectCount：对象数量
- relationshipCount：关系数量
- usedVariables：使用的变量引用
- missingItems：缺失项
- nextAction：是否需要用户补充信息
```

## 7. 禁止项

- 禁止自动补充用户未指定方向。
- 禁止查询 Port、Link。
- 禁止合并多个方向到一个 OAG/OAC 步骤。
- 禁止同一方向重复调用 OAG 或 OAC。
- 禁止默认调用 Function。
- 禁止空结果后自动放宽条件、换路径或重试。
- 禁止在默认运行中输出完整中间查询语言，除非 debug 模式明确要求。
