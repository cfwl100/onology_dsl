# 执行流水线检查点

第一层按照 Pipeline 模式执行。它既可以执行显式步骤，也可以在没有显式步骤时基于默认本体子图流程生成步骤。

## Checkpoint 0：输入分类

先判断输入属于哪一类：

| 输入类型 | 处理方式 |
|---|---|
| 只有语义目标、意图、知识或变量 | 进入默认本体子图规划流程。 |
| 有完整 `steps` | 检查步骤契约后直接执行。 |
| 有局部步骤或定制字段 | 先生成默认步骤，再应用覆盖、追加或跳过。 |

失败处理：如果既没有语义目标，也没有可执行步骤，返回 `MISSING_PLANNING_INPUT`。

## Checkpoint 1：合并定制内容

按 `customization-contract.md` 合并：

1. 用户显式输入。
2. 业务 Skill 注入的 `variables`。
3. 业务 Skill 注入的 `knowledge`。
4. `stepOverrides`、`stepAppends`、`stepSkips`。
5. 默认本体子图规划流程。

冲突时说明冲突，不得静默覆盖用户显式输入。

## Checkpoint 2：生成或确认步骤

- 没有 `steps`：按 `default-ontology-planning-flow.md` 生成默认步骤。
- 有完整 `steps`：检查每个步骤是否满足 `plan-step-contract.md`。
- 有定制字段：将定制内容应用到默认步骤或显式步骤。

失败处理：返回 `MISSING_PLAN_STEP_FIELD`，列出缺失字段。

## Checkpoint 3：步骤输入

执行每个步骤前，检查当前步骤的输入是否足以调用第二层能力。

失败处理：返回 `MISSING_STEP_INPUT`，不要猜测缺失对象、字段、关系或参数。

## Checkpoint 4：委托执行

每个步骤只调用一个能力：

- `OAG`：委托第二层子图检索。
- `OAC`：委托第二层数据访问。
- `FUNCTION_DISCOVERY`：委托第二层函数发现。
- `FUNCTION_CALL`：委托第二层函数调用。
- `SUMMARY`：由本层做归一化、规划或汇总，不调用原始 Tool。

## Checkpoint 5：结果绑定

只有前置步骤明确返回的字段才能绑定到后续步骤。绑定失败时停止执行并说明缺少哪个输出字段。

## Checkpoint 6：失败和空结果

- 执行失败：按 `failurePolicy` 处理。
- 查询为空：视为有效结果，不自动改写条件重试。
- 校验失败：不得执行后续步骤。
- 业务知识与平台结果冲突：以平台结果为准，并说明冲突。

## Checkpoint 7：结果汇总

按步骤顺序汇总：

1. 使用的默认步骤。
2. 业务 Skill 覆盖、追加或跳过的步骤。
3. 每步执行状态。
4. 关键输入和输出。
5. 未执行步骤及原因。
6. 最终结论和缺失项。
