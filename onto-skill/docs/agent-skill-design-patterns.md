# 本体 Agent Skill 设计模式说明

## 1. 设计背景

本体 Skill 体系采用三层结构：

```text
scenario-skill
  -> Ontology-based-planning-skill
    -> Ontology-platform-unified-skill
      -> OAG 本体子图 / OAC 本体访问 / Function 函数能力
```

设计目标是将业务语义、默认本体规划和平台能力解耦：

- 业务场景优先用自然语言注入业务知识、规则、SOP、禁止项和返回要求。
- 对外本体是一个整体，上层业务 Skill 只需提供公共 `本体ID`，不需要同时区分 `ontologyId` 和 `schemaRef`。
- 规划层负责基于本体子图结构规划单步或多步执行任务。
- 平台层封装 OAG、OAC、Function 三类能力，对上层暴露稳定的自然语言委托入口。
- OQL 生成和校验由 operation 手册、schema、validator、executor 共同约束。

---

## 2. 业务 Skill 定制的两层模型

业务 Skill 的定制内容分为两部分。

### 2.1 流程级定制

流程级定制回答：**默认 planning 大流程要执行哪些步骤、是否跳过、是否追加、步骤顺序如何。**

默认流程为：

```text
S1 读取业务注入与整理上下文
  -> S2 OAG 子图检索
  -> S3 基于本体子图的任务规划
  -> S4 OAC 数据访问
  -> S5 Function 发现
  -> S6 Function 执行
  -> S7 汇总结果
```

业务 Skill 可以自然语言说明：

- 执行全部默认步骤。
- 只执行 S2/S3，输出模型解释。
- 只执行 S2/S3/S4，生成或执行 OAC 查询。
- 先 Function，再 OAC，或 Function 作为备选。
- 多方向、多对象、多路径必须串行或并行。
- 某些步骤必须跳过，并给出原因。

### 2.2 步骤级定制

步骤级定制回答：**每个步骤输入什么、输出什么、执行规则是什么。**

可定制内容包括：

- S2 子图检索的 query 改写、检索策略、扩展方向、函数候选返回要求、子图返回结构要求。
- S3 基于子图规划的起点对象、终点对象、路径选择、OAC / Function 优先级、任务拆分规则。
- S4 OAC 查询的操作类型、查询对象、关系路径、过滤条件、返回字段、排序分组、空结果策略。
- S5/S6 Function 的函数选择依据、参数规格获取、参数组装、缺参策略、调用结果要求。
- S7 汇总结果的展示维度、分方向/分步骤输出、依据保留要求。

结构化字段可以作为增强，但不是强制接口；业务 Skill 可以直接注入自然语言规则文件。

---

## 3. Tool Wrapper：Ontology-platform-unified-skill

`Ontology-platform-unified-skill` 是本体平台能力包装器，对上层隐藏 OAG、OAC、Function 的接口差异。

| 能力 | 职责 | 入口 |
|---|---|---|
| OAG 本体子图 | 基于自然语言业务意图、公共本体ID和业务子图检索规则，返回 `result.seedNodes/nodes/edges/functions/actions` | `references/ontology-subgraph-search.md` |
| OAC 本体访问 | 基于公共本体ID、业务意图、本体子图依据和业务查询规则生成、校验、执行 OQL | `references/oac-data-access.md` |
| Function 函数能力 | 基于公共本体ID、`result.functions` 和业务函数规则获取规格、组装参数、调用函数 | `references/call-function.md` |

平台层不做跨阶段业务规划，只做能力路由和平台协议封装。

---

## 4. OAG / OAC / Function 职责边界

### 4.1 OAG：找本体结构依据

OAG 输入是自然语言业务意图、公共 `本体ID` 和业务子图检索规则，输出本体子图 JSON 及规划可用摘要。

OAG 负责：

- 检索对象、属性、关系、函数候选。
- 保留 `result.seedNodes`、`result.nodes`、`result.edges`、`result.functions`、`result.actions` 原始结构。
- 按业务定制返回结构要求输出摘要。
- 为 S3、OAC 和 Function 提供可信依据。

OAG 不负责生成 OQL、不执行数据查询、不直接调用函数。

### 4.2 S3：基于本体子图规划任务

S3 是 `Ontology-based-planning-skill` 内部规划步骤，不属于平台能力。

S3 输入为：OAG 子图结果 + 业务定制规划规则文件。输出为可执行步骤列表，包括 OAC 查询任务、Function 发现/调用任务、汇总任务等。

典型任务包括：

```text
从【起点对象类型】出发，查找到【终点对象类型】。
```

也可以是单对象查询、聚合查询、函数调用或多方向证据验证。

### 4.3 OAC：生成和校验本体查询

OAC 输入是公共 `本体ID`、自然语言数据访问业务意图、OAG 子图依据和业务查询规则，输出 OQL、校验结果以及可选执行结果。

OAC 负责：

- 判断 `QUERY / ASSOCIATION_QUERY / AGGREGATE`。
- 将公共 `本体ID` 作为 OQL `schemaRef` 来源。
- 读取唯一 operation 手册和对应 schema。
- 生成 OQL JSON。
- 运行 validator 校验。
- 用户明确要求执行时调用 executor。

OAC 不检索本体子图、不编造对象字段关系、不调用 Function。

### 4.4 Function：调用本体函数

Function 输入是公共 `本体ID`、业务函数意图、`result.functions` 候选、函数选择规则和上下文参数。

Function 固定流程：

1. 根据 `result.functions[].properties.description` 选择目标函数。
2. 提取 `properties.ontologyId` 和 `properties.id`。
3. 调用 `get_params_spec(ontology_id, function_id)`。
4. 解析 `physicalName`。
5. 调用 `call_function(physicalName, function_id, params)`。

Function 不检索本体子图、不生成 OQL、不编造参数或成功结果。

---

## 5. 面向自然语言的模块输入模板与输出格式

### 5.1 OAG 本体子图检索

```text
先找相关子图。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题，用于检索对象、属性、关系、函数候选>
业务定制文件：<已读取的子图检索规则文件或场景知识文件；可写无>
子图检索规则：<业务定制的检索策略、固定 query 模板、扩展方向、最大跳数、是否返回函数候选等>
检索目标：<需要检索哪些对象、属性、关系、函数候选；不得提前编造平台字段名>
子图返回结构要求：<业务希望从 result.seedNodes / nodes / edges / functions / actions 中保留哪些字段内容；未指定时保留完整原始 result>
期望输出：返回 OAG 原始图结构 JSON，包括 result.seedNodes、result.nodes、result.edges、result.functions、result.actions；同时按业务返回结构要求输出可用于后续规划的对象、字段归属、关系候选和函数候选摘要。
```

### 5.2 基于本体子图的任务规划

```text
基于本体子图规划执行任务。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题>
本体子图结果：<S2 返回的 subgraphRawResult 与摘要>
业务定制规划规则文件：<已读取的任务规划规则文件；可写无>
规划目标：<例如“从【起点对象类型】出发，查找到【终点对象类型】”；如果是单对象查询，说明只查询起点对象>
可用结构依据：<objectType、property、has_property、defines_relation、functions 的确认结果>
业务规划规则：<步骤顺序、优先使用 Function 或 OAC、路径选择、方向、返回要求、空结果策略>
期望输出：返回计划步骤列表；每个步骤说明 actionType、输入模板、依赖关系、预期输出、是否必须执行、失败策略。
```

### 5.3 OAC 本体数据访问

```text
查数据
本体ID：<公共本体ID，平台侧作为 schemaRef 来源>
操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE / 模型查询，如可判断>
查询对象：<对象类型和别名建议，来自子图 objectType>
关系路径：<仅在关系查询时填写，关系名必须来自 defines_relation.properties.name>
过滤条件：<用户条件及其对应字段依据；单位换算和枚举值说明>
返回要求：<返回字段、排序、分组、maxResults、空结果策略>
执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。
期望输出：返回操作类型判断、OQL JSON、校验结果、执行状态、数据结果或缺失项。
```

### 5.4 Function 函数调用

```text
调用function。
本体ID：<公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么需要函数能力，要解决什么问题>
函数来源：<来自 OAG result.functions，或上层业务 Skill 明确注入的函数目标>
functionId：<函数ID；发现阶段未知时说明需要从候选函数中选择>
函数选择依据：<使用 description、name、业务规则或上层知识说明选择原因>
上下文参数：<来自用户、OAC 结果、业务知识或上游步骤的参数值>
参数缺失策略：<缺少参数时停止并返回 missing，不得猜测>
输出要求：<需要返回函数结果、参数绑定、未执行原因或业务解释>
期望输出：返回函数选择结果、参数规格、参数组装结果、调用状态、函数原始结果或缺失项。
```

---

## 6. Generator：OAC 操作手册与 Schema

OAC 子模块承担 Generator 模式，将用户目标、业务变量和本体子图结果生成 OQL JSON。

| 操作 | 文档 | Schema |
|---|---|---|
| `QUERY` | `references/oac-query.md` | `schemas/oql-query.schema.json` |
| `ASSOCIATION_QUERY` | `references/oac-association-query.md` | `schemas/oql-association-query.schema.json` |
| `AGGREGATE` | `references/oac-aggregate.md` | `schemas/oql-aggregate.schema.json` |

生成链路：

```text
业务意图 / 业务查询规则 / OAG 子图结果
  -> 判断 operation
  -> 读取唯一 operation 手册
  -> 读取对应 schema
  -> 生成 OQL JSON
```

---

## 7. Reviewer：OQL Validator 与执行前校验

OAC 子模块同时承担 Reviewer 模式。所有 OQL 在执行前必须通过统一校验。

`oql_validator.py` 负责：

- 根据 `operation` 选择 schema。
- 执行 JSON Schema 结构校验。
- 校验 alias 引用。
- 校验 relationship `from/to` 引用。
- 校验 `aggregateFilter.metricAlias` 引用。
- 校验特殊返回项、聚合项和排序项等跨字段语义。
- 校验 `maxResults` 使用数字格式。

---

## 8. Inversion：业务 Skill 定制默认流程

业务定制 Skill 不直接调用 OAG、OAC、Function，而是把两类定制注入给 planning 层：

```text
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题>
已读取业务定制文件：<knowledge / rules / templates 文件路径，可多个>
业务知识与规则：<规则、SOP、禁止项、返回要求、空结果策略>
流程级定制：<执行全部默认步骤还是部分步骤；步骤顺序如何>
步骤级定制：<每个步骤的输入、输出和执行规则>
缺失信息：<没有则写无>
```

结构化字段只是可选增强，不是业务 Skill 的强制接口。

---

## 9. Pipeline：默认规划执行链

```text
S1 读取业务注入与整理上下文
  -> S2 OAG 子图检索
  -> S3 基于本体子图的任务规划
  -> S4 OAC 数据访问
  -> S5/S6 Function 发现与调用
  -> S7 汇总
```

Pipeline 的关键约束：

1. 字段必须来自子图 property 并通过 `has_property` 确认归属。
2. 关系必须来自 `defines_relation.properties.name`。
3. Function 必须来自子图 `functions` 候选或上层可信函数目标。
4. 对外只暴露公共本体ID，不要求业务 Skill 同时填写 ontologyId/schemaRef。
5. 业务意图必须是可执行的详细自然语言问题，而不是短标签。
6. 空结果是有效结果，不自动放宽条件重试。
7. 业务注入文件只能提供规则和模板，不能替代平台返回结果。
