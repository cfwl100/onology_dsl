# Function 调用

## 1. 本层职责

Function 模块负责根据本体子图返回的函数候选，获取函数参数规格、组装参数、调用函数并返回结果。

它只负责“函数选择 + 参数规格确认 + 参数组装 + 函数调用”。它不负责本体子图检索，不负责生成 OQL，不负责把函数调用和数据访问混在一个步骤里。

## 2. 输入来源和优先级

Function 输入可以来自：

- OAG 子图检索结果中的 `result.functions`。
- 业务 Skill 明确注入的函数目标或函数调用规则。
- 用户问题、OAC 查询结果、业务变量或上游步骤结果中的参数值。
- 公共 `本体ID`；如果函数候选返回更精确的 `properties.ontologyId`，以函数候选为准。

业务定制文件中的 S5/S6 Function 规则优先级最高，可覆盖本文件中的默认函数选择策略、输入模板、参数组装规则、输出要求和失败策略。

但业务定制不能凭空制造函数事实：可调用函数必须来自 OAG `result.functions` 或可信业务注入，参数规格必须来自 `get_params_spec`，执行必须使用 `physicalName`。

## 3. 面向自然语言的输入模板

Planning 层委托 Function 模块时默认使用以下模板；如果业务定制文件提供了 S5/S6 Function 模板，以业务定制文件为准。

```text
调用function。
本体ID：<公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么需要函数能力，要解决什么问题>
函数来源：<来自 OAG result.functions，或上层业务 Skill 明确注入的函数目标>
functionId：<函数ID；发现阶段未知时说明需要从候选函数中选择>
函数选择依据：<使用 description、name、业务规则或上层知识说明选择原因；可由业务定制文件覆盖>
上下文参数：<来自用户、OAC 结果、业务知识或上游步骤的参数值>
参数缺失策略：<缺少参数时停止并返回 missing，不得猜测；可由业务定制文件覆盖>
输出要求：<需要返回函数结果、参数绑定、未执行原因或业务解释；可由业务定制文件覆盖>
期望输出：返回函数选择结果、参数规格、参数组装结果、调用状态、函数原始结果或缺失项。
```

最小输入应包含：

```text
本体ID：<公共本体ID或函数候选本体ID>
业务意图：<调用函数的目标>
函数来源：<OAG result.functions 或可信业务注入>
上下文参数：<可用于组装函数参数的信息>
```

## 4. 子图检索返回的 functions 结构

子图检索返回结果中的 `result.functions` 数组包含候选函数，典型结构如下：

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
3. 业务定制文件明确指定函数选择规则时，优先使用业务规则进行候选匹配。
4. 选择后必须从选中函数的 `properties` 中提取：
   - `properties.ontologyId` → `ontology_id`
   - `properties.id` → `function_id`
5. 如果候选函数没有更精确的 `properties.ontologyId`，可使用自然语言输入中的公共 `本体ID`。
6. 如果候选函数不足或描述不匹配，返回“未发现可用函数”，不得编造。

## 5. 固定调用流程

Function 调用必须按以下顺序执行：

1. 根据子图检索结果的 `result.functions` 数组中各函数的 `description` 字段选择目标函数。
2. 提取选中函数的 `properties.ontologyId` 和 `properties.id` 作为 `get_params_spec` 的入参。
3. 调用 `get_params_spec(ontology_id, function_id)` 获取函数元数据。
4. 解析元数据中的 `physicalName`。
5. 基于用户问题、业务知识、OAC 结果或上游步骤结果组装 `params`。
6. 调用 `call_function(physicalName, function_id, params)` 执行函数。

注意：统一使用 `physicalName`，与 API 返回字段名保持一致。不得使用 `physical_name`、`physical` 或自行拼接的函数物理名替代。

## 6. 函数元数据要求

`get_params_spec` 返回的函数元数据至少需要包含：

```json
{
  "id": "<函数ID>",
  "name": "<函数名称>",
  "physicalName": "<物理名称>",
  "description": {"zh": "<中文描述>"},
  "inputs": [
    {
      "name": "<参数名>",
      "type": "<类型>",
      "required": true,
      "defaultValue": "<默认值>"
    }
  ],
  "outputs": {
    "name": "<输出参数名>",
    "type": "<类型>"
  }
}
```

如果 `physicalName` 缺失，必须返回 `MISSING_FUNCTION_PARAM_SPEC`，不得继续调用。

## 7. 输出格式

Function 输出必须区分“函数选择、参数规格、参数组装、调用状态、函数结果”。推荐输出：

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
- params：...
- 参数来源：用户问题 / OAC 结果 / 业务变量 / 默认值
- 缺失参数：...

### 4. 调用状态
- 是否调用：是/否
- 调用方式：call_function(physicalName, function_id, params)
- 失败原因：...

### 5. 函数结果
- 原始结果：...
- 结果摘要：...
- 错误信息：...
```

成功响应和失败响应必须保留平台真实返回，不得编造。

## 8. 参数组装规则

- 必填参数必须从用户问题、业务 Skill 注入、OAC 查询结果或函数默认值中获得。
- 可选参数如果没有上下文值但有默认值，可以使用默认值。
- 参数类型必须匹配：`str`、`int`、`bool`、`list`、`dict` 或自定义对象类型。
- 自定义对象类型需要先通过 OAC 查询对象完整字段后再组装，不得凭空构造。
- 缺少必填参数时返回缺失项，不调用函数。
- 业务定制文件可以覆盖参数来源优先级和缺参策略，但不能跳过 `get_params_spec`。

## 9. 错误处理

1. `result.functions` 为空：不调用函数，返回“未发现函数候选”。
2. 函数描述不匹配：返回候选不足，不编造。
3. `get_params_spec` 失败：保留真实错误。
4. `physicalName` 缺失：停止执行。
5. 参数校验失败：指出哪个参数缺失或类型不匹配。
6. `call_function` 失败：保留平台真实错误。
7. 不要把 Function 调用和 OAC 数据访问混在同一步里。

## 10. 本层边界

- 未知 `functionId` 时，不尝试调用。
- 未知参数规格时，不调用函数。
- 不编造参数名、参数类型、默认值或成功结果。
- 不把 Function 调用当成 OAC 查询。
- 不忽略 `result.functions` 中能直接满足业务目标的函数能力。
