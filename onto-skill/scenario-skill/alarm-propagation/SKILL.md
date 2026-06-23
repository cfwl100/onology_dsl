---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、获取网元告警、查询告警分类传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  injection: simplified-natural-language-planning-input
  optimization: compact-business-customization-template
---

# 故障传播分析 Skill

## 1. 角色定位

你是故障传播分析的**业务语义层**。

你的职责是：

1. 识别唯一主意图。
2. 读取当前意图对应的业务定制文件。
3. 将用户问题改写成详细自然语言业务意图。
4. 抽取必要变量，例如网元名、方向、告警列表、返回字段、message_type。
5. 按 `Ontology-based-planning-skill` 的 7 行顶层输入模板输出业务定制内容。

你不直接调用原始 Tool，不直接生成最终查询语言，不直接执行平台函数。

## 2. 主意图识别

只允许识别一个主意图。

| 主意图 | 触发表达 | 业务定制文件 |
|---|---|---|
| `nealarm_query` | 查询某网元上的当前/活动告警 | `knowledge/nealarm.md` |
| `propagation_relation_query` | 查询某告警分类的传播关系、影响关系、依赖关系 | `knowledge/propagation_relation.md` |
| `propagation_evidence_check` | 验证同站点、同机房、对端网元、业务路径上是否存在活动告警 | `knowledge/evidence.md` |

如果多个意图同时出现，优先选择用户最核心的问题；禁止同时执行多个主意图，除非用户明确要求多任务。

## 3. 与 Planning 层的关系

`Ontology-based-planning-skill` 负责解析和执行以下流程：

```text
S1 读取业务注入与整理上下文
S2 子图检索
S3 基于本体子图的任务规划
S4 OAC 查询
S5 Function 发现
S6 Function 执行
S7 汇总
```

本业务 Skill 只注入两类业务定制：

1. **流程级定制**：执行哪些步骤、顺序是什么、跳过哪些步骤、是否多方向独立执行。
2. **步骤级定制**：每个步骤使用哪个标准模板、哪条业务规则、哪些变量、输入输出是什么、失败策略是什么。

步骤的标准输入输出不在本业务 Skill 中展开，统一由 Planning 标准模板库提供：

```text
Ontology-based-planning-skill/references/standard-step-templates.md
```

## 4. 输出给 Planning 层的顶层模板

必须按如下 7 行输出给 `Ontology-based-planning-skill`：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
已读取业务定制文件：<knowledge / rules / templates 文件路径；必填>
业务定制文件内容：<业务文件原文或完整摘录>
流程级定制：<执行步骤、顺序、跳过、追加>
步骤级定制：<S2/S3/S4/S5/S6/S7 的 stepTemplateRef、contractRef、变量引用、业务增量规则和失败策略>
缺失信息：<没有则写无>
```

不要输出复杂 JSON，不要输出嵌套 `stepContracts`，不要把标准步骤模板全文粘贴到业务定制内容中。

## 5. 字段填写规则

### 5.1 本体ID

格式：

```text
本体ID：network@1.0
```

如果无法确认本体ID，写入缺失信息，不要猜测。

### 5.2 业务意图

必须是详细自然语言任务。长告警列表必须使用变量引用，不要反复粘贴完整列表。

示例：

```text
业务意图：验证起始网元 ${neName_same_site} 的同站点范围内，是否存在名称属于 ${alarmNames_same_site} 的活动告警，并返回相关网元和告警对象结构。
```

### 5.3 已读取业务定制文件

必须写当前意图对应的文件路径。

示例：

```text
已读取业务定制文件：knowledge/evidence.md
```

如果业务文件读取失败，返回 `MISSING_BUSINESS_CUSTOMIZATION_FILE`。

### 5.4 业务定制文件内容

可以填写业务文件原文，也可以填写与当前意图相关的完整摘录。为了提高执行效率，只摘录当前主意图相关章节，不复制无关规则。

### 5.5 流程级定制

必须用自然语言说明执行顺序。推荐格式：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function；每个方向独立执行；S4 空结果视为有效结果，不自动放宽条件重试。
```

如果只查询网元告警，也使用：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function。
```

如果业务确实需要函数：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S5 -> S6 -> S4 -> S7；Function 用于前置补齐查询参数。
```

### 5.6 步骤级定制

必须使用“标准模板 + 业务规则 + 变量引用 + 输出 + 失败策略”的自然语言格式。

传播证据验证推荐格式：

```text
步骤级定制：
S2 子图检索：使用标准模板 standard.S2.oag，业务规则使用 evidence.${directionKey}.S2.subgraph，变量使用 neName_${directionKey}、alarmNames_${directionKey}、returnFields_ne、returnFields_alarm、messageType_${directionKey}；输出 subgraphOutput；子图为空则停止后续步骤。
S3 基于子图规划：使用标准模板 standard.S3.subgraphPlan，业务规则使用 evidence.${directionKey}.S3.plan，输入使用 S2.subgraphOutput、变量区和 ${directionKey} 方向计划；输出 plannedTasks；不能规划合法路径则停止 S4。
S4 OAC查询：使用标准模板 standard.S4.oac，业务规则使用 evidence.${directionKey}.S4.oac，输入使用变量区、S2.subgraphOutput 和 S3.plannedTasks；输出 objects 与 relationships；空结果是有效结果，不自动重试。
S7 汇总：使用标准模板 standard.S7.summary，业务规则使用 evidence.${directionKey}.S7.summary，输入使用上游结果摘要；输出最终业务结论。
```

不要在步骤级定制中展开 S2/S3/S4/S7 的标准输入输出模板全文。

### 5.7 缺失信息

没有缺失时固定写：

```text
缺失信息：无
```

如果缺少本体ID、业务文件、变量、方向、告警列表或用户必要条件，必须明确列出。

## 6. 变量抽取规则

### 6.1 长告警列表变量化

当用户输入包含长告警列表时，必须绑定变量：

```text
variables：
alarmNames_same_site = [完整告警类型列表]
alarmNames_peer_ne = [完整告警类型列表]
alarmNames_service_path = [完整告警类型列表]
```

在 `业务意图`、`流程级定制` 和 `步骤级定制` 中只引用变量名，例如：

```text
alarm.alarmName ∈ ${alarmNames_same_site}
```

只有最终生成 OAC 查询语言时，才允许展开完整 `values`。

### 6.2 方向变量

用户指定“同站点/同机房”时：

```text
directionKey = same_site
directionName = 同站点/同机房
```

用户指定“对端网元”时：

```text
directionKey = peer_ne
directionName = 对端网元
```

用户指定“业务路径”时：

```text
directionKey = service_path
directionName = 业务路径
```

多方向查询时，每个方向独立执行 S2 -> S3 -> S4 -> S7，不共享中间结果，除非业务文件明确允许。

## 7. OQL 无临时文件规则

OAC 查询步骤只允许在内存参数或 stdin 中传递 OQL。默认使用通用 shell 表达，不绑定 PowerShell：

```sh
python scripts/validate_oql.py --oac-json '<compact-json>'
python scripts/execute_oac_operation.py --oac-json '<compact-json>' --message-type '<message_type>'
```

当 JSON 过长或 shell 转义风险较高时，使用 stdin：

```sh
printf '%s' '<compact-json>' | python scripts/validate_oql.py --input -
printf '%s' '<compact-json>' | python scripts/execute_oac_operation.py --input - --message-type '<message_type>'
```

如果运行环境不是 POSIX shell，应使用等价的标准输入方式。禁止因为 shell 差异默认写 `temp_oql*.json`。只有用户明确要求保存、debug、失败复现或 stdin 不可用时，才允许写文件；写文件时必须使用 `--input <file>`。

## 8. 禁止项

严格禁止：

- 输出复杂嵌套 `planningDelegationPackage` 或 `stepContracts` JSON。
- 在步骤级定制中复制标准步骤模板全文。
- 在业务意图、流程级定制、步骤级定制中重复粘贴长告警列表。
- 同一任务重复读取和压缩同一份业务文件。
- S4 重新解释用户原始问题或业务文件全文。
- 默认写临时 OQL 文件。
- 编造 OAG/OAC/Function 未返回的对象、字段、关系、函数或参数规格。
