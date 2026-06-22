# 本体数据访问（OAC）

## 角色定位

OAC 是本体平台的数据访问总控入口，负责把数据访问请求路由到唯一的 OQL 操作手册，并组织 schema、validator、executor 的闭环。

本文件只负责总控流程和路由，不展开具体 operation 的字段级细节。公共规则已内聚到各 operation 手册中，避免额外文件读取。

## 操作类型

| 操作类型 | 适用场景 | 子文档 |
|---|---|---|
| `QUERY` | 单对象或多个独立对象明细查询，不沿关系路径遍历 | `oac-query.md` |
| `ASSOCIATION_QUERY` | 一跳、多跳、归属、连接、路径遍历 | `oac-association-query.md` |
| `AGGREGATE` | 统计、分组、计数、求和、平均、最大、最小、聚合后过滤 | `oac-aggregate.md` |

## 总控流程

1. 判断唯一 OAC 操作类型。
2. 读取对应 operation 手册。
3. 读取对应 schema。operation 手册内已包含最小示例，不再读取独立 examples 目录。
4. 生成 OQL JSON。
5. 使用 `scripts/validate_oql.py` 校验。
6. 校验失败时修复，不得执行。
7. 用户明确要求执行时，调用 `scripts/execute_oac_operation.py`。

## Schema 权威规则

OQL 顶层结构、`version`、`returns` 类型、字段语法、`maxResults` 格式等以对应 schema 为准。

当前本体 Skill 的 OQL 初始版本统一为 `version: "1.0"`。生成 OQL 时必须使用 schema 中声明的版本，不得从历史样例沿用其他版本号。

## 自然语言委托模板

上层业务 Skill 可按以下信息委托 OAC：

| 字段 | 是否必填 | 说明 |
|---|:--:|---|
| schemaRef | 是 | 本体 schema 标识。用户或计划已给出时必须原样保留。 |
| 操作类型 | 是 | 中文描述即可，例如明细查询、路径查询、统计聚合。 |
| 查询对象 | 是 | 对象类型、别名、业务含义。 |
| 关系路径 | 条件必填 | 仅 `ASSOCIATION_QUERY` 必填。 |
| 过滤条件 | 否 | 字段归属对象、字段名、操作符、取值。 |
| 返回字段 | 是 | 返回哪个 alias 的哪些字段；具体结构以对应 schema 为准。 |
| 聚合要求 | 条件必填 | 仅 `AGGREGATE` 必填。 |
| 排序/限制 | 否 | 排序字段、方向、`maxResults` 数字值。 |
| 扩展说明 | 否 | 只填写已约定扩展字段。 |

## 路由判断

- 只查对象属性、明细、列表、字段值 → `QUERY`。
- 明确提到关系、路径、遍历、归属、连接、一跳、多跳 → `ASSOCIATION_QUERY`。
- 明确提到统计、聚合、分组、计数、求和、平均、最大、最小 → `AGGREGATE`。

## 校验与执行

| 脚本 | 作用 |
|---|---|
| `scripts/validate_oql.py` | 对 OQL JSON 做结构和语义校验。 |
| `scripts/execute_oac_operation.py` | 在用户明确要求执行时调用 OAC 服务。 |

执行前必须先完成 `validate_oql.py` 校验。校验失败时只修复 OQL，不直接执行。