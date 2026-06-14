# SEC 多维查询业务 Workflow 示例

本文定义 SEC 多维查询业务 Skill 内部承载的 workflow 示例。

重要原则：

1. Workflow 规划属于 `scenario-skill/sec-multidim`，不属于平台稳态 Skill。
2. 平台 Skill 不感知 `workflowId`、`stepId`、`dependsOn`、`variableBinding`。
3. 每次调用 OAC 时，本 Skill 必须把当前步骤整理成独立的 `oacSkillInput`。
4. 多步之间的结果读取、参数绑定、空结果判断由本业务 Skill 自行完成。

---

## Workflow 1：先执行对象 Function，再执行对象 OAC 查询

适用场景：

```text
在告警查询或对象查询场景中，需要先通过对象 Function 标准化对象上下文、补齐查询参数，再执行对象数据查询。
```

业务侧执行顺序：

```yaml
businessWorkflow:
  id: function-then-oac-query
  owner: scenario-skill/sec-multidim
  steps:
    - stepId: S1
      type: FUNCTION_CALL
      objective: 标准化对象上下文或补齐查询参数
      functionIntent: normalize_object_context
      output: normalizedContext
    - stepId: S2
      type: OAC_CALL
      objective: 使用 S1 输出构造当前 OAC 查询
      inputBuildRule:
        - 将 S1.output.normalizedObjectId 填入 completeOql.conditions
        - 将 S1.output.normalizedObjectType 填入 completeOql.objects
```

S2 调用平台 OAC 时，只传当前步骤输入：

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: 使用函数标准化结果查询对象数据
  completeOql:
    version: "1.0"
    schemaRef: <schemaRef>
    strict: true
    operation: QUERY
    objects:
      - objectType: <S1.output.normalizedObjectType>
        alias: o
    conditions:
      kind: GROUP
      relation: AND
      children:
        - kind: PREDICATE
          ref: o
          field: <object_id_field>
          operator: EQ
          values: ["<S1.output.normalizedObjectId>"]
    returns:
      - kind: FIELDS
        ref: o
        fields: [<业务要求返回字段>]
  messageType: object_query_result
  validateOnly: false
```

约束：`S1 → S2` 的绑定由本业务 Skill 完成，不传给平台 Skill。

---

## Workflow 2：栅格 A、小区 B 的 RSRP

场景类型：`S2_COMPOSITE_DIMENSION_SAME_METRIC`

业务语义：

```yaml
queryScene: COMPOSITE_DIMENSION
backendHint: DAC
objects: [grid, cell]
conditions:
  DIM_GRID: A
  DIM_CELL: B
returns:
  - DIM_GRID
  - DIM_CELL
  - C_RSRP
```

OAC 调用输入：

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
        deduplicateMetrics: true
    maxResults: 1000
  messageType: sec_grid_cell_rsrp
  validateOnly: false
```

---

## Workflow 3：栅格 A 对应的小区 RSRP

场景类型：`S3_OWNERSHIP_FILTER_SAME_METRIC`

业务语义：

```yaml
queryScene: OWNERSHIP_FILTER_DIMENSION_QUERY
backendHint: DAC
dimensionLift: true
```

说明：虽然用户说“对应 / 归属”，但只要多维模型支持通过栅格维度过滤并返回小区维度，就使用 `QUERY`，不强行走关系遍历。

OAC 调用输入：

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: 查询栅格 A 对应的小区 RSRP
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
    returns:
      - kind: FIELDS
        ref: c
        fields: [DIM_CELL]
      - kind: FIELDS
        ref: c
        fields: [C_RSRP]
    extensions:
      sec:
        queryScene: OWNERSHIP_FILTER_DIMENSION_QUERY
        targetBackend: DAC
        dimensionLift: true
    maxResults: 1000
  messageType: sec_grid_owned_cell_rsrp
  validateOnly: false
```

---

## Workflow 4：栅格 A、小区 B 的 PRB

场景类型：`S4_COMPOSITE_DIMENSION_DIFFERENT_METRIC`

业务语义：

```yaml
queryScene: COMPOSITE_DIMENSION_DIFFERENT_METRIC
backendHint: DAC
objects: [grid, cell]
conditions:
  DIM_GRID: A
  DIM_CELL: B
returns:
  - DIM_GRID
  - DIM_CELL
  - C_PRB
```

OAC 调用输入与 Workflow 2 类似，只需将返回指标替换为 `C_PRB`，并将 `extensions.sec.queryScene` 设置为 `COMPOSITE_DIMENSION_DIFFERENT_METRIC`。

---

## Workflow 5：栅格 A 对应的小区 PRB，且不存在维表升维

场景类型：`S5_RELATION_KEY_THEN_METRIC`

业务语义：

```yaml
queryScene: RELATION_KEY_THEN_METRIC
dimensionLift: false
```

该场景由本业务 Skill 拆成两次 OAC 调用。

### Step1：通过栅格 A 查询归属小区 CELL_ID

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

### Step2：使用 Step1 返回的 CELL_ID 查询小区 PRB

本业务 Skill 读取 Step1 的返回结果：

```yaml
resolvedCellIds: <Step1.rows[*].CELL_ID>
```

然后由本业务 Skill 将 `resolvedCellIds` 填入 Step2 的 `completeOql.conditions.children[0].values`。

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: 使用归属小区 CELL_ID 查询 PRB
  completeOql:
    version: "1.0"
    schemaRef: ams_topology@1.0
    strict: true
    operation: QUERY
    objects:
      - objectType: cell
        alias: c
    conditions:
      kind: GROUP
      relation: AND
      children:
        - kind: PREDICATE
          ref: c
          field: CELL_ID
          operator: IN
          values: [<resolvedCellIds>]
    returns:
      - kind: FIELDS
        ref: c
        fields: [CELL_ID]
      - kind: FIELDS
        ref: c
        fields: [C_PRB]
    extensions:
      sec:
        queryScene: CELL_METRIC_BY_RESOLVED_KEY
        targetBackend: DAC
    maxResults: 1000
  messageType: sec_cell_prb_by_resolved_key
  validateOnly: false
```

约束：

1. Step2 的条件别名必须是 `c`，不得使用未声明的 `g`。
2. Step1 的关系字段使用 `relationshipType`，不得写成 `objectType`。
3. 如果 Step1 返回空，本业务 Skill 直接返回空结果，不再生成 Step2。
4. 禁止把 `variableBinding` 传给平台 OAC；绑定动作由本业务 Skill 完成。
