# 执行流水线检查点

第一层按照 Pipeline 模式执行。步骤必须按顺序运行，不得跳过检查点。

## Checkpoint 1：计划完整性

检查执行计划是否包含步骤列表，每个步骤是否满足 `plan-step-contract.md`。

失败处理：返回 `MISSING_PLAN_STEP_FIELD`，列出缺失字段。

## Checkpoint 2：步骤输入

执行每个步骤前，检查当前步骤的输入是否足以调用第二层能力。

失败处理：返回 `MISSING_STEP_INPUT`，不要猜测缺失对象、字段、关系或参数。

## Checkpoint 3：委托执行

每个步骤只调用 `Ontology-platform-unified-skill` 的一个能力：

- `OAG`：子图检索。
- `OAC`：数据访问。
- `FUNCTION`：函数执行。

## Checkpoint 4：结果绑定

只有前置步骤明确返回的字段才能绑定到后续步骤。绑定失败时停止执行并说明缺少哪个输出字段。

## Checkpoint 5：失败和空结果

- 执行失败：按 `failurePolicy` 处理。
- 查询为空：视为有效结果，不自动改写条件重试。
- 校验失败：不得执行后续步骤。

## Checkpoint 6：结果汇总

按步骤顺序汇总：

1. 已执行步骤。
2. 每步状态。
3. 关键输出。
4. 未执行步骤及原因。
5. 最终结论。
