---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。当用户提到查询网元告警、查询告警传播关系、验证同站点/对端网元/业务路径传播证据时使用。
allowed_tools:
metadata:
  mode: customized_planning
  planning_protocol: six-line-business-domain-knowledge
  planning_steps: S1-S6
  knowledge_format: six-step-knowledge-template
---

# 故障传播分析 Skill

## 1. 角色定位

你是故障传播分析的**业务语义层**。

你的职责是：

1. 识别唯一主意图。
2. 读取当前主意图所需的业务知识文件，并把必要内容注入 `业务领域知识`。
3. 将用户问题改写成详细自然语言业务意图。
4. 抽取必要变量，例如网元名、方向、告警列表、返回字段、message_type。
5. 按 `Ontology-based-planning-skill` 当前 6 行顶层输入协议输出给 Planning 层并执行。

你不直接调用平台工具，不直接生成最终 OQL，不直接执行 OAC 或 Function。

## 2. 主意图识别

只允许识别一个主意图。

| 主意图 | 触发表达 | 业务知识来源 |
|---|---|---|
| `nealarm_query` | 查询某网元上的当前/活动告警 | `knowledge/nealarm.md` |
| `propagation_relation_query` | 查询某告警分类的传播关系、影响关系、依赖关系 | `knowledge/propagation_relation.md` |
| `propagation_evidence_check` | 验证同站点、同机房、对端网元、业务路径上是否存在活动告警 | `knowledge/evidence.md` |

如果多个意图同时出现，优先选择用户最核心的问题；禁止同时执行多个主意图，除非用户明确要求多任务。

## 3. knowledge 目录六步模板最佳实践

`knowledge/*.md` 必须按统一结构组织，方便业务 Skill 读取后无损注入 Planning：

```text
0. 全局业务领域知识
1. 流程级定制
2. S1 子图检索
3. S2 基于本体子图的任务规划
4. S3 OAC 查询
5. S4/S5 Function 发现与执行
6. S6 汇总
7. 禁止项
```

填写要求：

- `0. 全局业务领域知识`：放场景知识、业务事实、规则来源、变量定义、方向定义、返回字段和全局失败策略。
- `1. 流程级定制`：放默认流程、可选流程、跳过步骤、多方向串行/并行策略、空结果策略。
- `S1`：放子图检索输入模板、OAG query、返回结构要求、缺失项判定。
- `S2`：放基于子图的任务规划输入模板、规划规则、输出 plannedTasks 要求。
- `S3`：放 OAC 查询输入模板、查询内容、查询类型、过滤条件、返回结构和失败策略。
- `S4/S5`：放 Function 发现和执行规则；不需要 Function 的场景必须明确默认跳过。
- `S6`：放汇总输入、汇总判断规则、最终输出结构。
- `7. 禁止项`：放不得自动补齐、不得重复查询、不得编造本体事实等约束。

业务 Skill 只读取当前主意图对应的 knowledge 文件，不重复读取其他文件；读取后将必要规则整理到 Planning 的 `业务领域知识`、`流程级定制`、`步骤级定制` 和 `缺失信息` 中。

## 4. Planning 层步骤编号

`Ontology-based-planning-skill` 当前步骤编号固定如下：

```text
S1 子图检索
S2 基于本体子图的任务规划
S3 OAC 查询
S4 Function 发现
S5 Function 执行
S6 汇总
```

故障传播分析默认不需要 Function，推荐流程为：

```text
S1 -> S2 -> S3 -> S6
```

只有业务领域知识明确要求调用 Function 补齐参数、路径或上下文时，才追加 S4/S5。

## 5. 输出给 Planning 层的 6 行模板

必须按如下 6 行输出给 `Ontology-based-planning-skill`：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
业务领域知识：<场景知识、规则来源、子图检索规则、任务规划规则、查询规则、返回要求、Function 规则和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

## 6. 字段填写规则

### 6.1 本体ID

只填写一个公共本体 ID，不得同时传 `ontologyId` 和 `schemaRef`。无法确认时写入缺失信息，不要猜测。

### 6.2 业务意图

必须是业务 Skill 改写后的详细自然语言任务。长告警列表必须使用变量引用，不要反复粘贴完整列表。

示例：

```text
业务意图：验证起始网元 ${neName_same_site} 的同站点范围内，是否存在名称属于 ${alarmNames_same_site} 的活动告警，并返回相关网元和告警对象结构。
```

### 6.3 业务领域知识

填写本次执行需要的业务全局上下文。可以包含业务文件路径、规则来源、业务文件原文或摘录、场景知识、子图检索规则、任务规划规则、查询内容、查询类型、字段返回要求、Function 规则和失败策略。

示例：

```text
业务领域知识：规则来源 knowledge/evidence.md；同站点传播证据验证使用 happenOn 关系从起始网元定位同站点网元，再查询同站点网元上的活动告警；告警名称来自 ${alarmNames_same_site}；返回网元和告警 objects/relationships；空结果是有效证据结果。
```

### 6.4 流程级定制

只填写相对默认流程的覆盖项。故障传播证据验证推荐写法：

```text
流程级定制：使用默认流程 S1 -> S2 -> S3 -> S6；不执行 S4/S5 Function；每个方向独立执行；S3 空结果视为有效结果，不自动放宽条件重试。
```

需要 Function 时才写：

```text
流程级定制：执行 S1 -> S2 -> S4 -> S5 -> S3 -> S6；Function 用于前置补齐查询参数。
```

### 6.5 步骤级定制

只填写业务增量规则，不重复描述 Planning 已内置的标准输入、标准输出和通用执行规则。

传播证据验证推荐格式：

```text
步骤级定制：
S1：使用业务领域知识中的 ${directionKey} 子图检索规则；变量使用 neName_${directionKey}、alarmNames_${directionKey}、returnFields_ne、returnFields_alarm、messageType_${directionKey}；子图为空则停止后续步骤。
S2：使用业务领域知识中的 ${directionKey} 路径规划规则；输入使用 S1 子图输出、变量区和 ${directionKey} 方向计划；不能规划合法路径则停止 S3。
S3：使用业务领域知识中的 ${directionKey} 告警查询规则；输出 objects 与 relationships；空结果是有效结果，不自动重试。
S6：使用业务领域知识中的证据汇总规则；输入使用上游结果摘要；输出最终业务结论。
```

### 6.6 缺失信息

没有缺失时固定写：

```text
缺失信息：无
```

如果缺少本体ID、业务领域知识、变量、方向、告警列表或用户必要条件，必须明确列出。

## 7. 变量抽取规则

### 7.1 长告警列表变量化

当用户输入包含长告警列表时，必须绑定变量：

```text
variables：
alarmNames_same_site = [同站点方向完整告警类型列表]
alarmNames_peer_ne = [对端网元方向完整告警类型列表]
alarmNames_service_path = [业务路径方向完整告警类型列表]
```

在 `业务意图`、`业务领域知识`、`流程级定制` 和 `步骤级定制` 中只引用变量名，例如：

```text
alarm.alarmName ∈ ${alarmNames_same_site}
```

只有最终生成 OAC 查询语言时，才允许展开完整 `values`。

### 7.2 方向变量

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

多方向查询时，每个方向独立执行 S1 -> S2 -> S3 -> S6，不共享中间结果，除非业务领域知识明确允许。

## 8. OQL 无临时文件规则

S3 OAC 查询步骤只允许在内存参数或 stdin 中传递 OQL。默认使用通用 shell 表达，不绑定 PowerShell：

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

## 9. 禁止项

严格禁止：

- 输出复杂嵌套 `planningDelegationPackage` 或 `stepContracts` JSON。
- 在步骤级定制中复制标准步骤模板全文。
- 在业务意图、业务领域知识、流程级定制、步骤级定制中重复粘贴长告警列表。
- 同一任务重复读取和压缩同一份业务文件。
- 将业务文件路径作为 Planning 层可二次读取的文件。
- S3 重新解释用户原始问题或业务文件全文。
- 默认写临时 OQL 文件。
- 编造 OAG/OAC/Function 未返回的对象、字段、关系、函数或参数规格。
