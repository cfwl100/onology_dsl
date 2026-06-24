# 本体 Agent Skill 架构设计文档

本文档描述 `onto-skill` 的最新实现架构、分层职责、执行链路、Agent Skill 设计模式和开发约束。当前版本以“业务 Skill 组装 6 行输入，Planning Skill 直接读取并执行，Platform Skill 封装平台能力”为核心。

## 1. 设计目标

本体 Skill 体系面向 Agent 和业务定制场景，目标是：

- 让业务开发人员用 Markdown 维护业务知识。
- 让业务 Skill 只做业务语义识别和 6 行输入组装。
- 让 Planning Skill 基于本体子图生成执行计划。
- 让 Platform Skill 统一封装 OAG、OAC、Function 能力。
- 减少重复解析、重复上下文构造和不必要的大模型调用。
- 通过协议、schema、validator 和运行边界提升 Agent 执行稳定性。

## 2. 三层架构

```text
用户问题
  -> scenario-skill 业务定制层
  -> Ontology-based-planning-skill 规划层
  -> Ontology-platform-unified-skill 平台能力层
  -> OAG / OAC / Function
```

| 层级 | 主要职责 | 不做什么 |
|---|---|---|
| 业务定制层 scenario-skill | 识别主意图，读取业务知识，抽取变量，组装 6 行输入 | 不执行 OAG/OAC/Function，不生成 OQL |
| 规划层 Ontology-based-planning-skill | 直接读取 6 行输入，生成 executionPlan，执行 S1-S6 | 不重新改写业务意图，不重复构造字段映射对象 |
| 平台能力层 Ontology-platform-unified-skill | 封装 OAG、OAC、Function、OQL schema、validator、executor | 不承担业务场景语义识别 |

## 3. 架构流程图

```mermaid
flowchart TB
    U[用户自然语言问题]

    subgraph BIZ[业务定制层 scenario-skill]
        B1[识别唯一主意图]
        B2[读取 knowledge/*.md]
        B3[抽取业务变量]
        B4[组装 6 行 Planning 输入]
    end

    subgraph PLAN[规划层 Ontology-based-planning-skill]
        P0[直接读取 6 行原文]
        P1[生成 executionPlan]
        P2[S1 子图检索]
        P3[S2 基于子图任务规划]
        P4[S3 OAC 数据访问]
        P5[S4 Function 发现]
        P6[S5 Function 执行]
        P7[S6 汇总]
    end

    subgraph PLATFORM[平台能力层 Ontology-platform-unified-skill]
        OAG[OAG 本体子图]
        OAC[OAC 本体访问]
        FUNC[Function 能力]
        SCHEMA[OQL Schema / Validator / Executor]
    end

    U --> B1 --> B2 --> B3 --> B4 --> P0 --> P1
    P1 --> P2 --> OAG
    OAG --> P3
    P3 --> P4 --> OAC --> SCHEMA
    P3 --> P5 --> FUNC
    P5 --> P6 --> FUNC
    P4 --> P7
    P6 --> P7
    P7 --> R[最终业务结果]
```

## 4. 6 行输入协议

业务 Skill 传给 Planning 的唯一输入是 6 行文本：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<本次执行需要的场景知识、业务规则、子图检索规则、任务规划规则、查询规则、Function 规则、返回要求和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖项；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

Planning 运行时直接读取这 6 行原文，不再把它们重复转换为另一套字段结构。

## 5. 执行步骤 S1-S6

| 步骤 | 名称 | 说明 |
|---|---|---|
| S1 | 子图检索 | 基于本体ID、业务意图和业务知识请求 OAG 子图 |
| S2 | 基于本体子图的任务规划 | 基于对象、字段、关系、函数候选生成任务计划 |
| S3 | OAC 数据访问 | 生成、校验、执行 OQL，返回对象结构 |
| S4 | Function 发现 | 根据子图和业务规则选择函数候选 |
| S5 | Function 执行 | 获取参数规格并执行函数能力 |
| S6 | 汇总 | 汇总对象结构、函数结果、缺失项和失败原因 |

默认流程：

```text
S1 -> S2 -> S3 -> S6
```

需要 Function 时，可由业务 Skill 在流程级定制中写明：

```text
S1 -> S2 -> S4 -> S5 -> S3 -> S6
```

## 6. Agent Skill 业界常见 5 种设计模式

本仓库的本体 Skill 体系可抽象为 5 种常见 Agent Skill 设计模式。这些模式不是互斥关系，而是分层组合使用。

### 6.1 Router / Dispatcher 模式：意图路由与 Skill 分派

**业界含义**：先判断用户请求属于哪个业务场景或工具能力，再把任务分派给最合适的 Skill、工具或子流程，避免一个大 Prompt 同时承担所有职责。

**本仓库落地**：

- `scenario-skill/*/SKILL.md` 只识别唯一主意图。
- 每个主意图绑定一个或多个 `knowledge/*.md`。
- 业务 Skill 不直接执行平台能力，只向 `Ontology-based-planning-skill` 传递 6 行输入。

**代码亮点**：

- 用目录结构表达业务路由：`scenario-skill/<business-skill>/knowledge/<intent>.md`。
- 意图识别和执行规划解耦，业务新增时只新增业务 Skill 与 knowledge，不侵入 Platform Skill。
- `alarm-propagation` 已体现该模式：`nealarm_query`、`propagation_relation_query`、`propagation_evidence_check` 分别路由到不同 knowledge 文件。

### 6.2 Contract-first Prompt Interface 模式：协议优先的 Skill 间接口

**业界含义**：多 Agent 或多 Skill 协作时，优先定义稳定输入输出协议，再让各层围绕协议实现，减少自然语言自由传递带来的歧义。

**本仓库落地**：

- 业务 Skill 到 Planning Skill 的接口固定为 6 行输入。
- 字段名、含义、缺失信息和流程定制语义由产品文档约束。
- Planning Skill 运行时直接读取 6 行原文，不再额外构造字段映射对象。

**代码亮点**：

- 6 行协议是跨业务 Skill 的统一接口，降低业务定制成本。
- `流程级定制` 只描述相对默认流程的覆盖项，减少重复上下文。
- `步骤级定制` 只描述业务增量规则，不要求业务 Skill 复制标准步骤模板。
- 去掉 `planningContext`、`inputGate`、`stepRuleMap` 等中间结构，减少大模型冗余解析。

### 6.3 Knowledge-as-Code 模式：业务知识即代码

**业界含义**：把可复用业务规则、术语、路径约束、失败策略沉淀为版本化文本资产，让业务人员可维护、可评审、可回滚。

**本仓库落地**：

- 每个业务 Skill 下使用 `knowledge/*.md` 承载业务 Know-how。
- knowledge 文件按 6 行字段分段，既方便业务开发人员填写，也方便外层 SKILL 组装。
- `业务领域知识` 保留细粒度规则，不只写摘要。

**代码亮点**：

- knowledge 文件既是业务规则文档，也是运行时可摘录上下文。
- `## 可注入 6 行片段` 作为组装骨架，前面的细粒度规则作为保真知识来源。
- 对 `alarm-propagation` 这类复杂场景，业务规则如关系名动态获取、方向查询约束、返回字段、空结果策略都可独立维护。

### 6.4 Plan-and-Execute 模式：先规划再执行

**业界含义**：Agent 面对复杂任务时，先生成执行计划，再按步骤调用工具或子能力执行，最后汇总结果。

**本仓库落地**：

- `Ontology-based-planning-skill` 根据 6 行输入生成 `executionPlan`。
- 默认执行 `S1 -> S2 -> S3 -> S6`。
- 需要函数能力时才扩展为 `S1 -> S2 -> S4 -> S5 -> S3 -> S6`。

**代码亮点**：

- `executionPlan` 只由流程级定制决定，避免多次大模型解析。
- S1-S6 标准化后，每个步骤边界清晰，方便测试和替换。
- 空结果、缺失信息、Function 缺失等失败策略由步骤边界统一承载。

### 6.5 Tool Facade + Guardrail 模式：工具门面与安全护栏

**业界含义**：Agent 不直接裸调底层接口，而是通过统一工具门面访问能力，并在门面层做 schema 校验、环境检查、错误归一和跨平台兼容。

**本仓库落地**：

- `Ontology-platform-unified-skill` 封装 OAG、OAC、Function。
- OQL 先生成 JSON，再通过 schema 和 validator 校验。
- 真实 OAC 执行前检查服务环境。
- 复杂 JSON 优先使用 UTF-8 文件和 `--input`，减少 Shell 转义问题。
- 默认不生成链式 Shell 命令，避免 Windows PowerShell、CMD、Bash、zsh 等环境不兼容。

**代码亮点**：

- OQL schema 支持 `returns.fields: ["*"]`，同时仍限制过滤条件字段不能使用通配符。
- validator 与 executor 分离，校验成功不等于真实后端可执行。
- 执行脚本统一返回错误结构，例如环境缺失、JSON 解析失败、schema 校验失败。
- Shell 兼容规则从 Skill 文档层约束，减少 Agent 生成不可执行命令。

## 7. 五种模式与本仓库模块映射

| 设计模式 | 对应目录或文件 | 主要价值 |
|---|---|---|
| Router / Dispatcher | `onto-skill/scenario-skill/*/SKILL.md` | 业务场景路由，避免大而全 Prompt |
| Contract-first Prompt Interface | `onto-skill/docs/planning-input-interface.md`、`Ontology-based-planning-skill/SKILL.md` | 固定 6 行协议，减少歧义和冗余解析 |
| Knowledge-as-Code | `scenario-skill/*/knowledge/*.md` | 业务规则可维护、可评审、可版本化 |
| Plan-and-Execute | `Ontology-based-planning-skill/SKILL.md` | executionPlan 驱动 S1-S6，执行链路清晰 |
| Tool Facade + Guardrail | `Ontology-platform-unified-skill/` | 平台能力统一封装，schema 校验和环境护栏 |

## 8. 代码亮点总结

### 8.1 低冗余协议

业务 Skill 和 Planning Skill 之间只传 6 行输入，Planning 直接读取原文，不再反复生成中间映射对象。

### 8.2 无侵入业务扩展

新增业务场景只需要增加 scenario-skill 和 knowledge 文件，不修改 OAG/OAC/Function 的平台 Skill。

### 8.3 知识保真

业务知识按段维护，外层 Skill 组装时必须合并细粒度规则，避免只摘摘要导致业务约束丢失。

### 8.4 Schema-first 可靠执行

OQL 生成后必须经过 schema 和 validator 校验，复杂 JSON 通过文件输入传递，降低 Shell 引号转义风险。

### 8.5 跨平台命令鲁棒性

默认不输出链式命令，优先使用绝对脚本路径或分行命令；只有明确 Shell 类型并确认兼容时才使用连接符。

### 8.6 对象结构统一输出

OAC 最终业务输出统一为 `{objects, relationships}`，便于上层 Agent 汇总、比对和生成证据说明。

## 9. 业务定制层设计模式

业务 Skill 推荐结构：

```text
scenario-skill/<business-skill>/
├── SKILL.md
└── knowledge/
    ├── <intent-a>.md
    ├── <intent-b>.md
    └── <intent-c>.md
```

`SKILL.md` 负责选择主意图和组装 6 行输入。

`knowledge/*.md` 负责维护业务知识，建议按以下段落组织：

```text
## 本体ID
## 业务意图
## 业务领域知识
## 流程级定制
## 步骤级定制
## 缺失信息
## 可注入 6 行片段
```

其中“可注入 6 行片段”只是骨架，不能替代完整业务知识。业务 Skill 组装时必须保留业务领域知识中的细粒度规则。

## 10. Planning 层设计模式

Planning Skill 的核心原则：

- 直接使用 6 行输入原文。
- 根据流程级定制生成 `executionPlan`。
- 默认执行 `S1 -> S2 -> S3 -> S6`。
- 只有流程级定制要求 Function 时才加入 S4/S5。
- 每个步骤直接消费业务领域知识、步骤级定制和上游输出。
- 不重复构造 `planningContext`、`inputGate`、`stepRuleMap`。

## 11. Platform 层设计模式

`Ontology-platform-unified-skill` 封装三类能力。

| 能力 | 职责 | 输出 |
|---|---|---|
| OAG | 检索本体子图、对象、字段、关系、函数候选 | 子图原始结果和候选摘要 |
| OAC | 生成、校验、执行 OQL | `{objects, relationships}` |
| Function | 选择函数、获取参数规格、执行函数能力 | 函数结果或缺失项 |

OAC 中间过程可以包含 operation 判断、OQL 和 validation，但最终业务输出只保留对象结构和必要摘要。

## 12. OAC 生成与校验原则

OAC 遵循 Generator + Reviewer 模式：

```text
业务意图 / 业务知识 / 子图结果
  -> 判断 operation
  -> 读取唯一操作手册
  -> 读取对应 schema
  -> 生成 OQL JSON
  -> validator 校验
  -> 按需 executor 执行
```

复杂 OQL、长数组或跨 Shell 场景优先使用 UTF-8 JSON 文件和 `--input <json文件>`。短小 JSON 且确认引号安全时才使用 `--oac-json`。

执行真实 OAC 前必须确认服务环境变量已配置。缺少服务环境时，只能报告环境缺失，不得声称真实查询完成。

## 13. Shell 兼容原则

Skill 生成命令时必须考虑操作系统和 Shell：

- 看到 Windows 路径时，默认使用 Windows 兼容写法。
- 不确定 Shell 时，不生成链式命令。
- 默认优先使用绝对脚本路径，避免 `cd && python`。
- 只有用户明确说明当前是 Bash、zsh、CMD、WSL 或 Git Bash 并要求链式命令时，才使用对应 Shell 连接符。

## 14. 质量保障

建议建立以下测试：

- 业务 Skill：测试主意图识别、knowledge 读取、变量抽取、6 行组装。
- Planning Skill：测试 executionPlan 生成和 S1-S6 步骤衔接。
- Platform Skill：测试 OQL schema、validator、executor、Function 参数规格。
- Golden Case：覆盖简单查询、关系查询、聚合查询、Function 流程、多方向业务流程。

## 15. 关键边界

- 业务 Skill 不执行平台能力。
- Planning Skill 不编造本体事实。
- Platform Skill 不替代业务语义识别。
- 空结果是有效结果时，不自动放宽条件。
- 子图缺少对象、字段、关系或函数候选时，返回缺失信息，不猜测。
