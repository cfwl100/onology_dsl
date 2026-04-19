---
name: link-query
description: 处理通过单一关系类型从源对象获取关联对象的一跳读取请求。仅在关系是单跳导航且无需显式多跳路径时使用。
---
# 一跳关联读取

## 本层职责
1. 只处理从源对象出发，通过单一关系类型获取目标对象的一跳导航。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测关系类型、方向、唯一性或源对象筛选条件。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
至少需要：
- 两个对象别名（源对象、目标对象）
- `linkQuery`
- `returns`

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- `objects`
- `conditions`
- `returns`
- `orders`
- `maxResults`
- `linkQuery`
- `sourceQuery`

## 不出现的模块
- `relationships`
- `mutation`

## 操作特有约束
- `objects` 恰好两个：源对象和目标对象。
- `linkQuery` 只描述一跳关系导航。
- `mode` 为 `ONE` 时，必须具备明确的一条结果语义。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
