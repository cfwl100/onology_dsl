# 默认本体子图规划流程

本文件定义 `Ontology-based-planning-skill` 在没有完整外部步骤时必须使用的默认流程。

## 适用场景

当输入只有自然语言目标、业务意图、实体、约束、知识摘要或变量值，而没有完整 `steps` 时，使用本默认流程生成步骤。

## 默认阶段

| 阶段 | 默认动作 | actionType | 说明 |
|---|---|---|---|
| S1 | 归一化语义请求 | `SUMMARY` | 提取目标、实体、约束、时间范围、业务上下文和变量。 |
| S2 | 检索本体子图 | `OAG` | 围绕目标对象、关系、属性、函数候选检索相关子图。 |
| S3 | 解析子图能力 | `SUMMARY` | 从子图中识别对象、属性、关系、函数、SOP 和候选路径。 |
| S4 | 生成数据访问步骤 | `OAC` | 如果目标需要读取对象实例或统计数据，生成 OAC 查询步骤。 |
| S5 | 发现平台函数 | `FUNCTION_DISCOVERY` | 如果目标需要算法、决策、诊断或动作执行，发现候选函数。 |
| S6 | 调用平台函数 | `FUNCTION_CALL` | 在函数和参数已确认后调用函数。 |
| S7 | 汇总结论 | `SUMMARY` | 汇总子图依据、数据结果、函数结果、未完成项和缺失项。 |

## 默认步骤生成规则

1. 输入中没有完整步骤时，必须先生成默认步骤，不得直接跳到 OAC 或函数调用。
2. OAG 是默认流程的基础步骤，除非上层业务 Skill 显式提供可验证的本体子图结果。
3. OAC 步骤只能基于用户目标、业务知识、变量值和 OAG 返回的对象/关系/属性候选生成。
4. FUNCTION 步骤只能基于 OAG 返回的函数候选或上层业务 Skill 明确注入的函数目标生成。
5. 如果 S4 或 S6 缺少必要输入，返回缺失项，不得猜测字段、关系或函数参数。

## 默认步骤骨架

```json
{
  "steps": [
    {
      "stepId": "S1_normalize_request",
      "actionType": "SUMMARY",
      "input": {
        "goal": "用户目标",
        "intent": "可选业务意图",
        "entities": {},
        "constraints": {},
        "variables": {},
        "knowledge": "可选业务知识摘要"
      },
      "expectedOutput": ["normalizedGoal", "entities", "constraints", "variables"]
    },
    {
      "stepId": "S2_search_subgraph",
      "actionType": "OAG",
      "dependsOn": ["S1_normalize_request"],
      "input": {
        "query": "围绕目标检索相关本体子图"
      },
      "expectedOutput": ["objects", "relationships", "functions", "sop"]
    },
    {
      "stepId": "S3_plan_from_subgraph",
      "actionType": "SUMMARY",
      "dependsOn": ["S2_search_subgraph"],
      "input": {
        "subgraph": "S2 输出"
      },
      "expectedOutput": ["candidateObjects", "candidateRelations", "candidateFunctions", "nextSteps"]
    }
  ]
}
```

## 可省略阶段

- 仅需要解释模型时，可以在 S3 后结束。
- 仅需要查询数据时，可以执行 S4 后结束。
- 仅需要函数发现时，可以执行 S5 后结束。
- 需要完整业务闭环时，按 S1 到 S7 执行。

## 约束

- 默认流程可以被业务 Skill 改写，但不能跳过检查点。
- 上层业务 Skill 注入的 knowledge 只能作为规划依据，不能替代平台实际检索结果。
- 如果业务 Skill 已提供步骤，仍必须检查步骤契约和绑定关系。
