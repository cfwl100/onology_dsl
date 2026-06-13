# Function 调用

## 本层职责
1. 根据已知的 functionId 和 ontologyId 获取该 function 的入参规格
2. 判断是否还缺参数；如果缺，明确返回缺失项
3. 参数齐全后调用 function 并返回结果

## 前置条件
**functionId 和 ontologyId 是必须已知的输入**
- 如果没有收到 functionId，直接返回错误：`"缺少必需的 functionId，请先通过子图检索或其他方式获取要调用的函数ID"`
- 如果没有收到 ontologyId，直接返回错误：`"缺少必需的 ontologyId，请从子图检索结果中获取"`
- ontologyId 和 functionId 都来自子图检索结果的 `result.functions` 数组
- 不要自行编造 functionId 或 ontologyId

## 子图检索返回的 functions 结构

子图检索返回结果中的 `result.functions` 数组包含所有候选函数，结构如下：

```json
{
  "id": "<function_id>",
  "label": "function",
  "properties": {
    "qualifiedName": "<函数限定名>",
    "display": "{\"en\":\"<英文显示名>\"}",
    "description": "{\"zh\":\"<函数功能描述>\"}",
    "ontologyId": "<ontology_id>",
    "id": "<function_id>",
    "name": "<函数名>",
    "status": "ACTIVE",
    "inputParams": "<JSON字符串，包含参数定义>",
    ...
  }
}
```

**函数选择策略**：
1. 遍历 `result.functions` 数组
2. 重点关注每个函数的 `properties.description` 字段中文描述
3. 根据业务需求判断哪个函数最适合
4. **选择后必须从选中函数的 `properties` 中提取这两个关键参数**：
   - `properties.ontologyId` → 作为 `ontology_id`
   - `properties.id` → 作为 `function_id`

## 脚本顺序
1. 从子图检索返回的 `result.functions` 数组中选择目标函数，提取 `properties.ontologyId` 和 `properties.id`
2. 运行 `python scripts/get_function_params_spec.py --ontology-id <ontologyId> --function-id <functionId>`，获取函数元数据
3. 解析返回的简化元数据，确认参数要求
4. **从返回的简化元数据中提取 physicalName 字段**，这是下一步调用所必需的
5. 根据 inputs 数组组装参数，**必须满足 required=true 的必填参数**
6. 参数完整后运行 `python scripts/get_function_result.py --physicalName <physicalName> --function-id <functionId> --args '<json_string>'`

## 命令格式

```bash
# 获取函数参数规格
python scripts/get_function_params_spec.py --ontology-id <ontologyId> --function-id <functionId>

# 调用函数
python scripts/get_function_result.py --physicalName <physicalName> --function-id <functionId> --args '<json_string>'
```

## 简化元数据格式说明

`get_function_params_spec` 返回简化后的 JSON，结构如下：

```json
{
  "id": "<函数ID>",
  "name": "<函数名称>",
  "physicalName": "<物理名称，用于API调用>",
  "display": {"en": "显示名称"},
  "description": {"zh": "中文描述"},
  "status": "active",
  "inputs": [
    {
      "name": "<参数名>",
      "description": {"en": "...", "zh": "..."},
      "display": "<显示名称>",
      "type": "<类型>",
      "elementType": "<元素类型（仅 list 类型有）>",
      "required": true|false,
      "defaultValue": "<默认值>",
      "position": 0
    }
  ],
  "outputs": {
    "name": "<输出参数名>",
    "description": {"en": "...", "zh": "..."},
    "type": "<类型>"
  }
}
```

### 关键字段解读
- **id**: 函数ID
- **name**: 函数名称
- **physicalName**: 物理名称，用于 API 调用路径中，**必须从元数据中提取并传递给 get_function_result**
- **display**: 显示名称（多语言）
- **description**: 函数描述（多语言）
- **inputs**: 入参数组

## 参数组装规则

**args 参数由大模型根据 inputs 定义和对话上下文自行组装**

### inputs 数组字段说明

每个输入参数的结构如下：

```json
{
  "name": "<参数名>",
  "description": "<参数描述>",
  "display": "<显示名称>",
  "type": "<类型>",
  "elementType": "<元素类型（仅 list 类型有）>",
  "required": true|false,
  "defaultValue": "<默认值>",
  "position": 0
}
```

- **type** 可能的值：`str`, `int`, `bool`, `list`, `dict`, 或**自定义对象类型**（如 `Person`）
- **elementType**：仅当 type 为 `list` 时存在，表示列表元素的类型（如 `str` 表示 `list[str]`）
- **defaultValue**：如果参数没有提供值且有默认值，可直接使用默认值

### 组装步骤

1. **遍历 inputs 数组，找出 required=true 的必填参数**
2. **从当前对话上下文和已有信息中查找这些参数的值**
3. **如果缺少必填参数，返回错误信息**：
   ```
   "缺少必需的参数: xxx（类型: yyy），请在上下文中补充或说明如何获取"
   ```
4. **可选参数（required=false）的处理**：
   - 如果上下文中没有提供值但有 `defaultValue`，使用默认值
   - 如果没有默认值，可以不传
5. **参数类型必须匹配**：
   - `str` → 传字符串
   - `int` → 传数字
   - `bool` → 传布尔值
   - `list` → 传列表，注意参考 `elementType` 确定元素类型
   - `dict` 或**自定义对象类型** → 传对象（见下文）

### 自定义对象类型的处理

如果 `type` 是自定义对象类型（如 `Person`），需要**先查询该对象的完整字段结构**，再组装参数：

1. 调用数据查询能力获取对象的所有属性：
   ```
   查数据：查询Person的*
   ```
2. 根据返回的属性结构，组装完整的对象参数

**示例**：

假设 `Person` 是自定义类型，inputs 定义为：
```json
{
  "name": "person",
  "type": "Person",
  "required": true
}
```

则需要先查询 Person 的所有字段，再组装：
```json
{
  "person": {
    "name": "<姓名>",
    "age": <年龄>,
    "address": "<地址>"
  }
}
```

### 组装后的 args 示例

```json
{
  "start_time": "2026-01-26 14:40:00",
  "alarm_list": ["告警1", "告警2"],
  "person": {
    "name": "张三",
    "age": 30
  }
}
```

## 输出理解
`get_function_result` 返回的结果符合 outputs 中定义的格式：
- 成功时返回 `{"resultCode": "200", "resultMessage": "success", "result": {...}}`
- 失败时返回错误信息，需要根据错误提示调整参数后重试

## 错误处理
1. **脚本调用失败**: 保留真实错误信息，直接返回
2. **参数校验失败**: 明确指出哪个参数校验失败及原因
3. **重试**: 脚本内部已实现自动重试（3次，间隔1秒），如果仍然失败，返回最终错误
4. **不要编造成功结果**: 任何失败都必须如实返回
5. **网络异常、超时等错误**: 返回最终错误信息，由上层流程决定后续处理

## 本层边界
- 未知 functionId 时，不尝试调用，直接返回需要补充信息
- 未知参数规格时，不直接调用 function
- 不凭空编造参数名、参数类型或默认值
- 不把 function 调用和数据访问结构混在一个步骤里

## 完整调用流程示例
 
### Step 1: 获取函数规格
 
输入：
```json
{
  "function_id": "dtmi:com:huawei:ict:function:getCongestedAlarms:89676d70-8fdb-4c86-8778-822e3cca14d1"
}
```
 
输出：简化后的元数据
 
### Step 2: 组装参数
 
根据元数据中的 inputs：
- alarm_list (required=true, type=list)
- time_window (required=true, type=str)
- start_time (required=true, type=str)
 
从上下文获取参数值后组装：
```json
{
  "start_time": "2026-01-26 14:40:00",
  "alarm_list": ["Ethernet Physical (ETPI) Receive bandwidth usage rate threshold crossed"],
  "time_window": "3600000"
}
```
 
### Step 3: 调用函数
 
输入：
```json
{
  "function_id": "dtmi:com:huawei:ict:function:getCongestedAlarms:89676d70-8fdb-4c86-8778-822e3cca14d1",
  "args": {
    "start_time": "2026-01-26 14:40:00",
    "alarm_list": ["Ethernet Physical (ETPI) Receive bandwidth usage rate threshold crossed"],
    "time_window": "3600000"
  }
}
```
 
输出：函数执行结果
 
成功响应：
```json
{
  "resultCode": "200",
  "resultMessage": "success",
  "result": {
    "getCongestedAlarms_output": [
      {
        "alarmname": "Ethernet Physical (ETPI) Receive bandwidth usage rate threshold crossed",
        "firstoccurrence": "2026-01-26T14:40:00Z",
        "lastoccurrence": "2026-01-26T14:45:00Z",
        "sitename": "Beijing-DC1",
        "measure": "bandwidth_usage",
        "node": "router-01",
        "destinationport": "GigabitEthernet0/0/1",
        "standardalarmseverity": "critical",
        "identifier": "alarm-12345",
        "sourceid": "src-001"
      }
    ]
  }
}
```
 
失败响应（参数校验失败）：
```json
{
  "resultCode": "400",
  "resultMessage": "Parameter validation failed: missing required parameter 'start_time'",
  "result": null
}
```
 
失败响应（脚本调用失败）：
```json
{
  "error": true,
  "exception_type": "ConnectionError",
  "message": "Failed to connect to function service"
}
```