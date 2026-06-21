# 本体 Skill 优化方案

本文基于 Agent Skill 五种设计模式，对 `platform-skill` 下两层本体 Skill 做职责检视和重构建议。

## 模式定位

| Skill | 主模式 | 辅助模式 | 定位 |
|---|---|---|---|
| `Ontology-based-planning-skill` | Pipeline | Inversion | 默认本体子图规划层：自带默认流程，并支持上层业务 Skill 做意图、知识、变量和步骤定制。 |
| `Ontology-platform-unified-skill` | Tool Wrapper | Generator / Reviewer | 平台能力包装器：封装 OAG、OAC、Function；OAC 子模块负责 OQL 生成和校验。 |

## 已完成的结构优化

1. 第一层收敛为单文件默认规划层，内置默认流程、定制点、调用协议和强约束。
2. 第二层明确为 Tool Wrapper，不承担跨业务阶段规划。
3. OAC 总入口改为总控 Playbook，只负责路由、操作选择和校验闭环。
4. 三类 OAC 操作手册统一为独立手册：每个文件内聚公共规则、操作专属规则和最小示例。
5. 删除独立 `oql-common-rules.md`，减少一次额外读取。
6. 删除独立 `examples/` 目录，最小示例保留在 operation 手册中。
7. `scripts/oql_validator.py` 作为统一校验核心，供 CLI 校验和执行脚本复用。

## 当前目标结构

```text
Ontology-based-planning-skill/
└── SKILL.md

Ontology-platform-unified-skill/
├── SKILL.md
├── references/
│   ├── ontology-subgraph-search.md
│   ├── oac-data-access.md
│   ├── oac-query.md
│   ├── oac-association-query.md
│   ├── oac-aggregate.md
│   └── call-function.md
├── schemas/
└── scripts/
```

## 后续 P0 建议

1. 将 `scripts/test_oql_examples.py` 后续重命名为 `scripts/test_oql_contracts.py`，文件内容已经不依赖 examples 目录。
2. 补充 OQL contract 测试用例，覆盖更多 schema 反例。
3. 检查 `schemas/*.json` 与三个 operation 手册的字段约束是否持续一致。
4. 为 Function 子模块补充“发现函数 → 获取参数规格 → 参数补齐 → 调用”的 Inversion 流程。

## 后续 P1 建议

1. 增加 Skill lint，检查每个 OAC operation 手册是否引用 schema 和 validator。
2. 将场景型业务 Skill 与平台 Skill 的调用契约文档化。
3. 为不同 Agent 生成平台适配版本，例如 opencode 轻量版、Claude Code 详细版。

## 设计原则

- 顶层只路由，不展开内部协议。
- OAC 总入口只选择 operation，不承载字段细节。
- Operation 手册自包含，避免额外读取公共规则和 standalone examples。
- schema 负责结构契约。
- validator 负责跨字段语义校验。
- executor 只负责执行，不重复维护另一套规则。