# ASSOCIATION_QUERY - 关联路径查询

## 何时使用

`ASSOCIATION_QUERY` 用于显式关系路径查询，包括一跳、多跳、归属、连接和路径遍历。只要用户问题需要沿对象关系查询，即使只有一跳，也应使用本操作。

适用场景：

- 查询 A 与 B 的关系或路径。
- 查询某对象归属、连接、经过、包含、承载的对象。
- 对路径起点、终点或中间节点做联合筛选。
- 需要返回路径上的对象和关系字段。

不适用场景：

- 只查询对象自身字段 → 使用 `QUERY`。
- 统计、分组、聚合指标 → 使用 `AGGREGATE`。

## 必读资产

- Schema：`schemas/oql-association-query.schema.json`
- Validator：`scripts/validate_oql.py`

本文件已包含 ASSOCIATION_QUERY 所需公共规则和最小示例，不再读取 `oql-common-rules.md` 或独立 examples 目录。

## 结构边界

结构契约以 schema 为准。本手册只补充 Agent 生成时必须理解的语义规则。

- `version` 使用本体 Skill 初始版本 `1.0`，并以 schema 为准。
- `operation` 固定为 `ASSOCIATION_QUERY`。
- 必须声明 `objects`、`relationships` 和 `returns`。
- 不使用 `aggregateFilter`、`mutation`。
- `maxResults` 使用数字格式，例如 `1000`，不使用 `{"limit":1000,"offset":0}`。
- 用户或上层计划已提供 `schemaRef` 时必须原样保留，不得编造。

## relationships 规则

- 每条关系必须包含 `relationshipType`、`alias`、`from`、`to`。
- `from` 和 `to` 必须引用 `objects[].alias`。
- 多跳路径中，前一跳的 `to` 应与后一跳的 `from` 连续。
- 关系名必须来自已检索或已确认的本体关系，不得臆造。

## returns 规则

`returns` 的结构、可选类型和字段语法以 `schemas/oql-association-query.schema.json` 为准。本手册只强调业务生成原则：

- 返回项的 `ref` 可以引用对象 alias，也可以引用关系 alias。
- 关联查询应返回必要的路径关系。
- 若业务需要完整路径，`returns` 中应包含每个 `relationships[].alias` 的返回项。
- 不要把聚合指标写入关联查询 `returns`。

## conditions 规则

- `ref` 可以引用对象 alias，也可以引用关系 alias。
- 条件字段必须属于对应对象或关系。
- 不要把路径关系字段写到对象条件上。
- 条件值必须来自用户输入、上一步明确结果或已确认上下文，不得虚构。

## 生成步骤

1. 判断用户是否需要关系路径。
2. 按照输入模板中的`查询对象`声明路径上的 `objects`。
3. 按照输入模板中的`关系路径`按路径顺序声明 `relationships`。
4. 按照输入模板中的`过滤条件`生成对象或关系上的 `conditions`。
5. 按照输入模板中的`返回要求`、`期望输出`生成对象或关系返回项。
6. 生成 OQL JSON。复杂 OQL、长数组或 Windows 原生命令环境下，优先通过程序化 JSON 序列化写入 UTF-8 文件。
7. 调用 `validate_oql.py` 校验。复杂 OQL 优先使用 `--input <json文件>`；短小 JSON 且确认 Shell 引号安全时，才可使用 `--oac-json`。

## 校验与修复

校验失败时根据错误修复 OQL。常见错误：

- `relationships.from/to` 未引用对象 alias。
- 多跳路径被拆成多个单跳查询。
- 遗漏业务要求返回的关系路径。
- 把聚合需求误写为关联查询。
- `returns` 结构不符合 schema。
- `maxResults` 使用旧对象格式。
- `version` 未使用 schema 声明的初始版本。
- 手写 JSON 文件缺少逗号、括号不闭合或存在隐藏字符。
- 将长 JSON 通过 Shell 变量传给 `--oac-json` 后发生引号丢失。

## Shell 兼容校验命令

校验命令必须遵循 `oac-data-access.md` 中的“跨平台 Shell 兼容规则”和“复杂 JSON 优先文件输入”规则。

- Windows PowerShell、PowerShell 7+、Windows CMD、Bash/zsh、Linux、macOS、WSL、Git Bash 的命令连接符和路径写法不同。
- 不确定当前终端时，只输出逐行命令，不输出 Shell 专属连接符、管道或专属变量。
- 本文件不重复维护各 Shell 的完整示例，避免不同文档之间出现不一致。

## 最小示例

```json
{
  "version": "1.0",
  "schemaRef": "demo@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    { "objectType": "cell", "alias": "c" },
    { "objectType": "grid", "alias": "g" }
  ],
  "relationships": [
    { "relationshipType": "belongs_to", "alias": "r1", "from": "c", "to": "g" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "c",
    "field": "cell_id",
    "operator": "EQ",
    "values": ["CELL_A"]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "c", "fields": ["cell_id"] },
    { "kind": "FIELDS", "ref": "g", "fields": ["grid_id"] },
    { "kind": "FIELDS", "ref": "r1", "fields": ["*"] }
  ],
  "maxResults": 1000
}
```
