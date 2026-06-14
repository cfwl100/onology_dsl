# SEC 多维查询自然语言 Workflow 示例

本文只描述 `scenario-skill/sec-multidim` 内部的业务流程规划方式。平台稳态 Skill 不需要感知这些 workflow，也不需要识别 `workflowId`、`stepId`、`dependsOn`、`variableBinding` 等业务编排字段。

本业务 Skill 执行多步流程时，做法是：

1. 本 Skill 自己判断当前业务场景。
2. 本 Skill 自己决定先做哪一步、后做哪一步。
3. 每一步都用自然语言委托平台能力。
4. 如果前一步有结果，本 Skill 自己读取结果，并把结果写入下一步自然语言委托的过滤条件中。
5. 如果前一步为空，依赖它的后续步骤直接返回空，不重复查询。

---

## Workflow 1：先执行对象 Function，再执行对象 OAC 查询

适用场景：

```text
在告警查询或对象查询场景中，需要先通过对象 Function 标准化对象上下文、补齐查询参数，再执行对象数据查询。
```

业务侧自然语言流程：

```text
第一步：请调用本体平台函数能力，基于用户输入中的对象名称、对象类型、时间范围和业务上下文，选择对象上可用的标准化函数，输出标准对象标识、标准对象名称、推荐时间范围和可用于查询的过滤字段。

第二步：读取第一步函数返回结果。如果第一步返回标准对象标识，则将该标识作为 OAC 查询条件；如果第一步未返回可用标识，则停止并说明缺少可查询条件。

第三步：请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- 操作类型：QUERY
- 查询对象：<目标对象>
- 过滤条件：使用第一步函数返回的标准对象标识、时间范围和业务字段
- 返回字段：用户要求的字段；如用户未指定，只返回业务场景要求的最小字段集合
- 返回要求：OAC 返回什么字段就保留什么字段，结果为空即为空，不重复查询
```

注意：上述“第一步、第二步、第三步”只存在于本业务 Skill 内部，不传给平台 Skill 作为结构化 workflow。

---

## Workflow 2：查询栅格 A、小区 B 的 RSRP

场景判断：

```text
用户显式给出栅格 A 和小区 B，查询二者组合维度下的 RSRP。
这是跨对象、组合维度、相同指标/度量查询。
```

自然语言委托：

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：QUERY
- 查询对象：grid，别名 g；cell，别名 c
- 过滤条件：g.DIM_GRID 等于 A；c.DIM_CELL 等于 B
- 返回字段：g.DIM_GRID、c.DIM_CELL、c.C_RSRP
- 扩展要求：这是 SEC 组合维度查询，优先按 DAC 多维模型映射处理；如果生成 OQL 支持 extensions，请加入 SEC 场景标识 COMPOSITE_DIMENSION 和 targetBackend=DAC
- 返回要求：保留原始字段，结果为空即为空
```

---

## Workflow 3：查询栅格 A 对应的小区的 RSRP

场景判断：

```text
用户表达“栅格 A 对应/归属的小区”，查询小区维度下的 RSRP。
如果 DAC 多维模型支持通过 DIM_GRID 过滤并返回 DIM_CELL，则不拆成关系查询。
```

自然语言委托：

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：QUERY
- 查询对象：grid，别名 g；cell，别名 c
- 过滤条件：g.DIM_GRID 等于 A
- 返回字段：c.DIM_CELL、c.C_RSRP
- 扩展要求：这是 SEC 归属过滤的多维查询；若 OQL 支持 extensions，请表达 dimensionLift=true，含义是允许 DAC 根据多维模型从栅格维度过滤到小区维度
- 返回要求：保留原始字段，结果为空即为空
```

注意：这里用户说了“归属”，但不一定使用 `ASSOCIATION_QUERY`。只要多维模型支持通过栅格维度过滤到小区维度，就优先使用 `QUERY`。

---

## Workflow 4：查询栅格 A、小区 B 的 PRB

场景判断：

```text
用户显式给出栅格 A 和小区 B，查询 PRB。
即使 PRB 与栅格、小区不是完全相同指标/度量，只要用户给出了完整组合维度，也先按组合维度 QUERY 处理。
```

自然语言委托：

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：QUERY
- 查询对象：grid，别名 g；cell，别名 c
- 过滤条件：g.DIM_GRID 等于 A；c.DIM_CELL 等于 B
- 返回字段：g.DIM_GRID、c.DIM_CELL、c.C_PRB
- 扩展要求：这是 SEC 组合维度查询，优先按 DAC 多维模型映射处理；如果生成 OQL 支持 extensions，请加入 SEC 场景标识 COMPOSITE_DIMENSION 和 targetBackend=DAC
- 返回要求：保留原始字段；如果业务映射不全导致无记录，结果为空即为空
```

---

## Workflow 5：查询栅格 A 对应的小区 PRB，且不存在维表升维

场景判断：

```text
用户表达“栅格 A 对应/归属的小区 PRB”，但业务知识判断 PRB 不支持通过栅格维度直接升维查询。
此时不能把栅格过滤条件直接塞到小区 PRB 查询中，必须先查栅格到小区的关系主键，再用小区主键查 PRB。
```

自然语言流程：

```text
第一步：请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：ASSOCIATION_QUERY
- 查询对象：grid，别名 g；cell，别名 c
- 关系路径：g 通过 locateIn 关系到 c；关系名 locateIn 必须来自本体子图或已确认的业务建模
- 过滤条件：g.GRID_ID 等于 A
- 返回字段：c.CELL_ID
- 扩展要求：这是 SEC 关系主键发现步骤；如果生成 OQL 支持 extensions，请表达 relationResolve=GRID_TO_CELL
- 返回要求：保留返回的 CELL_ID；如果为空，后续 PRB 查询直接为空

第二步：本业务 Skill 读取第一步返回的 CELL_ID。如果返回多个 CELL_ID，则第二步使用 IN 条件；如果平台不支持 IN，则由本业务 Skill 拆成多次自然语言查询。

第三步：请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：QUERY
- 查询对象：cell，别名 c
- 过滤条件：c.CELL_ID 等于第一步返回的 CELL_ID，多个值使用 IN
- 返回字段：c.CELL_ID、c.C_PRB
- 扩展要求：这是 SEC 基于已解析小区主键查询 PRB 指标；优先按 DAC 多维模型映射处理
- 返回要求：保留原始字段，结果为空即为空
```

注意：第一步和第三步是两次独立的平台能力调用。平台 Skill 不需要理解这两个步骤之间的变量绑定关系，变量读取和填充由本业务 Skill 自己完成。
