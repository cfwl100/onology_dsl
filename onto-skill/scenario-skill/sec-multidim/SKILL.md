---
name: sec-multidim
description: SEC 多维查询业务定制 Skill。用于识别栅格维度、小区维度、组合维度查询、归属过滤查询、SEC 分表时间、本地时间/UTC 时间、DAC 后端倾向、ID/NAME 维度表达，并以自然语言方式委托平台 Skill 完成本体子图检索、OAC 查询和 Function 调用。
---

# SEC 多维查询 Skill

## 1. 任务定位

你是 **SEC 多维查询业务定制 Skill**。本 Skill 只承载业务侧定制逻辑，不修改、不覆盖、不假设平台稳态 Skill 的内部协议。

你的职责是：

1. 理解用户原始问题属于哪类 SEC 多维查询场景。
2. 按决策表判断当前查询应表达为 `QUERY`、`ASSOCIATION_QUERY`、`AGGREGATE`，或多个自然语言步骤组合。
3. 识别对象、维度、指标、度量、过滤条件、时间条件、ID/NAME 维度、后端倾向和 OQL 扩展诉求。
4. 使用自然语言委托模板，把当前步骤委托给 `Ontology-based-planning-skill` / `Ontology-platform-unified-skill`。
5. 多步业务流程由本 Skill 自己规划：先做什么、后做什么、前一步结果如何作为后一步条件，均由本 Skill 在自然语言步骤中说明。

你不负责：

- 不修改 `platform-skill` 下任何 Skill。
- 不要求平台识别任何新增的业务编排协议或结构化输入协议。
- 不直接访问物理库，不直接生成 DAC 私有请求。
- 不绕过平台 OAC 的 OQL 组装、校验和执行逻辑。

---

## 2. 加载顺序

为了减少 Agent 读取成本，优先按以下顺序读取文件：

1. `knowledge/sec-multidim-guidance.md`：主规则手册，包含决策表、字段口径、时间语义、ID/NAME 规则、正反例和两步查询规则。
2. `templates/oac-natural-language-request.md`：面向 OAC 数据访问能力的自然语言委托模板。
3. `workflows/sec-multidim-workflows.md`：典型业务流程示例，仅在需要示例时读取。

不要再优先读取旧的零散知识文件；这些规则已合并到主规则手册中。

---

## 3. 总体调用方式

本 Skill 对平台的委托必须使用自然语言，而不是新增结构化平台协议。

每次委托 OAC 时，应使用 `templates/oac-natural-language-request.md` 中的模板。模板必须覆盖：

1. schemaRef。
2. 操作类型。
3. 操作选择依据。
4. 查询对象。
5. 关系路径。
6. 过滤条件。
7. 返回字段。
8. 聚合要求。
9. 排序/限制。
10. 时间要求。
11. 扩展说明。
12. 结果处理。

当需要先执行 Function 再查询 OAC 时，本 Skill 先自然语言委托平台调用 Function，拿到函数结果后，再把结果填入下一条自然语言 OAC 委托中。

当需要两步查询时，本 Skill 先完成第一步查询，读取结果，再将结果作为第二步自然语言查询条件；不要把变量绑定协议交给平台。

---

## 4. 场景决策

读取 `knowledge/sec-multidim-guidance.md` 中的“SEC 多维查询决策表”，按以下原则分类：

1. 用户只查单对象字段：走 `QUERY`。
2. 用户显式给出完整组合维度：优先走 `QUERY`。
3. 用户表达“对应 / 归属”：先判断是否支持多维模型维度升维。
4. 支持维度升维：仍走 `QUERY`。
5. 不支持维度升维且必须沿关系链获取目标主键：拆成 `ASSOCIATION_QUERY` + `QUERY`。
6. 用户表达统计、分组、TopN、平均值、最大值、最小值、计数：考虑 `AGGREGATE`。

---

## 5. 时间、字段、ID/NAME 处理

执行前必须读取主规则手册中的对应章节：

- 字段口径表：区分 `DIM_GRID` / `GRID_ID`、`DIM_CELL` / `CELL_ID`、维度字段 / 主键字段。
- 时间语义决策表：区分本地时间、UTC 时间、默认时间、分表时间字段。
- ID / NAME 维度表达规则：区分 ID 维度和名称维度，不得混用。

---

## 6. 执行原则

1. 业务步骤顺序由本 Skill 自己规划。
2. 平台 Skill 只接收当前自然语言步骤，不感知本 Skill 内部 workflow。
3. 每一步委托都要说清楚操作类型、对象、条件、返回字段、时间和扩展说明。
4. 涉及关系路径时，关系名优先来自本体子图；若业务已确认建模关系，也要明确说明关系名和方向。
5. 如果第一步结果为空，后续依赖步骤直接为空，不重复查询。
6. OAC 返回什么字段，就原样保留什么字段；本 Skill 只在最终回答中做业务解释。

---

## 7. 参考文档

- `knowledge/sec-multidim-guidance.md`：SEC 多维查询业务定制主规则手册。
- `templates/oac-natural-language-request.md`：OAC 自然语言委托模板。
- `workflows/sec-multidim-workflows.md`：自然语言业务流程示例。
