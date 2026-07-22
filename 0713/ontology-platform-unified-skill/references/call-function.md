# Function 调用

根据子图函数候选，获取参数规格、组装参数、调用函数、返回结果。只做"函数选择 + 参数规格 + 参数组装 + 调用"，不做子图检索、不生成 OQL、不与数据访问混在同一步。

## 输入来源
- OAG 子图 `result.functions`；或业务 Skill 明确注入的函数目标。
- 公共 `本体ID`；若候选返回更精确 `properties.ontologyId`，以候选为准。
- 参数值来自用户问题/OAC 结果/业务知识/上游步骤。
- 业务定制 S5/S6 规则优先级最高，可覆盖默认策略，但不能跳过 `get_params_spec`、不能凭空制造函数事实。

## 子图返回的 functions 结构
```json
{
  "id": "<function_id>", "label": "function",
  "properties": {
    "qualifiedName": "<限定名>", "description": "{\"zh\":\"<描述>\"}",
    "ontologyId": "<id>", "id": "<function_id>", "name": "<名>", "status": "ACTIVE",
    "inputParams": "<JSON 字符串，参数定义>"
  }
}
```

## 函数选择
遍历 `result.functions`，按 `properties.description` 中文描述与业务目标匹配；业务定制指定规则时优先用业务规则；选中后提取 `properties.ontologyId`→`ontology_id`、`properties.id`→`function_id`。候选不足或描述不匹配返回"未发现可用函数"，不编造。

## 固定调用流程
1. 按 `description` 选目标函数，提取 `ontologyId`/`id`。
2. `python scripts/get_function_params_spec.py --ontology-id <ontology_id> --function-id <function_id>` 取元数据，解析 `physicalName`。
3. 基于用户/业务/OAC/上游结果组装 `params`。
4. `python scripts/get_function_result.py --physicalName <physicalName> --function-id <function_id> --params '<json>'` 执行。

> 统一用 `physicalName`（与 API 字段一致），禁用 `physical_name`/`physical`/自行拼接。

## 参数组装
- 必填参数须来自用户/业务注入/OAC 结果/默认值；可选无上下文值但有默认值可用默认值。
- 类型须匹配：`str`/`int`/`bool`/`list`/`dict`/自定义对象；自定义对象需先 OAC 查全字段再组装，不凭空构造。
- 缺必填参数返回缺失项，不调用。

## 错误处理
`result.functions` 为空→不调用；描述不匹配→候选不足不编造；`get_params_spec` 失败/`physicalName` 缺失→停止执行；参数校验失败→指出缺失/类型不符；`call_function` 失败→保留真实错误。不把 Function 调用当 OAC 查询；不忽略能直接满足目标的候选函数。

## 元数据要求
`get_params_spec` 须含 `physicalName`，缺失则返回 `MISSING_FUNCTION_PARAM_SPEC` 不继续调用。

## 输出
区分：函数选择（id/name/ontologyId/依据）、参数规格（physicalName/required/optional）、参数组装（params/来源/缺失）、调用状态（是否调用/方式/失败原因）、函数结果（原始/摘要/错误），保留平台真实返回不编造。
