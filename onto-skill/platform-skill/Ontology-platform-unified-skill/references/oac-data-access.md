# 本体数据访问（OAC）

## 本层职责
OAC 是本体平台的数据访问层，面向本体对象提供查询、聚合、路径遍历、创建、更新、删除等数据访问能力。

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

## OQL 扩展字段 extensions

OQL 可选支持 `extensions` 字段。该字段用于承载业务侧与 OAC 已经约定的扩展参数；无明确约定时应省略。

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---:|---|
| `extensions` | object | 否 | 扩展字段；无明确约定时应省略。 |

使用规则：

1. `extensions` 只能填写已约定的扩展参数。
2. 无明确扩展含义时不生成该字段。
3. `extensions` 不能替代 `conditions`；时间范围、对象过滤、指标过滤仍应写入标准条件。
4. 如果业务 Skill 根据对象时间属性描述识别出时间口径，可以表达 `localtime` 扩展：描述为本地时间时填写 `localtime` 为 true；描述为 UTC 时间时填写 `localtime` 为 false。
5. `localtime` 只表示时间口径，不表示时间范围。

## 子文档
- `oac-query.md` - QUERY 操作手册（无关联）
- `oac-association-query.md` - ASSOCIATION_QUERY 操作手册（有关联）
- `oac-aggregate.md` - AGGREGATE 操作手册（聚合查询）
