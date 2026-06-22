# 本体数据访问（OAC）

## 角色定位

OAC 是本体平台的数据访问总控入口，负责把自然语言数据访问需求路由到唯一的 OQL 操作手册，并组织 schema、validator、executor 的闭环。

OAC 只负责“生成、校验、必要时执行 OQL”。它不负责本体子图检索，不负责业务意图识别，不负责函数调用。

## 操作类型

| 操作类型 | 适用场景 | 子文档 |
|---|---|---|
| `QUERY` | 单对象或多个独立对象明细查询，不沿关系路径遍历 | `oac-query.md` |
| `ASSOCIATION_QUERY` | 一跳、多跳、归属、连接、路径遍历 | `oac-association-query.md` |
| `AGGREGATE` | 统计、分组、计数、求和、平均、最大、最小、聚合后过滤 | `oac-aggregate.md` |

## 面向自然语言的输入模板

上层业务 Skill 或 Planning 层可以用自然语言委托 OAC，不需要直接拼装 OQL JSON。推荐模板如下：

```text
请执行本体数据访问。

schemaRef：<schemaRef>
用户原始问题：<用户输入原文>
业务场景：<可选，例如 alarm-propagation / berth-plan-ontology>
查询目标：<自然语言描述要查什么数据>
本体子图依据：<来自 OAG 的对象、字段、关系、函数候选摘要；字段和关系必须来自子图>
候选操作类型：<明细查询 / 关系路径查询 / 聚合统计；不确定时说明判断依据>
查询对象：<对象类型、别名建议、业务含义>
关系路径：<仅关系查询需要，说明 from / relation / to / 方向 / 步数>
过滤条件：<字段、操作符、取值，字段归属对象必须清楚>
返回要求：<返回字段、聚合指标、排序、maxResults>
执行要求：<只生成 OQL / 校验 OQL / 用户确认后执行>
```

最小输入应包含：

```text
schemaRef：<schemaRef>
查询目标：<要查询的数据>
本体子图依据：<至少包含对象和字段归属；关系查询还要包含关系名>
返回要求：<需要返回什么>
```

## 输出格式

OAC 输出必须把“生成结果、校验结果、执行结果”分开，避免把未执行的 OQL 说成数据结果。推荐输出结构：

```text
## OAC 输出

### 1. 操作类型判断
- operation：QUERY / ASSOCIATION_QUERY / AGGREGATE
- 判断依据：...

### 2. OQL JSON
```json
{
  "version": "1.0",
  "schemaRef": "...",
  "operation": "..."
}
```

### 3. 校验结果
- 是否通过 validate_oql.py：是/否
- 失败原因：...
- 修复动作：...

### 4. 执行状态
- 是否执行：未执行 / 已执行
- 执行前提：用户已明确要求执行
- 执行脚本：scripts/execute_oac_operation.py

### 5. 执行结果或缺失项
- 数据结果：...
- 缺失字段/关系/schemaRef：...
- 风险说明：...
```

## 总控流程

1. 根据自然语言数据访问需求判断唯一 OAC 操作类型。
2. 读取对应 operation 手册。
3. 读取对应 schema。operation 手册内已包含最小示例，不再读取独立 examples 目录。
4. 基于用户问题、业务规则和 OAG 子图依据生成 OQL JSON。
5. 使用 `scripts/validate_oql.py` 校验。
6. 校验失败时修复，不得执行。
7. 用户明确要求执行时，调用 `scripts/execute_oac_operation.py`。

## Schema 权威规则

OQL 顶层结构、`version`、`returns` 类型、字段语法、`maxResults` 格式等以对应 schema 为准。

当前本体 Skill 的 OQL 初始版本统一为 `version: "1.0"`。生成 OQL 时必须使用 schema 中声明的版本，不得从历史样例沿用其他版本号。

## 路由判断

- 只查对象属性、明细、列表、字段值 → `QUERY`。
- 明确提到关系、路径、遍历、归属、连接、一跳、多跳 → `ASSOCIATION_QUERY`。
- 明确提到统计、聚合、分组、计数、求和、平均、最大、最小 → `AGGREGATE`。

## 输入边界

- `schemaRef` 是本体访问必需输入。
- 字段必须来自 OAG 子图确认的对象属性，或来自上层业务 Skill 的明确字段映射。
- 关系必须来自 OAG 子图确认的关系定义。
- 自然语言中的单位、同义词、业务别名可以由业务 Skill 说明，但最终 OQL 字段名必须是平台字段。

## 校验与执行

| 脚本 | 作用 |
|---|---|
| `scripts/validate_oql.py` | 对 OQL JSON 做结构和语义校验。 |
| `scripts/execute_oac_operation.py` | 在用户明确要求执行时调用 OAC 服务。 |

执行前必须先完成 `validate_oql.py` 校验。校验失败时只修复 OQL，不直接执行。
