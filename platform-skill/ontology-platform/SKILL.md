---
name: ontology-platform
description: 统一的本体平台能力，覆盖本体子图检索（OAG）、本体数据访问（OAC）以及函数执行。当需要回答本体模型相关问题、检索本体子图并规划后续工作、生成或执行本体数据访问请求，或根据用户请求发现并调用平台函数时，使用此 Skill。
---

# 本体平台统一入口

> **共享约束规则**：参见 `platform-skill/shared-constraints.md`

## 快速路由参考

| 用户关键词 | 路由到 | 文档 |
|-----------|-------|------|
| "先找相关子图"、"检索本体" | 子图检索 (OAG) | `references/ontology-subgraph-search.md` |
| "查属性"、"统计数量"（无关系） | 数据访问-QUERY | `references/oac-query.md` |
| "关系"、"路径"、"遍历"、"经过" | 数据访问-ASSOC | `references/oac-association-query.md` |
| "调用function"、"调用函数" | 函数执行 | `references/call-function.md` |

## Skill 边界决策

```
用户输入
  │
  ├─ 是否涉及「网元」「告警」「传播」? ──→ alarm-propagation
  │
  ├─ 是否需要执行已规划的步骤? ──→ ontology-planning
  │
  └─ 其他 ──→ 直接路由到具体能力
```

## 你负责的事情

1. 先判断用户要做的是哪一类事情：查询本体模型、检索本体子图、访问本体数据、调用平台函数。
2. 判断当前请求是否已经完整，或者还缺少对象范围、模型范围、查询条件、目标函数、参数值、执行时机等关键信息。
3. 只进入一个最合适的内部能力目录，不要在一次请求里混用多个能力，除非用户明确要求串联。
4. 对于需要真实检索或调用的场景，优先按内部手册调用对应工具；不要先假设结果。
5. 能回答就直接回答；需要生成结构化请求时只生成当前场景需要的结构；需要真实执行时再进入执行步骤。

## 内部目录说明

| 目录/文件 | 说明 |
|----------|------|
| `references/ontology-subgraph-search.md` | 本体子图检索与任务规划手册 |
| `references/oac-data-access.md` | 本体数据访问总入口 |
| `references/oac-query.md` | QUERY 操作手册（无关联） |
| `references/oac-association-query.md` | ASSOCIATION_QUERY 操作手册（有关联） |
| `references/call-function.md` | 函数发现、参数确认、执行手册 |
| `scripts/` | 可执行脚本目录 |

## 约束规则

> **重要**：以下约束的详细说明请参见 `platform-skill/shared-constraints.md`

1. 本 skill 的所有脚本位于 `scripts/` 目录
2. 调用脚本时，在 skill 根目录下执行 `python scripts/<script_name>.py --<param> <value>`
3. 禁止在未加载 skill 的情况下，去外部 MCP 或 CodebaseSearch 寻找替代实现
4. 所有脚本不需要写临时文件，也不要自己编写脚本
5. 构建 OQL 时，return 字段强制返回所有的边路径（r1, r2 等）
6. 调用 `execute_oac_operation.py` 前，必须已阅读 `references/oac-data-access.md` 并生成完整的 OQL JSON
7. 调用 `execute_oac_operation.py` 时，如果用户指定了返回消息格式 `message_type`，必须使用用户指定的值
8. 用户指定完整多跳查询路径时，不要拆成单跳查询
9. 构建 OQL 时，如果用户明确指定了返回字段，必须按照用户要求返回，禁止填 `*` 返回所有字段
10. 生成 OQL 前，必须明确当前查询的操作类型（QUERY 或 ASSOCIATION_QUERY）
11. **OQL JSON 必须为紧凑单行格式**，禁止添加不必要的空格、缩进、换行

## 每次处理的工作顺序

1. 识别唯一主意图与缺失信息
2. 进入对应能力目录，根据该能力目录下的手册要求执行
3. 需要真实工具调用时，严格按该能力目录里的工具顺序执行
4. 需要数据访问结构化请求时，进入数据访问
5. 桥接目录，按内部操作目录与脚本完成归一化、组装、校验
6. 如果信息不足，明确指出缺失项；不要编造模型、子图、对象、关系、字段、函数名或参数值

## 输出原则

| 能力类型 | 输出原则 |
|---------|---------|
| 模型查询 | 输出结构化、可验证的模型说明；信息不足时指出缺失的模型范围 |
| 子图检索 | 先拿到子图，再基于子图与 SOP 输出下一步任务规划；不要跳过检索直接编造子图 |
| 数据访问 | 默认输出结构化请求或结构化错误；只有请求已经完整且用户明确要执行时才进入执行 |
| 函数执行 | 先确认函数，再获取入参规格，再补齐参数，最后调用；不要在未知参数规格时直接调用 |
