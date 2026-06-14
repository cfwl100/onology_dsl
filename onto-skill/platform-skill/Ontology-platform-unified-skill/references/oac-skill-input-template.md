# OAC Skill 输入模板

本文定义上层业务 Skill 调用本体数据访问能力时的标准输入模板。

平台稳态 Skill 只识别当前一次 OAC 调用，不感知业务 workflow。业务 Skill 必须先完成业务语义理解、执行步骤规划、参数绑定，再按照本模板填写当前 OAC 请求。

---

## 1. 标准模板

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: <本次查询目的，可选>
  completeOql:
    version: "1.0"
    schemaRef: <schemaRef>
    strict: true
    operation: QUERY | ASSOCIATION_QUERY | AGGREGATE | CREATE | UPDATE | DELETE | UPSERT | BULK_CREATE | BULK_UPDATE | BULK_UPSERT
    objects:
      - objectType: <objectType>
        alias: <alias>
    relationships: []
    conditions: {}
    returns: []
    options: {}
    extensions: {}
    sourceQuery: {}
    maxResults: 1000
  messageType: <可选>
  validateOnly: false
```

---

## 2. 必填字段

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `oacSkillInput.requestType` | 是 | 固定为 `COMPLETE_OQL` |
| `oacSkillInput.completeOql` | 是 | 完整 OQL JSON |
| `completeOql.version` | 是 | OQL 版本 |
| `completeOql.schemaRef` | 是 | 本体 schema 引用 |
| `completeOql.strict` | 是 | 是否严格校验 |
| `completeOql.operation` | 是 | 查询动作 |
| `completeOql.objects` | 是 | 参与查询的对象 |
| `completeOql.conditions` | 按需 | 查询条件 |
| `completeOql.returns` | 查询类必填 | 返回字段、指标或表达式 |

---

## 3. 禁止字段

上层业务 Skill 不应将以下业务 workflow 字段传入 OAC：

- `workflowId`
- `executionPlan`
- `steps`
- `stepId`
- `dependsOn`
- `variableBinding`
- `fallbackPolicy`
- `outputRef`

如果业务需要这些字段，应只在业务 Skill 自己的 workflow 文档和执行逻辑中使用。业务 Skill 应在每一步调用 OAC 前，把当前步骤需要的对象、条件、返回字段、扩展参数全部落入 `completeOql`。

---

## 4. QUERY 示例

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: 查询栅格 A、小区 B 的 RSRP
  completeOql:
    version: "1.0"
    schemaRef: ams_topology@1.0
    strict: true
    operation: QUERY
    objects:
      - objectType: grid
        alias: g
      - objectType: cell
        alias: c
    conditions:
      kind: GROUP
      relation: AND
      children:
        - kind: PREDICATE
          ref: g
          field: DIM_GRID
          operator: EQ
          values: ["A"]
        - kind: PREDICATE
          ref: c
          field: DIM_CELL
          operator: EQ
          values: ["B"]
    returns:
      - kind: FIELDS
        ref: g
        fields: [DIM_GRID]
      - kind: FIELDS
        ref: c
        fields: [DIM_CELL]
      - kind: FIELDS
        ref: c
        fields: [C_RSRP]
    extensions:
      sec:
        queryScene: COMPOSITE_DIMENSION
        targetBackend: DAC
    maxResults: 1000
  messageType: sec_multidim_query
  validateOnly: false
```

---

## 5. ASSOCIATION_QUERY 示例

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: 通过栅格 A 查询归属小区 CELL_ID
  completeOql:
    version: "1.0"
    schemaRef: ams_topology@1.0
    strict: true
    operation: ASSOCIATION_QUERY
    objects:
      - objectType: grid
        alias: g
      - objectType: cell
        alias: c
    relationships:
      - relationshipType: locateIn
        alias: r1
        from: g
        to: c
    conditions:
      kind: GROUP
      relation: AND
      children:
        - kind: PREDICATE
          ref: g
          field: GRID_ID
          operator: EQ
          values: ["A"]
    returns:
      - kind: FIELDS
        ref: c
        fields: [CELL_ID]
    extensions:
      sec:
        queryScene: RELATION_KEY_DISCOVERY
        targetBackend: DAC
        relationResolve: GRID_TO_CELL
  messageType: sec_relation_key_query
  validateOnly: false
```

---

## 6. extensions 填写规则

`extensions` 必须作为 `completeOql` 的顶层字段，按 namespace 隔离。

SEC 示例：

```yaml
extensions:
  sec:
    partitionTime:
      timeMode: UTC
      sourceTimeZone: Asia/Shanghai
      partitionField: "3600"
    targetBackend: DAC
    dacAction: AGGRE_XDR
```

约束：

1. 不得在 `extensions` 中传递物理 SQL、GQL、TQL。
2. 不得通过 `extensions` 绕过 schema、mapping、capability 校验。
3. 未识别的扩展参数应由 OAC 返回 warning 或明确错误。

---

## 7. 多步业务查询的调用方式

多步业务查询由业务 Skill 自行编排。例如“先查栅格 A 对应的小区 ID，再查小区 PRB”：

1. 业务 Skill 生成 Step1 的 `oacSkillInput` 并调用 OAC。
2. 业务 Skill 读取 Step1 返回的 `CELL_ID`。
3. 业务 Skill 将 `CELL_ID` 填入 Step2 的 `completeOql.conditions.children[].values`。
4. 业务 Skill 生成 Step2 的 `oacSkillInput` 并再次调用 OAC。

平台 OAC 不接收 `variableBinding`，也不自动执行跨步骤绑定。