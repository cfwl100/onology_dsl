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
- 规划层负责把用户问题和业务定制说明整理成执行上下文，并驱动默认本体子图规划流程。
- 平台层封装 OAG、OAC、Function 三类能力，对上层暴露稳定的自然语言委托入口。
- OQL 生成和校验由 operation 手册、schema、validator、executor 共同约束。

---

## 2. Tool Wrapper：Ontology-platform-unified-skill

`Ontology-platform-unified-skill` 是本体平台能力包装器，对上层隐藏 OAG、OAC、Function 的接口差异。

| 能力 | 职责 | 入口 |
|---|---|---|
| OAG 本体子图 | 基于自然语言业务意图和公共本体ID检索对象、属性、关系、函数候选 | `references/ontology-subgraph-search.md` |
| OAC 本体访问 | 基于公共本体ID、业务意图和子图依据生成、校验、执行 OQL | `references/oac-data-access.md` |
| Function 函数能力 | 基于公共本体ID、函数候选和业务意图获取规格、组装参数、调用函数 | `references/call-function.md` |

平台层不做跨阶段业务规划，只做能力路由和平台协议封装。上层只需要使用稳定语义入口：

```text
先找相关子图
查数据
调用函数
对象有什么字段
```

---

## 3. OAG / OAC / Function 职责边界

### 3.1 OAG：找本体结构依据

OAG 输入是自然语言业务意图和公共 `本体ID`，输出本体子图结果及规划可用摘要。

OAG 负责：

- 检索对象、属性、关系、函数候选。
- 保留原始子图结果。
- 摘要化输出对象、字段归属、关系来源、函数候选。
- 为 OAC 和 Function 提供可信依据。

OAG 不负责：

- 不生成 OQL。
- 不执行数据查询。
- 不直接调用函数。
- 不把子图结果说成完整事实库。

### 3.2 OAC：生成和校验本体查询

OAC 输入是公共 `本体ID`、自然语言数据访问业务意图和 OAG 子图依据，输出 OQL、校验结果以及可选执行结果。

OAC 负责：

- 判断 `QUERY / ASSOCIATION_QUERY / AGGREGATE`。
- 将公共 `本体ID` 作为生成 OQL 时的 `schemaRef` 来源。
- 读取唯一 operation 手册和对应 schema。
- 生成 OQL JSON。
- 运行 validator 校验。
- 用户明确要求执行时调用 executor。

OAC 不负责：

- 不检索本体子图。
- 不编造对象、字段、关系。
- 不调用 Function。
- 不把未执行的 OQL 当成数据结果。

### 3.3 Function：调用本体函数

Function 输入是公共 `本体ID`、自然语言函数调用业务意图、`functionId` 和上下文参数，输出函数选择、参数规格、参数组装和调用结果。

Function 负责：

- 从 OAG 的 `result.functions` 或上层可信输入确认函数。
- 使用函数候选返回的 `ontologyId`；若候选没有更精确本体标识，则使用公共 `本体ID`。
- 获取函数参数规格。
- 组装 `args`。
- 调用函数并保留真实结果或错误。

Function 不负责：

- 不检索本体子图。
- 不生成 OQL。
- 不编造参数、默认值或成功结果。
- 不把函数调用和数据访问混在一个步骤里。

---

## 4. 面向自然语言的模块输入模板与输出格式

### 4.1 OAG 本体子图检索

#### 自然语言输入模板

```text
请执行本体子图检索。

本体ID：<对外公共本体ID>
业务意图：<改写后的详细自然语言问题，用于检索对象、属性、关系、函数候选>
检索目标：<希望找到哪些对象、属性、关系、函数候选>
业务知识补充：<可选，来自业务 Skill 的规则、SOP、禁止项、固定模板>
检索范围提示：<可选，例如优先关注告警、网元、链路、业务影响对象>
函数返回要求：<可选，是否需要返回 functions>
```

#### 输出格式

```text
## OAG 输出

### 1. 检索摘要
- 命中的业务主题：...
- 相关对象：...
- 相关属性：...
- 相关关系：...
- 相关函数候选：...

### 2. 原始子图结果
- 保留脚本返回的 result，包括 objects / properties / relationships / functions 等原始结构。

### 3. 规划可用依据
- 可用于 OAC 的对象类型：...
- 可用于 OAC 的字段及归属对象：...
- 可用于 ASSOCIATION_QUERY 的关系名：...
- 可用于 Function 调用的 functionId / ontologyId：...

### 4. 下一步建议
- 是否需要 OAC：是/否，原因：...
- 是否需要 Function：是/否，原因：...
- 缺失信息：...
```

### 4.2 OAC 本体数据访问

#### 自然语言输入模板

```text
请执行本体数据访问。

本体ID：<对外公共本体ID，作为 OQL schemaRef 来源>
业务意图：<改写后的详细自然语言数据访问问题>
查询目标：<自然语言描述要查什么数据>
本体子图依据：<来自 OAG 的对象、字段、关系、函数候选摘要>
候选操作类型：<明细查询 / 关系路径查询 / 聚合统计；不确定时说明判断依据>
查询对象：<对象类型、别名建议、业务含义>
关系路径：<仅关系查询需要，说明 from / relation / to / 方向 / 步数>
过滤条件：<字段、操作符、取值，字段归属对象必须清楚>
返回要求：<返回字段、聚合指标、排序、maxResults>
执行要求：<只生成 OQL / 校验 OQL / 用户确认后执行>
```

#### 输出格式

```text
## OAC 输出

### 1. 操作类型判断
- operation：QUERY / ASSOCIATION_QUERY / AGGREGATE
- 判断依据：...

### 2. OQL JSON
- 生成符合 schema 的 OQL JSON，其中 schemaRef 来自本体ID。

### 3. 校验结果
- 是否通过 validate_oql.py：是/否
- 失败原因：...
- 修复动作：...

### 4. 执行状态
- 是否执行：未执行 / 已执行
- 执行前提：用户已明确要求执行

### 5. 执行结果或缺失项
- 数据结果：...
- 缺失字段/关系/本体ID：...
- 风险说明：...
```

### 4.3 Function 函数调用

#### 自然语言输入模板

```text
请执行本体函数调用。

本体ID：<对外公共本体ID；函数候选返回更精确本体ID时以候选为准>
业务意图：<为什么要调用函数，要解决什么问题>
函数来源：<来自 OAG 子图 result.functions，或上层业务 Skill 明确给出的函数候选>
functionId：<函数ID；如果未知，先返回缺失项>
函数选择依据：<为什么选择这个函数，基于 description/name/业务规则>
上下文参数：<用户问题、数据查询结果、业务变量中可用于组装函数参数的信息>
参数缺失策略：<缺少必填参数时返回缺失项，不编造>
输出要求：<希望输出函数原始结果、摘要、错误信息或缺失项>
```

#### 输出格式

```text
## Function 输出

### 1. 函数选择
- functionId：...
- ontologyId：...
- functionName：...
- 选择依据：...

### 2. 参数规格
- 是否已获取参数规格：是/否
- physicalName：...
- required 参数：...
- optional 参数：...

### 3. 参数组装
- args：...
- 参数来源：用户问题 / OAC 结果 / 业务变量 / 默认值
- 缺失参数：...

### 4. 调用状态
- 是否调用：是/否
- 失败原因：...

### 5. 函数结果
- 原始结果：...
- 结果摘要：...
- 错误信息：...
```

---

## 5. Generator：OAC 操作手册与 Schema

OAC 子模块承担 Generator 模式，将用户目标、业务变量和本体子图结果生成 OQL JSON。

| 操作 | 文档 | Schema |
|---|---|---|
| `QUERY` | `references/oac-query.md` | `schemas/oql-query.schema.json` |
| `ASSOCIATION_QUERY` | `references/oac-association-query.md` | `schemas/oql-association-query.schema.json` |
| `AGGREGATE` | `references/oac-aggregate.md` | `schemas/oql-aggregate.schema.json` |

生成链路：

```text
用户问题 / 上层自然语言定制说明 / OAG 子图结果
  -> 判断 operation
  -> 读取唯一 operation 手册
  -> 读取对应 schema
  -> 生成 OQL JSON
```

价值：按操作类型渐进式披露，减少 Agent 上下文开销，避免 QUERY、ASSOCIATION_QUERY、AGGREGATE 规则混用。

---

## 6. Reviewer：OQL Validator 与执行前校验

OAC 子模块同时承担 Reviewer 模式。所有 OQL 在执行前必须通过统一校验。

`oql_validator.py` 是唯一 OQL 校验核心，负责：

- 根据 `operation` 选择 schema。
- 执行 JSON Schema 结构校验。
- 校验 alias 引用。
- 校验 relationship `from/to` 引用。
- 校验 `aggregateFilter.metricAlias` 引用。
- 校验特殊返回项、聚合项和排序项等跨字段语义。
- 校验 `maxResults` 使用数字格式。

---

## 7. Inversion：业务 Skill 定制默认流程

业务定制 Skill 不直接调用 OAG、OAC、Function，而是把业务知识、规则、禁止项和执行建议注入给 planning 层。

推荐注入格式：

```text
本体ID：<对外公共本体ID>
业务意图：<改写后的详细自然语言问题>
已读取知识：<knowledge 文件路径>
业务知识与规则：<规则、SOP、禁止项、返回要求、空结果策略>
执行定制要求：<如何改写默认子图检索、数据访问、函数或汇总步骤>
缺失信息：<没有则写无>
```

结构化字段只是可选增强，不是业务 Skill 的强制接口。

---

## 8. Pipeline：默认规划执行链

```text
S1 输入整理与规划上下文构造
  -> S2 OAG 子图检索
  -> S3 子图解析
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
