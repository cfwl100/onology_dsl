# ontology-platform-unified-skill

本体平台统一 Skill，单入口内聚三类能力：
1. **OAG 子图检索**：基于问题检索相关子图，结合 SOP 规划后续任务。
2. **OAC 数据访问**：生成、校验、执行 OQL（QUERY / ASSOCIATION_QUERY / AGGREGATE），返回对象结构结果。
3. **Function 执行**：发现函数、确认入参、补齐参数、发起调用。

## 目录
- `SKILL.md`：唯一入口（能力路由 + 命令规范 + 执行边界）。
- `references/`：三类能力操作手册，已内聚公共规则。
- `schemas/`：OQL 结构契约。
- `scripts/`：子图检索、OQL 校验、OAC 执行、函数参数规格、函数执行。
