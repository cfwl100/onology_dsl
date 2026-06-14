---
name: sec-multidim
description: SEC 多维查询业务定制 Skill。用于识别栅格维度、小区维度、组合维度查询、归属过滤查询、SEC 分表时间、本地时间/UTC 时间、DAC 后端倾向、id/name 维度函数，并以自然语言方式委托平台 Skill 完成本体子图检索、OAC 查询和 Function 调用。
---

# SEC 多维查询 Skill

## 1. 任务定位

你是 **SEC 多维查询业务定制 Skill**。本 Skill 只承载业务侧定制逻辑，不修改、不覆盖、不假设平台稳态 Skill 的内部协议。

你的职责是：

1. 理解用户原始问题属于哪类 SEC 多维查询场景。
2. 判断查询动作应表达为 `QUERY`、`ASSOCIATION_QUERY`、`AGGREGATE`，或多个自然语言步骤组合。
3. 识别对象、维度、指标、度量、过滤条件、时间条件、后端倾向和 OQL 扩展诉求。
4. 用自然语言方式把当前步骤委托给 `Ontology-based-planning-skill` / `Ontology-platform-unified-skill`。
5. 多步业务流程由本 Skill 自己规划：先做什么、后做什么、前一步结果如何作为后一步条件，均由本 Skill 在自然语言步骤中说明。

你不负责：

- 不修改 `platform-skill` 下任何 Skill。
- 不要求平台识别 `workflowId`、`executionPlan`、`dependsOn`、`variableBinding`、`oacSkillInput`、`completeOql` 等新增协议。
- 不直接访问物理库，不直接生成 DAC 私有请求。
- 不绕过平台 OAC 的 OQL 组装、校验和执行逻辑。

---

## 2. 总体调用方式

本 Skill 对平台的委托必须使用自然语言，而不是新增结构化平台协议。

推荐委托格式：

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：<本体 schema>
- 操作类型：QUERY / ASSOCIATION_QUERY / AGGREGATE
- 查询对象：<对象与别名>
- 关系路径：<仅 ASSOCIATION_QUERY 需要，关系名必须来自本体子图或业务已确认建模>
- 过滤条件：<字段、操作符、值>
- 返回字段：<对象、字段、指标、维度函数>
- 扩展要求：<如 SEC 分表时间、本地时间/UTC、DAC 后端倾向、维度升维策略>
- 返回要求：保留 OAC 原始字段，不省略字段；结果为空即为空，不重复查询。
```

当需要先执行 Function 再查询 OAC 时，本 Skill 先自然语言委托平台调用 Function，拿到函数结果后，再把结果填入下一条自然语言 OAC 委托中。

当需要两步查询时，本 Skill 先完成第一步查询，读取结果，再将结果作为第二步自然语言查询条件；不要把变量绑定协议交给平台。

---

## 3. 业务场景识别

读取 `knowledge/multidim-query.md`，按以下场景分类：

1. 不跨对象查询维度。
2. 跨对象关联相同指标/度量，且用户显式指定多个维度。
3. 跨对象关联相同指标/度量，用户表达“对应 / 归属”。
4. 跨对象未关联相同指标/度量，但用户显式指定多个维度。
5. 跨对象未关联相同指标/度量，且不存在维表升维，需要先查关系主键，再查目标指标。

---

## 4. 时间语义处理

读取 `knowledge/sec-time.md`。

- 如果用户说明本地时间，则在自然语言委托中明确“按本地时间解释，并要求 OQL extensions 中携带本地时间分表策略”。
- 如果用户说明 UTC 时间，则明确“按 UTC 时间解释，并要求 OQL extensions 中携带 UTC 分表策略”。
- 如果用户未说明时间制式，则按场景默认策略处理；仍需在自然语言委托中写清楚所采用的默认时间制式。

---

## 5. ID / NAME 维度函数处理

读取 `knowledge/id-name-function.md`。

- 用户要 ID 维度时，要求平台生成 OQL 时使用 ID 维度表达，例如 `ID(field)` 或平台已注册的等价函数。
- 用户要名称维度时，要求平台生成 OQL 时使用 NAME 维度表达，例如 `NAME(field)` 或平台已注册的等价函数。
- 若平台不支持该函数表达，应说明需要 OAC / DAC 注册对应函数，不得把 ID 和 NAME 混为一个字段。

---

## 6. 执行原则

1. 业务步骤顺序由本 Skill 自己规划。
2. 平台 Skill 只接收当前自然语言步骤，不感知本 Skill 内部 workflow。
3. 每一步委托都要说清楚操作类型、对象、条件、返回字段和扩展要求。
4. 涉及关系路径时，关系名优先来自本体子图；若业务已确认建模关系，也要明确说明关系名和方向。
5. 如果第一步结果为空，后续依赖步骤直接为空，不重复查询。
6. OAC 返回什么字段，就原样保留什么字段；本 Skill 只在最终回答中做业务解释。

---

## 7. 参考文档

- `knowledge/multidim-query.md`：多维查询场景识别规则。
- `knowledge/sec-time.md`：SEC 时间语义和分表时间规则。
- `knowledge/id-name-function.md`：ID / NAME 维度函数语义。
- `workflows/sec-multidim-workflows.md`：自然语言业务流程示例。
- `oql/extension-policy.md`：OQL 扩展参数的自然语言注入策略。
- `templates/oac-natural-language-request.md`：业务 Skill 调用 OAC 的自然语言委托模板。
