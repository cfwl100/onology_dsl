---
name: aggregate-query
description: 处理以统计、分组、计数、求和、平均值、最值或排行为核心的读取请求。仅在结果以分组键或聚合指标为中心时使用。
---
# 聚合读取

## 本层职责
1. 只处理统计、分组、排行类读取。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测聚合口径、字段或对象。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
至少需要：
- `objects`
- `returns`（且至少包含一个聚合指标）

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- `objects`
- `conditions`
- `returns`：仅允许分组项与聚合指标
- `orders`
- `maxResults`
- `sourceQuery`

## 不出现的模块
- `relationships`
- `linkQuery`
- `mutation`

## 操作特有约束
- 至少包含一个聚合指标。
- 分组项可以是字段，也可以是函数表达式。
- 不返回普通字段投影或写入内容。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
