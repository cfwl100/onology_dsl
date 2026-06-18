# 失败策略

本文件定义计划执行层的失败、缺失信息和空结果处理规则。

## 失败类型

| code | 触发场景 | 处理方式 |
|---|---|---|
| `MISSING_PLAN_STEP_FIELD` | 步骤缺少 `stepId`、`actionType`、`input` 或 `expectedOutput` | 停止执行，返回缺失字段。 |
| `MISSING_STEP_INPUT` | 当前步骤输入不足以调用第二层能力 | 停止执行，返回缺失输入。 |
| `INVALID_STEP_BINDING` | 绑定引用不存在的前置输出 | 停止执行，返回绑定失败原因。 |
| `PLATFORM_STEP_FAILED` | 第二层能力返回失败 | 停止执行或按步骤 `failurePolicy` 处理。 |
| `EMPTY_RESULT` | 平台执行成功但结果为空 | 视为有效结果，不自动重试。 |

## 结构化错误格式

```json
{
  "success": false,
  "error": {
    "code": "MISSING_STEP_INPUT",
    "message": "当前步骤缺少执行所需输入。",
    "missing": ["schemaRef", "queryObject"]
  }
}
```

## 处理原则

- 不把空结果当失败。
- 不因空结果自动改变条件重试。
- 不用猜测值补全缺失字段。
- 不把上一步返回值改造成字段名、关系名或函数名。
- 用户明确要求继续时，也必须说明风险和缺失项。
