# 本体数据访问（OAC）

## 本层职责
OAC（Ontology Data Access Capability）是本体平台的数据访问层，负责对本体数据进行查询、聚合、路径遍历、创建、更新、删除等操作。

## 操作类型
OAC 支持三种操作类型：

| 操作类型 | 说明 | 适用场景 |
|---------|------|---------|
| **QUERY** | 无关联的对象查询 | 单对象查询、不涉及对象间关系遍历 |
| **ASSOCIATION_QUERY** | 关联查询 | 多跳关系遍历、路径查询、起点终点与中间节点联合约束 |
| **AGGREGATE** | 聚合查询 | 分组统计、指标计算、聚合后过滤 |

## 路由判断
判断使用哪种操作：
- 用户只说"查XX的哪些属性"、查xx和xx的哪些属性、"没有提到对象间关系" → **QUERY**
- 用户明确提到"关系"、"路径"、"遍历"、"连接"、"经过" → **ASSOCIATION_QUERY**
- 用户明确提到"统计"、"聚合" → **AGGREGATE**

## 子文档
- `oac-query.md` - QUERY 操作手册（无关联）
- `oac-association-query.md` - ASSOCIATION_QUERY 操作手册（有关联）
- `oac-aggregate.md` - AGGREGATE 操作手册（聚合查询）

## 脚本
| 脚本 | 作用 |
|------|------|
| `execute_oac_operation.py` | 执行 OAC 请求 |