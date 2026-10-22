---
name: ontology-platform-unified-skill
description: 本体平台能力包装器。检索本体子图(OAG)、生成并执行 OQL 查询(OAC:QUERY/ASSOCIATION_QUERY/AGGREGATE)、发现并调用平台函数(Function)。查本体模型/子图、查数据统计聚合、生成或执行 OQL、调用函数时使用。
metadata:
  pattern: tool-wrapper
---

# 本体平台统一入口

本体平台能力包装器：把上层请求路由到三类真实能力并执行，不做跨阶段业务规划（由上层 Skill 编排）。本文件已内聚全部规则，无需读取其它文档即可完成生成与调用。

## 问数直连原则（性能关键）
问数场景下 OAG 与 OAC 是**一个连续编排步**：OAG 返回原始子图后，**直接消费原始子图生成 OQL 并调 OAC**，中间不得插入"摘要子图""生成 todo""重新规划"等独立 LLM 轮次——这是历史性能问题的主因。判型在生成 OQL 时一并完成。

## 能力路由
| 意图 | 能力 | 见 |
|---|---|---|
| 查本体模型、对象字段、关系结构 | 子图检索 OAG | 「OAG」 |
| 查数据、统计、聚合、路径、生成/执行 OQL | 数据访问 OAC | 「OAC」 |
| 查找函数、确认入参、调用函数 | 函数 Function | 「Function」 |

---

## OAG 子图检索

用上层传入的 query 检索本体子图。先检索，不跳过检索直接假设子图。

```bash
python scripts/semantic_subgraph_search.py --query "<问题/业务主题>" --ontology-id "<本体ID>"
```
也可 `--query-json '<json>'` 传可选参数。

- 必填：`query`。可选：`ontology-id`、`similarity-threshold`(0.6)、`include-functions`(0/1)、`seed-retrieval-mode`(hybrid)、`topK`(3)、`graph-expansion-strategy`(minimal)、`adaptive-retrieval`(1)、`hopLimit`(3)。
- query 规范（按形态选模板，不混用）：单对象明细/过滤 `【对象】携带【属性1】、【属性2】…`；关系/路径 `从【对象1】到【对象2】之间的路径，其中[对象1]携带【属性1]，[对象2]携带【属性2】【属性3】`。
- **输出：直接返回原始 `result.nodes`/`result.edges`/`result.functions`。调用方应直接消费原始子图生成 OQL，不得单独"摘要子图"或"生成 todo 任务清单"再规划。**
- 检索为空/噪声大时明确说明结果不足，不虚构子图。
- 边界：不当数据查询；无子图结果不给确定性路径结论；不直接执行函数或写数据。

### 子图 → OQL 直连映射（生成 OQL 时一次完成）
| 子图元素 | OQL 对应 |
|---|---|
| node 的 `objectType` | `objects[].objectType` |
| `property` + `has_property` 归属 | `conditions.field` / `returns.fields` |
| edge / `defines_relation.properties.name` | `relationships[].relationshipType` |
| `result.functions` | Function 候选（见「Function」） |

---

## OAC 数据访问

生成、校验、执行 OQL，返回对象结构结果。不做子图检索、意图识别、函数调用。

### 输入来源
1. 本体子图依据：OAG 的 `result.nodes`/`result.edges`/`result.functions`（**直接消费原始结构**，无需先摘要）。
2. 业务定制知识：查询内容、类型、返回字段、过滤、排序分组、空结果策略（优先级最高，可覆盖默认）。

**不能凭空制造平台事实**：对象须来自子图 `objectType`；字段须来自子图 `property` 并经 `has_property` 确认归属；关系须来自 `defines_relation.properties.name`；OQL 须通过 schema 与 validator。`本体ID` 作 `schemaRef` 来源，上游已给则原样保留不编造，上游不给则`schemaRef`参数不设置。

### 操作类型路由（判型在生成 OQL 时一并完成）
- **不显式依赖本体关系路径**，只查对象属性/明细/列表/字段值 → `QUERY`
- **显式依赖本体关系路径**（关系/路径/遍历/归属/连接/一跳/多跳）→ `ASSOCIATION_QUERY`；无论返回明细还是包含分组、计数、求和、平均、极值、聚合后过滤，都保持 `ASSOCIATION_QUERY`
- **不显式依赖本体关系路径**，但需要统计/聚合/分组/计数/求和/平均/极值/聚合后过滤 → `AGGREGATE`

### OQL 公共结构（`version` 固定 `"1.0"`，契约以 `schemas/` 下 schema 为准）
- 顶层：`version`、`schemaRef`、`strict`、`operation`、`objects[]`、`conditions`、`returns[]`、`maxResults`。
- `objects[]`：`{ "objectType", "alias" }`；别名默认同对象名，同名多个加数字后缀（如 `ne1`/`ne2`）。
- `maxResults` 用数字（如 `1000`），不用 `{"limit":..,"offset":..}`。
- `returns.kind=FIELDS.fields` 支持 `["*"]`（返回该 ref 全部字段），**仅此处允许**；条件/排序/表达式/GROUP_BY/非 COUNT 聚合字段禁用 `*`。
- `conditions` 为递归逻辑树：`GROUP`(`relation`+`children[]`) 或 `PREDICATE`(`ref`/`field`/`operator`/`values[]`)；`values` 须结合上下文真实数据显式赋值，不虚构。

### 操作符
| 操作符                                     | `values` 取值规则 | 说明                              |
|-----------------------------------------| ----------------- | --------------------------------- |
| `EQ` / `NE`                             | 恰好 1 个值       | 等于 / 不等于                     |
| `GT` / `GTE` / `LT` / `LTE`             | 恰好 1 个值       | 大于 / 大于等于 / 小于 / 小于等于 |
| `IN` / `NOT_IN`                         | 至少 1 个值       | 属于 / 不属于                     |
| `CONTAINS`                              | 恰好 1 个字符串值 | 字符串包含匹配                    |
| `BETWEEN`                               | 恰好 2 个值       | 范围（包含边界），如 `BETWEEN [10, 100]` |
| `STARTS_WITH`                           | 恰好 1 个字符串值 | 前缀匹配                          |
| `ENDS_WITH`                             | 恰好 1 个字符串值 | 后缀匹配                          |
| `IS_NULL`                               | 不允许            | 空值判断                          |
| `IS_NOT_NULL`                           | 不允许            | 非空判断                          |
| `IS_EMPTY`                              | 不允许            | 空字符串判断                      |
| `IS_NOT_EMPTY`                          | 不允许            | 非空字符串判断                    |
| `EXISTS`                                | 不允许，需定义 `subquery` | 子查询结果存在时返回 true                    |
| `NOT_EXISTS`                            | 不允许，需定义 `subquery` | 子查询结果不存在时返回 true                    |
	

### 各操作要点
- **QUERY**（无关联明细）：声明 `objects`+`returns`；不用 `relationships`/`aggregateFilter`/`mutation`；`returns.ref` 引用 `objects[].alias`；不把聚合/关系写入 returns。
- **ASSOCIATION_QUERY**（关联路径）：必须声明 `objects`+`relationships`+`returns`；每条关系含 `relationshipType`/`alias`(r1,r2..)/`from`/`to`，`from`/`to` 引用 `objects[].alias`，多跳前跳 `to`=后跳 `from`；支持两种互斥返回模式：①明细模式仅 `FIELDS`/`EXPR`/`FUNCTION`；②聚合模式仅 `GROUP_BY`/`METRIC` 且至少一个 `METRIC`。聚合模式可使用 `aggregateFilter`，其 `metricAlias` 必须引用同层 `METRIC.alias`；`conditions` 始终表示关系展开后的聚合前明细过滤。只要统计依赖 `relationships`，不得切换为 `AGGREGATE`。
- **AGGREGATE**（无关联聚合统计）：仅用于**不显式依赖 `relationships`** 的聚合；必须声明 `objects`+`returns`，`returns` 至少一个 `METRIC`，可含 `GROUP_BY`；不用 `relationships`/`mutation`/非聚合返回项；`COUNT` 可统计全部，`SUM`/`AVG`/`MIN`/`MAX` 须绑可聚合字段；`aggregateFilter`（聚合后过滤，类似 HAVING）`metricAlias` 须引用 `returns` 中 `METRIC.alias`；`conditions` 为聚合前明细级过滤，`ref` 引用 `objects[].alias`。

### 生成与执行流程（直连，无中间规划轮）
1. 由 OAG 原始子图事实 + 业务定制，**一次生成** OQL JSON（判型同时完成）。
2. 调用（脚本内部自动完成 OQL 校验，校验通过后执行）：
```bash
python scripts/execute_oac_operation.py --oac-json '<compact-json>' --message-type "<type>"
```
3. 校验失败只修 OQL 不执行；将结果转为 `{objects, relationships}` 返回。

### 命令规范
默认逐行命令 + 绝对脚本路径，禁用 `&&`/`||`/管道/Shell 专属变量（Windows PowerShell 5.1 不支持 `&&`）。复杂/长 OQL 优先 `--input <json文件>`（用 `json.dumps(ensure_ascii=False)` 程序化写文件，校验与执行复用同一文件）；短 JSON 且 Shell 引号安全才用 `--oac-json`，解析报错立即改用 `--input`。

### 输出格式
```json
{ "objects": [], "relationships": [] }
```
`objects[].id/.type/.props`；`relationships[]` 无关系时空数组。成功但空 → `{ "objects":[], "relationships":[] }`；错误/缺失由外层说明，不混入对象字段。

### 执行边界
- `execute_oac_operation.py` 内部已完成 OQL 校验，但真实执行依赖服务环境 `SERVICE_NAMESPACE`/`TENANT_ID`；缺失时报环境缺失，不得把校验成功误判为执行成功，不得自动切 mock。
- 未校验不执行；未知函数参数规格不调用函数；用户指定完整多跳路径不拆成单跳。

### 空结果处理（重要）
查询结果为空说明本体中确实无匹配数据，直接返回空结果，不自动重试或放宽条件。空结果是有效结果，不等于查询错误。不得在空结果时自动移除过滤条件、扩大 `maxResults`、修改 `conditions` 或更换查询对象；由用户决定是否调整查询策略。

### 最小示例
QUERY：
```json
{ "version":"1.0","schemaRef":"<本体ID>","strict":true,"operation":"QUERY",
  "objects":[{ "objectType":"device","alias":"d" }],
  "conditions":{ "kind":"PREDICATE","ref":"d","field":"status","operator":"EQ","values":["running"] },
  "returns":[{ "kind":"FIELDS","ref":"d","fields":["device_id","status"] }],
  "maxResults":1000 }
```
AGGREGATE：
```json
{ "version":"1.0","schemaRef":"<本体ID>","strict":true,"operation":"AGGREGATE",
  "objects":[{ "objectType":"cell_kpi","alias":"k" }],
  "returns":[{ "kind":"METRIC","function":"COUNT","ref":"k","field":"id","alias":"cnt" }],
  "maxResults":1000 }
```
ASSOCIATION_QUERY：`objects[]`+`relationships[]`(`relationshipType`/`alias`/`from`/`to`)+`conditions`(GROUP/PREDICATE)+`returns`。关系明细使用 `FIELDS/EXPR/FUNCTION`；关系聚合使用 `GROUP_BY/METRIC`（至少一个 `METRIC`），并可带 `aggregateFilter`，详见 `schemas/oql-association-query.schema.json`。

#### 三对象关联聚合最小示例

以下示例用于说明三个本体对象通过两条关系完成关联聚合。示例不绑定任何具体物理表名、字段名或客户模型，真实对象、属性和关系必须来自 OAG 返回的本体子图，物理主外键关系由 OMS binding 解析。

| 本体逻辑对象 | 示例 alias | 典型绑定语义 |
|---|---|---|
| 事实对象 A | `a` | 以 `<统计周期字段> + <主体标识字段>` 标识一个周期内的事实记录 |
| 主体对象 B | `b` | 通过 `<统计周期字段> + <主体标识字段>` 与事实对象 A 建立绑定 |
| 明细对象 C | `c` | 通过 `<统计周期字段> + <主体标识字段>` 与主体对象 B 建立绑定 |

关系链可抽象表达为：**事实对象 A → 主体对象 B → 明细对象 C**。若底层采用关系型数据源，OMS binding 可将两条本体关系解析为类似以下组合键关联：

```text
a.<统计周期字段> = b.<统计周期字段> AND a.<主体标识字段> = b.<主体标识字段>
b.<统计周期字段> = c.<统计周期字段> AND b.<主体标识字段> = c.<主体标识字段>
```

这些物理关联条件**不写入 OQL `conditions` 或 `relationships`**。OQL 只声明本体对象及本体关系；`objectType`、`relationshipType` 和字段名都必须使用 OAG 返回的真实本体元素，下面的尖括号内容仅为泛化占位符。

示例问题：**统计某个周期，按主体分类和明细状态分组，汇总事实指标。**

```json
{
  "version":"1.0",
  "schemaRef":"<本体ID>",
  "strict":true,
  "operation":"ASSOCIATION_QUERY",
  "objects":[
    {"objectType":"<事实对象A>","alias":"a"},
    {"objectType":"<主体对象B>","alias":"b"},
    {"objectType":"<明细对象C>","alias":"c"}
  ],
  "relationships":[
    {"relationshipType":"<A关联B关系>","alias":"r1","from":"a","to":"b","direction":"OUTBOUND","mode":"ONE"},
    {"relationshipType":"<B关联C关系>","alias":"r2","from":"b","to":"c","direction":"OUTBOUND","mode":"ONE"}
  ],
  "conditions":{
    "kind":"PREDICATE","ref":"b","field":"<统计周期字段>","operator":"EQ","values":["<目标周期>"]
  },
  "returns":[
    {"kind":"GROUP_BY","ref":"b","field":"<主体分类字段>","alias":"subjectCategory"},
    {"kind":"GROUP_BY","ref":"c","field":"<明细状态字段>","alias":"detailStatus"},
    {"kind":"METRIC","function":"SUM","ref":"a","field":"<事实指标字段>","alias":"totalMetric"}
  ],
  "orders":[
    {"field":"totalMetric","direction":"DESC"}
  ],
  "maxResults":1000
}
```

该示例体现三个关键原则：① 三个对象的物理表名和组合主外键不进入 canonical OQL；② OQL 只使用 OAG 返回的对象、属性、关系语义，OMS binding 负责把两条本体关系转换为真实物理关联；③ 查询显式依赖两条 `relationships`，因此即使包含 `GROUP_BY + SUM`，operation 仍必须为 `ASSOCIATION_QUERY`，不能改成 `AGGREGATE`。

---

## Function 函数调用

根据子图函数候选选择函数、取参数规格、组装参数、调用、返回结果。不与数据访问混在同一步。

### 输入来源
OAG 子图 `result.functions`，或业务 Skill 注入的函数目标；公共 `本体ID`，候选返回更精确 `properties.ontologyId` 时以候选为准；参数值来自用户/OAC 结果/业务知识/上游步骤。业务定制规则优先级最高，但不能跳过 `get_params_spec`、不凭空制造函数事实。

### 子图返回的 functions 结构
```json
{ "id":"<function_id>","label":"function","properties":{ "qualifiedName":"<限定名>","description":"{\"zh\":\"<描述>\"}","ontologyId":"<id>","id":"<function_id>","name":"<名>","status":"ACTIVE","inputParams":"<JSON 字符串，参数定义>" } }
```

### 调用流程
1. 遍历 `result.functions`，按 `properties.description` 中文描述与业务目标匹配（业务定制指定规则时优先），选中后提取 `properties.ontologyId`→`ontology_id`、`properties.id`→`function_id`。候选不足/不匹配返回"未发现可用函数"，不编造。
2. 取参数规格：
```bash
python scripts/get_function_params_spec.py --ontology-id <ontology_id> --function-id <function_id>
```
解析 `physicalName`（缺失则返回 `MISSING_FUNCTION_PARAM_SPEC` 不继续）。
3. 基于用户/业务/OAC/上游结果组装 `params`：必填须有来源，可选无上下文值可用默认值；类型须匹配 `str`/`int`/`bool`/`list`/`dict`/自定义对象（自定义对象需先 OAC 查全字段再组装）；缺必填返回缺失项不调用。
4. 执行（统一用 `physicalName`，禁 `physical_name`/`physical`/自行拼接）：
```bash
python scripts/get_function_result.py --physicalName <physicalName> --function-id <function_id> --params '<json>'
```

### 输出
区分：函数选择（id/name/ontologyId/依据）、参数规格（physicalName/required/optional）、参数组装（params/来源/缺失）、调用状态（是否调用/方式/失败原因）、函数结果（原始/摘要/错误），保留平台真实返回不编造。

### 错误处理
`result.functions` 为空→不调用；描述不匹配→候选不足不编造；`get_params_spec` 失败/`physicalName` 缺失→停止；参数校验失败→指出缺失/类型不符；`call_function` 失败→保留真实错误。不把 Function 调用当 OAC 查询；不忽略能直接满足目标的候选。

---

## 目录
- `schemas/`：OQL 结构契约（QUERY/ASSOCIATION_QUERY/AGGREGATE），脚本运行时加载；生成 OQL 以本文件结构为准，无需逐字段查阅。
- `scripts/`：`semantic_subgraph_search.py`(OAG)、`execute_oac_operation.py`(OAC，含内部校验)、`get_function_params_spec.py`/`get_function_result.py`(Function)、`oql_validator.py`(校验内核)。
