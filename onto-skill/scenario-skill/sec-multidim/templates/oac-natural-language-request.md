# OAC 自然语言委托模板

本模板供 `scenario-skill/sec-multidim` 在调用平台本体数据访问能力时使用。模板是业务 Skill 内部写法，不要求平台 Skill 识别新增结构化协议。

该模板面向 `oac-data-access.md` 中的数据访问能力描述，覆盖 `QUERY`、`ASSOCIATION_QUERY`、`AGGREGATE` 三类操作，并通过自然语言方式约束 OQL 生成要素。

---

## 1. 原始模板分析

原始模板：

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
1. schemaRef：
2. 操作类型：
3. 查询对象：
4. 关系路径：
5. 过滤条件：
6. 返回字段：
7. 排序/限制：
8. 扩展说明：
9. 结果处理：
```

该模板具备基本泛化能力，但准确性不足：

1. 没有说明操作选择依据，容易把“归属”一律误判为 `ASSOCIATION_QUERY`。
2. 没有说明 `关系路径` 仅适用于 `ASSOCIATION_QUERY`。
3. 没有覆盖 `AGGREGATE` 的 groupBy、metric、aggregateFilter。
4. 没有要求对象别名和条件归属，容易出现 ref 错误。
5. 没有显式时间要求，SEC 本地时间 / UTC / 分表时间容易遗漏。
6. 扩展说明边界不清，容易写成物理 SQL 或 DAC 私有请求。

---

## 2. 优化后的通用模板

每次委托 OAC 时，优先使用以下模板：

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：

1. schemaRef：<本体 schema，例如 ams_topology@1.0 或 dtmi:com:huawei:ict:sec>
2. 操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE>
3. 操作选择依据：<为什么选择该操作；例如“用户已给完整组合维度，走 QUERY”或“需要沿 locateIn 关系解析 CELL_ID，走 ASSOCIATION_QUERY”>
4. 查询对象：<对象类型、别名、用途；例如 grid 别名 g 用于栅格过滤，cell 别名 c 用于小区指标返回>
5. 关系路径：<仅 ASSOCIATION_QUERY 填写；写清 from、to、关系名、方向；关系名必须来自本体子图或已确认业务建模；QUERY 时明确“无关系路径”>
6. 过滤条件：<逐条列出条件所属对象别名、字段、操作符、值；时间条件也必须写在这里>
7. 返回字段：<逐条列出对象别名、字段、维度/指标含义、别名；禁止默认返回 *>
8. 聚合要求：<仅 AGGREGATE 填写；说明 groupBy、metric、aggregateFilter、having、TopN；非聚合写“无聚合”>
9. 排序/限制：<排序字段、方向、maxResults/limit；没有则写默认限制>
10. 时间要求：<时间范围、本地时间/UTC、采样字段或分表时间字段；没有则写“用户未指定时间，按场景默认策略”>
11. 扩展说明：<SEC 场景标识、DAC 后端倾向、维度升维、关系解析、ID/NAME 维度函数；不得写物理 SQL/GQL/TQL 或 DAC 私有请求>
12. 结果处理：<保留 OAC 原始字段；结果为空即为空；多步查询的下一步条件由业务 Skill 根据本步结果自行生成>
```

---

## 3. QUERY 模板

适用于单对象查询、组合维度查询、支持维度升维的归属过滤查询。

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：

1. schemaRef：ams_topology@1.0
2. 操作类型：QUERY
3. 操作选择依据：用户已给出完整组合维度，或 DAC 多维模型支持通过过滤维度返回目标维度，因此不需要关系路径。
4. 查询对象：grid，别名 g，用于栅格维度过滤；cell，别名 c，用于小区维度和指标返回。
5. 关系路径：无关系路径。本次不是关系遍历，不要生成 relationships。
6. 过滤条件：g.DIM_GRID 等于 A；c.DIM_CELL 等于 B。
7. 返回字段：g.DIM_GRID、c.DIM_CELL、c.C_RSRP。
8. 聚合要求：无聚合。
9. 排序/限制：maxResults 使用场景默认值；如用户指定 limit，以用户指定为准。
10. 时间要求：用户未指定时间，本次按 SEC 场景默认时间策略；如涉及时间字段，必须进入过滤条件。
11. 扩展说明：这是 SEC 组合维度查询，优先按 DAC 多维模型映射处理；如果生成 OQL 支持 extensions，请表达 SEC 场景标识 COMPOSITE_DIMENSION 和 targetBackend=DAC；不要直接生成 DAC 私有请求。
12. 结果处理：保留 OAC 原始字段；结果为空即为空，不重复查询。
```

---

## 4. ASSOCIATION_QUERY 模板

适用于必须沿关系链解析目标对象主键的场景。

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：

1. schemaRef：ams_topology@1.0
2. 操作类型：ASSOCIATION_QUERY
3. 操作选择依据：当前业务场景不支持通过栅格维度直接升维查询小区 PRB，必须先沿关系链解析小区主键 CELL_ID。
4. 查询对象：grid，别名 g，用于栅格主键过滤；cell，别名 c，用于返回归属小区主键。
5. 关系路径：g 通过 locateIn 关系到 c；关系方向是 g -> c；关系名 locateIn 必须来自本体子图或已确认业务建模。
6. 过滤条件：g.GRID_ID 等于 A。
7. 返回字段：c.CELL_ID。
8. 聚合要求：无聚合。
9. 排序/限制：maxResults 使用场景默认值。
10. 时间要求：本步骤是关系主键解析，不涉及 SEC 分表时间；如实际建模需要时间有效性，应补充时间条件。
11. 扩展说明：这是 SEC 关系主键发现步骤；如果生成 OQL 支持 extensions，请表达 relationResolve=GRID_TO_CELL；不要直接生成 DAC 私有请求。
12. 结果处理：保留返回的 CELL_ID；如果为空，后续 PRB 查询直接为空。
```

---

## 5. AGGREGATE 模板

适用于用户明确要求统计、分组、计数、平均值、最大值、最小值、TopN 等聚合语义。

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：

1. schemaRef：ams_topology@1.0
2. 操作类型：AGGREGATE
3. 操作选择依据：用户要求按维度分组统计指标，例如按小区统计平均 PRB，属于聚合查询。
4. 查询对象：cell，别名 c，用于小区维度和 PRB 指标。
5. 关系路径：无关系路径，除非用户明确要求按关系路径聚合。
6. 过滤条件：按用户指定的小区、栅格、时间范围填写；时间条件必须进入过滤条件。
7. 返回字段：分组维度为 c.DIM_CELL；指标为 AVG(c.C_PRB)，别名 avgPrb。
8. 聚合要求：groupBy=c.DIM_CELL；metric=AVG(c.C_PRB) as avgPrb；如用户要求“大于80%”，则作为聚合后过滤 avgPrb > 80。
9. 排序/限制：如用户要求 TopN，则按指标倒序排序并限制 N；否则使用场景默认限制。
10. 时间要求：按用户指定时间处理；若用户未指定，按 SEC 默认时间窗口。
11. 扩展说明：这是 SEC 多维聚合查询，优先按 DAC 多维模型映射处理；不要直接生成 DAC 私有请求。
12. 结果处理：保留聚合维度、指标别名和原始字段语义；结果为空即为空。
```

---

## 6. 多步查询模板

多步查询不得把变量绑定协议传给平台。业务 Skill 应按如下方式处理：

```text
第一步：用自然语言委托平台执行查询，获取结果。
第二步：业务 Skill 读取第一步结果中的关键字段。
第三步：业务 Skill 将关键字段写入第二次自然语言委托的过滤条件中。
第四步：再次调用平台能力执行第二次查询。
```

示例：

```text
第一步查询 grid A 归属的小区 CELL_ID。
如果第一步返回 CELL_ID=B，则第二步委托平台查询 cell 对象，过滤条件为 c.CELL_ID 等于 B，返回 c.CELL_ID 和 c.C_PRB。
如果第一步返回多个 CELL_ID，则第二步使用 IN 条件；如果平台不支持 IN，则业务 Skill 拆成多次查询。
```
