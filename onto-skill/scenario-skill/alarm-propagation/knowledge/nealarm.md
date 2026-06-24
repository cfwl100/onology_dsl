# 网元告警查询知识

本文档用于业务定制开发人员维护“查询网元告警”场景的 Planning 输入内容。外层 `alarm-propagation/SKILL.md` 读取本文件时，应保留下列原始业务规则，并组装为 6 行输入后传递给 `Ontology-based-planning-skill`。

---

## 本体ID

**填写值：**

```text
network@1.0
```

**填写说明：**固定填写公共本体 ID。

---

## 业务意图

**填写模板：**

```text
查询网元 ${neName} 上的当前活动告警，并返回告警对象结构。
```

**变量说明：**

- `${neName}`：用户指定的网元名称。
- 如果用户指定告警类型，可补充 `${alarmNames}`。
- 如果用户指定告警实例，可补充 `${identifier}`。

---

## 业务领域知识

### 场景知识

网元告警查询用于回答“某个网元当前有哪些活动告警”或“某个网元是否存在指定告警”。本场景查询告警对象，不查询异常事件对象。

### 业务规则

- 告警和异常事件不同，查询告警时不要查询 `AbnormalStatus`。
- `alarm.alarmName` 表示告警类型，不是单条告警唯一标识。
- 查询特定某条或某几条告警时，应优先使用 `alarm.identifier` 过滤。
- 查询某网元告警时，直接使用 `ne.name` 作为过滤条件，不需要先查询网元 ID。
- 未指定告警类型时，查询该网元下的当前活动告警。
- 如果用户指定告警类型，使用 `alarm.alarmName IN ${alarmNames}` 作为告警类型过滤。
- 如果用户指定告警实例，使用 `alarm.identifier = ${identifier}` 作为唯一实例过滤。

### 网元层级知识

| 层级 | 含义 | ne_layer |
|---|---|---|
| CN | 核心路由 Core Network | 30 |
| AN | 汇聚路由 Aggregation Network | 20 |
| EN | 接入路由 Edge Network | 10 |

### 子图检索规则

- 检索网元对象、告警对象以及二者之间的关联关系。
- 必须通过本体子图确认 `ne` 到 `alarm` 的关系路径。
- 子图输出中应保留 `ne`、`alarm`、字段归属、关系路径、函数候选和缺失项。
- 子图中没有 `alarm` 对象或告警字段时，应输出缺失信息，不得编造对象或字段。
- 关系名称以子图返回为准，不在本文件中固定关系名。

### 任务规划规则

- 没有可信函数候选时，默认规划 OAC 查询。
- OAC 查询过滤条件使用 `ne.name = ${neName}`。
- 用户明确要求指定告警实例时，使用 `alarm.identifier` 过滤。
- `alarmName` 仅用于告警类型过滤，不用于唯一实例定位。
- 规划结果必须明确对象计划、关系路径计划、过滤计划、返回字段计划和空结果策略。

### 查询规则

- 默认查询当前活动告警。
- 查询对象围绕 `ne` 和 `alarm` 组织。
- 过滤条件至少包含网元名称。
- 可选过滤条件包括告警类型列表和告警唯一标识。
- 期望输出只返回业务对象结构 `{objects, relationships}`。

### 返回要求

告警返回字段必须全部来自 `alarm` 对象，默认保留：

```text
ownerVid, severity, alarmName, identifier, firstOccurrence, lastOccurrence, clearTime, node
```

### Function 规则

- 默认不启用 Function。
- 如果子图中存在可信告警查询函数候选，可在流程级定制中启用 S4/S5。
- 函数候选只能来自本体子图返回。
- 函数输入必须来自用户问题、业务领域知识或上游步骤结果。
- 函数输出必须能映射到告警对象字段或 S6 汇总结构。
- 函数候选缺失或输入不完整时，使用 S3 OAC 查询路径。

### 返回要求和失败策略

- 非空结果表示发现匹配告警。
- 空结果表示该网元当前未发现匹配告警，不自动扩大查询范围。
- 缺少网元名称时，填写缺失信息，不得猜测补齐。
- 禁止查询 `AbnormalStatus` 替代 `alarm`。
- 禁止先查网元 ID 再查告警，除非子图事实证明必须这样做。
- 禁止把 `alarmName` 当作告警唯一标识。
- 禁止遗漏 alarm 的必返字段。
- 禁止编造子图未返回的关系或函数。

---

## 流程级定制

**默认填写：**

```text
使用默认流程 S1 -> S2 -> S3 -> S6。
```

**可选覆盖：**

```text
如果业务领域知识明确要求使用可信告警查询函数，且子图返回函数候选，可使用流程 S1 -> S2 -> S4 -> S5 -> S6。
```

---

## 步骤级定制

**默认填写：**

```text
S1：检索网元、告警及二者关系子图，保留字段归属、关系路径和函数候选；S2：规划网元到告警的查询任务，直接使用 ne.name 过滤，alarmName 只用于类型过滤，identifier 用于唯一实例过滤；S3：返回 alarm 的 ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、clearTime、node 字段以及对象结构；S6：汇总网元告警查询结果，说明空结果表示未发现匹配告警。
```

---

## 缺失信息

**默认填写：**

```text
无
```

**填写规则：**

- 缺少网元名称时填写：`缺少网元名称`。
- 缺少告警实例标识但用户要求查询特定实例时填写：`缺少告警唯一标识 identifier`。
- 子图缺少告警对象、字段或关系时，按实际缺失项填写。

---

## 可注入 6 行片段

外层 `SKILL.md` 可以复制本片段，但组装 `业务领域知识` 时必须保留上方关于告警/异常事件区别、`alarmName` 与 `identifier`、`ne.name` 过滤、返回字段和失败策略的细粒度规则。

```text
本体ID：network@1.0
业务意图：查询网元 ${neName} 上的当前活动告警，并返回告警对象结构。
业务领域知识：网元告警查询用于查询指定网元当前活动告警；查询告警对象 alarm，不查询 AbnormalStatus；ne.name 直接作为网元过滤条件，不需要先查网元 ID；alarmName 表示告警类型，不是唯一标识，identifier 表示告警唯一标识；指定告警类型时使用 alarmName 过滤，指定告警实例时使用 identifier 过滤；默认返回 alarm 字段 ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、clearTime、node；空结果表示当前未发现匹配告警，不自动扩大查询范围；默认不启用 Function，只有子图返回可信函数候选且业务明确要求时才追加 S4/S5。
流程级定制：使用默认流程 S1 -> S2 -> S3 -> S6。
步骤级定制：S1：检索网元、告警及二者关系子图，保留字段归属、关系路径和函数候选；S2：规划网元到告警的查询任务，直接使用 ne.name 过滤，alarmName 只用于类型过滤，identifier 用于唯一实例过滤；S3：返回 alarm 的 ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、clearTime、node 字段以及对象结构；S6：汇总网元告警查询结果，说明空结果表示未发现匹配告警。
缺失信息：无
```
