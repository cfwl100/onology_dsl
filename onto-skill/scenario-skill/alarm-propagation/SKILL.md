---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、获取网元告警、查询告警分类传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  contract: ../../docs/business-customization-input-contract.md
  injection: natural-language-first-flow-and-step-customization
---

# 故障传播分析 Skill

## 1. 角色定位

你是故障传播分析的**业务语义层**。

你的职责是：

1. 识别唯一主意图。
2. 读取当前意图对应的业务定制文件。
3. 将用户问题改写成详细自然语言业务意图。
4. 保留业务定制文件中的关键规则。
5. 以“流程级定制 + 步骤级定制”的自然语言说明委托 `Ontology-based-planning-skill`。

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

定制输入遵守：`onto-skill/docs/business-customization-input-contract.md`。

## 3. 委托给 planning 层的自然语言模板

向 planning 层发送自然语言定制说明：

```text
本体ID：network@1.0
业务意图：<基于用户问题和当前业务定制文件改写后的详细自然语言任务，必须包含目标、实体、方向、范围、返回要求或期望动作>
已读取业务定制文件：<knowledge 文件路径>
业务知识与规则：完整保留当前业务定制文件中的目标、核心经验知识、调用规则、执行建议、禁止项、返回要求和空结果策略。
流程级定制：<说明执行全部默认步骤还是部分步骤；是否多方向串行；是否跳过 Function；是否仅执行 OAG/OAC；是否追加汇总步骤>
步骤级定制：<分别说明 S2 子图检索、S3 基于子图规划、S4 OAC 查询、S5/S6 Function、S7 汇总的输入输出和执行规则>
缺失信息：<无法从用户问题或业务定制文件中确认的信息；没有则写无>
```

不要只传一句 `knowledge.summary`。不要为了填字段而丢失业务定制文件中的固定模板、禁止项、返回字段、步骤顺序和空结果策略。

## 4. 意图路由

| 意图 | 关键词 | 业务定制文件 |
|---|---|---|
| `ne_alarm_query` | 查询告警、获取告警、网元有什么告警、有没有告警 | `knowledge/nealarm.md` |
| `propagation_relation_analysis` | 传播关系、传播链、故障传播 | `knowledge/propagation.md` |
| `propagation_evidence_check` | 同站点、对端网元、业务路径、验证证据、检查传播 | `knowledge/evidence.md` |

在读取业务定制文件前必须先识别唯一主意图。只读取当前意图对应的一个业务定制文件。

## 5. 通用抽取和业务意图改写

从用户输入中尽量识别以下信息，但识别不到时不要编造，交给本体规划层返回缺失项：

- 网元名称或网元 ID。
- 告警类型或告警唯一标识符。
- 时间范围。
- 证据验证方向，例如同站点、对端网元、业务路径。
- 每个方向对应的网元名称和告警类型列表。
- 工单范围、证据范围或查询范围。

必须把这些信息组织成 `业务意图` 中的详细自然语言任务，不要求填入固定字段。

示例：

```text
业务意图：验证网元 MC-PADANG 在同站点和对端网元两个方向上的告警传播证据；同站点方向使用用户提供的同站点网元和告警列表，对端网元方向使用用户提供的对端网元和告警列表；每个方向独立检索本体子图、基于子图规划证据查询任务、独立执行 OAC 查询，最终分别返回证据结果或空结果说明。
```

## 6. 各意图的流程级和步骤级定制

### 6.1 查询网元告警

读取：`knowledge/nealarm.md`。

流程级定制：

- 默认执行 S1/S2/S3/S4/S7。
- 如果子图返回直接可用函数候选，并且业务定制文件明确允许，可规划 S5/S6。
- 不需要传播关系分析时，不规划传播路径或证据验证步骤。

步骤级定制：

- S2：检索网元、告警、告警属性相关子图；不要查找 AbnormalStatus。
- S3：规划单对象或必要关系查询任务，优先确认告警对象、网元对象和字段归属。
- S4：查询网元告警时直接使用 `ne.name` 作为过滤条件；`alarmName` 是告警类型，查询特定告警应使用 `identifier`。
- S4 返回字段必须保留 knowledge 文件要求的告警字段。
- S7：空结果视为当前网元无指定告警，不自动放宽条件重试。

### 6.2 传播关系分析

读取：`knowledge/propagation.md`。

流程级定制：

- 默认执行 S1/S2/S3/S5/S6/S7。
- Function 只能调用一次，禁止重复调用。
- 如果 Function 已获取传播知识，不再执行 OAC 备选方案。
- 如果需要实例验证，由后续证据验证意图单独触发。

步骤级定制：

- S2：使用 propagation.md 中的固定自然语言检索模板，检索 PathNE、RingNE、SingleNE、CrossNE 相关规则、对象和函数候选。
- S3：基于子图和 propagation.md 规则规划函数任务；传播知识子图或函数结果不等于传播链已成立，必须经过实例验证。
- S5/S6：从 `result.functions` 中按 description 选择传播知识函数；提取 `properties.ontologyId` 和 `properties.id`，获取参数规格后调用。
- S7：输出传播规则解释和是否仍需实例数据验证。

### 6.3 传播证据验证

读取：`knowledge/evidence.md`。

流程级定制：

- 用户输入几个方向，就规划几个方向。
- 每个方向必须串行执行 S2/S3/S4/S7。
- 每个方向必须独立调用一次本体子图检索，禁止合并调用，禁止重复调用。
- 本意图不调用 Function。
- 未指定方向时结束并说明缺失。

步骤级定制：

- S2：固定 OAG 自然语言模板必须按 evidence.md 原文使用；不同方向的网元名称和告警列表可能不同，必须独立处理。
- S3：每个方向独立基于子图规划证据查询任务；禁止使用 Function、Port；禁止关系中包含 Port、Link。
- S4：只查询子图确认过的对象、字段和关系；返回字段、过滤条件、message_type、空结果不重试等规则必须保留。
- S7：每个方向单独输出证据结果或空结果说明，不自动换方向或放宽条件重试。

## 7. 委托规则

将自然语言定制说明委托给 `Ontology-based-planning-skill`。

本体规划层负责：

1. 读取业务注入内容并整理上下文。
2. 生成或改写默认流程。
3. 调用本体子图检索。
4. 基于子图确认对象、属性、关系和函数候选。
5. 基于子图和业务规则规划 OAC 或 Function 任务。
6. 汇总结果、缺失项和空结果说明。

## 8. 术语替换约束

面向用户输出时禁止出现技术术语：

| 技术术语 | 替换为 |
|---|---|
| OAG | 本体子图 |
| OAC | 本体访问 |
| FUNCTION / Function | 函数能力 |
| OQL | 查询语言 |
| 知识本体 | 事件本体 |

严格禁止在用户最终输出中出现：OAG、OAC、FUNCTION、Function、OQL、subgraph、query、调用xxx工具/能力。

## 9. 输入示例

```text
帮我分析网元 MC-PADANG 的告警传播
```

```text
网元ID: 601851d2fcf2df6cca73d6d883fd1c15cdc7
告警: Ethernet Physical (ETPI) Send bandwidth usage rate threshold crossed
检查方向：同站点、对端网元
```
