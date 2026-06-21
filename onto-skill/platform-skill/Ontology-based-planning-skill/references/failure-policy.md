# 失败策略

本文件定义默认本体子图规划层的失败、缺失信息、定制冲突和空结果处理规则。

## 失败类型

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

## 结构化错误格式

```json
{
  "success": false,
  "error": {
    "code": "MISSING_STEP_INPUT",
    "message": "当前步骤缺少执行所需输入。",
    "missing": ["schemaRef", "queryObject"],
    "stepId": "S4_query_data"
  }
}
```

## 定制冲突输出格式

```json
{
  "success": false,
  "error": {
    "code": "CUSTOMIZATION_CONFLICT",
    "message": "业务 Skill 注入变量与用户显式输入冲突。",
    "conflicts": [
      {
        "field": "alarmName",
        "userValue": "A",
        "injectedValue": "B"
      }
    ]
  }
}
```

## 处理原则

- 不把空结果当失败。
- 不因空结果自动改变条件重试。
- 不用猜测值补全缺失字段。
- 不把业务知识当成平台实际查询结果。
- 不把上一步返回值改造成字段名、关系名或函数名。
- 用户显式输入优先于业务 Skill 注入变量。
- 用户明确要求继续时，也必须说明风险和缺失项。
