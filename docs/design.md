### 设计思路

按照 Skill 五种设计模式，当前本体 Skill 体系采用：

- `Ontology-platform-unified-skill`：Tool Wrapper，封装本体子图、本体访问和函数能力。
- OAC 子模块：Generator + Reviewer，按 operation 手册和 schema 生成并校验查询语言。
- `Ontology-based-planning-skill`：Pipeline + Inversion，提供默认本体子图规划流程，并接受上层业务 Skill 的知识、变量和步骤定制。
- `scenario-skill`：Inversion + Pipeline Extension，负责业务意图理解、知识注入和默认流程定制。

### S1 输入整理与规划上下文构造

原先称为“归一化语义请求”的步骤已经调整为“输入整理与规划上下文构造”。

设计结论：

- OAG 本体子图检索入参本身就是自然语言，因此不需要把用户问题重度归一化后再传给 OAG。
- Planning 层仍然需要轻量整理输入上下文，保留 `originalQuestion`，整理 `goal`、`entities`、`variables`、`constraints`、`ontologyId`、`schemaRef`、`steps` 和后续能力需求。
- S1 不得提前确定对象类型、字段名、关系名或函数参数；这些必须来自本体子图结果、用户显式输入或上层业务 Skill 注入。
- 显式步骤模式下，S1 退化为步骤契约检查和执行上下文绑定。
