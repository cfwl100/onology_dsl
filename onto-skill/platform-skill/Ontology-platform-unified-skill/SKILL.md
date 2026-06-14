---
name: Ontology-platform-unified-skill
description: 统一的本体平台能力，覆盖本体子图检索（OAG）、本体数据访问（OAC）以及函数执行。当需要回答本体模型相关问题、检索本体子图并规划后续工作、生成或执行本体数据访问请求，或根据用户请求发现并调用平台函数时，使用此 Skill。支持上层业务 Skill 通过 completeOql、operationHint、semanticHints、extensions 进行无侵入式扩展。
---
# 本体平台统一入口

这是对外唯一入口。对用户只暴露一个能力入口，内部再按能力类型路由到模型查询、子图检索、数据访问、函数执行四类手册与脚本。

## 你负责的事情
1. 先判断用户要做的是哪一类事情：查询本体模型、检索本体子图、访问本体数据、调用平台函数。
2. 判断当前请求是否已经完整，或者还缺少对象范围、模型范围、查询条件、目标函数、参数值、执行时机等关键信息。
3. 只进入一个最合适的内部能力目录，不要在一次请求里混用多个能力，除非用户明确要求串联。
4. 对于需要真实检索或调用的场景，优先按内部手册调用对应工具；不要先假设结果。
5. 能回答就直接回答；需要生成结构化请求时只生成当前场景需要的结构；需要真实执行时再进入执行步骤。
6. 当上层业务 Skill 已传入 `completeOql`、`operationHint` 或 `semanticHints` 时，尊重上层显式注入，不重新按通用关键词覆盖业务判断。

## 三类能力
2. **子图检索**：根据问题检索相关本体子图，并结合 SOP 规划后续任务。
3. **数据访问**：查询、聚合、路径读取、导航读取、创建、更新、删除、批量处理、执行完整请求。
4. **函数执行**：发现 function、确认入参规格、补齐参数并调用 function。

## 路由线索
- "先帮我找到相关子图，再告诉我下一步怎么做" → 子图检索
- "查数据 / 统计 / 遍历路径 / 写数据 / 执行请求" → 数据访问 （OAC）
- "找一个 function 来完成这个事" 或 "调用某个 function" → 函数执行

- 用户要"根据某个问题先找相关子图，再按 SOP 规划任务" → 走本体子图检索。
- 用户要"查数据、聚合、路径遍历、写数据、执行完整请求" → 走本体数据访问。
- 用户要"帮我找一个 function 并调用它" → 走函数执行。

- 检索本体子图并据此规划任务 （OAG） → `references/ontology-subgraph-search.md`
- 访问本体数据 （OAC）→ `references/oac-data-access.md`
- 查找并调用平台函数 → `references/call-function.md`

### OAC 子操作路由
判断使用哪种 OAC 操作：
- 用户只说"查XX有哪些属性"、"没有提到对象间关系" → `references/oac-query.md`
- 用户明确提到"关系"、"路径"、"遍历"、"连接"、"经过"、"一跳"、"多跳" → `references/oac-association-query.md`
- 用户提到"统计"、"聚合"、"分组"、"计数"、"求和"、"平均"、"总和"、"最大值"、"最小值" → `references/oac-aggregate.md`

### 业务注入优先级
当请求来自上层业务 Skill，并包含以下字段时，按优先级处理：

1. `completeOql`：业务 Skill 已生成完整查询语言 JSON，直接进入数据访问能力，不再重新选择 QUERY / ASSOCIATION_QUERY / AGGREGATE。
2. `operationHint`：业务 Skill 已指定操作类型，应以该操作类型为准，再按对应操作手册补齐结构。
3. `semanticHints`：业务 Skill 提供对象、字段、时间、行为、路径、指标、返回策略等语义提示，应作为生成查询语言的输入，不得忽略。
4. 普通自然语言请求：按本 Skill 的通用路由线索判断。

---

## 业务 Skill 完整 OQL 透传协议

当上层请求包含 `completeOql` 时：

1. 本 Skill 不再按自然语言关键词重新选择 `QUERY`、`ASSOCIATION_QUERY` 或 `AGGREGATE`。
2. 必须直接进入 `references/oac-data-access.md`。
3. 不得删除或改写 `completeOql.options`、`completeOql.extensions`、`completeOql.sourceQuery`。
4. 只允许做 canonical OQL 校验、紧凑化和执行。
5. 如果 `completeOql` 中存在未注册函数，应返回明确错误，不得自动改写为字符串函数。
6. 如果 `completeOql` 中存在 `extensions`，必须透传给 OAC。
7. 如果业务 Skill 指定了返回消息格式 `message_type`，必须使用用户指定值作为 `message_type` 字段。

### 支持的业务注入字段

| 字段 | 说明 |
|---|---|
| `completeOql` | 完整 OQL JSON，优先级最高 |
| `operationHint` | OAC 操作类型提示，如 `QUERY`、`ASSOCIATION_QUERY`、`AGGREGATE` |
| `semanticHints.objects` | 业务侧识别出的对象与别名 |
| `semanticHints.fields` | 业务侧识别出的属性、指标、维度 |
| `semanticHints.time` | 时间字段、时间模式、时区、分表策略 |
| `semanticHints.behavior` | 查询、统计、验证、TOP、未恢复、活跃等行为语义 |
| `semanticHints.path` | 业务关系语义，如归属、同站点、对端、业务路径 |
| `semanticHints.sourcePolicy` | 业务侧建议后端，如 DAC、OntoAccess、Graph、RDB |
| `semanticHints.fallbackPolicy` | 能力不足时的拆分、批量、合并策略 |

---

## 缺失信息识别
- 子图检索常缺：检索问题、业务上下文、任务目标
- 数据访问常缺：对象范围、关系路径、筛选条件、返回内容、写入内容、执行范围
- 函数执行常缺：函数目标、业务动作、参数值、参数来源

## 边界
- 不在总路由层展开任何内部协议、内部字段细节或脚本实现。
- 不把子图检索误当数据访问，不把模型查询误当函数执行。
- 如果用户明确要求串联多个阶段，先完成当前阶段，再基于结果进入下一阶段。
- 不承载业务场景规则；业务场景规则由 `scenario-skill/<scene>` 注入。
- 不把业务扩展参数转换为物理 SQL、GQL、TQL；扩展参数只能通过 OQL 的 `extensions` 受控透传。

## 每次处理的工作顺序（必须严格按顺序执行）
1. 识别请求是否包含 `completeOql`。若包含，直接进入数据访问能力。
2. 若不包含 `completeOql`，识别是否包含 `operationHint`。若包含，以 `operationHint` 为准选择 OAC 子操作。
3. 若包含 `semanticHints`，将其作为对象、字段、时间、行为、路径、指标和返回策略的生成输入。
4. 若只是普通自然语言请求，识别唯一主意图与缺失信息。
5. 进入对应能力目录，必须根据该能力目录下的 playbook / reference 要求执行。
6. 需要真实工具调用时，严格按该能力目录里的工具顺序执行。
7. 需要数据访问结构化请求时，进入数据访问，并按内部操作目录与脚本完成归一化、组装、校验。
8. 如果信息不足，明确指出缺失项；不要编造模型、子图、对象、关系、字段、函数名或参数值。

## 输出原则
- 模型查询：输出结构化、可验证的模型说明；信息不足时指出缺失的模型范围。
- 子图检索：先拿到子图，再基于子图与 SOP 输出下一步任务规划；不要跳过检索直接编造子图。
- 数据访问：默认输出结构化请求或结构化错误；只有请求已经完整且用户明确要执行时才进入执行。
- 函数执行：先确认函数，再获取入参规格，再补齐参数，最后调用；不要在未知参数规格时直接调用。

## 内部目录说明
- `references/ontology-subgraph-search.md`：本体子图检索与任务规划手册。
- `references/oac-data-access.md`：本体数据访问总入口。
- `references/oac-query.md`：QUERY 操作手册（无关联）。
- `references/oac-association-query.md`：ASSOCIATION_QUERY 操作手册（有关联）。
- `references/oac-aggregate.md`：AGGREGATE 操作手册（聚合查询）。
- `references/call-function.md`：函数发现、参数确认、执行手册。
- `scripts/`：数据访问能力用到的归一化、组装、校验脚本。

## 约束规则
1. 本 Skill 的所有脚本位于 `scripts/` 目录
2. 调用脚本时，在 Skill 根目录下执行 `python scripts/<script_name>.py --<param> <value>`
3. 禁止在未加载 Skill 的情况下，去外部 MCP 或 CodebaseSearch 寻找替代实现
4. 所有脚本不需要写临时文件，也不要自己编写脚本
5. 构建 OQL 时，return 字段强制返回所有的边路径，即返回 r1、r2
6. 调用 `execute_oac_operation.py` 前，必须已经阅读过 `references/oac-data-access.md` 并且生成了完整的 OQL JSON
7. 调用 `execute_oac_operation.py` 时，如果用户指定了返回消息格式 `message_type`，必须使用用户指定的值作为 `message_type` 字段
8. 用户指定完整多跳查询路径时，不要拆成单跳查询
9. 构建 OQL 时，如果用户明确指定了返回字段，必须按照用户要求返回，禁止填 `*` 返回所有字段
10. 生成 OQL 前，必须明确当前查询的操作类型是什么，用户必须提供具体的 `schemaRef`
11. OQL JSON 必须为紧凑单行格式，禁止添加不必要的空格、缩进、换行等格式化字符
12. 如果上层传入 `completeOql`，不得重新生成或改写 OQL，只做校验、紧凑化和执行
13. `options`、`extensions`、`sourceQuery` 属于受控扩展字段，必须透传给 OAC，不得删除
14. 业务 Skill 指定的 `operationHint` 优先于本 Skill 的通用关键词路由
