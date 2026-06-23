# Ontology-based-planning-skill 对外输入接口

本文档定义业务定制 Skill 调用 `Ontology-based-planning-skill` 时使用的对外输入格式。目标是让业务侧使用自然语言格式化约束，而不是构造复杂 JSON、嵌套 stepContracts 或重复展开标准步骤模板。

## 1. 顶层输入模板

业务定制 Skill 只需要按如下 7 行组织输入：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
已读取业务定制文件：<knowledge / rules / templates 文件路径；必填>
业务定制文件内容：<业务文件原文或完整摘录>
流程级定制：<执行步骤、顺序、跳过、追加>
步骤级定制：<S2/S3/S4/S5/S6/S7 的 stepTemplateRef、contractRef、变量引用、业务增量规则和失败策略>
缺失信息：<没有则写无>
```

## 2. 每行填写规范

### 2.1 本体ID

格式：

```text
本体ID：<公共本体ID>
```

要求：

- 只填写一个对外公共本体ID。
- 不要求业务侧同时填写 `ontologyId` 和 `schemaRef`。
- Planning 层会将公共本体ID传递给 OAG、OAC 和 Function。

### 2.2 业务意图

格式：

```text
业务意图：<详细自然语言问题>
```

要求：

- 填写改写后的详细自然语言任务。
- 不要只填写短意图标签。
- 长列表只写变量引用，例如 `${alarmNames_same_site}`，不要重复粘贴完整列表。

### 2.3 已读取业务定制文件

格式：

```text
已读取业务定制文件：<knowledge / rules / templates 文件路径；必填>
```

要求：

- 必须列出已经读取的业务定制文件路径。
- 如果业务定制文件没有读取成功，必须在“缺失信息”中说明。
- 该行只写路径，不复制文件全文。

### 2.4 业务定制文件内容

格式：

```text
业务定制文件内容：<业务文件原文或完整摘录>
```

要求：

- 可以填写业务文件原文，也可以填写足以支撑本次任务的完整摘录。
- 如果文件很长，优先摘录与当前意图相关的章节。
- 不要重复粘贴与当前意图无关的业务规则。

### 2.5 流程级定制

格式：

```text
流程级定制：按照执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function 的格式给出。
```

要求：

- 必须明确执行哪些步骤和步骤顺序。
- 必须明确跳过哪些步骤以及原因。
- 推荐写法如下：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function；每个方向独立执行；S4 空结果视为有效结果，不自动放宽条件重试。
```

其他示例：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S5 -> S6 -> S4 -> S7；Function 用于前置补齐查询参数。
```

```text
流程级定制：只执行 S1 -> S2 -> S3；不执行 S4/S5/S6/S7；仅输出子图规划结果。
```

### 2.6 步骤级定制

格式：

```text
步骤级定制：按照“标准步骤模板 + 业务增量规则 + 变量引用 + 失败策略”的自然语言格式给出。
```

要求：

- 子图检索、基于子图的任务规划、OAC查询、Function查询等 step 的标准输入和标准输出，统一来自标准步骤模板库 `standard-step-templates.md`。
- 业务侧不要复制标准模板全文。
- 业务侧只需要说明每个步骤使用哪个标准模板、哪个业务增量规则、哪些变量，以及失败策略。
- 推荐写法如下：

```text
步骤级定制：
S2 子图检索：使用标准模板 standard.S2.oag，业务规则使用 evidence.same_site.S2.subgraph，变量使用 neName_same_site、alarmNames_same_site、returnFields_ne、returnFields_alarm、messageType_same_site；输出 subgraphOutput；子图为空则停止后续步骤。
S3 基于子图规划：使用标准模板 standard.S3.subgraphPlan，业务规则使用 evidence.same_site.S3.plan，输入使用 S2.subgraphOutput、变量区和 same_site 方向计划；输出 plannedTasks；不能规划合法路径则停止 S4。
S4 OAC查询：使用标准模板 standard.S4.oac，业务规则使用 evidence.same_site.S4.oac，输入使用变量区、S2.subgraphOutput 和 S3.plannedTasks；输出 objects 与 relationships；空结果是有效结果，不自动重试。
S7 汇总：使用标准模板 standard.S7.summary，业务规则使用 evidence.same_site.S7.summary，输入使用上游结果摘要；输出最终业务结论。
```

如果需要 Function：

```text
S5 Function发现：使用标准模板 standard.S5.functionDiscovery，业务规则使用 <业务文件中的函数选择规则>，输出 functionSelection。
S6 Function执行：使用标准模板 standard.S6.functionCall，业务规则使用 <业务文件中的参数组装规则>，输入使用 functionSelection 和变量区，输出 functionOutput。
```

### 2.7 缺失信息

格式：

```text
缺失信息：<没有则写无>
```

要求：

- 没有缺失时固定写“无”。
- 如果缺业务文件、变量、本体ID、方向、对象、字段、关系、函数或参数规格，必须明确列出。
- 缺失信息不能通过猜测补齐。

## 3. 执行侧解析规则

Planning 层收到上述 7 行输入后，按如下方式解析：

1. 读取 `本体ID`、`业务意图`、`业务定制文件内容`。
2. 从 `流程级定制` 中解析步骤顺序、跳过步骤、追加步骤和失败策略。
3. 从 `步骤级定制` 中解析每个步骤的 `stepTemplateRef`、业务规则引用、变量引用、输入来源、输出目标和失败策略。
4. 标准输入输出不从业务文本中复制，而从 `standard-step-templates.md` 查找。
5. 业务规则只作为增量覆盖，不允许编造 OAG/OAC/Function 未返回的平台事实。
6. 默认使用 compact 模式；只有 debug、失败定位或用户明确要求时才展开标准模板全文。

## 4. 与标准步骤模板库的关系

标准模板库路径：

```text
references/standard-step-templates.md
```

模板职责：

- `standard.S2.oag`：定义子图检索标准输入输出。
- `standard.S3.subgraphPlan`：定义基于子图任务规划标准输入输出。
- `standard.S4.oac`：定义 OAC 查询标准输入输出。
- `standard.S5.functionDiscovery`：定义 Function 发现标准输入输出。
- `standard.S6.functionCall`：定义 Function 调用标准输入输出。
- `standard.S7.summary`：定义结果汇总标准输入输出。

业务定制 Skill 只引用这些模板编号，不重复展开模板内容。
