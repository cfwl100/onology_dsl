# 本体数据访问（OAC）

## 1. 角色定位

OAC 是本体平台的数据访问总控入口，负责把自然语言数据访问需求路由到唯一的 OQL 操作手册，并组织 schema、validator、executor 的闭环。

OAC 只负责“生成、校验、必要时执行 OQL”。它不负责本体子图检索，不负责业务意图识别，不负责函数调用。

对上层自然语言模板只暴露公共 `本体ID`。平台内部生成 OQL 时，将该 `本体ID` 作为 OQL 的 `schemaRef` 来源。

## 2. 输入来源

OAC 输入由两类信息结合生成：

1. 本体子图依据：来自 OAG 的 `result.nodes`、`result.edges`、`result.functions` 等结构结果。
2. 业务定制知识：来自业务 Skill 注入文件，包括查询内容、查询类型、返回字段、过滤条件、排序分组、空结果策略等。

OAC 不接受未经过子图确认的字段和关系。业务知识只能提供查询意图和映射线索，最终对象、字段、关系必须以子图和 schema 为准。

## 3. 操作类型

| 操作类型 | 适用场景 | 子文档 |
|---|---|---|
| `QUERY` | 单对象或多个独立对象明细查询，不沿关系路径遍历 | `oac-query.md` |
| `ASSOCIATION_QUERY` | 一跳、多跳、归属、连接、路径遍历 | `oac-association-query.md` |
| `AGGREGATE` | 统计、分组、计数、求和、平均、最大、最小、聚合后过滤 | `oac-aggregate.md` |

## 4. 面向自然语言的固定输入模板

Planning 层委托 OAC 时必须使用以下模板：

```text
查数据
本体ID：<公共本体ID，平台侧作为 schemaRef 来源>
操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE / 模型查询，如可判断>
查询对象：<对象类型和别名建议，来自子图 objectType>
关系路径：<仅在关系查询时填写，关系名必须来自 defines_relation.properties.name>
过滤条件：<用户条件及其对应字段依据；单位换算和枚举值说明>
返回要求：<返回字段、排序、分组、maxResults、空结果策略>
执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。
期望输出：返回操作类型判断、OQL JSON、校验结果、执行状态、数据结果或缺失项。
```

最小输入应包含：

```text
本体ID：<公共本体ID>
操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE，如可判断>
查询对象：<来自子图 objectType>
本体子图依据：<至少包含对象和字段归属；关系查询还要包含关系名>
返回要求：<需要返回什么>
```

## 5. 输出格式

OAC 输出必须把“操作判断、生成结果、校验结果、执行结果”分开。

```text
## OAC 输出

### 1. 操作类型判断
- operation：QUERY / ASSOCIATION_QUERY / AGGREGATE
- 判断依据：来自用户意图、业务规则、子图结构和查询目标。

### 2. OQL JSON
- 输出符合 schema 的 OQL JSON。
- version 使用 schema 声明的当前版本。
- schemaRef 来自公共本体ID。

### 3. 校验结果
- 是否通过 validate_oql.py：是/否
- 字段归属校验：是/否
- 关系来源校验：是/否
- 失败原因：...
- 修复动作：...

### 4. 执行状态
- 是否执行：未执行 / 已执行
- 执行前提：用户已明确要求执行
- 执行脚本：scripts/execute_oac_operation.py

### 5. 执行结果或缺失项
- 数据结果：...
- 缺失字段/关系/本体ID：...
- 风险说明：...
```

## 6. 总控流程

1. 根据自然语言数据访问需求、业务知识和子图依据判断唯一 OAC 操作类型。
2. 读取对应 operation 手册。
3. 读取对应 schema。operation 手册内已包含最小示例，不再读取独立 examples 目录。
4. 基于业务意图、业务规则和 OAG 子图依据生成 OQL JSON。
5. 使用 `scripts/validate_oql.py` 校验。
6. 校验失败时修复，不得执行。
7. 用户明确要求执行时，调用 `scripts/execute_oac_operation.py`。

## 7. Schema 权威规则

OQL 顶层结构、`version`、`schemaRef`、`returns` 类型、字段语法、`maxResults` 格式等以对应 schema 为准。

当前本体 Skill 的 OQL 初始版本统一为 `version: "1.0"`。生成 OQL 时必须使用 schema 中声明的版本，不得从历史样例沿用其他版本号。

## 8. 路由判断

- 只查对象属性、明细、列表、字段值 → `QUERY`。
- 明确提到关系、路径、遍历、归属、连接、一跳、多跳 → `ASSOCIATION_QUERY`。
- 明确提到统计、聚合、分组、计数、求和、平均、最大、最小 → `AGGREGATE`。

## 9. 输入边界

- `本体ID` 是自然语言模板的必需输入，并作为生成 OQL 时的 `schemaRef` 来源。
- 查询对象必须来自 OAG 子图确认的 `objectType`。
- 字段必须来自 OAG 子图确认的 `property`，并通过 `has_property` 确认归属。
- 关系必须来自 OAG 子图确认的 `defines_relation.properties.name`。
- 自然语言中的单位、同义词、业务别名可以由业务 Skill 说明，但最终 OQL 字段名必须是平台字段。
- 业务定制知识中的查询类型和返回字段是生成依据，但不能越过 schema 和子图约束。

## 10. 校验与执行

| 脚本 | 作用 |
|---|---|
| `scripts/validate_oql.py` | 对 OQL JSON 做结构和语义校验。 |
| `scripts/execute_oac_operation.py` | 在用户明确要求执行时调用 OAC 服务。 |

执行前必须先完成 `validate_oql.py` 校验。校验失败时只修复 OQL，不直接执行。
