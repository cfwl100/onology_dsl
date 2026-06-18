# Ontology-platform-unified-skill

统一的本体平台 Skill，对外只暴露一个入口，内部包含四类能力：

1. **OMS 本体模型查询**：查询对象类型、属性、关系、枚举、约束、映射等模型信息。
2. **OAG 本体子图检索**：基于输入问题检索相关子图，并结合 SOP 与子图信息规划后续任务。
3. **OAC 本体数据访问**：生成、归一化、组装、校验并在需要时执行本体数据访问请求。
4. **Function 执行**：根据用户意图发现合适的 function，获取入参规格，补齐参数并发起调用。

## 目录概览

- `SKILL.md`：对外唯一入口。
- `references/routing.md`：四类能力总路由。
- `references/capabilities/oms-model-query/`：OMS 手册。
- `references/capabilities/ontology-subgraph-search/`：OAG 手册。
- `references/capabilities/oac-data-access/`：OAC 桥接与内部读写执行手册。
- `references/capabilities/call-function/`：Function 调用手册。
- `scripts/`：OAC 公共脚本与内部操作包装脚本。
- `assets/fixtures/`：示例输入与测试夹具。
- `scripts/tests/`：Python 测试。

## OAC 桥接说明

当前包里的 OAC 能力保留原有内部操作粒度：
- 普通对象读取
- 聚合查询
- 路径关联查询
- 一跳关联导航
- 创建 / 更新 / 删除
- upsert / 批量写入
- 完整请求执行

这些内部能力不再对外暴露为独立 Skill，而是作为统一 Skill 内部的桥接目录与脚本能力使用。
