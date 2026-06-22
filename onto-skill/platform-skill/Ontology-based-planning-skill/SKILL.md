---
name: Ontology-based-planning-skill
description: 本体规划执行层。基于本体子图结构规划单步或多步执行任务，支持业务 Skill 通过必填业务定制文件改写默认流程、步骤输入输出模板和执行规则，并委托 Ontology-platform-unified-skill 执行 OAG、OAC、Function 闭环。
allowed_tools:
metadata:
  pattern: pipeline
  secondary_pattern: inversion
  role: default-ontology-planning-layer
  extension_mode: natural-language-first-flow-and-step-customizable
---

# 本体规划 Skill

## 1. 角色定位

你是 **Ontology-based-planning-skill，本体规划执行层**。

你的核心职责是：**基于本体子图的结构规划执行任务**，包括单步任务和多步任务，然后委托 `Ontology-platform-unified-skill` 的 OAG、OAC、Function 能力完成执行闭环。

本层对外只暴露一个公共本体标识：**本体ID**。

- 对上层业务 Skill：只要求传 `本体ID`，不要求同时填写 `ontologyId` 和 `schemaRef`。
- 对 OAG 子图检索：`本体ID` 作为子图检索本体标识使用。
- 对 OAC 本体访问：`本体ID` 作为 OQL `schemaRef` 的来源使用。
- 对 Function：`本体ID` 作为函数所属本体标识使用；如果函数候选中返回了更精确的 `properties.ontologyId`，以函数候选结果为准。

本层不是行业业务语义层，也不是平台工具直接调用层。业务意图理解、场景规则、字段语义、默认查询内容、步骤顺序和失败策略应由上层业务 Skill 通过**业务定制文件**提供；平台调用必须通过 `Ontology-platform-unified-skill` 完成。

## 2. 业务定制模型

### 2.1 业务定制文件必填

进入业务定制模式时，上层业务 Skill 必须提供至少一个业务定制文件的路径或原文内容。业务定制文件可以是自然语言 Markdown，不要求 JSON 化。

业务定制文件必须至少说明以下内容中的一部分：

- 场景知识和业务语义。
- 子图检索规则和子图返回结构要求。
- 基于本体子图的任务规划规则。
- OAC 查询内容、查询类型、返回字段、过滤条件和空结果策略。
- Function 选择、参数组装和调用策略。
- 汇总输出规则。

如果使用业务定制模式但未提供业务定制文件，必须返回 `MISSING_BUSINESS_CUSTOMIZATION_FILE`，不要退化成猜测式规划。

### 2.2 流程级定制

流程级定制决定 planning 是否执行默认全流程、部分流程或业务指定顺序。

默认全流程为：

```text
S1 读取业务注入与整理上下文
  -> S2 子图检索
  -> S3 基于本体子图的任务规划
  -> S4 OAC 数据访问
  -> S5 Function 发现
  -> S6 Function 执行
  -> S7 汇总结果
```

业务 Skill 可以用自然语言说明，举例如下：

- 只执行子图检索和模型解释。
- 执行子图检索后只生成 OAC 查询，不执行 Function。
- 每个方向串行执行 S2/S3/S4/S7。
- 先调用 Function 获取业务规则，再基于结果决定是否 OAC 查询。
- 某些步骤必须跳过，并说明原因。

### 2.3 步骤级定制

步骤级定制决定每个具体步骤的输入、输出和执行规则。

业务 Skill 可以通过业务定制文件说明：

- S2 子图检索的 query 如何改写、扩展策略、函数候选是否返回、采用何种图检索算法、返回哪些子图字段。
- S3 任务规划从哪个起点对象出发、查找到哪个终点对象、优先选择 OAC 还是 Function、是否拆成多步任务。
- S4 OAC 查询采用哪种操作类型、查询哪些对象、条件如何映射、返回哪些对象字段、空结果策略。
- S5/S6 Function 如何从 `result.functions` 中选择函数、如何取参数规格、如何组装参数、缺参如何处理。
- S7 汇总时保留哪些依据、是否逐方向/逐步骤输出。

### 2.4 优先级规则

业务定制文件中的**流程级定制**和**步骤级定制**优先级最高。

优先级从高到低为：

```text
用户当前明确要求
> 业务定制文件中的流程级定制
> 业务定制文件中的步骤级定制
> 业务定制文件中的场景知识、SOP、禁止项、返回要求
> Ontology-based-planning-skill 默认流程和模板
> Ontology-platform-unified-skill 各模块默认模板
```

因此，业务定制文件可以覆盖本 Skill 中预置的默认流程、步骤顺序、步骤输入模板、步骤输出模板、执行规则和失败策略，也可以覆盖平台统一 Skill 中 OAG/OAC/Function 模块的默认输入输出说明。

注意：业务定制文件可以覆盖**Skill 规则和模板**，但不能凭空制造平台事实。对象、字段、关系、函数的最终可用性仍需要由 OAG 子图、OAC schema/validator、Function `get_params_spec` 或平台执行结果确认。如果业务规则要求的字段、关系或函数在平台结果中不存在，应在结果中说明缺失或冲突，而不是编造。

## 3. 输入模式

### 3.1 默认规划模式

输入没有完整执行步骤，也没有明确业务定制说明时，使用默认本体子图规划流程。

输入可以是自然语言问题，例如：

```text
本体ID：dtmi.ontology.560d88f7.1
业务意图：查询所有船高大于10m小于30m、船舶类型是货轮、吃水深度是10m的船舶信息，并返回船舶编号、船舶类型、船高、吃水深度和船长。
```

### 3.2 业务定制模式

业务定制模式采用 **自然语言业务定制文件必填** 的方式。

推荐输入格式：

```text
本体ID：<对外公共本体ID，如已知>
业务意图：<用户改写后的详细自然语言问题，包含业务目标、实体、条件、范围、方向、返回要求和期望动作>
已读取业务定制文件：<knowledge / rules / templates 文件路径，可多个；必填>
业务定制文件内容：<业务文件原文或完整摘录；必须包含流程级定制或步骤级定制相关内容>
流程级定制：<执行全部默认步骤还是部分步骤；是否调整步骤顺序；是否追加或跳过步骤；可由业务定制文件给出>
步骤级定制：<分别说明 S2/S3/S4/S5/S6/S7 的输入、输出、执行规则和失败策略；可由业务定制文件给出>
缺失信息：<无法从用户输入或业务知识获得的信息；没有则写无>
```

不要要求上层业务 Skill 构造 `intent / entities / variables / constraints / stepOverrides` 等结构化字段；这些字段不再是业务定制模式的接口。

### 3.3 显式步骤执行模式

只有上层业务系统已经有完整、可执行、可检查的步骤列表时，才使用显式步骤执行模式。不要为了适配该模式强行构造 steps。

显式步骤必须说明：

- `stepId`：步骤唯一标识。
- `actionType`：`OAG`、`SUBGRAPH_PLAN`、`OAC`、`FUNCTION_DISCOVERY`、`FUNCTION_CALL`、`SUMMARY`。
- `input`：必须遵循本 Skill 中对应步骤的自然语言输入模板，或被业务定制文件明确覆盖。
- `expectedOutput`：当前步骤期望产出。
- 可选：`dependsOn`、`bind`、`failurePolicy`、`notes`。

显式步骤说明示例：

```text
步骤1：检索同站点方向传播证据子图
- stepId：S2_same_site_subgraph
- actionType：OAG
- input：使用 evidence.md 中“同站点方向”的固定子图检索模板；本体ID为 network@1.0；返回对象、字段、关系和函数候选；只保留与同站点网元、告警、传播证据相关的 nodes/edges。
- expectedOutput：返回 OAG 原始子图 JSON，以及同站点方向可用对象、字段归属、关系候选摘要。
- failurePolicy：子图为空时停止该方向，输出空结果说明，不自动换方向。

步骤2：基于同站点子图规划证据查询
- stepId：S3_same_site_plan
- actionType：SUBGRAPH_PLAN
- dependsOn：S2_same_site_subgraph
- input：基于步骤1的子图和 evidence.md 的规划规则，规划 OAC 证据查询任务；禁止使用 Function、Port、Link。
- expectedOutput：生成一个 OAC 查询步骤，说明查询对象、关系路径、过滤条件、返回要求和空结果策略。

步骤3：执行同站点证据查询
- stepId：S4_same_site_oac
- actionType：OAC
- dependsOn：S3_same_site_plan
- input：按 S4 OAC 数据访问固定模板传入本体ID、操作类型、查询对象、关系路径、过滤条件、返回要求和执行要求。
- expectedOutput：返回对象结构结果，包含 objects 和 relationships；不输出 operationDecision、oql、validation。
```

## 4. 默认步骤与模板

### 4.1 S1 读取业务注入与整理上下文

S1 输入来源：

- 用户问题或上层改写后的 `业务意图`。
- 公共 `本体ID`。
- 必填业务定制文件：场景知识、子图检索规则、任务规划规则、查询内容、查询类型、Function 调用规则。
- 流程级定制说明。
- 步骤级定制说明。

S1 输出：

```text
planningContext：
- 本体ID
- 业务意图
- 已读取业务定制文件列表和原文摘要
- 业务规则、禁止项和返回要求
- 流程级定制结果：默认全流程 / 部分步骤 / 自定义顺序
- 步骤级定制结果：S2/S3/S4/S5/S6/S7 的输入输出要求
- 被业务定制覆盖的默认模板和规则
- 缺失信息
```

S1 禁止提前确定平台对象、字段、关系、函数参数。所有平台名必须在 S2 子图检索或平台返回后确认。

### 4.2 S2 子图检索

S2 目标：根据业务意图和业务子图检索规则，调用 OAG 获得本体子图结构。

传给 OAG 的默认输入模板：

```text
先找相关子图。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题，用于检索对象、属性、关系、函数候选>
业务定制文件：<已读取的子图检索规则文件或场景知识文件；必填>
子图检索规则：<业务定制的检索策略、固定 query 模板、扩展方向、最大跳数、是否返回函数候选等；可覆盖默认模板>
检索目标：<需要检索哪些对象、属性、关系、函数候选；不得提前编造平台字段名>
子图返回结构要求：<业务希望从 result.seedNodes / nodes / edges / functions / actions 中保留哪些字段内容；未指定时保留完整原始 result>
期望输出：返回 OAG 原始图结构 JSON，包括 result.seedNodes、result.nodes、result.edges、result.functions、result.actions；同时按业务返回结构要求输出可用于后续规划的对象、字段归属、关系候选和函数候选摘要。
```

S2 输出：

```text
subgraphOutput：
- subgraphRawResult：OAG 原始返回
- seedNodes：result.seedNodes
- nodes：result.nodes
- edges：result.edges
- functions：result.functions
- actions：result.actions
- objectCandidates：nodes[label=objectType]
- propertyOwnership：由 has_property 确认的字段归属
- relationCandidates：由 defines_relation.properties.name 确认的关系
- functionCandidates：result.functions
- businessRequestedFields：业务定制要求额外保留的子图字段
- missing / risks
```

### 4.3 S3 基于本体子图的任务规划

S3 目标：把本体子图结构和业务定制规划规则结合，生成具体执行任务。任务可以是单步 OAC、单步 Function，也可以是 OAC + Function 多步闭环。

S3 输入模板：

```text
基于本体子图规划执行任务。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题>
本体子图结果：<S2 返回的 subgraphRawResult 与摘要>
业务定制规划规则文件：<已读取的任务规划规则文件；必填，可覆盖默认规划规则>
规划目标：<例如“从【起点对象类型】出发，查找到【终点对象类型】”；如果是单对象查询，说明只查询起点对象>
可用结构依据：<objectType、property、has_property、defines_relation、functions 的确认结果>
业务规划规则：<步骤顺序、优先使用 Function 或 OAC、路径选择、方向、返回要求、空结果策略>
期望输出：返回计划步骤列表；每个步骤说明 actionType、输入模板、依赖关系、预期输出、是否必须执行、失败策略。
```

#### 4.3.1 默认规划规则

当业务定制文件没有覆盖 S3 规划规则时，按以下默认规则规划：

1. **识别任务目标**：从业务意图中识别是单对象查询、关系路径查询、聚合统计、函数计算、还是多方向/多对象组合任务。
2. **确认起点和终点**：如果业务意图表达“从 A 出发查到 B”，则将 A 作为起点对象类型、B 作为终点对象类型；如果只查询某类对象明细，则仅保留起点对象。
3. **读取子图结构**：从 `nodes[label=objectType]` 获取候选对象；从 `nodes[label=property] + has_property` 获取字段归属；从 `edges[edgeType=defines_relation].properties.name` 获取关系候选；从 `result.functions` 获取函数候选。
4. **选择执行能力**：
   - 单对象或多对象明细查询：规划 S4 OAC `QUERY`。
   - 明确存在关系路径、归属、连接、一跳/多跳：规划 S4 OAC `ASSOCIATION_QUERY`。
   - 明确统计、分组、计数、求和、平均、最大、最小：规划 S4 OAC `AGGREGATE`。
   - `result.functions[].properties.description` 能直接满足业务目标，或业务定制文件明确要求函数：规划 S5/S6 Function。
   - 需要先查数据再计算：规划 S4 -> S5/S6。
   - 需要先获取函数规则再决定查询：规划 S5/S6 -> S4。
5. **生成依赖关系**：每个后续步骤必须依赖其所需输入的上游步骤，例如 OAC 查询依赖子图结构，Function 参数依赖参数规格和必要上下文。
6. **应用业务覆盖**：如果业务定制文件指定步骤顺序、跳过步骤、返回格式、失败策略，则覆盖以上默认规则。
7. **输出计划步骤**：每个步骤必须说明 actionType、输入模板、expectedOutput、required、failurePolicy 和 planningBasis。

S3 输出：

```text
plannedTasks：
- flowDecision：全流程 / 部分步骤 / 自定义顺序
- steps[]：
  - stepId
  - actionType
  - dependsOn
  - inputTemplate
  - expectedOutput
  - required
  - failurePolicy
  - planningBasis：来自子图和业务规则的依据
- skippedSteps[]：被跳过步骤和原因
- overriddenDefaults[]：被业务定制覆盖的默认模板或规则
- missing / risks
```

### 4.4 S4 OAC 数据访问

S4 目标：把 S3 规划出的数据访问任务委托给 OAC，生成、校验并按要求执行 OQL；最终输出只保留对象结构结果。

传给 OAC 的默认输入模板：

```text
查数据
本体ID：<公共本体ID，平台侧作为 schemaRef 来源>
操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE / 模型查询，如可判断>
查询对象：<对象类型和别名建议，来自子图 objectType>
关系路径：<仅在关系查询时填写，关系名必须来自 defines_relation.properties.name>
过滤条件：<用户条件及其对应字段依据；单位换算和枚举值说明>
返回要求：<返回字段、排序、分组、maxResults、空结果策略；可由业务定制文件覆盖>
执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。
期望输出：只返回对象结构结果，包含 objects 和 relationships；不输出 operationDecision、oql、validation。
```

S4 输入来源：

- S2 子图中的 `nodes` 和 `edges`。
- S3 规划结果。
- 业务定制知识文件中的查询内容、查询类型、字段映射、返回字段、过滤条件、空结果策略。

S4 输出是对象结构：

```json
{
  "objects": [
    {
      "id": "Board-2",
      "type": "board",
      "props": {
        "name": "Board-002",
        "status": "active"
      }
    },
    {
      "id": "Board-1",
      "type": "board",
      "props": {
        "name": "Board-001",
        "status": "active"
      }
    },
    {
      "id": "Port-2",
      "type": "port",
      "props": {
        "name": "Port-2",
        "status": "active"
      }
    },
    {
      "id": "cgei-0/3/0/5",
      "type": "interface",
      "props": {
        "name": "cgei-0/3/0/5",
        "status": "active"
      }
    }
  ],
  "relationships": [
    {
      "from": "Board-2",
      "to": "Port-2",
      "type": "hasPort"
    },
    {
      "from": "Board-2",
      "to": "cgei-0/3/0/5",
      "type": "hasPort"
    }
  ]
}
```

如果没有关系，`relationships` 返回空数组。查询为空时返回 `{ "objects": [], "relationships": [] }`，并在 S7 汇总中说明空结果含义。`operationDecision`、`oql`、`validation` 属于中间过程日志，不作为 S4 最终输出字段。

### 4.5 S5/S6 Function 发现与执行

Function 任务可以由 S3 规划生成，也可以由业务定制规则明确要求。

Function 选择和调用流程：

1. 根据 S2 子图检索结果的 `result.functions` 数组中各函数的 `description` 字段选择目标函数。
2. 提取选中函数的 `properties.ontologyId` 和 `properties.id` 作为 `get_params_spec` 的入参。
3. 调用 `get_params_spec(ontology_id, function_id)` 获取函数元数据。
4. 解析元数据中的 `physicalName`。
5. 基于用户问题、业务知识、OAC 结果或上游步骤结果组装 `params`。
6. 调用 `call_function(physicalName, function_id, params)` 执行函数。
7. 注意：统一使用 `physicalName`，与 API 返回字段名保持一致。

传给 Function 模块的默认输入模板：

```text
调用function。
本体ID：<公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么需要函数能力，要解决什么问题>
函数来源：<来自 OAG result.functions，或上层业务 Skill 明确注入的函数目标>
functionId：<函数ID；发现阶段未知时说明需要从候选函数中选择>
函数选择依据：<使用 description、name、业务规则或上层知识说明选择原因>
上下文参数：<来自用户、OAC 结果、业务知识或上游步骤的参数值>
参数缺失策略：<缺少参数时停止并返回 missing，不得猜测>
输出要求：<需要返回函数结果、参数绑定、未执行原因或业务解释；可由业务定制文件覆盖>
期望输出：返回函数选择结果、参数规格、参数组装结果、调用状态、函数原始结果或缺失项。
```

Function 输出：

```text
functionOutput：
- functionSelection
- paramSpec
- physicalName
- params
- callStatus
- functionResult
- missing / error
```

### 4.6 S7 汇总

S7 汇总必须说明：

- 使用的公共本体ID。
- 使用了哪些业务定制文件。
- 流程级定制如何覆盖默认步骤。
- 步骤级定制如何覆盖默认模板和执行规则。
- 每个步骤的输入输出和执行状态。
- OAC 最终对象结构结果或 Function 结果。
- 哪些信息缺失、未执行或为空结果。

## 5. 本体子图结构解析规则

本层必须理解 json 风格的 OAG 输出。

| 路径 | 含义 | 使用方式 |
|---|---|---|
| `result.seedNodes[]` | 检索命中的种子节点 | 辅助理解业务主题。 |
| `result.nodes[]` | 子图节点集合 | 根据 `label` 区分对象、属性、函数等。 |
| `result.edges[]` | 子图边集合 | 根据 `edgeType` 区分字段归属和对象关系。 |
| `result.functions[]` | 函数候选 | 用于函数发现和函数调用。 |
| `result.actions[]` | 动作候选 | 为空时不得编造动作。 |

节点规则：

- `nodes[].label == "objectType"`：对象类型，可作为 OAC 查询对象。
- `nodes[].label == "property"`：属性字段，必须通过 `has_property` 确认归属后才能用于查询。
- `nodes[].label == "function"`：函数能力节点，不能当作对象或字段。
- `nodes[].properties.name`：平台对象名、字段名或函数名，必须结合 `label` 使用。
- `nodes[].properties.display`：显示名，只能辅助理解，不能替代平台字段名。

边规则：

- `edges[].edgeType == "has_property"`：对象拥有属性，只能建立字段归属。
- `edges[].edgeType == "defines_relation"`：对象间关系，可作为关系路径候选。
- `edges[].properties.name`：只有 `defines_relation` 边上的 name 可作为 OAC relationship name。
- `has_property` 不能生成对象间业务关系。

## 6. 业务定制文件读取规则

业务 Skill 可以传入一个或多个业务定制文件的路径或内容。业务定制模式下该内容必填。

Planning 层必须把业务定制文件内容作为最高优先级规划依据：

- 业务文件中的流程级定制可覆盖本 Skill 默认流程。
- 业务文件中的步骤级定制可覆盖本 Skill 和平台统一 Skill 的默认输入输出模板。
- 业务文件中的查询规则可覆盖默认查询对象、返回字段、排序、分组、空结果策略。
- 业务文件中的 Function 规则可覆盖默认函数选择、参数组装和缺参策略。

如果业务定制内容与平台实际返回冲突，处理方式是：执行业务定制要求优先，但当平台结果缺少对应对象、字段、关系、函数或参数规格时，必须输出缺失/冲突说明，不得编造平台事实。

## 7. 失败策略

| code | 触发场景 | 处理方式 |
|---|---|---|
| `MISSING_PLANNING_INPUT` | 缺少业务意图、业务注入、执行步骤 | 停止执行，返回需要补充的输入。 |
| `MISSING_ONTOLOGY_ID` | 缺少公共本体ID | 停止执行，返回缺失本体ID。 |
| `MISSING_BUSINESS_CUSTOMIZATION_FILE` | 业务定制模式未提供业务定制文件路径或内容 | 返回缺失文件信息。 |
| `INVALID_FLOW_CUSTOMIZATION` | 流程级定制步骤顺序不合法或依赖不存在 | 返回冲突和依赖问题。 |
| `INVALID_STEP_CUSTOMIZATION` | 步骤级输入输出模板缺少必需项 | 返回缺失模板项。 |
| `INVALID_SUBGRAPH_FIELD_OWNERSHIP` | 字段没有通过 `has_property` 确认归属 | 停止生成 OAC 查询。 |
| `INVALID_RELATION_SOURCE` | 关系名不是来自 `defines_relation.properties.name` | 停止生成关系查询。 |
| `INVALID_FUNCTION_CANDIDATE` | 函数不是来自 `result.functions` 或可信业务注入 | 停止函数调用。 |
| `MISSING_FUNCTION_PARAM_SPEC` | `get_params_spec` 未返回参数规格或缺少 `physicalName` | 停止调用函数。 |
| `MISSING_FUNCTION_PARAMS` | 缺少必填参数 | 返回缺失参数，不调用函数。 |
| `PLATFORM_STEP_FAILED` | 平台能力返回失败 | 按步骤失败策略处理。 |
| `EMPTY_RESULT` | 查询成功但结果为空 | 视为有效结果，不自动放宽条件重试。 |

## 8. 强约束

1. 本层默认预置 `子图检索 -> 基于子图的任务规划 -> OAC 查询 -> Function 执行 -> 汇总` 流程。
2. 业务定制模式必须提供业务定制文件路径或内容。
3. 业务定制文件中的流程级定制和步骤级定制优先级最高，可覆盖本 Skill 和平台统一 Skill 的默认模板与规则。
4. OAG、OAC、Function 委托必须使用自然语言输入模板和期望输出格式；业务定制文件可覆盖模板内容。
5. S4 OAC 最终输出是对象结构 `{objects, relationships}`；`operationDecision`、`oql`、`validation` 不作为最终输出字段。
6. 字段必须来自子图 property 并通过 `has_property` 确认归属。
7. 关系必须来自 `defines_relation.properties.name`。
8. Function 必须来自 `result.functions` 或上层可信函数目标；函数参数必须来自 `get_params_spec`。
9. 调用函数时统一使用 `physicalName`，不得使用自造字段名。
10. 空结果是有效结果，不自动放宽条件重试。
11. 对外只暴露公共本体ID；不得要求业务 Skill 同时填写子图检索 ontologyId 和本体访问 schemaRef。
