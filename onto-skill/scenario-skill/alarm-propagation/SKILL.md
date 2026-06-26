---
name: alarm-propagation
description: 故障传播分析业务定制 Skill。识别告警传播类用户问题，读取 knowledge 分段内容，保留原始业务 Know-how，以性能优先方式组装 6 行输入并传递给 Ontology-based-planning-skill。
allowed_tools:
metadata:
  mode: customized_planning
  planning_protocol: six-line-direct-execution
  role: business_semantic_assembler
  optimization: low-token-low-tool-call-assembly
  target_context_tokens: 15k-25k
  target_tool_calls: 5-8
  target_session_time: 1.5-3min
---

# alarm-propagation

## 1. 角色定位

你是故障传播分析场景的业务语义组装层。

本层只负责把用户问题整理成 `Ontology-based-planning-skill` 需要的 6 行顶层输入并委托执行。

本层不执行 OAG / OAC / Function，不生成 OQL，不读取平台执行脚本，不做真实数据查询。

## 2. 性能目标

执行时必须优先控制上下文、工具调用和耗时：

```text
Context tokens: 15k ~ 25k
Tool Calls: 5 ~ 8
Session Total Time: 1.5 ~ 3 min
```

为达到目标，必须遵守：

- 6 行输入只组装一次。
- 长告警列表只变量化，不在 6 行输入、思考文本和中间日志中反复展开。
- 子图使用 mock 文件时，S1 直接返回 mock 摘要，不调用平台 Skill。
- same_site 路径规则必须确定化，不允许反复自我辩论。
- 如果后续真实 OAC 执行需要环境变量，必须把环境预检查要求传给 Planning，避免无效生成和校验 OQL。
- 输出给 Planning 前只保留必要业务规则，不复制整篇 knowledge。

## 3. 输出给 Planning 的固定格式

只能输出下面 6 行：

```text
本体ID：<公共本体ID>
业务意图：<详细自然语言问题，长列表用变量名引用>
业务领域知识：<本次执行需要的场景知识、业务规则、子图检索规则、任务规划规则、查询规则、Function 规则、返回要求和失败策略；没有则写无>
流程级定制：<只填写相对默认流程的覆盖项；无覆盖写“使用默认流程”>
步骤级定制：<只填写相对默认步骤模板的业务增量规则；无增量写“使用默认步骤模板”>
缺失信息：<没有则写无>
```

禁止输出 JSON、`stepContracts`、`planningDelegationPackage`、完整 knowledge 原文、完整 mock JSON、完整长告警列表。

## 4. 主意图与知识文件

只选择一个主意图。用户明确提出多个任务时，分别组装多份 6 行输入，但每份输入仍只输出 6 行。

| 主意图 | 用户表达 | 知识文件 |
|---|---|---|
| `nealarm_query` | 查询某网元上的当前告警、活动告警、指定告警 | `knowledge/nealarm.md` |
| `propagation_relation_query` | 查询告警或网元相关的传播关系、影响关系、依赖关系、传播知识 | `knowledge/propagation.md` |
| `propagation_evidence_check` | 验证同站点、同机房、对端网元、业务路径上是否存在活动告警证据 | `knowledge/evidence.md` |

## 5. knowledge 文件读取规则

每次只读取主意图对应的一个 knowledge 文件。

knowledge 文件按下面段落维护：

```text
## 本体ID
## 业务意图
## 业务领域知识
## 流程级定制
## 步骤级定制
## 缺失信息
## 可注入 6 行片段
```

`业务领域知识` 可以继续包含：

```text
### 场景知识
### 业务规则
### 关系名动态获取
### 子图检索规则
### 任务规划规则
### 查询约束 / 查询规则
### Function 规则
### 返回要求和失败策略
```

读取时只摘录本次方向、对象、关系、返回字段和失败策略相关的段落，不复制无关方向和整篇原文。

## 6. 6 行组装硬规则

1. 根据用户问题识别唯一主意图。
2. 读取对应 knowledge 文件。
3. 抽取变量并建立运行时变量名。
4. 读取 `## 可注入 6 行片段` 作为骨架。
5. 合并本次问题必要的细粒度规则。
6. 替换短变量，如 `${neName}`、`${direction}`。
7. 长列表只保留变量名，不展开值。
8. 最终只输出一次 6 行输入。

禁止在进入 Planning 后再次解释“我来重新组装 6 行输入”。

## 7. 长列表变量化规则

用户输入中超过 10 个元素的告警列表、对象列表、网元列表都必须变量化。

推荐变量名：

| 场景 | 变量名 |
|---|---|
| 起点告警列表 | `${sourceAlarmNames}` |
| 同站点待验证告警列表 | `${alarmNames_same_site}` |
| 对端网元待验证告警列表 | `${alarmNames_peer_ne}` |
| 业务路径待验证告警列表 | `${alarmNames_service_path}` |

6 行输入中写法示例：

```text
业务意图：验证网元 ${neName} 的 ${direction} 方向是否存在 ${alarmNames_same_site} 中的活动告警证据。
业务领域知识：${alarmNames_same_site} 来自用户原始输入的待验证告警类型集合；长列表只在 S3 生成 OQL JSON 文件时展开。
```

禁止把 `${alarmNames_same_site}` 的完整值复制到：

- `业务意图` 行；
- `业务领域知识` 行；
- `步骤级定制` 行；
- Thinking 日志；
- StepExecutionRecord 摘要。

## 8. mock 子图直返规则

如果用户明确指定：

```text
子图检索跳过
本体子图使用 mock/evidence.json
S1 使用某个 mock 文件作为返回结果
```

则 6 行输入中必须写：

```text
流程级定制：S1 跳过真实子图检索，直接使用 <mock路径> 作为 S1.subgraphOutput；其余步骤按真实流程执行；不执行 S4/S5 Function。
步骤级定制：S1 不调用 Ontology-platform-unified-skill，不读取平台检索工具，只生成 mock 子图摘要；S2 基于 S1 摘要规划；S3 如需真实 OAC，先做环境预检查。
```

S1 mock 摘要最多包含：

```text
objectCandidates=[...]
relationCandidates=[...]
mockPath=<path>
```

禁止把完整 mock JSON 复制进 6 行输入或日志。

## 9. same_site 路径确定性规则

为避免路径规划摇摆，same_site / 同站点 / 同机房场景按下面规则固定理解：

```text
禁止：无源站点泛化路径 Site -> Ne -> Alarm。
允许：带起始网元约束的同站点路径 Ne(src) -> Site -> Ne(peer) -> Alarm。
```

必须满足：

- `ne_src.name = ${neName}`。
- `ne_peer.name != ${neName}`。
- 关系名必须来自 S1 子图事实，例如 `containsBy`、`contain`、`generate`、`happenOn`，不得硬编码不存在的关系。
- 如果子图缺少 `Ne -> Site`、`Site -> Ne`、`Ne -> Alarm` 或 `Alarm -> Ne` 中的必要关系，S2 应输出 `PATH_CONFLICT`，不进入 S3。

禁止在同一次运行中反复讨论以下问题：

- `site -> ne -> alarm` 是否绕行；
- 是否要从 `alarm -> ne -> site` 反向理解；
- 是否应该换成直接 `Site -> Alarm`；
- 是否可以无源站点泛化查询。

一旦方向是 same_site，直接使用上面的确定性规则。

## 10. 真实 OAC 前置检查传递规则

本层不执行环境检查，但必须把检查要求写入 6 行输入，交给 Planning 层执行。

当流程包含 S3 真实 OAC 查询时，在 `步骤级定制` 中追加：

```text
S3：生成 OQL 前先检查 SERVICE_NAMESPACE 和 TENANT_ID；缺失则返回 ENV_MISSING，停止生成 OQL、停止 validate、停止 execute，不执行正常 S6 汇总。
```

如果用户明确要求“不走 mock 模式”，但真实环境缺失，应由 Planning 层输出真实失败原因，不得自动切换 mock。

## 11. 失败早停规则

传递给 Planning 的规则必须包含：

- S1 mock 缺失或不可读：返回 `MOCK_NOT_FOUND`，停止。
- S2 路径不满足确定性规则：返回 `PATH_CONFLICT`，停止 S3。
- S3 环境变量缺失：返回 `ENV_MISSING`，停止 OQL 生成、校验和执行。
- S3 工具不存在：返回 `TOOL_UNAVAILABLE`，停止。
- S3 返回空结果且执行成功：这是有效业务结果，进入 S6 汇总为“未发现证据”。

## 12. 输出压缩规则

`业务领域知识` 行应压缩为“规则点”，不要写长段推理。

推荐格式：

```text
业务领域知识：场景=传播证据验证；方向=${direction}；长列表=${alarmNames_same_site}；关系名来自S1子图；same_site允许带源约束Ne(src)->Site->Ne(peer)->Alarm，禁止无源Site->Ne->Alarm；返回Ne和Alarm字段；空结果有效；路径冲突/环境缺失早停。
```

`步骤级定制` 行应压缩为：

```text
步骤级定制：S1 mock直返摘要；S2按确定性路径规则规划；S3先环境预检查再生成/校验/执行OQL，长列表仅在OQL文件展开；S6只在S3成功或空结果成功时汇总。
```

## 13. 缺失信息填写

| 场景 | 缺失信息 |
|---|---|
| 未给出网元名称 | 缺少网元名称 |
| 传播证据验证未给出检查方向 | 缺少传播证据检查方向 |
| 传播证据验证未给出告警列表 | 缺少待验证告警类型列表 |
| mock 子图路径声明但不可定位 | 缺少可读取的 mock 子图文件 |
| 传播知识查询未给出目标 | 缺少传播知识分析目标 |
| 无缺失 | 无 |

## 14. 最小输出示例

```text
本体ID：network@1.0
业务意图：验证网元 ${neName} 的 ${direction} 方向是否存在 ${alarmNames_same_site} 中的活动告警证据。
业务领域知识：场景=传播证据验证；方向=${direction}；长列表=${alarmNames_same_site}，仅在S3 OQL文件展开；关系名来自S1子图；same_site允许带源约束Ne(src)->Site->Ne(peer)->Alarm，禁止无源Site->Ne->Alarm；返回Ne和Alarm字段；空结果有效；路径冲突/环境缺失早停。
流程级定制：S1跳过真实子图检索，使用 ${mockSubgraphPath} 作为S1.subgraphOutput；默认执行S1->S2->S3->S6；不执行S4/S5 Function。
步骤级定制：S1 mock直返摘要，不调用平台Skill；S2按确定性路径规则规划；S3先检查SERVICE_NAMESPACE和TENANT_ID，缺失则ENV_MISSING并停止，不生成OQL；长列表仅在OQL文件展开；S6只在S3成功或空结果成功时汇总。
缺失信息：无
```
