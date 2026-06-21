# 计划步骤输入契约

本文件定义 `Ontology-based-planning-skill` 可接收的两类输入：

1. **语义请求输入**：没有完整步骤，由本层使用默认本体子图规划流程生成步骤。
2. **显式步骤输入**：上层业务 Skill 已经提供完整或局部步骤，由本层检查、合并和执行。

## 输入类型一：语义请求

当输入不包含完整 `steps` 时，至少需要提供以下信息之一：

| 字段 | 说明 |
|---|---|
| `goal` | 用户目标或业务目标。 |
| `intent` | 上层业务 Skill 识别出的业务意图。 |
| `query` | 原始自然语言问题。 |
| `knowledge` | 上层业务 Skill 注入的知识摘要、规则或 SOP。 |

可选字段：

| 字段 | 说明 |
|---|---|
| `entities` | 实体值，例如对象 ID、名称、告警名、设备名。 |
| `variables` | 变量值，例如时间范围、工单范围、过滤条件。 |
| `constraints` | 约束条件。 |
| `stepOverrides` | 覆盖默认步骤。 |
| `stepAppends` | 追加业务步骤。 |
| `stepSkips` | 跳过默认步骤。 |
| `failurePolicy` | 失败处理策略。 |

语义请求输入会先进入 `default-ontology-planning-flow.md`，再合并 `customization-contract.md` 中定义的定制内容。

## 输入类型二：显式步骤

当输入包含 `steps` 时，每个步骤至少包含：

| 字段 | 说明 |
|---|---|
| `stepId` | 步骤唯一标识，例如 `S1_search_subgraph`。 |
| `actionType` | 步骤类型：`OAG`、`OAC`、`FUNCTION_DISCOVERY`、`FUNCTION_CALL`、`SUMMARY`。 |
| `input` | 当前步骤需要传递给第二层 Skill 或本层汇总器的输入。 |
| `expectedOutput` | 当前步骤期望产出的结果，用于后续绑定。 |

## 步骤可选字段

| 字段 | 说明 |
|---|---|
| `dependsOn` | 当前步骤依赖的前置步骤 ID。 |
| `bind` | 前置步骤输出到当前输入的绑定规则。 |
| `failurePolicy` | 失败处理策略：`STOP`、`RETURN_MISSING`、`SKIP_WITH_REASON`。 |
| `notes` | 补充说明，不得替代必填字段。 |

## actionType 约束

- `OAG`：用于本体子图检索，只传递检索目标、起点/终点、业务上下文。
- `OAC`：用于本体数据访问，只传递查询目标、对象、关系路径、条件、返回字段和执行要求。
- `FUNCTION_DISCOVERY`：用于发现候选函数，只传递函数目标、业务动作和参数来源。
- `FUNCTION_CALL`：用于调用已确认函数，只传递函数标识和已确认参数。
- `SUMMARY`：用于本层内部归一化、规划、证据汇总和结论生成，不调用原始 Tool。

## 默认步骤与显式步骤的合并

- 没有 `steps` 时，生成默认步骤。
- 有完整 `steps` 时，优先执行显式步骤。
- 有 `steps` 且同时存在 `stepOverrides`、`stepAppends`、`stepSkips` 时，先检查显式步骤，再应用定制规则。
- 上层业务 Skill 只能通过契约字段定制流程，不得要求本层跳过检查点。

## 禁止行为

- 缺少 `goal`、`intent`、`query`、`knowledge` 且没有 `steps` 时，不得执行。
- 缺少 `actionType` 的显式步骤不得执行。
- 缺少当前步骤必要输入时不得调用第二层。
- `bind` 中不能引用不存在的前置步骤输出。
- 不得把前置步骤结果中的值当成新的字段名、关系名或函数名。
