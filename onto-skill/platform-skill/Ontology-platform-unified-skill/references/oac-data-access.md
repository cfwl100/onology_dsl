# 本体数据访问（OAC）

## 本层职责

OAC（Ontology Data Access Capability）是本体平台的数据访问层，负责对本体数据进行查询、聚合、路径遍历、创建、更新、删除等操作。

本层只处理本体数据访问协议、OQL 组装、OQL 校验、OQL 执行与结果返回，不承载具体业务场景规则。业务场景规则、业务 workflow、执行顺序、前后步骤变量绑定、降级策略均由上层 `scenario-skill` 承载。

---

## OAC Skill 输入模板

上层业务 Skill 在调用本体数据访问能力时，必须优先按照以下模板组织输入。

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: <本次 OAC 查询的业务目的，可选>
  completeOql:
    version: "1.0"
    schemaRef: <schemaRef>
    strict: true
    operation: QUERY | ASSOCIATION_QUERY | AGGREGATE | CREATE | UPDATE | DELETE | UPSERT | BULK_CREATE | BULK_UPDATE | BULK_UPSERT
    objects: []
    relationships: []        # 仅 ASSOCIATION_QUERY 或路径类查询需要
    conditions: {}           # 查询条件
    returns: []              # 查询返回字段、指标或表达式
    options: {}              # 可选，OQL 标准选项
    extensions: {}           # 可选，业务受控扩展参数
    sourceQuery: {}          # 可选，受控 sourceQuery
    maxResults: 1000
  messageType: <可选，调用方指定的返回消息类型>
  validateOnly: false
```

### 模板填写规则

1. `requestType` 固定为 `COMPLETE_OQL`。
2. `completeOql` 必须是完整、可校验、可执行的 OQL。
3. 查询动作必须写在 `completeOql.operation` 中。
4. `schemaRef` 必须写在 `completeOql.schemaRef` 中。
5. 对象、关系、条件、返回字段必须写入 `completeOql` 内部，不通过额外 workflow 字段补充。
6. `options`、`extensions`、`sourceQuery` 必须作为 `completeOql` 的顶层字段透传。
7. 上层业务 Skill 不应把业务 workflow、stepId、dependsOn、variableBinding、fallbackPolicy 传给 OAC。
8. 如果需要多步查询，上层业务 Skill 应自行逐步调用 OAC；每一步都按照本模板生成独立 `oacSkillInput`。

---

## 完整 OQL 优先规则

当上层业务 Skill 已经生成 `completeOql` 时，本层必须直接执行该 OQL：

1. 不重新选择 `QUERY`、`ASSOCIATION_QUERY`、`AGGREGATE`。
2. 不重新生成 `objects`、`relationships`、`conditions`、`returns`。
3. 不删除 `options`、`extensions`、`sourceQuery`。
4. 只做 OQL 合法性校验、紧凑化和执行。
5. 如果发现别名、字段、关系、函数未注册或不符合 schema，返回明确错误。

---

## 操作类型

OAC 支持三种基础查询操作类型：

| 操作类型 | 说明 | 适用场景 |
|---------|------|---------|
| **QUERY** | 对象查询 | 单对象查询、多对象同事实模型查询、不涉及对象间关系遍历 |
| **ASSOCIATION_QUERY** | 关联查询 | 多跳关系遍历、路径查询、起点终点与中间节点联合约束 |
| **AGGREGATE** | 聚合查询 | 分组统计、指标计算、聚合后过滤 |

当没有传入完整 OQL，需要本层根据自然语言生成 OQL 时，按以下通用规则判断：

- 用户只说“查 XX 的哪些属性”、查 xx 和 xx 的哪些属性、没有提到对象间关系 → **QUERY**。
- 用户明确提到“关系”、“路径”、“遍历”、“连接”、“经过” → **ASSOCIATION_QUERY**。
- 用户明确提到“统计”、“聚合” → **AGGREGATE**。

如果上层已传入完整 OQL，则上述自然语言路由不生效，以 `completeOql.operation` 为准。

---

## `extensions` 透传

OQL 顶层允许携带 `extensions` 字段。该字段用于业务场景向 OAC 编译器、数据源适配器或执行后端传递受控扩展参数。

### 约束

1. `extensions` 必须为对象。
2. 必须按 namespace 隔离，例如 `extensions.sec`、`extensions.alarm`。
3. 不得在 `extensions` 中传递物理 SQL、GQL、TQL。
4. 不得通过 `extensions` 绕过 schema / mapping / capability 校验。
5. OAC 服务端必须基于白名单识别 `extensions`。
6. 未识别的 `extensions` 应返回 warning 或明确错误，由服务策略决定。

### SEC 分表时间示例

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

---

## 扩展函数表达式

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

---

## 子文档

- `oac-skill-input-template.md` - OAC Skill 输入模板
- `oac-query.md` - QUERY 操作手册（无关联）
- `oac-association-query.md` - ASSOCIATION_QUERY 操作手册（有关联）
- `oac-aggregate.md` - AGGREGATE 操作手册（聚合查询）

## 脚本

| 脚本 | 作用 |
|------|------|
| `execute_oac_operation.py` | 执行 OAC 请求 |