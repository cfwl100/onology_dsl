# AGGREGATE - 聚合查询

## 何时使用

`AGGREGATE` 用于面向对象集合的统计、分组、指标计算和聚合后过滤。

适用场景：

- 统计数量、求和、平均、最大、最小。
- 按字段或时间桶分组统计。
- 对聚合指标做二次过滤。

不适用场景：

- 返回对象明细 → 使用 `QUERY`。
- 沿关系路径查询明细 → 使用 `ASSOCIATION_QUERY`。

## 必读资产

- Schema：`schemas/oql-aggregate.schema.json`
- Validator：`scripts/validate_oql.py`

本文件已包含 AGGREGATE 所需公共规则和最小示例，不再读取 `oql-common-rules.md` 或独立 examples 目录。

## 结构边界

结构契约以 schema 为准。本手册只补充 Agent 生成时必须理解的语义规则。

- `version` 使用本体 Skill 初始版本 `1.0`，并以 schema 为准。
- `operation` 固定为 `AGGREGATE`。
- 必须声明 `objects` 和 `returns`。
- `returns` 至少包含一个 `METRIC`，可包含 `GROUP_BY`。
- 不使用 `relationships`、`mutation` 或非聚合返回项。
- `maxResults` 使用数字格式，例如 `1000`，不使用 `{"limit":1000,"offset":0}`。
- 用户或上层计划已提供 `schemaRef` 时必须原样保留，不得编造。

## returns 规则

`returns` 的结构、可选类型和字段语法以 `schemas/oql-aggregate.schema.json` 为准。本手册只强调业务生成原则：

- 至少一个 `METRIC`。
- `COUNT` 可以统计全部记录。
- `SUM`、`AVG`、`MIN`、`MAX` 必须绑定可聚合字段。
- 分组需求写入 `GROUP_BY`。
- 明细字段返回不属于聚合查询；需要明细时使用 `QUERY` 或 `ASSOCIATION_QUERY`。

## aggregateFilter 规则

`aggregateFilter` 用于聚合后过滤，语义类似 HAVING。

- `metricAlias` 必须引用 `returns` 中 `METRIC.alias`。
- 可使用 `METRIC_PREDICATE` 或 `GROUP`。
- 不得引用未声明指标。

## conditions 规则

`conditions` 是聚合前的明细级过滤。

- `ref` 必须引用 `objects[].alias`。
- 条件字段必须属于对应对象。
- 条件值必须来自用户输入、上一步明确结果或已确认上下文，不得虚构。

## 生成步骤

1. 判断用户是否要求统计或分组。
2. 声明聚合对象。
3. 将明细级过滤写入 `conditions`。
4. 将分组写入 `GROUP_BY`。
5. 将统计指标写入 `METRIC`。
6. 将聚合后过滤写入 `aggregateFilter`。
7. 生成 OQL JSON。复杂 OQL、长数组或 Windows 原生命令环境下，优先通过程序化 JSON 序列化写入 UTF-8 文件。
8. 调用 `validate_oql.py` 校验。复杂 OQL 优先使用 `--input <json文件>`；短小 JSON 且确认 Shell 引号安全时，才可使用 `--oac-json`。

## 校验与修复

校验失败时根据错误修复 OQL。常见错误：

- 没有 `METRIC`。
- 使用了非聚合返回项。
- `aggregateFilter.metricAlias` 未引用已声明指标。
- 聚合函数绑定字段不合法。
- 把明细查询误写成聚合。
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
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "cell_kpi",
      "alias": "k"
    }
  ],
  "returns": [
    {
      "kind": "METRIC",
      "function": "COUNT",
      "ref": "k",
      "field": "id",
      "alias": "cnt"
    }
  ],
  "maxResults": 1000
}
```
