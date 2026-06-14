# SEC 多维查询场景识别规则

## 1. 场景分类

### S1：不跨对象查询维度

用户只查询单对象下的维度、属性、指标或度量。

执行策略：

```yaml
workflowId: single-object-dimension-query
operationHint: QUERY
stepCount: 1
backendHint: DAC_OR_ONTO_ACCESS
```

---

### S2：跨对象关联了相同指标/度量，且用户显式指定多个维度

示例：

```text
查询栅格为 A，小区为 B 的 RSRP
```

语义判断：

```yaml
queryScene: COMPOSITE_DIMENSION
objects:
  - grid
  - cell
conditions:
  - DIM_GRID = A
  - DIM_CELL = B
returns:
  - DIM_GRID
  - DIM_CELL
  - C_RSRP
operationHint: QUERY
backendHint: DAC
stepCount: 1
```

说明：

- 用户显式给出了栅格维度和小区维度。
- RSRP 是可在多维模型中通过组合维度过滤的指标。
- 业务 Skill 应生成单条 `QUERY`，不需要关系遍历。

---

### S3：跨对象关联了相同指标/度量，用户表达归属关系

示例：

```text
查询栅格 A 对应的小区的 RSRP
查询栅格 A 归属的小区 RSRP
```

语义判断：

```yaml
queryScene: OWNERSHIP_FILTER_DIMENSION_QUERY
objects:
  - grid
  - cell
conditions:
  - DIM_GRID = A
returns:
  - DIM_CELL
  - C_RSRP
operationHint: QUERY
backendHint: DAC
dimensionLift: true
stepCount: 1
```

说明：

- 虽然用户使用了“对应 / 归属”，但如果 DAC 多维模型支持通过 `DIM_GRID` 过滤并返回 `DIM_CELL`，则不走 `ASSOCIATION_QUERY`。
- 只有当业务配置明确“不存在维表升维”时，才降级为 S5 两步查询。

---

### S4：跨对象未关联相同指标/度量，但用户显式指定多个维度

示例：

```text
查询栅格为 A，小区为 B 的 PRB
```

语义判断：

```yaml
queryScene: COMPOSITE_DIMENSION_DIFFERENT_METRIC
objects:
  - grid
  - cell
conditions:
  - DIM_GRID = A
  - DIM_CELL = B
returns:
  - DIM_GRID
  - DIM_CELL
  - C_PRB
operationHint: QUERY
backendHint: DAC
stepCount: 1
```

说明：

- 用户显式指定了栅格维度和小区维度。
- 即使 PRB 不属于栅格对象的同类指标，只要多维模型中可以按组合维度过滤并返回该指标，仍使用 `QUERY`。
- 如果访问无记录，返回空即可，不重复查询。

---

### S5：跨对象未关联相同指标/度量，且不存在维表升维

示例：

```text
查询栅格 A 对应的小区的 PRB
```

适用条件：

```yaml
queryScene: RELATION_KEY_THEN_METRIC
ownershipRelation: true
dimensionLift: false
stepCount: 2
```

执行策略：

```yaml
steps:
  - stepId: S1
    operationHint: ASSOCIATION_QUERY
    objective: 通过栅格主属性查询归属小区主键 CELL_ID
  - stepId: S2
    operationHint: QUERY
    objective: 以上一步输出的 CELL_ID 查询小区 PRB 指标
```

说明：

- 第一步通过本体关系或关系绑定逻辑模型解析栅格到小区的主键。
- 第二步在小区对象下查询指标。
- 必须使用 `variableBinding` 将 S1 输出绑定到 S2 条件。

---

## 2. operationHint 选择规则

| 用户表达 | 业务判断 | operationHint |
|---|---|---|
| 查询栅格 A、小区 B 的 RSRP | 组合维度查询 | QUERY |
| 查询栅格 A 对应的小区 RSRP | 支持维表升维 | QUERY |
| 查询栅格 A、小区 B 的 PRB | 组合维度查询 | QUERY |
| 查询栅格 A 对应的小区 PRB | 不支持维表升维 | ASSOCIATION_QUERY + QUERY |
| 统计每个小区的平均 PRB | 聚合查询 | AGGREGATE |
| 沿关系链查对象 | 关系路径查询 | ASSOCIATION_QUERY |

---

## 3. DAC 与 OntoAccess 分段策略

| 场景 | 推荐后端 |
|---|---|
| 多维模型维度/指标查询 | DAC |
| SDR / XDR 事实表查询 | DAC |
| 对象实例属性查询 | OntoAccess |
| 对象关系主键解析 | OntoAccess 或 DAC，按 mapping 能力决定 |
| 图关系路径遍历 | OntoAccess / Graph |
| 查询后复杂合并 | Function |

如果单条 OQL 无法由 OAC 后端能力覆盖，业务 Skill 应规划多步执行，而不是在单个 OQL 中硬塞物理后端逻辑。
