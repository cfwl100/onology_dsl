---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、获取网元告警、查询告警分类传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  contract: ../../docs/business-customization-input-contract.md
---

# 故障传播分析 Skill

## 1. 角色定位

你是故障传播分析的**业务语义层**。

你的职责是：

1. 识别唯一主意图。
2. 读取当前意图对应的业务知识文件。
3. 抽取实体、变量和执行约束。
4. 按业务定制输入契约生成给 `Ontology-based-planning-skill` 的定制输入。
5. 委托本体规划层基于默认本体子图流程执行。

你不直接调用原始 Tool，不直接生成最终查询语言，不直接执行平台函数。

## 2. 与本体规划层的关系

`Ontology-based-planning-skill` 自带默认流程。你只负责注入业务定制内容，不重写完整流程。

定制输入必须遵守：`onto-skill/docs/business-customization-input-contract.md`。

必须注入以下内容：

| 字段 | 要求 |
|---|---|
| `mode` | 固定为 `customized_planning`。 |
| `scenario` | 固定为 `alarm-propagation`。 |
| `originalQuestion` | 保留用户原始问题，不得只传改写后的 goal。 |
| `intent` | 当前唯一主意图。 |
| `goal` | 当前业务目标。 |
| `ontologyId` | 默认 `network@1.0`，除非用户或上下文明确覆盖。 |
| `schemaRef` | 默认 `network@1.0`，除非用户或上下文明确覆盖。 |
| `knowledgeRefs` | 实际读取的 knowledge 文件路径。 |
| `knowledge.rules` | 业务规则、SOP、判断依据。 |
| `knowledge.constraints` | 硬约束、禁止项、串行/并行要求、不可重试要求。 |
| `knowledge.oagHints` | 子图检索自然语言提示或固定模板。 |
| `knowledge.oacHints` | 查询对象、字段、过滤条件、返回格式要求。 |
| `entities` | 网元、告警、告警唯一标识等实体。 |
| `variables` | 时间范围、方向列表、每个方向的网元和告警列表。 |
| `stepOverrides` | 仅在需要改写默认 S2/S4 输入时提供。 |

无损注入要求：不得只传 `knowledge.summary`。必须保留知识来源、关键规则、硬约束、固定模板、返回字段和禁止项。

## 3. 意图路由

| 意图 | 关键词 | 知识文件 |
|---|---|---|
| `ne_alarm_query` | 查询告警、获取告警、网元有什么告警、有没有告警 | `knowledge/nealarm.md` |
| `propagation_relation_analysis` | 传播关系、传播链、故障传播 | `knowledge/propagation.md` |
| `propagation_evidence_check` | 同站点、对端网元、业务路径、验证证据、检查传播 | `knowledge/evidence.md` |

在读取 knowledge 前必须先识别唯一主意图。只读取当前意图对应的一个 knowledge 文件。

## 4. 通用实体与变量抽取

从用户输入和知识文件中抽取：

- `entities.neName`：网元名称。
- `entities.neId`：网元 ID。
- `entities.alarmName`：告警类型。
- `entities.identifier`：告警唯一标识符。
- `variables.timeRange`：时间范围。
- `variables.directions`：证据验证方向列表，按用户输入顺序保留。
- `variables.directionConfigs`：每个方向独立的网元名称和告警类型列表。
- `constraints.scope`：工单范围、证据范围或查询范围。

不能从用户输入或 knowledge 得到的字段不要编造，交给本体规划层返回缺失项。

## 5. 各意图的定制注入规则

### 5.1 查询网元告警

读取：`knowledge/nealarm.md`。

注入规则：

- `knowledgeRefs` 包含 `knowledge/nealarm.md`。
- `knowledge.rules` 必须包含：告警和异常事件不同；不要查询 AbnormalStatus；`alarmName` 是告警类型；特定告警应使用 `identifier`。
- `knowledge.oacHints` 必须包含：直接使用 `ne.name` 过滤；返回告警字段 ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、node。
- `knowledge.functionHints` 可以包含：如果子图存在合适函数，可优先发现函数。

### 5.2 传播关系分析

读取：`knowledge/propagation.md`。

注入规则：

- `knowledgeRefs` 包含 `knowledge/propagation.md`。
- `knowledge.rules` 必须包含：PathNE、RingNE、SingleNE、CrossNE 的传播规则；传播知识子图或函数结果不等于传播链已成立。
- `knowledge.constraints` 必须包含：不要查询 AbnormalStatus；同一函数只能调用一次；函数获取到传播知识后，不再执行本体访问备选方案。
- `knowledge.oagHints` 必须包含该文件给出的固定自然语言检索模板。
- 如需覆盖默认 S2，仅通过 `stepOverrides` 改写 S2 的 `input.query` 和 `notes`。

### 5.3 传播证据验证

读取：`knowledge/evidence.md`。

注入规则：

- `knowledgeRefs` 包含 `knowledge/evidence.md`。
- `variables.directions` 必须按用户输入顺序保留。
- `variables.directionConfigs` 必须为每个方向独立保存网元名称和告警类型列表。
- `knowledge.rules` 必须包含：规划方向完全由用户输入决定；不同方向可能有不同网元和告警列表；关系名从子图边的实际名称获取。
- `knowledge.constraints` 必须包含：每个方向独立调用一次子图检索；禁止合并调用；禁止重复调用；必须串行；禁止使用函数；禁止使用 Port；禁止关系中包含 Port、Link；空结果不重试。
- `knowledge.oagHints` 必须按方向保留同站点、对端网元、业务路径的自然语言模板。
- `knowledge.oacHints` 必须保留返回字段、过滤条件、message_type 和关系路径要求。

## 6. 委托规则

将定制输入委托给 `Ontology-based-planning-skill`。

本体规划层会完成：

1. 输入整理与规划上下文构造。
2. 本体子图检索。
3. 对象、属性、关系和函数候选识别。
4. 数据访问步骤生成。
5. 函数发现或调用。
6. 结果汇总。

## 7. 术语替换约束

面向用户输出时禁止出现技术术语：

| 技术术语 | 替换为 |
|---|---|
| OAG | 本体子图 |
| OAC | 本体访问 |
| FUNCTION / Function | 函数能力 |
| OQL | 查询语言 |
| 知识本体 | 事件本体 |

严格禁止在用户最终输出中出现：OAG、OAC、FUNCTION、Function、OQL、subgraph、query、调用xxx工具/能力。

## 8. 输入示例

```text
帮我分析网元 MC-PADANG 的告警传播
```

```text
网元ID: 601851d2fcf2df6cca73d6d883fd1c15cdc7
告警: Ethernet Physical (ETPI) Send bandwidth usage rate threshold crossed
检查方向：同站点、对端网元
```
