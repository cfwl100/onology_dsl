# 本体 Agent Skill 设计模式说明

## 1. 设计背景

本体 Skill 体系采用三层结构：

```text
scenario-skill
  -> Ontology-based-planning-skill
    -> Ontology-platform-unified-skill
      -> 本体子图 / 本体访问 / 函数能力
```

设计目标是将业务语义、默认本体规划和平台能力解耦：

- 业务场景只注入意图、知识、变量和必要步骤改写。
- 规划层提供默认本体子图驱动的执行流程。
- 平台层封装本体子图、本体访问和函数能力。
- OQL 生成和校验由 schema、operation 手册和脚本共同约束。

本文按照 Agent Skill 五种设计模式说明当前本体 Skill 的设计思想：

1. Tool Wrapper，工具封装。
2. Generator，生成器。
3. Reviewer，审查器。
4. Inversion，控制反转。
5. Pipeline，流水线。

---

## 2. Tool Wrapper：Ontology-platform-unified-skill

`Ontology-platform-unified-skill` 是本体平台能力包装器，对上层隐藏本体子图、本体访问和函数能力的接口差异。

| 能力 | 说明 | 入口 |
|---|---|---|
| 本体子图 | 检索对象、属性、关系、函数候选 | `references/ontology-subgraph-search.md` |
| 本体访问 | 生成、校验、执行 OQL | `references/oac-data-access.md` |
| 函数能力 | 发现函数、确认参数、调用函数 | `references/call-function.md` |

平台层不做跨阶段业务规划，只做能力路由和平台协议封装。上层只需要使用稳定语义入口：

```text
先找相关子图
查数据
调用function
对象有什么字段
```

价值：降低业务 Skill 对平台接口的耦合，避免业务 Skill 直接拼接底层请求，并支持后续替换平台 API 而不影响上层。

---

## 3. Generator：OAC 操作手册与 Schema

OAC 子模块承担 Generator 模式，将用户目标、业务变量和本体子图结果生成 OQL JSON。

| 操作 | 文档 | Schema |
|---|---|---|
| `QUERY` | `references/oac-query.md` | `schemas/oql-query.schema.json` |
| `ASSOCIATION_QUERY` | `references/oac-association-query.md` | `schemas/oql-association-query.schema.json` |
| `AGGREGATE` | `references/oac-aggregate.md` | `schemas/oql-aggregate.schema.json` |

每个 operation 手册都是自包含生成器：包含适用场景、不适用场景、公共规则、专属规则和最小 OQL 示例，只读取对应 schema，不再额外读取公共规则文件或 examples 目录。

生成链路：

```text
用户问题 / 上层步骤
  -> 判断 operation
  -> 读取唯一 operation 手册
  -> 读取对应 schema
  -> 生成 OQL JSON
```

价值：按操作类型渐进式披露，减少 Agent 上下文开销，避免 QUERY、ASSOCIATION_QUERY、AGGREGATE 规则混用。

---

## 4. Reviewer：OQL Validator 与执行前校验

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
- 校验 `ID(field)` / `NAME(field)` 的合法位置。
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

## 5. Pipeline：Ontology-based-planning-skill

`Ontology-based-planning-skill` 是默认本体子图规划层，采用 Pipeline 模式。它自带默认执行流程，而不是完全依赖上层业务 Skill 传入 steps。

| 阶段 | 动作 | 说明 |
|---|---|---|
| S1 | 输入整理与规划上下文构造 | 保留原始自然语言问题，整理目标、实体、变量、约束、`ontologyId`、`schemaRef` 和后续能力需求。 |
| S2 | 检索本体子图 | OAG 入参保持自然语言，优先使用用户原始问题或业务 Skill 注入的问题。 |
| S3 | 解析子图能力 | 确认字段归属、关系来源、函数候选。 |
| S4 | 生成数据访问步骤 | 基于子图结果生成本体访问查询步骤。 |
| S5 | 发现平台函数 | 根据子图 `functions` 或业务目标选择候选函数。 |
| S6 | 调用平台函数 | 在参数明确后调用函数能力。 |
| S7 | 汇总结论 | 汇总子图依据、数据结果、函数结果和缺失项。 |

### S1 的定位

S1 不是业务语义理解，也不是 OAG 入参重写器。OAG 子图检索入参本身就是自然语言，因此 S1 只做轻量的输入整理与规划上下文构造：

- 保留 `originalQuestion`，作为本体子图检索优先输入。
- 整理 `goal`、`intent`、`entities`、`variables`、`constraints`、`ontologyId`、`schemaRef`、`steps`。
- 判断后续是否需要本体子图、本体访问、函数发现或函数调用。
- 识别缺失项。
- 合并业务 Skill 注入的知识、变量和步骤改写。

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

## 6. Inversion：Scenario Skill 与业务定制

`scenario-skill` 采用 Inversion 模式。业务 Skill 不直接调用平台能力，而是向规划层注入业务上下文。

业务 Skill 负责：

- 意图理解。
- 知识注入。
- 实体和值提取。
- 变量传递。
- 约束声明。
- 步骤覆盖、追加或跳过。

业务 Skill 不负责：

- 直接生成 OQL。
- 直接解析本体子图结构。
- 直接调用 OAC、OAG 或 Function。
- 重写默认规划流程。

上层业务 Skill 可以传入：

```text
intent
knowledge
entities
variables
constraints
stepOverrides
stepAppends
stepSkips
failurePolicy
```

规划层按优先级合并：

```text
用户显式输入
  > 业务 variables
  > 业务 knowledge
  > 业务 step overrides
  > 默认本体子图规划流程
```

价值：业务控制内容，平台控制流程；场景知识可插拔；默认流程可继承、覆盖、追加、跳过。

---

## 7. 三种运行模式

### 7.1 默认规划模式

上层只提供业务目标、自然语言问题和必要变量，规划层自动生成默认步骤。

```text
User
  -> scenario-skill
  -> Ontology-based-planning-skill 默认流程
  -> Ontology-platform-unified-skill
```

### 7.2 业务定制模式

上层提供业务知识、变量、约束和局部步骤改写。

```text
User
  -> scenario-skill 注入 knowledge / variables / overrides
  -> planning 默认流程 + 定制合并
  -> platform 执行
```

### 7.3 显式步骤执行模式

上层已经给出完整 steps，规划层只做检查、绑定、执行和汇总。

```text
User
  -> scenario-skill 生成 steps
  -> planning 检查并执行 steps
  -> platform 执行每个步骤
```

---

## 8. 模式映射总表

| 层级 | Skill | 主模式 | 辅助模式 | 说明 |
|---|---|---|---|---|
| 业务层 | `scenario-skill/*` | Inversion | Pipeline Extension | 注入业务语义、知识、变量和流程定制。 |
| 规划层 | `Ontology-based-planning-skill` | Pipeline | Inversion | 提供默认本体子图规划流程，并接受业务定制。 |
| 平台层 | `Ontology-platform-unified-skill` | Tool Wrapper | Generator / Reviewer | 封装本体子图、本体访问、函数能力。 |
| OAC 子模块 | `oac-query / association / aggregate` | Generator | Reviewer | 生成 OQL 并用 schema/validator 校验。 |
| 脚本层 | `oql_validator.py` | Reviewer | - | 统一执行前校验。 |

---

## 9. 设计原则

### 9.1 分层解耦

```text
业务知识不进入平台层。
平台协议不进入业务层。
默认规划不绑定具体行业。
```

### 9.2 渐进式披露

Agent 只读取当前任务所需文件：

```text
scenario-skill
  -> planning SKILL.md
  -> platform SKILL.md
  -> 唯一 operation 手册
  -> 对应 schema
```

### 9.3 契约优先

- 子图结构约束对象、属性、关系来源。
- Schema 约束 OQL JSON 结构。
- Validator 约束跨字段语义。
- Executor 执行前再次校验。

### 9.4 业务可定制

```text
默认流程 + 业务知识 + 变量 + 步骤改写
```

### 9.5 不臆造

Agent 不得编造对象类型、属性字段、关系名、函数名、函数参数或查询条件。所有内容必须来自用户输入、业务 Skill 注入或本体子图结果。

---

## 10. 后续演进建议

1. 为 `scenario-skill` 增加统一定制输入模板。
2. 为 planning 层增加可机器校验的 plan schema。
3. 为 OAC 增加更多 invalid 回归样例。
4. 将本体子图解析规则抽象为单独的 validator。
5. 将该体系沉淀为 Graph-guided Planning Pattern，用于描述本体子图驱动的 Agent 规划方法。
