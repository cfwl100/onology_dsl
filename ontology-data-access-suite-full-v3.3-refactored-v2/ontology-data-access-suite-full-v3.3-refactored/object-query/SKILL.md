---
name: object-query
description: 处理不涉及统计聚合、不涉及显式多跳路径、也不属于一跳关系导航的普通对象读取请求。仅在需要生成普通对象读取的结构化请求时使用。
---
# 普通对象读取

## 本层职责
1. 只处理单类或并列多类对象的普通读取。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测 schema、对象、字段或关系。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
至少需要：
- `objects`
- `returns`

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- `objects`
- `conditions`
- `returns`：仅允许字段投影与派生列表达式
- `orders`
- `maxResults`
- `sourceQuery`

## 不出现的模块
- `relationships`
- `linkQuery`
- `mutation`

## 操作特有约束
- 至少返回一个结果项。
- 不引入显式关系路径。
- 不引入聚合分组指标。
- 允许在条件和派生列中使用内置函数。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
