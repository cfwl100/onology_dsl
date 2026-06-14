# SEC 多维查询 Workflow 示例

本文定义 SEC 多维查询业务 Skill 输出给 `Ontology-based-planning-skill` 的执行计划示例。

---

## Workflow 1：先执行对象 Function，再执行对象 OAC 查询

适用场景：

```text
在告警查询场景中，先执行对象上的函数能力，再执行对象数据查询。
```

执行计划：

```yaml
executionPlan:
  scenario: sec-multidim
  workflowId: function-then-oac-query
  steps:
    - stepId: S1
      stepType: FUNCTION_CALL
      objective: 标准化对象上下文或补齐查询参数
      functionIntent: normalize_object_context
      outputRef: normalizedContext

    - stepId: S2
      stepType: DATA_ACCESS
      dependsOn: [S1]
      operationHint: QUERY
      completeOql: <业务 Skill 生成的完整 OQL>
      variableBinding:
        - from: S1.output.normalizedObjectId
          to: completeOql.conditions.children[0].values
          mode: EQ
```

---

## Workflow 2：栅格 A、小区 B 的 RSRP

场景类型：`S2_COMPOSITE_DIMENSION_SAME_METRIC`

业务语义：

```yaml
queryScene: COMPOSITE_DIMENSION
operationHint: QUERY
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

执行计划：

```yaml
executionPlan:
  scenario: sec-multidim
  workflowId: grid-cell-rsrp
  steps:
    - stepId: S1
      stepType: DATA_ACCESS
      operationHint: QUERY
      completeOql:
        version: "2.0"
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
```

---

## Workflow 3：栅格 A 对应的小区 RSRP

场景类型：`S3_OWNERSHIP_FILTER_SAME_METRIC`

业务语义：

```yaml
queryScene: OWNERSHIP_FILTER_DIMENSION_QUERY
operationHint: QUERY
backendHint: DAC
dimensionLift: true
```

说明：虽然用户说“对应 / 归属”，但只要多维模型支持通过栅格维度过滤并返回小区维度，就使用 `QUERY`，不强行走关系遍历。

执行计划：

```yaml
executionPlan:
  scenario: sec-multidim
  workflowId: grid-to-cell-rsrp-with-dimension-lift
  steps:
    - stepId: S1
      stepType: DATA_ACCESS
      operationHint: QUERY
      completeOql:
        version: "2.0"
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
```

---

## Workflow 4：栅格 A、小区 B 的 PRB

场景类型：`S4_COMPOSITE_DIMENSION_DIFFERENT_METRIC`

业务语义：

```yaml
queryScene: COMPOSITE_DIMENSION_DIFFERENT_METRIC
operationHint: QUERY
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

执行计划与 Workflow 2 类似，只需将返回指标替换为 `C_PRB`，并将 `extensions.sec.queryScene` 设置为 `COMPOSITE_DIMENSION_DIFFERENT_METRIC`。

---

## Workflow 5：栅格 A 对应的小区 PRB，且不存在维表升维

场景类型：`S5_RELATION_KEY_THEN_METRIC`

业务语义：

```yaml
queryScene: RELATION_KEY_THEN_METRIC
operationHint: ASSOCIATION_QUERY + QUERY
dimensionLift: false
```

执行计划：

```yaml
executionPlan:
  scenario: sec-multidim
  workflowId: grid-to-cell-prb-by-relation-key
  steps:
    - stepId: S1
      stepType: DATA_ACCESS
      operationHint: ASSOCIATION_QUERY
      objective: 通过栅格 A 查询归属小区 CELL_ID
      outputRef: relatedCells
      completeOql:
        version: "2.0"
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

    - stepId: S2
      stepType: DATA_ACCESS
      dependsOn: [S1]
      operationHint: QUERY
      objective: 使用 S1 返回的 CELL_ID 查询小区 PRB
      completeOql:
        version: "2.0"
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
              values: []
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
      variableBinding:
        - from: S1.rows[*].CELL_ID
          to: completeOql.conditions.children[0].values
          mode: IN
```

约束：

1. Step2 的条件别名必须是 `c`，不得使用未声明的 `g`。
2. Step1 的关系字段使用 `relationshipType`，不得写成 `objectType`。
3. 如果 Step1 返回空，Step2 直接返回空，不重复查询。
