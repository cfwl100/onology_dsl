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

本文件已包含 ASSOCIATION_QUERY 所需公共规则和最小示例，如有需要可读`schemas/oql-association-query.schema.json`获取详细规则。

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
6. 生成 OQL JSON。
7. 调用 `scripts/execute_oac_operation.py --oac-json '<compact-json>' --message-type '<type>'`，脚本内部自动完成 OQL 校验。

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

###  ASSOCIATION_QUERY完整结构定义模版样例

```json
{
  "version": "1.0",
  "schemaRef": "<本体ID>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "maxResults": 1000,
  "objects": [
    { "objectType": "<对象类型>", "alias": "<对象类型别名，默认和对象名保持一致，如果一条路径有多个同名对象，则添加数字后缀，如对象为ne，别名默认是ne，如果有两个ne, 则取ne1, ne2>" },
	"..."
  ],
  "relationships": [
    {
      "relationshipType": "<逻辑关系类型>",
      "alias": "<逻辑关系类型别名, 默认从r1开始，多个则r1, r2, r3>",
      "from": "<该关系开始object,必须在objects中存在>",
      "to": "<该关系目标object,必须在objects中存在>"
    },
	"..."
  ],
  "conditions": {
    "kind": "<`GROUP`或`PREDICATE`>", 
    "children": [
      {
        "kind": "<`GROUP`或`PREDICATE`>",
        "ref": "<必须来自于objects或者relationships中的alias>",
        "field": "<条件字段名>",
        "operator": "<操作符，详细见操作符定义表格>",
        "values": ["value1", "value2", "..."]
      },
      "..."
    ]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "src", "fields": ["*"] },
    "..."
  ]
}

```
### 操作符定义表格
| 操作符                                     | `values` 取值规则 | 说明                              |
|-----------------------------------------| ----------------- | --------------------------------- |
| `EQ` / `NE`                             | 恰好 1 个值       | 等于 / 不等于                     |
| `GT` / `GTE` / `LT` / `LTE`             | 恰好 1 个值       | 大于 / 大于等于 / 小于 / 小于等于 |
| `IN` / `NOT_IN`                         | 至少 1 个值       | 属于 / 不属于                     |
| `CONTAINS`                              | 恰好 1 个字符串值 | 字符串包含匹配                    |
| `BETWEEN`                               | 恰好 2 个值       | 范围（包含边界），如 `BETWEEN [10, 100]` |
| `STARTS_WITH`                           | 恰好 1 个字符串值 | 前缀匹配                          |
| `ENDS_WITH`                             | 恰好 1 个字符串值 | 后缀匹配                          |
| `IS_NULL`                               | 不允许            | 空值判断                          |
| `IS_NOT_NULL`                           | 不允许            | 非空判断                          |
| `IS_EMPTY`                              | 不允许            | 空字符串判断                      |
| `IS_NOT_EMPTY`                          | 不允许            | 非空字符串判断                    |

### `conditions` 统一条件表达式注意事项
1. `conditions` 统一表达查询筛选、更新目标与删除目标。
   其结构为递归逻辑树，而非自由拼装对象。
2. `conditions`中的`values`数组，必须结合上下文已知的真实数据进行显式赋值。

## 示例
### 示例1：设备到数据中心的多跳路径查询

```json
{
  "version": "1.0",
  "schemaRef": "dtmi.ontology.00000",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "device",
      "alias": "d"
    },
    {
      "objectType": "derver",
      "alias": "s"
    },
    {
      "objectType": "dataCenter",
      "alias": "dc"
    }
  ],
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s"
    },
    {
      "relationshipType": "deployed_in",
      "alias": "r2",
      "from": "s",
      "to": "dc"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "d",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      },
      {
        "kind": "PREDICATE",
        "ref": "dc",
        "field": "region",
        "operator": "EQ",
        "values": ["华东"]
      }
    ]
  },
  "returns": [
    { 
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["*"]
    },
    {
      "kind": "FIELDS",
      "ref": "r1",
      "fields": ["*"]
    }
  ],
  "maxResults": 100000
}
```