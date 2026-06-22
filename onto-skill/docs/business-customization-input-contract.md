# 业务定制 Skill 输入契约

## 1. 目标

业务定制 Skill 位于 `scenario-skill/`，负责把用户问题、业务知识、实体变量和执行约束整理成 `Ontology-based-planning-skill` 可消费的业务定制输入。

该契约用于解决两个问题：

1. 让上层业务 Skill 更方便地注入自己的定制内容。
2. 避免只传 `knowledge.summary` 导致原始业务规则、硬约束、固定模板和返回要求丢失。

---

## 2. 推荐输入信封

业务定制 Skill 推荐生成以下结构：

```json
{
  "mode": "customized_planning",
  "scenario": "业务场景名",
  "originalQuestion": "用户原始问题",
  "intent": "业务意图",
  "goal": "业务目标",
  "ontologyId": "本体子图检索使用的本体ID",
  "schemaRef": "本体访问使用的schemaRef",
  "knowledgeRefs": ["knowledge/xxx.md"],
  "knowledge": {
    "facts": [],
    "rules": [],
    "constraints": [],
    "oagHints": [],
    "oacHints": [],
    "functionHints": [],
    "rawEvidenceRefs": []
  },
  "entities": {},
  "variables": {},
  "constraints": {},
  "stepOverrides": [],
  "stepAppends": [],
  "stepSkips": [],
  "failurePolicy": {}
}
```

---

## 3. 字段说明

| 字段 | 说明 |
|---|---|
| `mode` | 固定为 `customized_planning`，表示业务定制模式。 |
| `scenario` | 业务 Skill 名称，便于审计。 |
| `originalQuestion` | 用户原始问题，必须保留，OAG 子图检索优先使用自然语言原文。 |
| `intent` | 上层业务 Skill 识别出的唯一主意图。 |
| `goal` | 最终业务目标。 |
| `ontologyId` | 本体子图检索入参。 |
| `schemaRef` | 本体访问入参。 |
| `knowledgeRefs` | 已读取的业务知识文件路径。 |
| `knowledge.facts` | 业务事实。 |
| `knowledge.rules` | SOP、判断规则和推理规则。 |
| `knowledge.constraints` | 禁止项、硬约束、串行/并行要求、不可重试要求。 |
| `knowledge.oagHints` | 本体子图检索自然语言提示或固定模板。 |
| `knowledge.oacHints` | 本体访问查询对象、字段、过滤、返回格式提示。 |
| `knowledge.functionHints` | 函数发现或调用建议。 |
| `knowledge.rawEvidenceRefs` | 需要保留的原始知识引用，例如文件名和章节名。 |
| `entities` | 用户输入实体，例如网元、告警、船舶、业务路径等。 |
| `variables` | 变量值，例如时间范围、方向列表、告警列表等。 |
| `constraints` | 当前请求级约束。 |
| `stepOverrides` | 覆盖默认步骤输入、期望输出、失败策略或备注。 |
| `stepAppends` | 在默认流程后追加步骤。 |
| `stepSkips` | 跳过默认步骤，必须给出原因。 |
| `failurePolicy` | 失败处理策略。 |

---

## 4. 无损注入原则

1. 不要只传 `knowledge.summary`。
2. 必须保留 `knowledgeRefs`，让 planning 层能知道知识来源。
3. 强约束、禁止项、固定模板、返回字段、方向顺序、不可重试规则必须进入 `knowledge.constraints` 或 `constraints`。
4. 用户原始问题必须进入 `originalQuestion`。
5. 上层业务 Skill 已知的 `ontologyId`、`schemaRef` 必须直接注入。
6. 业务知识只能作为规划依据；对象、字段、关系、函数最终仍以本体子图和平台返回结果为准。
7. 如果用户显式输入与业务知识冲突，以用户显式输入优先，并在冲突中说明。

---

## 5. 与三种模式的关系

| 模式 | 上层业务 Skill 应该怎么做 |
|---|---|
| 默认规划模式 | 只传 `originalQuestion`、`goal`、必要的 `ontologyId` / `schemaRef`。 |
| 业务定制模式 | 使用本文定义的定制输入信封，注入业务知识、变量、约束和局部步骤改写。 |
| 显式步骤执行模式 | 直接传完整 `steps`，planning 层只做步骤契约检查和绑定。 |

---

## 6. alarm-propagation 示例要点

`alarm-propagation` 不应只向 planning 层传递“当前意图对应的业务知识摘要”，而应按意图保留以下信息：

- `knowledgeRefs`：实际读取的 knowledge 文件。
- `knowledge.rules`：告警唯一标识符、传播链、证据验证等规则。
- `knowledge.constraints`：禁止查 AbnormalStatus、禁止 Function、每个方向独立 OAG、禁止重复查询等硬约束。
- `knowledge.oagHints`：固定 OAG 自然语言 query 模板。
- `knowledge.oacHints`：返回字段、过滤条件、message_type、关系路径要求。
- `entities`：网元名称、告警名称、告警 identifier。
- `variables`：方向列表、每个方向的网元名称、告警类型列表、时间范围。
- `stepOverrides`：只覆盖 S2 子图检索和 S4 数据访问的输入提示，不重写默认流程。
