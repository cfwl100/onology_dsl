# Function 调用

## 本层职责

Function 模块负责根据本体子图返回的函数候选，获取函数参数规格、组装参数、调用函数并返回结果。

它只负责“函数规格确认 + 参数组装 + 函数调用”。它不负责本体子图检索，不负责生成 OQL，不负责把函数调用和数据访问混在一个步骤里。

## 前置条件

`functionId` 和函数所属本体标识是函数调用的必需输入，必须来自本体子图检索结果的 `result.functions`，或由上层业务 Skill 明确给出可信来源。

- 如果没有 `functionId`，直接返回缺失项：`缺少必需的 functionId，请先通过子图检索或业务上下文确认要调用的函数。`
- 如果没有公共 `本体ID` 且函数候选中也没有 `ontologyId`，直接返回缺失项：`缺少必需的本体ID，请从子图检索结果或业务上下文中获取。`
- 不得自行编造 `functionId`、`ontologyId`、参数名、参数类型或默认值。

## 面向自然语言的输入模板

上层业务 Skill 或 Planning 层可以用自然语言委托 Function 模块，不需要直接构造复杂 JSON。推荐模板如下：

```text
请执行本体函数调用。

本体ID：<对外公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么要调用函数，要解决什么问题>
函数来源：<来自 OAG 子图 result.functions，或上层业务 Skill 明确给出的函数候选>
functionId：<函数ID；如果未知，先返回缺失项>
函数选择依据：<为什么选择这个函数，基于 description/name/业务规则>
上下文参数：<用户问题、数据查询结果、业务变量中可用于组装函数参数的信息>
参数缺失策略：<缺少必填参数时返回缺失项，不编造>
输出要求：<希望输出函数原始结果、摘要、错误信息或缺失项>
```

最小输入应包含：

```text
本体ID：<对外公共本体ID或函数候选本体ID>
业务意图：<调用函数的目标>
functionId：<functionId>
上下文参数：<可用于组装函数参数的信息>
```

## 子图检索返回的 functions 结构

子图检索返回结果中的 `result.functions` 数组包含候选函数，常见结构如下：

```json
{
  "id": "<function_id>",
  "label": "function",
  "properties": {
    "qualifiedName": "<函数限定名>",
    "description": "{\"zh\":\"<函数功能描述>\"}",
    "ontologyId": "<ontology_id>",
    "id": "<function_id>",
    "name": "<函数名>",
    "status": "ACTIVE",
    "inputParams": "<JSON字符串，包含参数定义>"
  }
}
```

函数选择策略：

1. 遍历 `result.functions` 数组。
2. 优先根据 `properties.description` 的中文描述与业务目标匹配。
3. 选择后必须从选中函数的 `properties` 中提取：
   - `properties.ontologyId` → `ontology_id`
   - `properties.id` → `function_id`
4. 如果候选函数没有更精确的 `properties.ontologyId`，可使用自然语言输入中的公共 `本体ID`。
5. 如果候选函数不足或描述不匹配，返回“未发现可用函数”，不得编造。

## 输出格式

Function 模块输出必须区分“函数选择、参数规格、参数组装、调用结果”。推荐输出结构：

```text
## Function 输出

### 1. 函数选择
- functionId：...
- ontologyId：...
- functionName：...
- 选择依据：...

### 2. 参数规格
- 是否已获取参数规格：是/否
- physicalName：...
- required 参数：...
- optional 参数：...

### 3. 参数组装
- args：...
- 参数来源：用户问题 / OAC 结果 / 业务变量 / 默认值
- 缺失参数：...

### 4. 调用状态
- 是否调用：是/否
- 调用命令：scripts/get_function_result.py ...
- 失败原因：...

### 5. 函数结果
- 原始结果：...
- 结果摘要：...
- 错误信息：...
```

成功响应通常为：

```json
{
  "resultCode": "200",
  "resultMessage": "success",
  "result": {}
}
```

失败响应必须保留真实错误，例如：

```json
{
  "resultCode": "400",
  "resultMessage": "Parameter validation failed: missing required parameter 'start_time'",
  "result": null
}
```

## 脚本顺序

1. 从子图检索返回的 `result.functions` 中选择目标函数，提取 `ontologyId` 和 `functionId`；如函数候选无 `ontologyId`，使用公共 `本体ID`。
2. 运行：

```bash
python scripts/get_function_params_spec.py --ontology-id <ontologyId> --function-id <functionId>
```

3. 解析返回的简化元数据，确认 `physicalName`、`inputs`、`outputs`。
4. 根据 `inputs` 组装 `args`，必须满足所有 `required=true` 的必填参数。
5. 参数完整后运行：

```bash
python scripts/get_function_result.py --physicalName <physicalName> --function-id <functionId> --args '<json_string>'
```

## 简化元数据格式

`get_function_params_spec` 返回简化 JSON，关键结构如下：

```json
{
  "id": "<函数ID>",
  "name": "<函数名称>",
  "physicalName": "<物理名称>",
  "description": {"zh": "<中文描述>"},
  "status": "active",
  "inputs": [
    {
      "name": "<参数名>",
      "type": "<类型>",
      "required": true,
      "defaultValue": "<默认值>",
      "position": 0
    }
  ],
  "outputs": {
    "name": "<输出参数名>",
    "type": "<类型>"
  }
}
```

## 参数组装规则

- 必填参数必须从用户问题、业务 Skill 注入、OAC 查询结果或函数默认值中获得。
- 可选参数如果没有上下文值但有默认值，可以使用默认值。
- 参数类型必须匹配：`str`、`int`、`bool`、`list`、`dict` 或自定义对象类型。
- 自定义对象类型需要先通过 OAC 查询对象完整字段后再组装，不得凭空构造。
- 缺少必填参数时返回缺失项，不调用函数。

## 错误处理

1. 脚本调用失败：保留真实错误信息。
2. 参数校验失败：指出哪个参数失败及原因。
3. 网络异常或超时：返回最终错误，由上层流程决定是否继续。
4. 不要编造成功结果。
5. 不要在同一步里混合 Function 调用和 OAC 数据访问。

## 本层边界

- 未知 `functionId` 时，不尝试调用。
- 未知参数规格时，不调用函数。
- 不编造参数名、参数类型、默认值或成功结果。
- 不把 Function 调用当成 OAC 查询。
