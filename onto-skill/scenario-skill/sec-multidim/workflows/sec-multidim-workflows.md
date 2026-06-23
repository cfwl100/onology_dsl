# SEC 多维查询流程级与步骤级定制示例

本文提供 `scenario-skill/sec-multidim` 面向 `Ontology-based-planning-skill` 的流程级和步骤级定制示例。

这些示例只描述业务 Skill 如何注入 Planning 层，不是平台 OAC 的结构化协议。Planning 层负责基于业务定制文件、OAG 本体子图和平台能力模板生成最终执行步骤。

---

## 1. 通用委托格式

业务 Skill 识别场景后，向 Planning 层传递如下内容：

```text
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题>
业务定制文件内容：<knowledge/sec-multidim-guidance.md 中与当前场景相关的规则>
流程级定制：<执行哪些步骤、跳过哪些步骤、是否追加步骤、步骤顺序>
步骤级定制：<S2/S3/S4/S5/S6/S7 的输入、输出和执行规则>
缺失信息：<没有则写无>
```

所有示例都默认：

- 业务定制文件 `knowledge/sec-multidim-guidance.md` 已读取。
- OAC 最终输出只保留 `{objects, relationships}`。
- 空结果是有效结果，不自动放宽条件。
- 对外只使用公共 `本体ID`。

---

## 2. 示例一：单步组合维度明细查询

用户问题：

```text
查询栅格 A、小区 B 最近 1 小时的 RSRP。
```

Planning 输入：

```text
本体ID：<公共本体ID>
业务意图：查询 SEC 多维模型中栅格维度 A 和小区维度 B 组合条件下，最近 1 小时的小区 RSRP 指标明细；返回 DIM_GRID、DIM_CELL、C_RSRP；按默认本地时间处理；结果为空即为空。
业务定制文件内容：读取 knowledge/sec-multidim-guidance.md 中 S2 组合维度查询、字段口径、时间语义和正反例规则。
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6 Function。
步骤级定制：
- S2：检索 grid、cell、DIM_GRID、DIM_CELL、C_RSRP、时间字段 3600。
- S3：规划组合维度指标明细 QUERY，不走关系路径。
- S4：过滤 DIM_GRID=A、DIM_CELL=B、3600 在最近 1 小时范围内；返回 DIM_GRID、DIM_CELL、C_RSRP；如支持 extensions，表达 localtime="true"。
- S7：返回对象结构和业务解释。
缺失信息：无。
```

---

## 3. 示例二：归属过滤且支持维度升维

用户问题：

```text
查询栅格 A 对应的小区 RSRP。
```

Planning 输入：

```text
本体ID：<公共本体ID>
业务意图：查询栅格 A 归属或对应小区的 RSRP 指标；业务规则判断 RSRP 支持通过 DIM_GRID 过滤并返回 DIM_CELL，因此优先按多维模型维度升维查询，不走关系路径。
业务定制文件内容：读取 knowledge/sec-multidim-guidance.md 中 S3 归属过滤多维查询、维度升维、字段口径和反例规则。
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 S5/S6。
步骤级定制：
- S2：检索 grid、cell、DIM_GRID、DIM_CELL、C_RSRP，并同时检索 grid 到 cell 的关系候选作为备选结构依据。
- S3：虽然用户表达“对应/归属”，但因业务规则支持维度升维，规划 OAC 明细 QUERY，而不是 ASSOCIATION_QUERY。
- S4：过滤 DIM_GRID=A，返回 DIM_CELL、C_RSRP；扩展说明 dimensionLift=true。
- S7：说明本次使用多维模型升维过滤，不走关系路径。
缺失信息：如缺少时间范围，按 SEC 默认时间策略处理。
```

---

## 4. 示例三：两步关系主键解析 + 指标查询

用户问题：

```text
查询栅格 A 对应的小区 PRB。
```

业务前提：

```text
业务定制文件判断 PRB 不支持通过栅格维度直接升维查询，需要先通过关系路径解析 CELL_ID。
```

Planning 输入：

```text
本体ID：<公共本体ID>
业务意图：查询栅格 A 归属小区的 PRB 指标；由于 PRB 不支持通过 DIM_GRID 维度升维直接查询，需要先沿 grid 到 cell 的关系路径查询 CELL_ID，再用 CELL_ID 查询 C_PRB。
业务定制文件内容：读取 knowledge/sec-multidim-guidance.md 中 S5 两步查询、字段口径、关系主键解析和空结果策略。
流程级定制：执行 S1 -> S2 -> S3 -> S4a -> S4b -> S7；不执行 Function。
步骤级定制：
- S2：检索 grid、cell、GRID_ID、CELL_ID、C_PRB、grid 到 cell 的关系候选。
- S3：规划两个 OAC 任务：S4a 关系路径查询 CELL_ID；S4b 按 CELL_ID 查询 C_PRB。
- S4a：按栅格到小区关系路径查询小区主键，通过 grid.GRID_ID=A 沿子图确认的关系查询 cell.CELL_ID。
- S4b：读取 S4a 返回的 CELL_ID；如果一个值则使用等值条件，如果多个值则优先使用 IN 条件；返回 CELL_ID、C_PRB。
- S7：合并两个 OAC 结果；如果 S4a 为空，S4b 不执行，返回空对象结构并说明原因。
缺失信息：如子图未返回 grid 到 cell 的关系，返回缺失关系说明。
```

---

## 5. 示例四：聚合统计查询

用户问题：

```text
统计最近一天每个小区的平均 PRB，并返回大于 80% 的小区。
```

Planning 输入：

```text
本体ID：<公共本体ID>
业务意图：统计最近一天每个小区的平均 PRB，过滤平均 PRB 大于 80% 的小区，返回小区维度、平均 PRB 和排序结果。
业务定制文件内容：读取 knowledge/sec-multidim-guidance.md 中 S6 聚合统计、字段口径、时间语义和聚合规则。
流程级定制：执行 S1 -> S2 -> S3 -> S4 -> S7；不执行 Function。
步骤级定制：
- S2：检索 cell、DIM_CELL、C_PRB、时间字段 3600。
- S3：规划 AGGREGATE，分组字段为 DIM_CELL，聚合函数为 AVG(C_PRB)，聚合后过滤 avg_prb > 80。
- S4：生成并执行聚合查询；时间范围为最近一天；如本地时间口径，表达 localtime="true"。
- S7：返回对象结构或聚合对象结构，并解释聚合口径。
缺失信息：无。
```

---

## 6. 示例五：Function 前置补齐上下文

用户问题：

```text
查询网元 X 最近 5 分钟的关键指标，先按平台规则标准化网元名称。
```

Planning 输入：

```text
本体ID：<公共本体ID>
业务意图：先通过本体函数能力标准化网元 X 的对象上下文，获得标准对象标识和可查询字段，再查询最近 5 分钟关键指标。
业务定制文件内容：读取 knowledge/sec-multidim-guidance.md 中 S7 Function 前置查询、时间语义和函数调用规则。
流程级定制：执行 S1 -> S2 -> S3 -> S5 -> S6 -> S4 -> S7。
步骤级定制：
- S2：检索网元对象、关键指标字段、可用函数候选 result.functions。
- S3：规划 Function 前置任务和后续 OAC 查询任务。
- S5：从 result.functions 中按 description 选择标准化函数。
- S6：调用 get_params_spec，解析 physicalName，组装 params，调用 call_function(physicalName, function_id, params)。
- S4：将函数返回的标准对象标识写入过滤条件，查询最近 5 分钟关键指标。
- S7：输出函数结果、查询结果和缺失项。
缺失信息：如果函数参数规格缺少必填参数，停止并返回缺失项。
```

---

## 7. 禁止写法

禁止把如下内容直接传给平台能力层：

```text
workflowId: xxx
stepId: S4a
dependsOn: S4a
variableBinding: ${S4a.CELL_ID}
```

这些内容只能存在于业务 Skill 和 Planning 层的自然语言规则中。平台 OAG/OAC/Function 只接收当前步骤的自然语言输入模板。
