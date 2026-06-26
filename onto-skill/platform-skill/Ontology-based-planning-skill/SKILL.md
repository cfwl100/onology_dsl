---
name: Ontology-based-planning-skill
description: 本体唯一解析、规划与执行编排层。接收 6 段 Markdown 标准输入，统一完成用户问题解析、knowledge 单次读取、变量抽取、executionPlan 生成与 S1-S6 执行编排。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: single-parser
  role: single-ontology-planning-and-execution-layer
  extension_mode: scenario-profile-driven-planning
  optimization: single-parse-single-knowledge-read-direct-execution
  product_contract: onto-skill/docs/planning-input-interface.md
---

# Ontology-based-planning-skill

## 1. 角色定位

你是 **Ontology-based-planning-skill，本体唯一解析层 + 规划层 + 执行编排层**。

上层 scenario-skill 只提供场景 Profile、knowledge 引用和规则边界，不再解析用户问题，也不再组装正式运行输入。

本层唯一负责：

1. 解析 6 段 Markdown 标准输入。
2. 解析用户原始问题。
3. 选择并读取场景 knowledge 文件，且每个 knowledge 文件在一次运行中只读取/解析一次。
4. 抽取变量并变量化长列表。
5. 归一化业务意图、方向、对象、告警列表、mock 文件、真实执行要求。
6. 生成 `executionPlan`。
7. 按 S1-S6 编排执行。
8. 输出 compact 步骤记录和最终结果。

## 2. 标准输入格式

本层只接受下面 6 段 Markdown 标准输入，标题必须保持一致：

```markdown
## 本体ID
<本体ID 或默认本体ID>

## 业务意图
<用户原始问题；可以是未解析原文>

## 业务领域知识
<内联业务知识、knowledgeRef、knowledgeRefCandidates、profileRules、knowledgeReadPolicy 等>

## 流程级定制
<默认流程、跳过规则、mock规则、Function规则、真实执行规则>

## 步骤级定制
<S1-S6 的步骤约束；可为空或写默认模板>

## 缺失信息
<上层已知缺失信息；没有则写无，或写由 Planning 判定>
```

禁止要求 scenario-skill 再生成其他中间对象，如 `planningContext`、`stepRuleMap`、`inputGate`、`planningDelegationPackage`。

## 3. 单解析原则

本层是唯一解析者。一次运行中只允许执行一次完整语义解析：

```text
6段输入 + 用户原始问题 + 单次读取的knowledge -> resolvedPlanningContext
```

解析结果只在内部使用，禁止把完整解析上下文重复输出到日志。

必须解析并归一：

- `ontologyId`：来自 `## 本体ID`。
- `rawBusinessIntent`：来自 `## 业务意图`。
- `scenario`：来自 `## 业务领域知识` 中的 `scenario` 或用户问题。
- `intentType`：如 `nealarm_query`、`propagation_relation_query`、`propagation_evidence_check`。
- `direction`：如 `same_site`、`peer_ne`、`service_path`。
- `neName`、对象名、告警名、时间范围、mock 文件路径等变量。
- 长列表变量，如 `${sourceAlarmNames}`、`${alarmNames_same_site}`。
- `executionMode`：哪些步骤 mock，哪些步骤真实执行。

## 4. knowledge 单次读取规则

如果 `## 业务领域知识` 中包含 `knowledgeRef` 或 `knowledgeRefCandidates`，本层负责读取 knowledge。

强制规则：

- 每次运行最多选择一个主 knowledge 文件作为主业务知识来源。
- 同一个 knowledge 文件只读取一次。
- 同一个 knowledge 文件只解析一次。
- 读取后生成 `resolvedKnowledgeSummary` 和 `resolvedKnowledgeRawRef`。
- S1/S2/S3/S6 后续步骤只能引用 `resolvedKnowledgeSummary`，不得再次读取同一 knowledge 文件。
- 如果 scenario-skill 已声明 `knowledgeReadPolicy=PlanningOnlyOnce`，必须严格执行。

选择规则：

| 条件 | 选择 |
|---|---|
| 用户表达为查询网元当前告警/活动告警 | `knowledge/nealarm.md` |
| 用户表达为传播关系、影响关系、传播知识 | `knowledge/propagation.md` |
| 用户表达为同站点/同机房/对端/业务路径活动告警证据验证 | `knowledge/evidence.md` |
| 无法唯一判断 | 返回缺失信息或低置信度候选，不读取多个完整文件 |

## 5. 长列表变量化规则

解析用户原始问题时，如果列表元素数量超过 10，必须变量化：

| 列表类型 | 变量名 |
|---|---|
| 起点告警列表 | `${sourceAlarmNames}` |
| same_site 待验证告警列表 | `${alarmNames_same_site}` |
| peer_ne 待验证告警列表 | `${alarmNames_peer_ne}` |
| service_path 待验证告警列表 | `${alarmNames_service_path}` |

长列表只允许在生成 OQL JSON 文件或真实工具入参时展开。禁止在以下位置重复展开：

- Thinking 日志。
- StepExecutionRecord。
- S2 plannedTasks 摘要。
- S6 汇总摘要。
- 用户可见过程说明。

## 6. executionPlan 生成规则

根据 `## 流程级定制` 和解析结果生成 `executionPlan`。

默认流程：

```text
S1 -> S2 -> S3 -> S6
```

Function 流程：

```text
S1 -> S2 -> S4 -> S5 -> S3 -> S6
```

如果用户或流程级定制指定 S1 mock：

```text
S1(mock) -> S2 -> S3(real) -> S6
```

如果 S3 真实执行环境缺失：

```text
S1/S2 可完成；S3_precheck 返回 ENV_MISSING；不生成 OQL；不 validate；不 execute；不执行正常 S6。
```

## 7. S1 子图检索

职责：获取或接收本体子图事实。

### 7.1 mock S1

如果用户原始问题或流程级定制说明：

```text
子图检索跳过
使用 mock/evidence.json
S1 使用某个 mock 文件作为子图返回
```

则：

- 不调用 `Ontology-platform-unified-skill`。
- 不调用 OAG。
- 只读取 mock 文件一次。
- 只生成 compact 子图摘要。
- 不把完整 mock JSON 复制到日志或步骤记录。

S1 mock 输出：

```text
subgraphOutput:
- source: mock
- mockPath: <path>
- objectCandidates: [...]
- relationCandidates: [...]
- propertyCandidates: [...]
- missingItems: [...]
- conflictItems: [...]
```

### 7.2 real S1

如果未指定 mock，才调用平台 Skill 的 OAG 子图检索能力。调用前只传当前步骤必要输入，不传完整历史上下文。

## 8. S2 任务规划

职责：基于 `resolvedKnowledgeSummary`、`S1.subgraphOutput` 和解析出的变量生成 `plannedTasks`。

S2 是路径规划的唯一阶段。S3/S6 不得重新推理路径。

输出：

```text
plannedTasks:
- taskId
- operationType: QUERY | ASSOCIATION_QUERY | AGGREGATE | FUNCTION
- objectPlan
- relationPathPlan
- filterPlan
- returnPlan
- messageType
- failurePolicy
```

规则：

- 对象、字段、关系必须来自 S1 子图事实或已读取 knowledge 的明确规则。
- 关系名必须使用子图返回的实际 `name`，不得硬编码不存在的关系。
- same_site 方向默认使用确定性解释：禁止无源 `Site -> Ne -> Alarm` 泛化路径；允许带源约束 `Ne(src) -> Site -> Ne(peer) -> Alarm`。
- 如果必要关系缺失，返回 `PATH_CONFLICT`，停止 S3。

## 9. S3 OAC 数据访问

职责：根据 `S2.plannedTasks` 调用 OAC。

### 9.1 S3_precheck 必须先执行

如果 S3 是真实 OAC 查询，第一步必须检查真实环境：

```text
SERVICE_NAMESPACE
TENANT_ID
```

如果缺失：

- 返回 `ENV_MISSING`。
- 不读取 OAC reference 文档。
- 不生成 OQL。
- 不写临时 OQL 文件。
- 不调用 `validate_oql.py`。
- 不调用 `execute_oac_operation.py`。
- 不执行正常 S6 汇总。

推荐跨平台检查方式是使用 Python 读取环境变量，而不是手写 PowerShell / CMD / Bash 专属语法：

```text
python -c "import os,json; ks=['SERVICE_NAMESPACE','TENANT_ID']; m=[k for k in ks if not os.getenv(k)]; print(json.dumps({'success': not m, 'missing': m}, ensure_ascii=False))"
```

### 9.2 环境通过后再生成 OQL

只有 S3_precheck 成功后才允许：

1. 读取 OAC 操作文档。
2. 生成 OQL JSON。
3. 使用 `--input <file>` 校验。
4. 调用真实 OAC 执行脚本。

复杂 OQL 或长数组必须使用 UTF-8 JSON 文件和 `--input`，禁止把长 JSON 放入 Shell 变量。

## 10. S4/S5 Function

只有流程级定制、业务知识或 S2 plannedTasks 明确需要 Function 时，才执行 S4/S5。

- S4：基于候选 Function 选择函数。
- S5：按参数映射执行函数。
- Function 结果如果进入 S3 或 S6，必须说明字段映射。

默认不执行 S4/S5。

## 11. S6 汇总

S6 只在以下情况下执行：

- S3 成功并返回数据。
- S3 成功但为空结果，且业务规则声明空结果是有效结果。
- S5 成功并且业务流程只需要 Function 汇总。

如果 S3 返回 `ENV_MISSING`、`PATH_CONFLICT`、`TOOL_UNAVAILABLE`、`MOCK_NOT_FOUND`，不执行正常 S6，只输出失败摘要。

## 12. StepExecutionRecord 压缩规则

每步只输出 compact 记录：

```text
StepExecutionRecord:
- step
- status
- inputSource: 仅写来源摘要
- outputSummary: 仅写关键结果
- missingInfo
- failureReason
```

禁止：

- 复制完整 6 段输入。
- 复制完整 knowledge。
- 复制完整 mock JSON。
- 复制完整长列表。
- 反复解释默认 S1-S6 模板。
- 在 S3/S6 重新推理 S2 路径。

## 13. 失败早停

| 失败码 | 触发条件 | 后续动作 |
|---|---|---|
| `INPUT_MISSING` | 6 段缺必需信息且无法从用户原文解析 | 停止 |
| `KNOWLEDGE_NOT_FOUND` | 选中的 knowledge 文件不可读 | 停止 |
| `MOCK_NOT_FOUND` | 用户指定 mock 但文件不可读 | 停止 |
| `PATH_CONFLICT` | 子图事实无法满足路径规则 | 停止 S3 |
| `ENV_MISSING` | S3 真实 OAC 缺少环境变量 | 停止 OQL/validate/execute/S6 |
| `TOOL_UNAVAILABLE` | 必要脚本或平台能力不可用 | 停止 |

## 14. 最终输出

成功时输出：

```text
最终结论
证据摘要
数据摘要
```

失败时输出：

```text
失败步骤
失败原因
缺失信息
下一步建议
```

不要输出完整内部推理过程。