# 本体 Agent Skill 设计模式说明

## 1. 设计背景

本体 Skill 体系采用三层结构：

```text
scenario-skill
  -> Ontology-based-planning-skill
    -> Ontology-platform-unified-skill
      -> OAG 本体子图 / OAC 本体访问 / Function 函数能力
```

设计目标是将业务语义、默认本体规划和平台能力解耦：

- 业务场景优先用自然语言注入业务知识、规则、SOP、禁止项和返回要求。
- 规划层负责把用户问题和业务定制说明整理成执行上下文，并驱动默认本体子图规划流程。
- 平台层封装 OAG、OAC、Function 三类能力，对上层暴露稳定的自然语言委托入口。
- OQL 生成和校验由 operation 手册、schema、validator、executor 共同约束。

本文按照 Agent Skill 五种设计模式说明当前本体 Skill 的设计思想：

1. Tool Wrapper，工具封装。
2. Generator，生成器。
3. Reviewer，审查器。
4. Inversion，控制反转。
5. Pipeline，流水线。

---

## 2. Tool Wrapper：Ontology-platform-unified-skill

`Ontology-platform-unified-skill` 是本体平台能力包装器，对上层隐藏 OAG、OAC、Function 的接口差异。

| 能力 | 职责 | 入口 |
|---|---|---|
| OAG 本体子图 | 基于自然语言检索对象、属性、关系、函数候选 | `references/ontology-subgraph-search.md` |
| OAC 本体访问 | 基于子图依据生成、校验、执行 OQL | `references/oac-data-access.md` |
| Function 函数能力 | 基于函数候选获取规格、组装参数、调用函数 | `references/call-function.md` |

平台层不做跨阶段业务规划，只做能力路由和平台协议封装。上层只需要使用稳定语义入口：

```text
先找相关子图
查数据
调用函数
对象有什么字段
```

价值：降低业务 Skill 对平台接口的耦合，避免业务 Skill 直接拼接底层请求，并支持后续替换平台 API 而不影响上层。

---

## 3. OAG / OAC / Function 职责边界

### 3.1 OAG：找本体结构依据

OAG 输入是自然语言问题和 `ontologyId`，输出本体子图结果及规划可用摘要。

OAG 负责：

- 检索对象、属性、关系、函数候选。
- 保留原始子图结果。
- 摘要化输出对象、字段归属、关系来源、函数候选。
- 为 OAC 和 Function 提供可信依据。

OAG 不负责：

- 不生成 OQL。
- 不执行数据查询。
- 不直接调用函数。
- 不把子图结果说成完整事实库。

### 3.2 OAC：生成和校验本体查询

OAC 输入是自然语言数据访问需求、`schemaRef` 和 OAG 子图依据，输出 OQL、校验结果以及可选执行结果。

OAC 负责：

- 判断 `QUERY / ASSOCIATION_QUERY / AGGREGATE`。
- 读取唯一 operation 手册和对应 schema。
- 生成 OQL JSON。
- 运行 validator 校验。
- 用户明确要求执行时调用 executor。

OAC 不负责：

- 不检索本体子图。
- 不编造对象、字段、关系。
- 不调用 Function。
- 不把未执行的 OQL 当成数据结果。

### 3.3 Function：调用本体函数

Function 输入是自然语言函数调用目标、`ontologyId`、`functionId` 和上下文参数，输出函数选择、参数规格、参数组装和调用结果。

Function 负责：

- 从 OAG 的 `result.functions` 或上层可信输入确认函数。
- 获取函数参数规格。
- 组装 `args`。
- 调用函数并保留真实结果或错误。

Function 不负责：

- 不检索本体子图。
- 不生成 OQL。
- 不编造参数、默认值或成功结果。
- 不把函数调用和数据访问混在一个步骤里。

---

## 4. 面向自然语言的模块输入模板与输出格式

### 4.1 OAG 本体子图检索

#### 自然语言输入模板

```text
请执行本体子图检索。

本体ID：<ontologyId>
用户原始问题：<用户输入原文>
业务场景：<可选，例如 alarm-propagation / berth-plan-ontology>
检索目标：<希望找到哪些对象、属性、关系、函数候选>
业务知识补充：<可选，来自业务 Skill 的规则、SOP、禁止项、固定模板>
检索范围提示：<可选，例如优先关注告警、网元、链路、业务影响对象>
函数返回要求：<可选，是否需要返回 functions>
```

#### 输出格式

```text
## OAG 输出

### 1. 检索摘要
- 命中的业务主题：...
- 相关对象：...
- 相关属性：...
- 相关关系：...
- 相关函数候选：...

### 2. 原始子图结果
- 保留脚本返回的 result，包括 objects / properties / relationships / functions 等原始结构。

### 3. 规划可用依据
- 可用于 OAC 的对象类型：...
- 可用于 OAC 的字段及归属对象：...
- 可用于 ASSOCIATION_QUERY 的关系名：...
- 可用于 Function 调用的 functionId / ontologyId：...

### 4. 下一步建议
- 是否需要 OAC：是/否，原因：...
- 是否需要 Function：是/否，原因：...
- 缺失信息：...
```

### 4.2 OAC 本体数据访问

#### 自然语言输入模板

```text
请执行本体数据访问。

schemaRef：<schemaRef>
用户原始问题：<用户输入原文>
业务场景：<可选>
查询目标：<自然语言描述要查什么数据>
本体子图依据：<来自 OAG 的对象、字段、关系、函数候选摘要>
候选操作类型：<明细查询 / 关系路径查询 / 聚合统计；不确定时说明判断依据>
查询对象：<对象类型、别名建议、业务含义>
关系路径：<仅关系查询需要，说明 from / relation / to / 方向 / 步数>
过滤条件：<字段、操作符、取值，字段归属对象必须清楚>
返回要求：<返回字段、聚合指标、排序、maxResults>
执行要求：<只生成 OQL / 校验 OQL / 用户确认后执行>
```

#### 输出格式

```text
## OAC 输出

### 1. 操作类型判断
- operation：QUERY / ASSOCIATION_QUERY / AGGREGATE
- 判断依据：...

### 2. OQL JSON
- 生成符合 schema 的 OQL JSON。

### 3. 校验结果
- 是否通过 validate_oql.py：是/否
- 失败原因：...
- 修复动作：...

### 4. 执行状态
- 是否执行：未执行 / 已执行
- 执行前提：用户已明确要求执行

### 5. 执行结果或缺失项
- 数据结果：...
- 缺失字段/关系/schemaRef：...
- 风险说明：...
```

### 4.3 Function 函数调用

#### 自然语言输入模板

```text
请执行本体函数调用。

业务目标：<为什么要调用函数，要解决什么问题>
用户原始问题：<用户输入原文>
业务场景：<可选>
函数来源：<来自 OAG 子图 result.functions，或上层业务 Skill 明确给出的函数候选>
ontologyId：<函数所属本体ID>
functionId：<函数ID；如果未知，先返回缺失项>
函数选择依据：<为什么选择这个函数，基于 description/name/业务规则>
上下文参数：<用户问题、数据查询结果、业务变量中可用于组装函数参数的信息>
参数缺失策略：<缺少必填参数时返回缺失项，不编造>
输出要求：<希望输出函数原始结果、摘要、错误信息或缺失项>
```

#### 输出格式

```text
## Function 输出

### 1. 函数选择
- functionId：...
- ontologyId：...
- functionName：...
- 选择依据：...

### 2. 参数规格
- 是否已获取参数规格：是/否
- physicalName：...
- required 参数：...
- optional 参数：...

### 3. 参数组装
- args：...
- 参数来源：用户问题 / OAC 结果 / 业务变量 / 默认值
- 缺失参数：...

### 4. 调用状态
- 是否调用：是/否
- 失败原因：...

### 5. 函数结果
- 原始结果：...
- 结果摘要：...
- 错误信息：...
```

---

## 5. Generator：OAC 操作手册与 Schema

OAC 子模块承担 Generator 模式，将用户目标、业务变量和本体子图结果生成 OQL JSON。

| 操作 | 文档 | Schema |
|---|---|---|
| `QUERY` | `references/oac-query.md` | `schemas/oql-query.schema.json` |
| `ASSOCIATION_QUERY` | `references/oac-association-query.md` | `schemas/oql-association-query.schema.json` |
| `AGGREGATE` | `references/oac-aggregate.md` | `schemas/oql-aggregate.schema.json` |

每个 operation 手册都是自包含生成器：包含适用场景、不适用场景、业务生成规则和最小 OQL 示例；字段级语法以对应 schema 为准，不再额外读取公共规则文件或 examples 目录。

生成链路：

```text
用户问题 / 上层自然语言定制说明 / OAG 子图结果
  -> 判断 operation
  -> 读取唯一 operation 手册
  -> 读取对应 schema
  -> 生成 OQL JSON
```

价值：按操作类型渐进式披露，减少 Agent 上下文开销，避免 QUERY、ASSOCIATION_QUERY、AGGREGATE 规则混用。

---

## 6. Reviewer：OQL Validator 与执行前校验

OAC 子模块同时承担 Reviewer 模式。所有 OQL 在执行前必须通过统一校验。

```text
OQL JSON
  -> scripts/oql_validator.py
  -> scripts/validate_oql.py
  -> scripts/execute_oac_operation.py
```

`oql_validator.py` 是唯一 OQL 校验核心，负责：

- 根据 `operation` 选择 schema。
- 执行 JSON Schema 结构校验。
- 校验 alias 引用。
- 校验 relationship `from/to` 引用。
- 校验 `aggregateFilter.metricAlias` 引用。
- 校验特殊返回项、聚合项和排序项等跨字段语义。
- 校验 `maxResults` 使用数字格式。

执行链路：

```text
生成 OQL
  -> validate_oql.py 校验
  -> 失败则修复
  -> 用户确认执行
  -> execute_oac_operation.py 再次校验
  -> 调用 OAC 服务
```

价值：避免 schema、文档、执行脚本规则漂移，禁止未校验 OQL 直接执行。

---

## 7. Pipeline：Ontology-based-planning-skill

`Ontology-based-planning-skill` 是默认本体子图规划层，采用 Pipeline 模式。它自带默认执行流程，而不是完全依赖上层业务 Skill 传入 steps。

| 阶段 | 动作 | 说明 |
|---|---|---|
| S1 | 输入整理与规划上下文构造 | 保留原始自然语言问题和业务自然语言定制说明，整理目标、约束、`ontologyId`、`schemaRef` 和后续能力需求。 |
| S2 | 检索本体子图 | OAG 入参保持自然语言，优先使用用户原始问题或业务 Skill 注入的问题。 |
| S3 | 解析子图能力 | 确认字段归属、关系来源、函数候选。 |
| S4 | 生成数据访问步骤 | 基于子图结果生成本体访问查询步骤。 |
| S5 | 发现平台函数 | 根据子图 `functions` 或业务目标选择候选函数。 |
| S6 | 调用平台函数 | 在参数明确后调用函数能力。 |
| S7 | 汇总结论 | 汇总子图依据、数据结果、函数结果和缺失项。 |

### S1 的定位

S1 不是业务语义理解，也不是 OAG 入参重写器。OAG 子图检索入参本身就是自然语言，因此 S1 只做轻量的输入整理与规划上下文构造：

- 保留 `originalQuestion`，作为本体子图检索优先输入。
- 保留上层业务 Skill 的自然语言定制说明，不能因为未拆成 JSON 字段而丢失规则。
- 从自然语言定制说明中整理业务目标、知识来源、硬约束、禁止项、返回要求、OAG 检索提示、OAC 查询提示、Function 调用提示和失败策略。
- 判断后续是否需要本体子图、本体访问、函数发现或函数调用。
- 识别缺失项。

S1 不得提前确定对象类型、字段名、关系名或函数参数；这些必须来自本体子图返回结果或上层明确输入。

### Pipeline 检查点

- 没有 `ontologyId` 时，不调用本体子图。
- 没有 `schemaRef` 时，不执行本体访问。
- 字段必须通过 `has_property` 确认归属。
- 关系必须来自 `defines_relation.properties.name`。
- `functions` 为空时不得编造函数。
- 上一步结果为空时，不重复查询同一方向。

价值：提供可复用默认流程，避免每个业务 Skill 重写同一套规划逻辑，并通过本体子图约束对象、字段、关系和函数来源。

---

## 8. Inversion：Scenario Skill 与业务定制

`scenario-skill` 采用 Inversion 模式。业务 Skill 不直接调用平台能力，而是向规划层注入业务上下文。

业务 Skill 负责：

- 意图理解。
- 读取业务 knowledge。
- 用自然语言保留规则、SOP、禁止项、返回要求和失败策略。
- 抽取必要实体和值。
- 在确有必要时提供可选结构化字段。

业务 Skill 不负责：

- 直接生成 OQL。
- 直接解析本体子图结构。
- 直接调用 OAC、OAG 或 Function。
- 为适配 Planning 层强行构造复杂 JSON。

上层业务 Skill 推荐传入一段自然语言定制说明：

```text
场景：<业务场景名称>
用户原始问题：<用户输入原文>
本体子图检索本体ID：<ontologyId，如已知>
本体访问schemaRef：<schemaRef，如已知>
业务意图：<当前业务 Skill 识别出的唯一主意图>
已读取知识：<knowledge 文件路径或知识名称>
业务知识与规则：<完整保留 knowledge 中的规则、SOP、禁止项、返回要求、空结果策略>
执行定制要求：<说明希望如何改写默认 S2/S4/S5/S6/S7>
```

结构化字段可以作为可选增强，但不是强制接口：

```text
intent / knowledge / entities / variables / constraints / stepOverrides / stepAppends / stepSkips / failurePolicy
```

规划层按优先级合并：

```text
用户显式输入
  > 业务自然语言定制说明
  > 业务结构化字段
  > 默认本体子图规划流程
```

价值：业务控制内容，平台控制流程；场景知识可插拔；默认流程可继承、覆盖、追加、跳过。

---

## 9. 三种运行模式

### 9.1 默认规划模式

上层只提供业务目标、自然语言问题和必要上下文，规划层自动生成默认步骤。

```text
User
  -> scenario-skill
  -> Ontology-based-planning-skill 默认流程
  -> Ontology-platform-unified-skill
```

### 9.2 业务定制模式

上层提供自然语言业务定制说明，结构化字段只是可选增强。

```text
User
  -> scenario-skill 注入自然语言定制说明
  -> planning 默认流程 + 定制合并
  -> platform 执行 OAG / OAC / Function
```

以 `alarm-propagation` 为例，上层可以传：

```text
场景：alarm-propagation
用户原始问题：验证告警A向下游方向的传播证据。
本体子图检索本体ID：network@1.0
本体访问schemaRef：network@1.0
业务意图：传播证据验证
已读取知识：knowledge/evidence.md
业务知识与规则：方向由用户问题决定；每个方向必须独立调用一次 OAG；禁止合并多个方向；多方向必须串行；禁止把 Function、Port、Link 当作传播证据对象；空结果是正常结果，不自动换方向或放宽条件重试。
执行定制要求：改写 S2 的子图检索问题，按 evidence.md 的方向模板检索；S4 只查询证据对象和返回字段；S7 汇总每个方向的证据和空结果原因。
```

### 9.3 显式步骤执行模式

上层已经给出完整 steps，规划层只做检查、绑定、执行和汇总。不要为了适配而强行构造 steps。

```text
User
  -> scenario-skill 生成 steps
  -> planning 检查并执行 steps
  -> platform 执行每个步骤
```

---

## 10. 模式映射总表

| 层级 | Skill | 主模式 | 辅助模式 | 说明 |
|---|---|---|---|---|
| 业务层 | `scenario-skill/*` | Inversion | Pipeline Extension | 优先注入自然语言业务定制说明，可选注入结构化字段。 |
| 规划层 | `Ontology-based-planning-skill` | Pipeline | Inversion | 提供默认本体子图规划流程，并接受自然语言业务定制。 |
| 平台层 | `Ontology-platform-unified-skill` | Tool Wrapper | Generator / Reviewer | 封装 OAG、OAC、Function 能力。 |
| OAG 子模块 | `ontology-subgraph-search` | Tool Wrapper | Retriever | 检索本体结构依据。 |
| OAC 子模块 | `oac-query / association / aggregate` | Generator | Reviewer | 生成 OQL 并用 schema/validator 校验。 |
| Function 子模块 | `call-function` | Tool Wrapper | Parameter Binder | 获取规格、组装参数、调用函数。 |
| 脚本层 | `oql_validator.py` | Reviewer | - | 统一执行前校验。 |

---

## 11. 设计原则

### 11.1 分层解耦

```text
业务知识不进入平台层。
平台协议不进入业务层。
默认规划不绑定具体行业。
```

### 11.2 自然语言优先

业务定制 Skill 可以直接传自然语言规则和知识片段；Planning 层负责整理，不要求上层业务 Skill 构造复杂 JSON。

### 11.3 渐进式披露

Agent 只读取当前任务所需文件：

```text
scenario-skill
  -> planning SKILL.md
  -> platform SKILL.md
  -> OAG / OAC / Function 唯一模块手册
  -> 必要 schema
```

### 11.4 契约优先

- 子图结构约束对象、属性、关系来源。
- Schema 约束 OQL JSON 结构。
- Validator 约束跨字段语义。
- Executor 执行前再次校验。

### 11.5 业务可定制

```text
默认流程 + 自然语言业务知识 + 可选结构化字段 + 局部步骤改写
```

### 11.6 不臆造

Agent 不得编造对象类型、属性字段、关系名、函数名、函数参数或查询条件。所有内容必须来自用户输入、业务 Skill 注入或本体子图结果。

---

## 12. 后续演进建议

1. 为自然语言业务定制说明增加更多行业样例。
2. 为 planning 层增加可机器校验的 plan schema，但保持对自然语言输入的兼容。
3. 为 OAC 增加更多 invalid 回归样例。
4. 将本体子图解析规则抽象为单独的 validator。
5. 将该体系沉淀为 Graph-guided Planning Pattern，用于描述本体子图驱动的 Agent 规划方法。
