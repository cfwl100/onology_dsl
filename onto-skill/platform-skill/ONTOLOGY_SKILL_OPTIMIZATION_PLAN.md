# 本体 Skill 优化方案

本文基于 Agent Skill 五种设计模式，对 `platform-skill` 下两层本体 Skill 做职责检视和重构建议。

## 模式定位

| Skill | 主模式 | 辅助模式 | 定位 |
|---|---|---|---|
| `Ontology-based-planning-skill` | Pipeline | Inversion | 计划执行器：接收执行步骤，做检查点、委托执行、结果绑定和汇总。 |
| `Ontology-platform-unified-skill` | Tool Wrapper | Generator / Reviewer | 平台能力包装器：封装 OAG、OAC、Function；OAC 子模块负责 OQL 生成和校验。 |

## 已完成的结构优化

1. 第一层明确为 Pipeline Executor，不再承载 OQL、关系、函数等平台内部协议。
2. 第二层明确为 Tool Wrapper，不再承担跨业务阶段规划。
3. OAC 总入口改为总控 Playbook，只负责路由、公共流程和校验闭环。
4. 新增 `oql-common-rules.md`，承载跨操作公共规则。
5. 三类 OAC 操作手册统一为同构结构：何时使用、资产、字段、returns、conditions、生成步骤、校验与修复、最小示例。
6. 第一层新增计划步骤契约、执行流水线检查点和失败策略。

## 推荐目标结构

```text
Ontology-based-planning-skill/
├── SKILL.md
└── references/
    ├── plan-step-contract.md
    ├── execution-pipeline.md
    └── failure-policy.md

Ontology-platform-unified-skill/
├── SKILL.md
├── references/
│   ├── ontology-subgraph-search.md
│   ├── oac-data-access.md
│   ├── oql-common-rules.md
│   ├── oac-query.md
│   ├── oac-association-query.md
│   ├── oac-aggregate.md
│   └── call-function.md
├── schemas/
├── examples/
└── scripts/
```

## 后续 P0 建议

1. 将 `scripts/validate_oql.py` 的校验逻辑抽成 `scripts/oql_validator.py`，供 `execute_oac_operation.py` 复用。
2. 统一 `maxResults` 为数字格式，避免 schema、examples、executor 漂移。
3. 确认 `returns.kind = FUNCTION` 的 ID/NAME 写法在执行脚本中也被接受。
4. 增加 `scripts/test_oql_examples.py`，保证 examples 始终可通过 validator。

## 后续 P1 建议

1. 增加 `tests/valid` 与 `tests/invalid`，覆盖反例。
2. 增加 Skill lint，检查每个 reference 是否引用 schema、example、validator。
3. 为 Function 子模块补充“发现函数 → 获取参数规格 → 参数补齐 → 调用”的 Inversion 流程。
4. 将场景型业务 Skill 与平台 Skill 的调用契约文档化。

## 设计原则

- 顶层只路由，不展开内部协议。
- Operation 手册只描述单一操作。
- schema 负责结构契约。
- validator 负责跨字段语义校验。
- examples 负责 few-shot 生成参考。
- executor 只负责执行，不重复维护另一套规则。
