---
name: Ontology-platform-unified-skill
description: 统一的本体平台能力，覆盖本体子图检索（OAG）、本体数据访问（OAC）以及函数执行。当需要回答本体模型相关问题、检索本体子图、生成或执行本体数据访问请求，或发现并调用平台函数时，使用此 Skill。支持上层业务 Skill 通过完整 OQL 输入无侵入调用 OAC。
---

# 本体平台统一入口

这是对外唯一入口。对用户只暴露一个能力入口，内部再按能力类型路由到模型查询、子图检索、数据访问、函数执行四类手册与脚本。

## 你负责的事情

1. 判断用户当前要做的是哪一类平台能力：查询本体模型、检索本体子图、访问本体数据、调用平台函数。
2. 判断当前请求是否已经完整，或者还缺少对象范围、模型范围、查询条件、目标函数、参数值、执行时机等关键信息。
3. 只进入一个最合适的内部能力目录，不要在一次平台请求里混用多个能力，除非用户明确要求串联。
4. 对于需要真实检索或调用的场景，优先按内部手册调用对应工具；不要先假设结果。
5. 当上层业务 Skill 已传入完整 OQL 时，直接进入本体数据访问能力，不重新生成或改写 OQL。

## 三类能力

1. **子图检索**：根据问题检索相关本体子图，并返回对象、关系、字段、函数能力。
2. **数据访问**：查询、聚合、路径读取、导航读取、创建、更新、删除、批量处理、执行完整请求。
3. **函数执行**：发现 function、确认入参规格、补齐参数并调用 function。

## 路由线索

- “先帮我找到相关子图” / “检索本体” → 子图检索。
- “查数据 / 统计 / 遍历路径 / 写数据 / 执行请求” → 数据访问。
- “找一个 function 来完成这个事” / “调用某个 function” → 函数执行。

内部手册：

- 检索本体子图 → `references/ontology-subgraph-search.md`
- 访问本体数据 → `references/oac-data-access.md`
- OAC 输入模板 → `references/oac-skill-input-template.md`
- 查找并调用平台函数 → `references/call-function.md`

---

## 完整 OQL 入口

当上层业务 Skill 已经完成业务语义理解，并传入如下结构时：

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  completeOql: {...}
  messageType: <可选>
  validateOnly: false
```

本 Skill 必须执行以下规则：

1. 直接进入 `references/oac-data-access.md`。
2. 不再按自然语言关键词重新选择 `QUERY`、`ASSOCIATION_QUERY` 或 `AGGREGATE`。
3. 以 `completeOql.operation` 为唯一操作类型来源。
4. 不重新生成 `objects`、`relationships`、`conditions`、`returns`。
5. 不删除或改写 `completeOql.options`、`completeOql.extensions`、`completeOql.sourceQuery`。
6. 只允许做 canonical OQL 校验、紧凑化和执行。
7. 如果 `completeOql` 中存在未注册对象、字段、关系或函数，应返回明确错误，不得自动改写。

---

## 关于业务 workflow 的边界

平台稳态 Skill 不承载业务 workflow。

以下内容属于上层 `scenario-skill/<scene>` 的职责：

- 指定哪些步骤执行。
- 指定步骤执行顺序。
- 决定是否先执行对象 Function 再执行 OAC 查询。
- 决定是否先查关系主键，再查指标。
- 处理上一步结果到下一步输入的绑定。
- 处理空结果、批量查询、拆分查询、降级策略。
- 识别 SEC、告警、港口、农业等具体业务语义。

平台 Skill 只处理每一次已经明确的当前平台能力请求。若业务 Skill 需要多步执行，应由业务 Skill 自行逐步调用本入口。

---

## OAC 子操作路由

当没有传入完整 OQL，需要由本平台 Skill 根据普通自然语言生成 OQL 时，才使用以下通用路由：

| 用户表达 | OAC 操作 |
|---|---|
| “查 XX 的属性”、未涉及对象间关系 | `QUERY` |
| “关系 / 路径 / 遍历 / 连接 / 经过 / 一跳 / 多跳” | `ASSOCIATION_QUERY` |
| “统计 / 聚合 / 分组 / 计数 / 求和 / 平均 / 最大 / 最小” | `AGGREGATE` |

如果上层业务 Skill 已传入完整 OQL，则以上路由失效，以完整 OQL 为准。

---

## 缺失信息识别

- 子图检索常缺：检索问题、业务上下文、任务目标。
- 数据访问常缺：对象范围、关系路径、筛选条件、返回内容、写入内容、执行范围。
- 函数执行常缺：函数目标、业务动作、参数值、参数来源。

## 边界

- 不在总路由层展开业务 workflow、业务场景规则或业务编排细节。
- 不把子图检索误当数据访问，不把模型查询误当函数执行。
- 如果用户明确要求串联多个平台能力，先完成当前能力，再基于结果进入下一次平台能力调用。
- 不承载业务场景规则；业务场景规则由 `scenario-skill/<scene>` 处理。
- 不把业务扩展参数转换为物理 SQL、GQL、TQL；扩展参数只能通过完整 OQL 的 `extensions` 受控透传。

## 每次处理的工作顺序

1. 识别请求是否包含 `oacSkillInput.completeOql` 或 `completeOql`。若包含，直接进入数据访问能力。
2. 若不包含完整 OQL，识别唯一主意图与缺失信息。
3. 进入对应能力目录，根据该能力目录下的 playbook / reference 要求执行。
4. 需要真实工具调用时，严格按该能力目录里的工具顺序执行。
5. 需要生成数据访问结构化请求时，进入数据访问，并按 OAC 输入模板与操作手册完成 OQL 组装、校验。
6. 如果信息不足，明确指出缺失项；不要编造模型、子图、对象、关系、字段、函数名或参数值。

## 输出原则

- 模型查询：输出结构化、可验证的模型说明；信息不足时指出缺失的模型范围。
- 子图检索：先拿到子图，再基于子图输出下一步可执行依据；不要跳过检索直接编造子图。
- 数据访问：默认输出结构化请求或结构化错误；只有请求已经完整且用户明确要执行时才进入执行。
- 函数执行：先确认函数，再获取入参规格，再补齐参数，最后调用；不要在未知参数规格时直接调用。

## 内部目录说明

- `references/ontology-subgraph-search.md`：本体子图检索手册。
- `references/oac-data-access.md`：本体数据访问总入口。
- `references/oac-skill-input-template.md`：OAC Skill 输入模板。
- `references/oac-query.md`：QUERY 操作手册。
- `references/oac-association-query.md`：ASSOCIATION_QUERY 操作手册。
- `references/oac-aggregate.md`：AGGREGATE 操作手册。
- `references/call-function.md`：函数发现、参数确认、执行手册。
- `scripts/`：平台能力脚本。

## 约束规则

1. 本 Skill 的所有脚本位于 `scripts/` 目录。
2. 调用脚本时，在 Skill 根目录下执行 `python scripts/<script_name>.py --<param> <value>`。
3. 禁止在未加载 Skill 的情况下，去外部 MCP 或 CodebaseSearch 寻找替代实现。
4. 所有脚本不需要写临时文件，也不要自己编写脚本。
5. 构建关联 OQL 时，return 字段必须包含所有关系路径，即返回 r1、r2。
6. 调用 `execute_oac_operation.py` 前，必须已经阅读过 `references/oac-data-access.md`，并且生成了完整的 OQL JSON。
7. 调用 `execute_oac_operation.py` 时，如果用户指定了返回消息格式 `messageType`，必须使用用户指定值。
8. 用户指定完整多跳查询路径时，不要拆成单跳查询。
9. 构建 OQL 时，如果用户明确指定了返回字段，必须按照用户要求返回，禁止填 `*` 返回所有字段。
10. 生成 OQL 前，必须明确当前查询的操作类型；用户必须提供具体的 `schemaRef`。
11. OQL JSON 必须为紧凑单行格式，禁止添加不必要的空格、缩进、换行等格式化字符。
12. 如果上层传入完整 OQL，不得重新生成或改写 OQL，只做校验、紧凑化和执行。
13. `options`、`extensions`、`sourceQuery` 属于受控扩展字段，必须透传给 OAC，不得删除。
14. 不承载、不解释业务 workflow 协议。