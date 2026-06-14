# 本体数据访问（OAC）

## 本层职责

OAC（Ontology Data Access Capability）是本体平台的数据访问层，负责对本体数据进行查询、聚合、路径遍历、创建、更新、删除等操作。

本层只处理本体数据访问协议、OQL 组装、OQL 校验、OQL 执行与结果返回，不承载具体业务场景规则。业务场景规则由上层 `scenario-skill` 通过 `operationHint`、`semanticHints`、`completeOql`、`extensions` 注入。

## 操作类型

OAC 支持三种基础操作类型：

| 操作类型 | 说明 | 适用场景 |
|---------|------|---------|
| **QUERY** | 无关联的对象查询 | 单对象查询、多对象同事实模型查询、不涉及对象间关系遍历 |
| **ASSOCIATION_QUERY** | 关联查询 | 多跳关系遍历、路径查询、起点终点与中间节点联合约束 |
| **AGGREGATE** | 聚合查询 | 分组统计、指标计算、聚合后过滤 |

## 路由判断

判断使用哪种操作：
- 用户只说"查XX的哪些属性"、查xx和xx的哪些属性、"没有提到对象间关系" → **QUERY**
- 用户明确提到"关系"、"路径"、"遍历"、"连接"、"经过" → **ASSOCIATION_QUERY**
- 用户明确提到"统计"、"聚合" → **AGGREGATE**

## 上层业务 Skill 注入协议

### 1. completeOql 优先

当上层业务 Skill 已经生成 `completeOql` 时，本层必须直接执行该 OQL：

1. 不重新选择 QUERY / ASSOCIATION_QUERY / AGGREGATE。
2. 不重新生成 objects / relationships / conditions / returns。
3. 不删除 `options`、`extensions`、`sourceQuery`。
4. 只做 OQL 合法性校验、紧凑化和执行。
5. 如果发现别名、字段、关系、函数未注册或不符合 schema，返回明确错误。

### 2. operationHint 优先

当上层业务 Skill 传入 `operationHint` 时，以业务 Skill 指定的操作类型为准。

```yaml
operationHint: QUERY | ASSOCIATION_QUERY | AGGREGATE
```

例如 SEC 多维场景中，用户说“栅格 A 对应的小区 RSRP”，虽然自然语言包含“对应 / 归属”，但如果业务 Skill 判断 DAC 多维模型支持通过栅格维度过滤并返回小区维度，则可传入：

```yaml
operationHint: QUERY
semanticHints:
  queryScene: OWNERSHIP_FILTER_DIMENSION_QUERY
```

本层不得仅因为出现“归属”一词就强行改为 `ASSOCIATION_QUERY`。

### 3. semanticHints 作为 OQL 拼接输入

当上层业务 Skill 未直接传入 `completeOql`，但传入 `semanticHints` 时，本层应将其作为 OQL 组装输入。

| semanticHints 字段 | 说明 |
|---|---|
| `objects` | 业务侧解析出的对象、别名、对象类型 |
| `fields` | 业务侧解析出的属性、维度、指标、度量 |
| `time` | 时间字段、时间范围、时区、分表时间策略 |
| `behavior` | 查询、统计、验证、TOP、活跃、未恢复等行为语义 |
| `path` | 归属、同站点、对端网元、业务路径等关系语义 |
| `sourcePolicy` | DAC、OntoAccess、Graph、RDB 等后端倾向 |
| `fallbackPolicy` | 拆分查询、批量查询、函数合并、空结果处理策略 |

### 4. extensions 透传

OQL 顶层允许携带 `extensions` 字段。该字段用于业务场景向 OAC 编译器、数据源适配器或执行后端传递受控扩展参数。

#### 约束

1. `extensions` 必须为对象。
2. 必须按 namespace 隔离，例如 `extensions.sec`、`extensions.alarm`。
3. 不得在 `extensions` 中传递物理 SQL、GQL、TQL。
4. 不得通过 `extensions` 绕过 schema / mapping / capability 校验。
5. OAC 服务端必须基于白名单识别 `extensions`。
6. 未识别的 `extensions` 应返回 warning 或明确错误，由服务策略决定。

#### SEC 分表时间示例

```json
"extensions": {
  "sec": {
    "partitionTime": {
      "timeMode": "UTC",
      "sourceTimeZone": "Asia/Shanghai",
      "partitionField": "3600"
    },
    "targetBackend": "DAC",
    "dacAction": "AGGRE_XDR"
  }
}
```

### 5. 扩展函数表达式

业务 Skill 如需表达多维模型中的 ID 维度或名称维度，应优先使用 OQL 受控函数表达式，不应把函数写成普通字符串。

推荐：

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "namespace": "sec",
    "name": "NAME",
    "args": [
      { "kind": "FIELD", "ref": "o", "field": "release_cause" }
    ]
  },
  "alias": "release_cause_name"
}
```

不推荐：

```json
{ "kind": "FUNCTION", "ref": "o", "field": "NAME(release_cause)", "alias": "release_cause_name" }
```

## 子文档

- `oac-query.md` - QUERY 操作手册（无关联）
- `oac-association-query.md` - ASSOCIATION_QUERY 操作手册（有关联）
- `oac-aggregate.md` - AGGREGATE 操作手册（聚合查询）

## 脚本

| 脚本 | 作用 |
|------|------|
| `execute_oac_operation.py` | 执行 OAC 请求 |
