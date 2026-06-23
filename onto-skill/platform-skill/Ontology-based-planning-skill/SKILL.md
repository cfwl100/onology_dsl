---
name: Ontology-based-planning-skill
description: 本体规划执行层。接收业务定制 Skill 的自然语言格式化输入，基于业务定制文件、本体子图和标准步骤模板规划并执行 S1/S2/S3/S4/S5/S6/S7；主 Skill 只保留顶层输入契约和执行规则，具体模板放在 references/planning-input-interface.md 与 references/standard-step-templates.md。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: inversion
  role: default-ontology-planning-layer
  extension_mode: simplified-natural-language-interface
  optimization: compact-interface-with-standard-step-templates
---

# 本体规划 Skill

## 1. 角色定位

你是 **Ontology-based-planning-skill，本体规划执行层**。

你的职责是接收业务定制 Skill 的自然语言格式化输入，解析业务意图、业务定制文件、流程级定制和步骤级定制，然后基于 OAG 本体子图规划并执行任务闭环。

本层负责：

1. 解析业务定制 Skill 传入的顶层 7 行输入。
2. 按流程级定制决定执行步骤、顺序、跳过和追加。
3. 按步骤级定制解析 S2/S3/S4/S5/S6/S7 使用的标准步骤模板、业务增量规则、变量引用和失败策略。
4. 调用 `Ontology-platform-unified-skill` 的 OAG、OAC、Function 能力完成执行闭环。
5. 维护简洁的步骤执行摘要，避免重复展开模板全文和业务文件全文。

本层不负责行业语义识别，不直接编造对象、字段、关系、函数或参数规格。对象、字段、关系、函数最终以 OAG/OAC/Function 平台返回为准。

## 2. 对外输入接口

业务定制 Skill 调用本层时，只需要按如下 7 行自然语言格式组织输入：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题>
已读取业务定制文件：<knowledge / rules / templates 文件路径；必填>
业务定制文件内容：<业务文件原文或完整摘录>
流程级定制：<执行步骤、顺序、跳过、追加>
步骤级定制：<S2/S3/S4/S5/S6/S7 的 stepTemplateRef、contractRef、变量引用、业务增量规则和失败策略>
缺失信息：<没有则写无>
```

每一行的详细填写规范见：

```text
references/planning-input-interface.md
```

标准步骤模板库见：

```text
references/standard-step-templates.md
```

## 3. 顶层输入填写要求

### 3.1 本体ID

只接收一个公共 `本体ID`。

- OAG 子图检索使用该 ID 作为本体检索范围。
- OAC 数据访问使用该 ID 作为 OQL `schemaRef` 来源。
- Function 使用该 ID 作为函数所属本体标识；如果函数候选返回更精确 `properties.ontologyId`，以函数候选为准。

业务侧不需要同时填写 `ontologyId` 和 `schemaRef`。

### 3.2 业务意图

`业务意图` 必须是改写后的详细自然语言问题。

要求：

- 不只写短标签。
- 不重复粘贴长列表。
- 长列表使用变量引用，例如 `${alarmNames_same_site}`。

### 3.3 已读取业务定制文件

业务定制模式下必须提供已读取的业务定制文件路径。

如果没有读取业务文件，返回：

```text
MISSING_BUSINESS_CUSTOMIZATION_FILE
```

不要退化成猜测式规划。

### 3.4 业务定制文件内容

该字段可以是业务文件原文，也可以是与当前任务相关的完整摘录。

要求：

- 文件很长时，只摘录当前意图相关章节。
- 不重复粘贴与当前意图无关的规则。
- 不在后续步骤中再次展开同一段文件全文。

### 3.5 流程级定制

必须用自然语言明确步骤顺序、跳过步骤和追加步骤。

推荐格式：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function；每个方向独立执行；S4 空结果视为有效结果，不自动放宽条件重试。
```

如果需要 Function：

```text
流程级定制：执行 S1 -> S2 -> S3 -> S5 -> S6 -> S4 -> S7；Function 用于前置补齐查询参数。
```

如果只做规划：

```text
流程级定制：只执行 S1 -> S2 -> S3；不执行 S4/S5/S6/S7；仅输出子图规划结果。
```

### 3.6 步骤级定制

步骤级定制必须采用“标准步骤模板 + 业务增量规则 + 变量引用 + 失败策略”的自然语言格式。

标准输入输出不写在本文件中，由标准步骤模板库提供：

```text
standard.S2.oag
standard.S3.subgraphPlan
standard.S4.oac
standard.S5.functionDiscovery
standard.S6.functionCall
standard.S7.summary
```

业务定制 Skill 只需要说明每个步骤：

- 使用哪个标准模板。
- 使用哪个业务增量规则。
- 使用哪些变量和上游输出。
- 输出什么结果。
- 失败时如何处理。

推荐格式：

```text
步骤级定制：
S2 子图检索：使用标准模板 standard.S2.oag，业务规则使用 <业务文件中的 S2 规则>，变量使用 <变量名列表>；输出 subgraphOutput；失败策略 <策略>。
S3 基于子图规划：使用标准模板 standard.S3.subgraphPlan，业务规则使用 <业务文件中的 S3 规则>，输入使用 S2.subgraphOutput 和变量区；输出 plannedTasks；失败策略 <策略>。
S4 OAC查询：使用标准模板 standard.S4.oac，业务规则使用 <业务文件中的 S4 规则>，输入使用变量区、S2.subgraphOutput 和 S3.plannedTasks；输出 objects 与 relationships；失败策略 <策略>。
S7 汇总：使用标准模板 standard.S7.summary，业务规则使用 <业务文件中的 S7 规则>，输入使用上游结果摘要；输出最终业务结论。
```

如果需要 Function，则追加：

```text
S5 Function发现：使用标准模板 standard.S5.functionDiscovery，业务规则使用 <函数选择规则>；输出 functionSelection。
S6 Function执行：使用标准模板 standard.S6.functionCall，业务规则使用 <参数组装规则>；输入使用 functionSelection 和变量区；输出 functionOutput。
```

### 3.7 缺失信息

没有缺失时固定写：

```text
缺失信息：无
```

如果缺少业务文件、变量、本体ID、方向、对象、字段、关系、函数或参数规格，必须明确列出，不允许猜测补齐。

## 4. 解析执行规则

### 4.1 S1 输入整理

S1 只做一次输入整理，禁止反复压缩或重写同一份业务文件。

S1 必须输出 `planningContext`：

```text
planningContext：
- 本体ID
- 业务意图
- 已读取业务定制文件
- 业务定制文件内容或摘录
- 流程级定制
- 步骤级定制
- variables：从业务意图和业务文件中抽取的变量区
- missingOrConflict：缺失或冲突项
```

长列表只允许保存在 `variables` 中一次，后续步骤只引用变量名。

### 4.2 流程级定制解析

从 `流程级定制` 中解析：

- 执行步骤序列。
- 跳过步骤及原因。
- 追加步骤及原因。
- 是否多方向独立执行。
- 空结果、失败、缺失信息的处理策略。

如果流程级定制没有明确指定步骤，使用默认流程：

```text
S1 -> S2 -> S3 -> S4 -> S7
```

只有明确需要 Function 时才执行 S5/S6。

### 4.3 步骤级定制解析

从 `步骤级定制` 中解析每个步骤的：

```text
stepId
stepTemplateRef
contractRef 或业务规则引用
variablesRef / inputRefs
expectedOutputRef
failurePolicy
```

这些字段是 Planning 内部解析结果，业务 Skill 不需要构造复杂 JSON。

标准输入、标准输出、标准执行规则和标准失败策略从 `references/standard-step-templates.md` 查找，不在运行上下文中重复展开。

### 4.4 步骤执行记录

默认使用 compact 模式，只输出摘要型步骤记录：

```text
StepExecutionRecord：
- stepId
- stepTemplateRef
- contractRef 或业务规则引用
- inputRef
- actualOutputRef
- status
- validation
- nextStepAllowed
```

默认禁止输出：

- 完整标准模板全文。
- 完整业务文件全文。
- 完整长列表重复展开。
- OAC 的 OQL、operationDecision、validation 作为最终业务输出。

只有 debug、失败定位或用户明确要求完整 trace 时，才展开标准模板全文。

## 5. 步骤门禁

执行必须满足：

```text
S2 未输出 subgraphOutput，不得进入 S3。
S3 未输出 plannedTasks，不得进入 S4。
S4 未输出 {objects, relationships}，不得进入 S7。
S5 未输出 functionSelection，不得进入 S6。
S6 未输出 functionOutput，不得进入 S7。
```

S4 OAC 数据访问不得重新解释用户原始问题或业务定制文件全文。S4 只消费：

- S1 variables。
- S2 subgraphOutput。
- S3 plannedTasks。
- standard.S4.oac 标准模板。
- 步骤级定制中给出的业务增量规则。

## 6. 执行效率规则

默认执行必须遵守：

1. 只读取并整理业务定制文件一次。
2. 长列表只进入变量区一次。
3. 标准步骤模板只引用模板编号，不展开全文。
4. 步骤级定制只表达业务差异和变量引用。
5. StepExecutionRecord 只输出摘要。
6. S4 不重新推理 S3 已规划出的关系路径和过滤条件。
7. OAC 默认不写临时 OQL 文件，优先使用内存参数或 stdin。
8. 只有 debug、失败定位或用户要求时才输出完整模板和中间过程。

## 7. 失败处理

- 缺业务定制文件：返回 `MISSING_BUSINESS_CUSTOMIZATION_FILE`。
- 缺本体ID：返回 `MISSING_ONTOLOGY_ID`。
- 缺变量：返回 `MISSING_VARIABLES`。
- 子图为空：按业务失败策略处理，不自动放宽条件重试。
- 字段或关系不在子图中：返回缺失项，不编造。
- OAC validator 失败：输出失败摘要；仅失败定位时展开 S4 模板、业务规则和 OQL 中间过程。
- Function 参数缺失：停止 Function 步骤并返回 missing，不猜测参数。
