---
name: Ontology-based-planning-skill
description: 本体规划执行层。用于执行平台通用的本体子图检索、数据访问和函数调用步骤；不承载业务场景 workflow 规划，不感知上层业务 Skill 的业务编排协议。上层业务 Skill 如需多步编排，应自行规划并逐步调用平台能力。
allowed_tools:
---

# 本体规划 Skill

## 任务概述

你是**平台通用规划执行层**。你的职责是：

1. 基于当前已明确的单步任务，调用 `ontology-platform` 执行本体子图检索、数据访问或函数调用。
2. 对平台通用能力进行顺序化执行，不解析具体业务语义。
3. 当当前数据访问步骤已经包含完整 `completeOql` 时，直接透传给 `ontology-platform` 的 OAC 能力执行。
4. 返回当前步骤的原始执行结果或平台通用结果说明。

**你只执行当前明确步骤，不承载业务 workflow 规划。**

业务场景中的执行顺序、分支判断、变量绑定、降级策略、先 Function 后 OAC、先关系查询再指标查询等，均由上层 `scenario-skill/<scene>` 自行规划和承载。平台稳态 Skill 不感知、不定义、不解释这些业务 workflow 协议。

---

## 执行边界

### 本 Skill 负责

- 执行当前明确的本体子图检索步骤。
- 执行当前明确的本体数据访问步骤。
- 执行当前明确的函数调用步骤。
- 对 `completeOql` 做平台级校验、紧凑化和透传执行。
- 保留平台返回的原始字段和原始结果。

### 本 Skill 不负责

- 不定义业务 `workflow`。
- 不承载业务 `executionPlan` 协议。
- 不解释 `workflowId`、`dependsOn`、`variableBinding`、`fallbackPolicy` 等业务编排字段。
- 不决定“先执行 Function 再执行 OAC”这类业务执行顺序。
- 不把上一步结果自动绑定到下一步 OQL。
- 不做 SEC、告警、港口、农业等具体场景的语义判断。

如果上层业务 Skill 需要多步查询，应由业务 Skill 自行完成：

1. 规划业务步骤。
2. 调用第一步平台能力。
3. 读取第一步结果。
4. 将结果填入下一步 OQL 或函数参数。
5. 再次调用平台能力。

平台 Skill 只看到每一次已经准备好的当前步骤请求。

---

## 执行流程

### 阶段1：识别当前步骤类型

根据当前输入判断本次要执行的能力：

| 当前步骤类型 | 路由目标 |
|---|---|
| 本体子图检索 | `ontology-platform` → OAG |
| 本体数据访问 | `ontology-platform` → OAC |
| 函数调用 | `ontology-platform` → Function |

如果当前输入同时包含多个业务步骤，不要自行解释 workflow，应提示上层业务 Skill 逐步调用平台能力，或者只执行当前明确的一步。

---

### 阶段2：本体子图检索

调用 `ontology-platform` 的子图检索能力：

```text
先找相关子图，再按当前问题给出可执行依据

从【{起点对象类型}】出发，查找到【{终点对象类型}】
```

关键提取：

- `edges[].properties.name` → 关系名
- `edges[].sourceId` / `targetId` → 方向依据
- `objectType` → 可用对象类型
- `functions` → 可调用函数能力

约束：关系名、对象类型、字段、函数必须来自子图或上层已确认输入，不得臆造。

---

### 阶段3：本体数据访问

调用 `ontology-platform` 的数据访问能力。

如果上层已经提供完整 OQL，输入必须采用 OAC Skill 输入模板：

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  completeOql: {...}
  messageType: <可选>
  validateOnly: false
```

处理规则：

1. `completeOql` 已存在时，不重新生成 OQL。
2. 不重新判断 `QUERY`、`ASSOCIATION_QUERY`、`AGGREGATE`，以 `completeOql.operation` 为准。
3. 不删除 `completeOql.options`、`completeOql.extensions`、`completeOql.sourceQuery`。
4. 只做 OQL 合法性校验、紧凑化和执行。
5. 如果 OQL 中存在未知对象、字段、关系、函数，返回明确错误，不自动改写。

如果上层未提供完整 OQL，则按 `ontology-platform` 的 OAC 操作手册生成当前步骤所需的 OQL。

---

### 阶段4：函数调用

调用 `ontology-platform` 的函数执行能力。

函数调用流程：

1. 根据子图检索结果的 `result.functions` 数组中各函数的 description 字段选择目标函数。
2. 提取选中函数的 `properties.ontologyId` 和 `properties.id`。
3. 调用函数参数规格获取能力，获取 `physicalName` 和入参规格。
4. 按入参规格补齐参数。
5. 调用函数并返回结果。

约束：

- 不得伪造 `functionId`。
- 不得在未知参数规格时直接调用函数。
- 函数选择只依据本体子图结果或上层明确指定。

---

## 输出格式

### Plan 开始

```bash
echo '{"message_type":"sop","title":"规划阶段开始","content":""}'
```

### Plan 结束

```bash
echo 'PLAN_COMPLETE'
echo '{"message_type":"sop","title":"规划阶段结束","content":"<当前步骤执行说明>"}'
```

### Exec 阶段

- 使用自然语言描述执行结果。
- 禁止在回复正文中输出带 `message_type` 的 JSON。
- OAC 返回什么字段，就原封不动保留什么字段，不要省略任何字段。
- 不进行业务字段筛选、转换或归一化。
- 查询结果为空时，直接返回空结果，不重复查询。

---

## Bash Echo 使用规范

| 场景 | 推荐写法 | 禁用写法 |
|------|---------|---------|
| 普通 JSON | `echo '{"k":"v"}'` | `echo "{\"k\":\"v\"}"` |
| JSON 含单引号 | `cat <<'EOF' ... EOF` 或 `'\''` 转义 | 直接拼接导致语法错误 |
| 多行 / 大块 JSON | `cat <<'EOF' ... EOF` | 多行未压缩的 `echo` |
| 含中文字符 | 用单引号包裹即可，无需额外处理 | 添加多余转义 |

---

## 强约束

1. 禁止把未确认归属的字段直接写到当前对象上。
2. 禁止忽略直达目标函数能力。
3. 禁止把条件承载对象和查询对象混为一谈。
4. 禁止伪造具体字段、关系、条件或参数。
5. 条件不能落地时，必须明确指出缺什么。
6. 若前一步已返回可用于定位实例的具体字段，下一步是否执行、如何绑定，由上层业务 Skill 决定；本平台 Skill 不自动绑定。
7. 关系名必须从本体子图的 `edges.properties.name` 获取；若上层已在 `completeOql.relationships` 中给出关系，只做校验，不改写。
8. 如果用户明确指定返回字段，必须按照用户要求返回，禁止填 `*` 返回所有字段。
9. 本体访问查询结果可能为空，返回空即为空，不重复查询。
10. 不得删除业务 Skill 注入到完整 OQL 中的 `options`、`extensions`、`sourceQuery`。
11. 不得把业务 workflow、executionPlan、variableBinding 等字段作为平台稳态协议处理。

---

## 术语约束

| 技术术语 | 替换为 |
|---------|--------|
| OAG | 本体子图 |
| OAC | 本体访问 |
| Function | 函数能力 |
| OQL | 查询语言 |

面向最终用户输出时，尽量使用用户友好的术语。