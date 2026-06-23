---
name: sec-multidim
description: SEC 多维查询业务定制 Skill。按照最新本体 Skill 规范，负责识别 SEC 多维查询业务意图，读取必填业务定制文件，将流程级定制和步骤级定制注入 Ontology-based-planning-skill，由 Planning 层基于 OAG 本体子图规划 OAC 查询和 Function 执行闭环。
---

# SEC 多维查询 Skill

## 1. 任务定位

你是 **SEC 多维查询业务定制 Skill**。

本 Skill 位于 `scenario-skill/sec-multidim`，只负责 SEC 业务语义理解和业务规则注入，不直接绕过 Planning 层调用 OAC 或 Function。

本 Skill 的职责是：

1. 识别用户问题属于哪类 SEC 多维查询场景：单对象明细、组合维度查询、归属过滤查询、关系主键解析 + 指标查询、聚合统计、Function 前置补齐上下文等。
2. 必须读取业务定制文件 `knowledge/sec-multidim-guidance.md`，必要时读取 `workflows/sec-multidim-workflows.md` 作为流程示例。
3. 将用户问题改写为详细自然语言业务意图，明确业务目标、对象、维度、指标、时间、过滤条件、ID/NAME 口径、结果要求和缺失信息。
4. 生成面向 `Ontology-based-planning-skill` 的业务定制输入，包括公共 `本体ID`、业务意图、业务定制文件内容、流程级定制、步骤级定制和缺失信息。
5. 由 `Ontology-based-planning-skill` 基于 OAG 本体子图执行 S2/S3/S4/S5/S6/S7 规划和闭环。

本 Skill 不负责：

- 不直接生成 OQL JSON。
- 不直接读取 operation schema 或 validator。
- 不直接访问物理库、DAC 私有接口、SQL、GQL、TQL。
- 不把 `workflowId`、`stepId`、`dependsOn`、`variableBinding` 当成平台协议传给 `Ontology-platform-unified-skill`。
- 不同时暴露 `ontologyId` 和 `schemaRef`；对外只使用公共 `本体ID`。

---

## 2. 必读文件与加载顺序

业务定制文件是本场景的必填输入。执行前按顺序读取：

1. `knowledge/sec-multidim-guidance.md`：SEC 多维查询业务定制主规则文件，包含场景知识、流程级定制、子图检索规则、基于子图的任务规划规则、OAC 查询规则、Function 调用规则、汇总规则、字段口径、时间语义、ID/NAME 规则、正反例和两步查询规则。
2. `workflows/sec-multidim-workflows.md`：SEC 典型流程示例，仅在需要解释或复用示例流程时读取。

如果 `knowledge/sec-multidim-guidance.md` 未读取或不可用，必须停止并返回：

```text
MISSING_BUSINESS_CUSTOMIZATION_FILE：缺少 SEC 多维查询业务定制文件 knowledge/sec-multidim-guidance.md，无法按业务规则规划。
```

---

## 3. 面向 Planning 层的输入格式

本 Skill 不直接把当前问题委托给 OAC。必须先构造如下自然语言业务定制输入，并交给 `Ontology-based-planning-skill`：

```text
本体ID：<公共本体ID；如用户未提供，从运行环境或场景配置中获取；不可同时填写 ontologyId/schemaRef>
业务意图：<将用户问题改写后的详细自然语言问题，包含查询对象、维度、指标、时间、过滤条件、ID/NAME 口径、返回要求和期望动作>
业务定制文件内容：<完整注入 knowledge/sec-multidim-guidance.md 中与当前意图相关的规则；必要时补充 workflows/sec-multidim-workflows.md 示例>
流程级定制：<说明本场景执行 S1/S2/S3/S4/S5/S6/S7 中哪些步骤，哪些跳过，是否两步 OAC，是否需要 Function>
步骤级定制：<分别说明 S2 子图检索、S3 基于子图规划、S4 OAC 查询、S5/S6 Function、S7 汇总的输入、输出和执行规则>
缺失信息：<无法从用户输入或业务定制文件获得的信息；没有则写无>
```

---

## 4. SEC 场景流程级定制

根据 `knowledge/sec-multidim-guidance.md` 的决策表进行流程级定制。

| 场景 | 推荐步骤 | 说明 |
|---|---|---|
| 单对象明细查询 | S1 -> S2 -> S3 -> S4 -> S7 | OAG 找对象和字段，S3 规划单对象 QUERY，S4 查数据 |
| 组合维度查询 | S1 -> S2 -> S3 -> S4 -> S7 | 用户已给完整组合维度，优先按 DAC 多维模型明细查询 |
| 归属过滤且支持维度升维 | S1 -> S2 -> S3 -> S4 -> S7 | 不因“归属/对应”直接走关系路径，优先按多维模型维度升维查询 |
| 归属过滤且不支持维度升维 | S1 -> S2 -> S3 -> S4a -> S4b -> S7 | 第一次 OAC 沿关系路径查目标主键，第二次 OAC 用主键查指标明细 |
| 聚合统计 / TopN | S1 -> S2 -> S3 -> S4 -> S7 | S3 规划 AGGREGATE，S4 生成聚合查询并返回对象结构或聚合对象结构 |
| Function 前置补齐上下文 | S1 -> S2 -> S3 -> S5 -> S6 -> S4 -> S7 | 先基于 result.functions 选择函数，获取参数规格和 physicalName，函数结果作为 OAC 过滤条件 |

如果用户明确要求只解释模型结构或只输出规划，则可只执行 S1/S2/S3/S7，不执行 S4/S5/S6。

---

## 5. SEC 步骤级定制

### 5.1 S2 子图检索定制

输入给 Planning 的 S2 定制要求：

```text
子图检索规则：
- 根据 SEC 业务意图检索 grid、cell、多维事实对象、指标对象、EPC网络等相关对象。
- 检索 DIM_GRID、GRID_ID、DIM_CELL、CELL_ID、C_RSRP、C_PRB、3600、release_cause 等字段候选。
- 出现“对应/归属”时必须检索 grid 到 cell 的关系候选，但是否使用关系路径由 S3 决定。
- 出现 Function 前置补齐上下文时必须返回 result.functions。
- 子图输出保留 result.seedNodes、result.nodes、result.edges、result.functions、result.actions 原始结构，并输出对象、字段归属、关系候选和函数候选摘要。
```

### 5.2 S3 基于本体子图的任务规划定制

输入给 Planning 的 S3 定制要求：

```text
基于 OAG 子图和 SEC 业务规则规划：
1. 用户只查单对象字段时，规划单对象 QUERY。
2. 用户显式给出栅格 A、小区 B，并查询 RSRP/PRB 等指标时，规划组合维度明细 QUERY。
3. 用户表达“栅格 A 对应/归属的小区指标”时，先判断业务定制文件是否说明支持维度升维；支持时规划明细 QUERY，不支持时规划两步 OAC。
4. 用户表达统计、分组、TopN、平均值、最大值、最小值、计数时，规划 AGGREGATE。
5. 用户要求先标准化对象、补齐上下文或业务定制文件要求 Function 前置时，规划 S5/S6 Function，然后将函数结果写入 S4 过滤条件。
6. 对象、字段、关系、函数候选必须来自 OAG 子图；业务规则可覆盖默认模板和执行顺序，但不能编造子图不存在的平台事实。
```

### 5.3 S4 OAC 查询定制

S4 必须由 Planning 层按平台 OAC 模板生成自然语言委托。SEC 业务规则只注入以下内容：

```text
查数据
本体ID：<公共本体ID>
操作类型：<查询对象属性 / 查询组合维度指标明细 / 查询归属过滤下的指标明细 / 按关系路径查询主键 / 按主键查询指标明细 / 分组统计 / TopN 查询>
查询对象：<来自子图 objectType，例如 grid g、cell c、EPC网络 e>
关系路径：<仅关系主键解析场景填写，关系名必须来自 defines_relation.properties.name；其他场景写无关系路径>
过滤条件：<DIM_GRID、GRID_ID、DIM_CELL、CELL_ID、时间字段、指标条件、ID/NAME 口径等；时间范围必须进入过滤条件>
返回要求：<返回维度字段、指标字段、排序、分组、maxResults、空结果策略>
执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。
期望输出：只返回对象结构结果，包含 objects 和 relationships。
```

### 5.4 S5/S6 Function 定制

仅在用户或业务定制文件明确要求 Function 前置补齐上下文时使用：

```text
函数调用规则：
- 从 OAG result.functions 中按 description 选择目标函数。
- 提取 properties.ontologyId 和 properties.id 作为 get_params_spec 入参。
- 调用 get_params_spec 获取参数规格，解析 physicalName。
- 用用户输入、业务知识和上游结果组装 params。
- 调用 call_function(physicalName, function_id, params)。
- 缺少必填参数时停止并返回缺失项，不得猜测。
```

### 5.5 S7 汇总定制

S7 输出必须保留：

- 最终对象结构 `{objects, relationships}`。
- 使用的业务规则依据。
- 如果是两步查询，说明第一步主键解析结果如何进入第二步查询。
- 如果结果为空，说明按业务规则空结果是有效结果，未自动放宽条件。
- 如果缺少字段、关系、函数或参数规格，输出缺失项和冲突说明。

---

## 6. 业务意图改写规则

用户问题必须改写为详细自然语言业务意图，不能只保留短标签。

示例：

```text
用户问题：查询栅格 A、小区 B 的 RSRP。
业务意图：查询 SEC 多维模型中栅格维度 A 和小区维度 B 组合条件下的小区 RSRP 指标明细；过滤条件包含 DIM_GRID=A、DIM_CELL=B 和用户指定时间范围；返回 DIM_GRID、DIM_CELL、C_RSRP；结果为空即为空，不自动改走关系路径。
```

```text
用户问题：查询栅格 A 对应的小区 PRB。
业务意图：查询栅格 A 归属小区的 PRB 指标；先依据业务定制文件判断 PRB 是否支持通过 DIM_GRID 维度升维直接查询，如果不支持，则先沿 grid 到 cell 的关系路径查询 CELL_ID，再用 CELL_ID 查询 C_PRB；结果为空不重试。
```

---

## 7. 参考文档

- `knowledge/sec-multidim-guidance.md`：SEC 多维查询业务定制主规则文件。
- `workflows/sec-multidim-workflows.md`：典型流程级和步骤级定制示例。
- `../../platform-skill/Ontology-based-planning-skill/SKILL.md`：Planning 层默认步骤和业务定制输入规范。
- `../../platform-skill/Ontology-platform-unified-skill/references/oac-data-access.md`：平台 OAC 数据访问能力说明。
- `../../platform-skill/Ontology-platform-unified-skill/references/ontology-subgraph-search.md`：平台 OAG 子图检索能力说明。
- `../../platform-skill/Ontology-platform-unified-skill/references/call-function.md`：平台 Function 调用能力说明。
