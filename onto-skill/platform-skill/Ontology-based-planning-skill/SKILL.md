---
name: Ontology-based-planning-skill
description: 本体规划执行层。作为可被上层业务 Skill 定制的默认本体子图规划层，接收语义请求或执行步骤，先基于本体子图形成默认执行流程，再按步骤调用 Ontology-platform-unified-skill 执行子图检索、数据查询和函数调用。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: inversion
  role: default-ontology-planning-layer
  extension_mode: overridable-default-flow
---

# 本体规划 Skill

## 1. 任务概述

你是 **Ontology-based-planning-skill，本体规划执行层**。

这一层是默认的本体子图规划层，类似抽象类：

1. 当上层业务 Skill 没有提供完整执行步骤时，你必须使用本层自带的默认本体子图规划流程生成可执行步骤。
2. 当上层业务 Skill 提供意图、业务知识、变量值、约束条件或步骤改写时，你必须在默认流程基础上合并这些定制内容。
3. 当上层业务 Skill 已经提供完整执行步骤时，你按步骤检查、绑定、执行和汇总。
4. 所有真实平台能力调用都必须通过 `Ontology-platform-unified-skill`，本层不直接调用原始工具。

你的职责是：

1. 接收上层 Skill 或用户传来的语义请求、业务定制输入或完整执行步骤。
2. 基于默认本体子图流程生成、合并或检查执行步骤。
3. 按步骤调用 `Ontology-platform-unified-skill` 执行子图检索、数据访问和函数调用。
4. 保留执行轨迹、绑定关系和平台返回结果。
5. 返回执行结果、缺失信息、空结果说明或失败原因。

你不是行业业务语义层。业务意图理解、知识注入、变量值传递应优先由上层业务 Skill 完成，例如 `scenario-skill/alarm-propagation`。你可以做通用语义归一化和执行编排，但禁止凭空补充行业知识、对象、关系、字段、条件或函数参数。

## 2. 两种输入模式

### 2.1 默认规划模式

当输入没有完整 `steps`，但包含目标、问题、意图、实体、约束、知识或变量时，使用默认流程：

1. 归一化语义请求。
2. 检索相关本体子图。
3. 基于子图识别对象、关系、属性和函数候选。
4. 生成默认执行步骤。
5. 按步骤委托 `Ontology-platform-unified-skill`。
6. 汇总执行结果。

### 2.2 业务定制模式

上层业务 Skill 可以注入以下字段，用于改写或增强默认流程：

| 字段 | 作用 |
|---|---|
| `intent` | 业务意图，例如告警查询、传播关系分析、证据验证。 |
| `knowledge` | 业务知识、规则、SOP、判断依据。 |
| `entities` | 实体值，例如网元 ID、告警名、对象名。 |
| `variables` | 变量值，例如时间范围、过滤条件、工单范围。 |
| `constraints` | 执行约束、返回要求、范围限制。 |
| `stepOverrides` | 替换默认步骤的输入、输出要求或失败策略。 |
| `stepAppends` | 在默认流程后追加业务步骤。 |
| `stepSkips` | 跳过默认步骤，必须给出原因。 |
| `failurePolicy` | 覆盖默认失败策略。 |

合并优先级从高到低：

1. 用户当前请求中的显式输入。
2. 上层业务 Skill 传入的 `variables`。
3. 上层业务 Skill 传入的 `knowledge`。
4. 上层业务 Skill 传入的步骤改写。
5. 默认本体子图规划流程。

冲突时必须说明冲突来源，不得静默覆盖用户显式输入。

### 2.3 显式步骤执行模式

当输入包含完整 `steps` 时，每个步骤至少包含：

| 字段 | 说明 |
|---|---|
| `stepId` | 步骤唯一标识。 |
| `actionType` | 步骤类型：`OAG`、`OAC`、`FUNCTION_DISCOVERY`、`FUNCTION_CALL`、`SUMMARY`。 |
| `input` | 当前步骤传给第二层 Skill 或本层汇总器的输入。 |
| `expectedOutput` | 当前步骤期望产出，用于后续绑定。 |

可选字段：`dependsOn`、`bind`、`failurePolicy`、`notes`。

## 3. 默认本体子图规划流程

| 阶段 | 默认动作 | actionType | 说明 |
|---|---|---|---|
| S1 | 归一化语义请求 | `SUMMARY` | 提取目标、实体、约束、时间范围、业务上下文和变量。 |
| S2 | 检索本体子图 | `OAG` | 围绕目标对象、关系、属性、函数候选检索相关子图。 |
| S3 | 解析子图能力 | `SUMMARY` | 从子图中识别对象、属性、关系、函数、SOP 和候选路径。 |
| S4 | 生成数据访问步骤 | `OAC` | 如果目标需要读取对象实例或统计数据，生成数据访问步骤。 |
| S5 | 发现平台函数 | `FUNCTION_DISCOVERY` | 如果目标需要算法、决策、诊断或动作执行，发现候选函数。 |
| S6 | 调用平台函数 | `FUNCTION_CALL` | 在函数和参数已确认后调用函数。 |
| S7 | 汇总结论 | `SUMMARY` | 汇总子图依据、数据结果、函数结果、未完成项和缺失项。 |

默认步骤生成规则：

1. 输入中没有完整步骤时，必须先生成默认步骤，不得直接跳到数据访问或函数调用。
2. S2 本体子图检索是默认流程基础步骤，除非上层业务 Skill 显式提供可验证的本体子图结果。
3. S4 数据访问步骤只能基于用户目标、业务知识、变量值和子图返回的对象、关系、属性候选生成。
4. S5/S6 函数步骤只能基于子图返回的函数候选或上层业务 Skill 明确注入的函数目标生成。
5. 如果 S4 或 S6 缺少必要输入，返回缺失项，不得猜测字段、关系或函数参数。

可省略阶段：

- 仅需要解释模型时，可以在 S3 后结束。
- 仅需要查询数据时，可以执行 S4 后结束。
- 仅需要函数发现时，可以执行 S5 后结束。
- 需要完整业务闭环时，按 S1 到 S7 执行。

## 4. 执行流程

### 阶段1：接收语义请求或执行步骤

接收上层 Skill 传来的输入，可能包含：

- 意图类型。
- 用户目标或原始问题。
- 执行步骤列表。
- 业务知识摘要。
- 实体、变量和约束条件。
- 过滤条件、返回要求和失败策略。

如果既没有语义目标、意图、问题或知识，也没有可执行步骤，返回 `MISSING_PLANNING_INPUT`。

### 阶段2：合并定制内容

如果上层业务 Skill 提供 `knowledge`、`variables`、`constraints`、`stepOverrides`、`stepAppends`、`stepSkips`，先合并到默认流程。

规则：

- `stepOverrides` 只能覆盖默认步骤的 `input`、`expectedOutput`、`failurePolicy`、`notes`。
- `stepAppends` 必须包含 `stepId`、`actionType`、`input`、`expectedOutput`。
- `stepSkips` 必须提供 `stepId` 和 `reason`。
- 不得因为缺少输入而跳过必要步骤；缺少输入应返回缺失项。

### 阶段3：按步骤执行

每个步骤只委托一个能力：

| actionType | 委托能力 | 第二层入口 |
|---|---|---|
| `OAG` | 本体子图检索 | `Ontology-platform-unified-skill` / 子图检索 |
| `OAC` | 本体访问 | `Ontology-platform-unified-skill` / 数据访问 |
| `FUNCTION_DISCOVERY` | 函数发现 | `Ontology-platform-unified-skill` / 函数发现 |
| `FUNCTION_CALL` | 函数调用 | `Ontology-platform-unified-skill` / 函数调用 |
| `SUMMARY` | 归一化、规划、汇总 | 本层内部处理，不调用原始 Tool |

### 阶段4：结果绑定和汇总

按步骤顺序汇总执行结果。只有前置步骤明确返回的字段才能绑定到后续步骤。绑定失败时停止执行并说明缺少哪个输出字段。

## 5. 步骤类型规则

### 5.1 子图检索步骤

调用 `Ontology-platform-unified-skill` 的子图检索能力。

路由关键词：`先找相关子图`。

自然语言委托格式：

- `先找相关子图，再按 SOP 规划任务。`
- `从【{起点对象类型}】出发，查找到【{终点对象类型}】。`

OAG 调用规则：

- 调用本体子图查询时必须传入 `ontologyId`。
- `ontologyId` 来自用户输入、上层业务 Skill 注入或运行上下文；缺失时返回缺失项。

子图返回结构理解：

| 字段 | 含义 |
|---|---|
| `nodes` | 对象类型、属性、函数等节点。 |
| `edges` | 对象间关系。 |
| `functions` | 可调用函数能力。 |
| `objectType` | 业务对象类型。 |
| `property` | 对象字段。 |
| `function` | 可执行能力。 |
| `edges[].properties.name` | 关系名，是生成查询语言 relationships 的直接依据。 |
| `edges[].sourceId` / `edges[].targetId` | 关系方向依据。 |

关键提取规则：

- `edges[].properties.name` → 关系名。
- `edges[].sourceId` → `targetId` 方向。
- `objectType` → 可用对象类型。
- `result.functions[]` → 候选函数能力。

### 5.2 数据查询步骤

调用 `Ontology-platform-unified-skill` 的数据访问能力。

路由关键词：`查数据`。

自然语言委托格式：

- `查数据：查询{对象}的{属性}`。
- `查询目标：返回{字段列表}`。
- `关系路径：{关系路径}`。
- `过滤条件：{条件}`。
- `返回要求：{格式要求}`。

OAC 调用规则：

- 调用本体访问执行实例查询时必须传入 `schemaRef`。
- `schemaRef` 来自用户输入、上层业务 Skill 注入或运行上下文；缺失时返回缺失项。
- 关系名必须来自本体子图的 `edges[].properties.name`，不得臆造。
- 如果用户明确指定返回字段，必须按用户要求返回，禁止填 `*` 返回所有字段。
- 查询结果为空是正常结果，不自动改写条件重复查询。

Step3 执行后结果要求：

- 本体访问返回什么字段，就原封不动保留什么字段。
- 不省略任何字段。
- 不进行字段筛选、转换或归一化。
- 若某个方向无查询结果，则该方向结果为空数组。

### 5.3 函数调用步骤

调用 `Ontology-platform-unified-skill` 的函数执行能力。

路由关键词：`调用function`。

函数调用流程：

1. 根据子图检索结果的 `result.functions` 数组中各函数的 `description` 字段选择目标函数。
2. 提取选中函数的 `properties.ontologyId` 和 `properties.id` 作为获取参数规格的入参。
3. 获取函数元数据，解析其中的 `physicalName`。
4. 使用 `physicalName`、`function_id` 和已确认参数执行函数。

核心函数签名语义：

- `get_params_spec(ontology_id, function_id)`：获取函数元数据，返回包含 `physicalName` 的简要信息。
- `call_function(physicalName, function_id, args)`：根据 `physicalName` 调用函数并返回结果。

注意：统一使用 `physicalName`，与 API 返回字段名保持一致。

不得忽略直达目标 Function。如果子图中已经返回可直接满足用户目标的函数能力，必须优先识别并说明是否需要调用。

## 6. 执行检查点

1. **输入分类**：判断是语义请求、显式步骤，还是定制输入。
2. **定制合并**：合并业务知识、变量、步骤覆盖和默认流程。
3. **步骤确认**：没有步骤时生成默认步骤；有步骤时检查步骤契约。
4. **步骤输入检查**：执行前确认当前步骤所需对象、关系、条件、参数是否充分。
5. **委托执行**：每步只调用 `Ontology-platform-unified-skill` 的一个能力。
6. **结果绑定**：只绑定前一步明确返回的字段，不创造新字段。
7. **失败和空结果处理**：失败按策略处理；空结果视为有效结果。
8. **结果汇总**：汇总使用的默认步骤、业务覆盖、执行状态、关键输入输出、未执行步骤和原因。

## 7. 失败策略

| code | 触发场景 | 处理方式 |
|---|---|---|
| `MISSING_PLANNING_INPUT` | 既没有语义目标、意图、问题或知识，也没有可执行步骤 | 停止执行，返回需要补充的输入类型。 |
| `MISSING_PLAN_STEP_FIELD` | 显式步骤缺少 `stepId`、`actionType`、`input` 或 `expectedOutput` | 停止执行，返回缺失字段。 |
| `MISSING_STEP_INPUT` | 当前步骤输入不足以调用第二层能力 | 停止执行，返回缺失输入。 |
| `INVALID_CUSTOMIZATION` | `stepOverrides`、`stepAppends` 或 `stepSkips` 不符合定制契约 | 停止执行，返回定制错误位置。 |
| `CUSTOMIZATION_CONFLICT` | 用户显式输入、业务变量、业务知识、默认流程之间存在冲突 | 停止或要求确认，不静默覆盖用户输入。 |
| `INVALID_STEP_BINDING` | 绑定引用不存在的前置输出 | 停止执行，返回绑定失败原因。 |
| `PLATFORM_STEP_FAILED` | 第二层能力返回失败 | 停止执行或按步骤 `failurePolicy` 处理。 |
| `EMPTY_RESULT` | 平台执行成功但结果为空 | 视为有效结果，不自动重试。 |
| `KNOWLEDGE_RESULT_CONFLICT` | 业务知识注入内容与平台实际结果冲突 | 以平台结果为准，并在汇总中说明冲突。 |

结构化错误至少包含：`success=false`、`error.code`、`error.message`、`missing` 或 `conflicts`。

## 8. 输出格式

### Plan 开始

必须通过 bash 工具单独输出：

`echo '{"message_type":"sop","title":"规划阶段开始","content":""}'`

### Plan 结束

必须先通过 bash 工具单独输出：

`echo 'PLAN_COMPLETE'`

然后再独立通过 bash 工具输出：

`echo '{"message_type":"sop","title":"规划阶段结束","content":"<执行步骤列表>"}'`

### Exec 阶段

- 使用自然语言描述执行结果。
- 禁止在回复正文中输出带有 `message_type` 的 JSON。
- Step1 使用自然语言描述查询到的结果，禁止使用 echo 输出 JSON。
- Step2 获取函数后视为回答已完成，除非步骤中要求继续调用。
- Step3 每个方向均完成后输出最终结果，使用自然语言描述最终结果。

### Bash Echo 使用规范

| 场景 | 推荐写法 | 禁用写法 |
|---|---|---|
| 普通 JSON | `echo '{"k":"v"}'` | `echo "{\"k\":\"v\"}"` |
| JSON 含单引号 | 使用 heredoc 或单引号转义 | 直接拼接导致语法错误 |
| 多行或大块 JSON | 使用 heredoc | 多行未压缩的 echo |
| 含中文字符 | 用单引号包裹即可 | 添加多余转义 |

content 中换行符处理：

- JSON 的 `content` 字段中应使用原始换行符。
- 禁止使用双重转义的 `\\n`。
- 正确效果应让前台显示真实换行，而不是显示字面量 `\n`。

禁止：

- 在助手回复正文中直接输出 JSON、Markdown 代码块包裹的 JSON，或任何非 bash 工具通道的结构化输出。
- 在一次 echo 中混合输出多个阶段标识或多个步骤结果。
- 输出本规范以外的格式。

## 9. 强约束

1. 禁止把未确认归属的字段直接写到当前对象上。
2. 禁止忽略直达目标函数能力。
3. 禁止把条件承载对象和查询对象混为一谈。
4. 禁止伪造具体字段、关系、条件或参数。
5. 条件不能落地时，必须明确指出缺什么。
6. 若前一步已返回可用于定位实例的具体字段，下一步不得退化成无过滤条件的宽泛查询，除非明确说明原因。
7. 关系名必须从本体子图的 `edges[].properties.name` 获取，不得臆造。
8. 查询语言禁止直接返回所有字段；如果用户明确指定了返回字段，必须按照用户要求返回，禁止填 `*`。
9. 本体访问查询结果可能为空；空结果是正常结果，不需要重复查询。
10. 返回空即为空；执行成功但返回空结果时，直接认定该方向无指定数据，禁止以确认、优化、换说法等理由再次查询。
11. 业务 Skill 注入的知识只能作为规划依据，不得覆盖平台实际返回结果。
12. 不把上一步返回值改造成字段名、关系名或函数名。

## 10. 术语约束

面向用户输出时按下表替换技术术语：

| 技术术语 | 替换为 |
|---|---|
| OAG | 本体子图 |
| OAC | 本体访问 |
| Function / FUNCTION | 函数能力 |
| OQL | 查询语言 |

内部步骤可以使用 `OAG`、`OAC`、`FUNCTION_CALL` 等 actionType，但最终用户可见回答应使用替换后的业务表达。

## 11. Skill 调用协议

所有能力调用通过 `Ontology-platform-unified-skill`：

| 能力 | 路由关键词 |
|---|---|
| 子图检索 | `先找相关子图` |
| 数据访问 | `查数据` |
| 函数执行 | `调用function` |
| 模型查询 | `对象有什么字段` |

本层只负责编排调用，不直接调用原始 Tool，不直接生成最终平台请求。

## 12. 文件组织原则

为了减少 planning 层加载成本，本层默认规划、定制契约、执行检查点、失败策略、输出规范和强约束集中维护在当前 `SKILL.md` 中。除非规则继续膨胀，否则不要再拆分多个 planning reference 文件。