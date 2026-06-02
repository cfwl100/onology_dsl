# Function 调用

## 本层职责
1. 根据已知的 functionId 获取该 function 的入参规格
2. 判断是否还缺参数；如果缺，明确返回缺失项
3. 参数齐全后调用 function 并返回结果

## 前置条件
**functionId 是必须已知的输入**
- 如果没有收到 functionId，直接返回错误：`"缺少必需的 functionId，请先通过子图检索或其他方式获取要调用的函数ID"`
- 不要自行编造 functionId

## 脚本顺序
1. 先运行 `python scripts/get_function_params_spec.py --function-id <functionId>`，获取函数元数据
2. 解析返回的简化元数据，确认参数要求
3. 根据 inputs 数组组装参数，**必须满足 required=true 的必填参数**
4. 参数完整后运行 `python scripts/get_function_result.py --function-id <functionId> --params '<json_string>'`

### 调用示例
```bash
# 获取函数参数规格
python scripts/get_function_params_spec.py --function-id "dtmi:test:test:8888"

# 调用函数
python scripts/get_function_result.py --function-id "dtmi:test:test:8888" --params '{"param1": "value1"}'
```

## 简化元数据格式说明

`get_function_params_spec` 返回简化后的 JSON，结构如下：

```json
{
  "id": "函数ID",
  "name": "函数名称",
  "display": {"en": "显示名称", "zh": "中文显示名"},
  "description": {"en": "英文描述", "zh": "中文描述"},
  "status": "active",
  "inputs": [
    {
      "name": "参数名",
      "description": {"en": "...", "zh": "..."},
      "type": "str|int|list|dict",
      "required": true|false,
      "position": 0
    }
  ],
  "outputs": {
    "name": "输出参数名",
    "description": {"en": "...", "zh": "..."},
    "type": "str|int|list|dict"
  }
}
```

### 关键字段解读
- **inputs**: 入参数组，每个元素包含：
  - `name`: 参数名称
  - `description`: 参数描述（包含中文说明）
  - `type`: 参数类型 (str, int, list, dict)
  - `required`: 是否必填
  - `position`: 参数顺序
- **outputs**: 出参描述，包含输出结构说明

## 参数组装规则
1. 遍历 inputs 数组，找出 required=true 的必填参数
2. 从当前对话上下文和已有信息中查找这些参数的值
3. 如果缺少必填参数，返回错误信息，格式：`"缺少必需的参数: xxx（类型: yyy），请在上下文中补充或说明如何获取"`
4. 可选参数（required=false）可以不传或使用默认值
5. 参数类型必须匹配：str 传字符串，int 传数字，list 传列表，dict 传字典

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
  "params": {
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