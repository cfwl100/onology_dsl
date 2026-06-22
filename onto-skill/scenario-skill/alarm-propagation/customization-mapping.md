# alarm-propagation 定制输入映射说明

## 1. 目标

本文说明如何把 `alarm-propagation` 原有业务知识无损映射到 `Ontology-based-planning-skill` 的业务定制输入模式。

核心原则：

- 不只传 `knowledge.summary`。
- 保留原始知识来源 `knowledgeRefs`。
- 把规则、硬约束、固定模板、返回字段、执行顺序分别放入结构化字段。
- 只覆盖默认流程的必要步骤，不重写完整 planning 流程。

---

## 2. 通用映射

| 原始内容 | 新输入字段 |
|---|---|
| 用户原始问题 | `originalQuestion` |
| 唯一主意图 | `intent` |
| 分析目标 | `goal` |
| knowledge 文件路径 | `knowledgeRefs[]` |
| 业务事实 | `knowledge.facts[]` |
| 传播规则、判断规则、SOP | `knowledge.rules[]` |
| 禁止项、强制串行、不可重复查询 | `knowledge.constraints[]` |
| 固定本体子图检索模板 | `knowledge.oagHints[]` |
| 查询字段、过滤条件、返回格式 | `knowledge.oacHints[]` |
| 函数发现或调用建议 | `knowledge.functionHints[]` |
| 网元、告警、identifier | `entities` |
| 时间范围、方向列表、每方向配置 | `variables` |
| 局部步骤改写 | `stepOverrides` |

---

## 3. 查询网元告警映射

读取文件：`knowledge/nealarm.md`。

必须保留的信息：

| 知识内容 | 目标字段 |
|---|---|
| 告警和异常事件不同，不查 AbnormalStatus | `knowledge.rules` / `knowledge.constraints` |
| alarmName 是告警类型 | `knowledge.rules` |
| 特定告警使用 identifier | `knowledge.rules` |
| 可直接使用 ne.name 查询网元告警 | `knowledge.oacHints` |
| 返回 ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、node | `knowledge.oacHints` |
| 可优先通过 Function 查询告警 | `knowledge.functionHints` |

建议只覆盖 S4 数据访问提示，不直接生成最终查询语言。

---

## 4. 传播关系分析映射

读取文件：`knowledge/propagation.md`。

必须保留的信息：

| 知识内容 | 目标字段 |
|---|---|
| 不查 AbnormalStatus | `knowledge.constraints` |
| alarmName 是告警类型，identifier 是唯一标识 | `knowledge.rules` |
| PathNE、RingNE、SingleNE、CrossNE 传播规则 | `knowledge.rules` |
| 每个 Function 只能调用一次 | `knowledge.constraints` |
| 获取 Function 结果后，不再执行 OAC 备选方案 | `knowledge.constraints` |
| 固定本体子图检索问题 | `knowledge.oagHints` / `stepOverrides[S2].input.query` |
| 传播知识不等于传播链成立，必须实例验证 | `knowledge.rules` |

建议只覆盖 S2 子图检索输入，保留后续默认流程。

---

## 5. 传播证据验证映射

读取文件：`knowledge/evidence.md`。

必须保留的信息：

| 知识内容 | 目标字段 |
|---|---|
| 用户输入几个方向就规划几个方向 | `variables.directions` / `knowledge.rules` |
| 每个方向网元和告警列表可能不同 | `variables.directionConfigs` |
| 每个方向独立调用一次子图检索 | `knowledge.constraints` |
| 禁止合并多个方向 | `knowledge.constraints` |
| 必须按用户输入顺序串行调用 | `constraints.executionOrder` |
| 同一方向只能调用一次 | `knowledge.constraints` |
| 禁止 Function | `knowledge.constraints` |
| 禁止 Port 对象和 Port/Link 关系 | `knowledge.constraints` |
| 关系名从子图边实际名称获取 | `knowledge.rules` |
| 同站点、对端网元、业务路径固定子图检索模板 | `knowledge.oagHints` |
| 返回起始网元、途经网元和告警字段 | `knowledge.oacHints` |
| 空结果不重试 | `constraints.noRetryOnEmptyResult` |

建议根据 `variables.directions` 动态生成多个方向的子步骤或步骤追加；每个方向应保留独立上下文，不能合并为一个查询。

---

## 6. 防信息丢失检查清单

业务 Skill 生成定制输入前必须自检：

1. 是否保留了 `originalQuestion`？
2. 是否写入了 `knowledgeRefs`？
3. 是否把禁止项写入 `knowledge.constraints`？
4. 是否把固定 OAG 自然语言模板写入 `knowledge.oagHints`？
5. 是否把返回字段和过滤条件写入 `knowledge.oacHints`？
6. 是否保留了每个方向的独立配置？
7. 是否避免直接生成最终查询语言？
8. 是否只通过 `stepOverrides` 覆盖必要的默认步骤？
9. 是否把用户没有提供的字段留给 planning 层返回缺失项？

---

## 7. 示例输入模式选择

| 用户问题 | 推荐模式 |
|---|---|
| 帮我查询某网元的告警 | 业务定制模式，覆盖 S4 数据访问提示。 |
| 帮我分析某网元的故障传播 | 业务定制模式，覆盖 S2 子图检索提示，优先发现函数。 |
| 按同站点、对端网元检查传播证据 | 业务定制模式，按方向追加或覆盖多组 S2/S4 步骤。 |
| 外部系统已经给出完整步骤 | 显式步骤执行模式。 |
