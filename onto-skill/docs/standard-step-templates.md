# Onto-skill 使用说明与标准步骤模板

本文档说明业务 Skill、Planning Skill 和 Platform Skill 如何按最新实现协同工作，并给出 S1-S6 标准步骤模板。业务 Skill 只需要提供业务增量，Planning 层直接读取 6 行输入并执行标准步骤。

## 1. 使用流程总览

```text
业务 Skill 输出 6 行输入
  -> Planning Skill 生成 executionPlan
  -> S1 子图检索
  -> S2 基于子图任务规划
  -> S3 OAC 数据访问
  -> 可选 S4/S5 Function
  -> S6 汇总
```

默认流程：

```text
S1 -> S2 -> S3 -> S6
```

Function 流程示例：

```text
S1 -> S2 -> S4 -> S5 -> S3 -> S6
```

## 2. 业务 Skill 使用说明

业务 Skill 只输出 6 行：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<本次执行需要的场景知识、业务规则、子图检索规则、任务规划规则、查询规则、Function 规则、返回要求和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖项；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

业务 Skill 不需要展开本文件的标准模板全文，只需要在 `步骤级定制` 中写业务增量。

## 3. 标准步骤索引

| 步骤 | 名称 | actionType | 标准输出 |
|---|---|---|---|
| S1 | 子图检索 | OAG | subgraphOutput |
| S2 | 基于子图任务规划 | SUBGRAPH_PLAN | plannedTasks |
| S3 | OAC 数据访问 | OAC | objectStructure |
| S4 | Function 发现 | FUNCTION_DISCOVERY | functionSelection |
| S5 | Function 执行 | FUNCTION_CALL | functionOutput |
| S6 | 汇总 | SUMMARY | finalAnswer |

## 4. S1 子图检索模板

### 输入

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<对象、字段、关系、函数候选规则>
步骤级定制：<S1 子图检索业务增量；没有则使用默认模板>
```

### 输出

```text
subgraphOutput:
- subgraphRawResult：OAG 原始结果引用
- objectCandidates：对象候选摘要
- propertyOwnership：字段归属摘要
- relationCandidates：关系候选摘要
- functionCandidates：函数候选摘要
- missingOrConflict：缺失或冲突项
```

### 失败策略

- 子图为空时，按业务失败策略处理。
- 对象、字段、关系缺失时，返回缺失项，不编造。
- 多方向场景建议分方向独立检索。

## 5. S2 基于子图任务规划模板

### 输入

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<路径规则、对象选择规则、查询类型规则、Function 前后置规则>
本体子图结果：<S1.subgraphOutput 引用>
步骤级定制：<S2 任务规划业务增量；没有则使用默认模板>
```

### 输出

```text
plannedTasks:
- taskId
- taskType：OAC_QUERY / ASSOCIATION_QUERY / AGGREGATE_QUERY / FUNCTION_CALL / MIXED
- operationType：QUERY / ASSOCIATION_QUERY / AGGREGATE / FUNCTION
- objectPlan：对象和 alias 计划
- relationPathPlan：关系路径计划
- filterPlan：过滤条件计划
- returnPlan：返回字段计划
- dependsOn：依赖的上游任务
- failurePolicy
```

### 失败策略

- 无法从子图得到合法对象或关系时，停止依赖步骤。
- 多路径均可用时，按业务规则优先级选择。
- S2 输出是 S3/S4/S5 的任务计划输入。

## 6. S3 OAC 数据访问模板

### 输入

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<过滤、返回、聚合、空结果和失败处理规则>
步骤级定制：<S3 OAC 数据访问业务增量；没有则使用默认模板>
操作类型：<来自 S2.plannedTasks.operationType>
查询对象：<来自 S2.plannedTasks.objectPlan>
关系路径：<来自 S2.plannedTasks.relationPathPlan；仅关系查询需要>
过滤条件：<来自 S2.plannedTasks.filterPlan>
返回要求：<来自 S2.plannedTasks.returnPlan>
```

### 输出

```json
{
  "objects": [],
  "relationships": []
}
```

### OQL 生成与执行规则

- OQL 必须先通过 validator 校验，再按需执行。
- 复杂 OQL、长数组、跨 Shell 场景优先写入 UTF-8 JSON 文件，并使用 `--input <json文件>`。
- 短小 JSON 且确认引号安全时，才使用 `--oac-json`。
- 校验和执行应复用同一个 JSON 文件，避免二次复制导致引号损坏。
- 真实执行前必须检查服务环境变量是否齐全。
- 空结果是有效结果时，不自动放宽条件、不换路径、不重试。

### 返回字段通配规则

OQL `returns.kind=FIELDS.fields` 支持 `fields: ["*"]`，表示返回该对象或关系 alias 的全部字段。

该通配只允许出现在返回字段中，不允许用于过滤条件、排序字段或表达式字段。

关系查询中，`ref` 可以引用对象 alias，也可以引用关系 alias。

## 7. S4 Function 发现模板

### 输入

```text
本体ID：<公共本体ID>
业务意图：<为什么需要函数能力>
业务领域知识：<Function 选择规则、优先级、输入输出要求>
步骤级定制：<S4 Function 发现业务增量；没有则使用默认模板>
函数来源：<OAG result.functions 或业务规则指定目标>
```

### 输出

```text
functionSelection:
- selectedFunctionId
- selectedOntologyId
- selectedPhysicalNameCandidate
- selectionBasis
- missingOrConflict
```

### 失败策略

- 没有函数候选时，返回缺失项，不进入 S5。
- 多个候选无法判定时，返回歧义项。

## 8. S5 Function 执行模板

### 输入

```text
functionSelection：<S4 输出引用>
参数规格：<参数规格查询结果>
上下文参数：<变量、OAC 结果或上游步骤输出引用>
参数缺失策略：<来自业务规则或默认 missing>
```

### 输出

```text
functionOutput:
- functionId
- physicalName
- params
- callStatus
- rawResult
- missingOrConflict
```

### 失败策略

- 未获取参数规格时，不调用函数。
- 缺少必填参数时，不猜测参数。
- 未解析到 physicalName 时，不调用函数。

## 9. S6 汇总模板

### 输入

```text
业务意图：<详细自然语言问题>
业务领域知识：<最终结论、证据组织、空结果解释、失败解释规则>
步骤级定制：<S6 汇总业务增量；没有则使用默认模板>
输入来源：<上游步骤摘要、objectStructure、functionOutput、missingOrConflict>
```

### 输出

```text
finalAnswer:
- answer：最终业务结论
- evidence：支撑证据摘要
- dataSummary：数据摘要
- missingInfo：缺失信息
- failureReason：失败原因；无失败则为空
```

### 失败策略

- S6 不重新执行上游步骤。
- S6 不重新展开长列表。
- S6 不把 OQL、validation、operationDecision 混入最终对象结构。

## 10. 跨 Shell 命令使用说明

Skill 生成命令时遵循最低风险原则：默认不输出链式命令。

推荐方式：使用绝对脚本路径或分行命令。

Windows 路径示例：

```powershell
python "C:\Users\<user>\.config\opencode\skills\Ontology-platform-unified-skill\scripts\validate_oql.py" --input "C:\Users\<user>\query.json"
```

切目录时分行：

```powershell
Set-Location "C:\Users\<user>\.config\opencode\skills\Ontology-platform-unified-skill"
python .\scripts\validate_oql.py --input "C:\Users\<user>\query.json"
```

Linux / macOS / WSL 示例：

```bash
python "/home/<user>/.config/opencode/skills/Ontology-platform-unified-skill/scripts/validate_oql.py" --input "/home/<user>/query.json"
```

只有用户明确说明当前 Shell 支持链式命令并要求使用时，才使用对应连接符。

## 11. 常见错误与处理

| 错误 | 原因 | 处理 |
|---|---|---|
| `&&` 不是有效语句分隔符 | Windows PowerShell 5.1 不支持该写法 | 使用绝对脚本路径或分行命令 |
| JSON parse error | 长 JSON 被 Shell 引号处理破坏 | 使用 `--input <json文件>` |
| OQL schema error | 字段、返回结构或类型不符合 schema | 对照 operation schema 修正 |
| ENV missing | 真实服务环境变量缺失 | 配置服务环境变量后再执行 |

## 12. 使用建议

- 业务 Skill 只写业务知识和 6 行输入，不复制标准步骤全文。
- Planning Skill 直接消费 6 行输入，不重复构造映射对象。
- Platform Skill 负责执行细节和校验。
- 复杂 OQL 一律优先文件输入。
- 失败时保留缺失项和失败原因，不编造成功结果。