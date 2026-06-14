# OAC 自然语言委托模板

本模板供 `scenario-skill/sec-multidim` 在调用平台本体数据访问能力时使用。模板是业务 Skill 内部写法，不要求平台 Skill 识别新增结构化协议。

## 1. 通用模板

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：<本体 schema>
- 操作类型：QUERY / ASSOCIATION_QUERY / AGGREGATE
- 查询对象：<对象类型、别名、用途>
- 关系路径：<仅关系查询需要；关系名和方向必须明确>
- 过滤条件：<字段、操作符、值；说明条件属于哪个对象>
- 返回字段：<对象、字段、指标、维度函数；禁止默认返回 *>
- 时间要求：<时间范围、本地时间/UTC、采样字段或分表时间字段>
- 扩展要求：<SEC 场景标识、DAC 后端倾向、维度升维、关系解析、ID/NAME 维度函数>
- 返回要求：保留 OAC 原始字段；查询成功但结果为空时直接返回空，不重复查询。
```

## 2. QUERY 示例

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：QUERY
- 查询对象：grid，别名 g；cell，别名 c
- 过滤条件：g.DIM_GRID 等于 A；c.DIM_CELL 等于 B
- 返回字段：g.DIM_GRID、c.DIM_CELL、c.C_RSRP
- 扩展要求：这是 SEC 组合维度查询，优先按 DAC 多维模型映射执行；如果生成 OQL 支持 extensions，请表达 SEC 场景标识 COMPOSITE_DIMENSION 和 targetBackend=DAC
- 返回要求：保留原始字段，结果为空即为空
```

## 3. ASSOCIATION_QUERY 示例

```text
请调用本体平台的数据访问能力，按如下要求生成并执行 OQL：
- schemaRef：ams_topology@1.0
- 操作类型：ASSOCIATION_QUERY
- 查询对象：grid，别名 g；cell，别名 c
- 关系路径：g 通过 locateIn 关系到 c
- 过滤条件：g.GRID_ID 等于 A
- 返回字段：c.CELL_ID
- 扩展要求：这是 SEC 关系主键发现步骤；如果生成 OQL 支持 extensions，请表达 relationResolve=GRID_TO_CELL
- 返回要求：保留返回的 CELL_ID；如果为空，后续查询直接为空
```

## 4. 多步查询模板

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
