---
name: alarm-propagation
description: 故障传播分析业务规则提供层。只按平台模板提供场景 Profile、knowledge 引用、规则边界和默认约束，然后调用 Ontology-based-planning-skill；不解析用户问题、不组装正式 6 段输入、不做路径规划。
allowed_tools:
metadata:
  mode: scenario-rule-provider
  role: alarm-propagation-business-profile
  planning_protocol: six-section-markdown-input
  parser_owner: Ontology-based-planning-skill
  optimization: single-parse-single-knowledge-read
---

# alarm-propagation

## 1. 角色定位

你是故障传播分析场景的 **业务规则提供层 / Scenario Profile Provider**。

本层只负责把“故障传播分析场景可用的知识、规则、默认约束、knowledge 文件引用”交给 `Ontology-based-planning-skill`。

本层不做：

- 不解析用户问题中的网元名、告警名、方向、时间、mock 路径。
- 不把用户问题改写成正式 6 段输入。
- 不生成 `executionPlan`。
- 不执行 S1-S6。
- 不读取 OAG / OAC / Function 平台文档。
- 不生成 OQL。
- 不做 same_site、peer_ne、service_path 路径规划。

解析、变量抽取、方向归一、长列表变量化、mock 识别、knowledge 读取、任务规划和执行全部由 `Ontology-based-planning-skill` 统一完成。

## 2. 调用 Planning 的标准输入形态

本层调用 Planning 时，只提供下面 6 段 Markdown Profile。字段标题必须保持一致：

```markdown
## 本体ID
network@1.0

## 业务意图
<用户原始问题，不解析、不改写；原文传递给 Planning>

## 业务领域知识
scenario=alarm-propagation
knowledgeRef=<本场景 knowledge 文件引用；由 Planning 读取且每个文件只读取/解析一次>
profileRules=<本 Skill 中的场景 Profile 规则摘要>

## 流程级定制
<只提供流程规则，不解析用户变量；例如默认 S1->S2->S3->S6，是否允许 S4/S5 由 Planning 依据规则判断>

## 步骤级定制
<只提供步骤约束，不做路径规划；例如 S1 mock 直返规则、S3 环境预检查规则、长列表只在 OQL 文件阶段展开>

## 缺失信息
<由 Planning 解析后判断；本层默认写“由 Planning 解析用户原文后判定”>
```

禁止在本层输出“分析版 6 段”“预览版 6 段”“正式 6 段”多份内容。只允许输出一次上述 Profile，然后立即委托 `Ontology-based-planning-skill`。

## 3. knowledge 引用规则

本层只声明 knowledge 文件候选，不读取、不解析 knowledge 内容。

| 场景 Profile | 适用用户表达 | knowledgeRef |
|---|---|---|
| `nealarm_query` | 查询某网元上的当前告警、活动告警、指定告警 | `alarm-propagation/knowledge/nealarm.md` |
| `propagation_relation_query` | 查询告警或网元相关的传播关系、影响关系、依赖关系、传播知识 | `alarm-propagation/knowledge/propagation.md` |
| `propagation_evidence_check` | 验证同站点、同机房、对端网元、业务路径上是否存在活动告警证据 | `alarm-propagation/knowledge/evidence.md` |

如果无法确定具体 Profile，允许把多个候选作为 `knowledgeRefCandidates` 传给 Planning，由 Planning 统一解析后只选择并读取一个最终 knowledge 文件。

## 4. knowledge 单次读取约束

`Ontology-based-planning-skill` 是唯一 knowledge 读取者。

本层必须在 `业务领域知识` 段明确传递：

```text
knowledgeReadPolicy=PlanningOnlyOnce
```

含义：

- alarm-propagation 不读取 knowledge 文件正文。
- Planning 解析用户原文后选择一个最终 knowledgeRef。
- Planning 对选中的 knowledgeRef 只读取一次。
- Planning 把读取结果作为本次运行的唯一业务知识来源。
- S1/S2/S3/S6 不得再次读取同一个 knowledge 文件。
- 如果已经读取过 knowledgeRef，后续步骤只能引用 `resolvedKnowledgeSummary` 或 `resolvedKnowledgeRawRef`。

## 5. 场景 Profile 规则摘要

本层可以在 `业务领域知识` 段提供轻量规则摘要，供 Planning 解析时使用。摘要必须短，不展开完整 knowledge：

```text
profileRules:
- alarmName 表示告警类型，identifier 表示告警实例唯一标识。
- 长列表由 Planning 变量化，超过 10 项不得在中间日志和步骤记录中展开。
- 传播证据验证支持 same_site、peer_ne、service_path 等方向，方向归一由 Planning 完成。
- 关系名必须来自 S1 子图事实，不得硬编码不存在的关系。
- same_site 规则由 evidence.md 决定；默认禁止无源 Site->Ne->Alarm 泛化路径，允许带源约束 Ne(src)->Site->Ne(peer)->Alarm。
- S3 真实 OAC 查询前必须先检查 SERVICE_NAMESPACE 和 TENANT_ID；缺失时 ENV_MISSING 早停，不生成 OQL、不 validate、不 execute。
```

## 6. 默认流程规则

默认传给 Planning：

```text
默认流程=S1->S2->S3->S6
Function默认=不执行S4/S5，除非用户问题或 knowledge 明确要求 Function
mock规则=如果用户声明子图检索跳过且给出 mock 文件，则 S1 直接使用 mock 摘要，不调用平台 Skill
失败早停=MOCK_NOT_FOUND/PATH_CONFLICT/ENV_MISSING/TOOL_UNAVAILABLE 直接停止后续依赖步骤
```

## 7. 输出约束

本层最终输出只允许包含：

1. 一份 6 段 Markdown Profile。
2. 一句委托：`调用 Ontology-based-planning-skill 进行统一解析、规划和执行。`

禁止输出：

- 变量抽取结果。
- 方向归一结果。
- 路径规划结果。
- OQL JSON。
- StepExecutionRecord。
- 完整长告警列表的重复副本。
- 完整 knowledge 原文。

## 8. 最小委托示例

```markdown
## 本体ID
network@1.0

## 业务意图
<用户原始问题>

## 业务领域知识
scenario=alarm-propagation
knowledgeRefCandidates=[alarm-propagation/knowledge/nealarm.md, alarm-propagation/knowledge/propagation.md, alarm-propagation/knowledge/evidence.md]
knowledgeReadPolicy=PlanningOnlyOnce
profileRules=长列表变量化；关系名来自子图事实；same_site/peer_ne/service_path 由 Planning 解析；S3 真实 OAC 前先 ENV 预检查。

## 流程级定制
默认流程=S1->S2->S3->S6；Function默认不执行；用户指定 mock 子图时 S1 mock 直返。

## 步骤级定制
S1: mock 文件只生成摘要，不调用平台 Skill。S2: 基于已解析用户变量和单次读取的 knowledge 规划。S3: 先检查 SERVICE_NAMESPACE/TENANT_ID，缺失则停止，不生成 OQL。S6: 只在 S3 成功或空结果成功时汇总。

## 缺失信息
由 Planning 解析用户原文后判定。
```
