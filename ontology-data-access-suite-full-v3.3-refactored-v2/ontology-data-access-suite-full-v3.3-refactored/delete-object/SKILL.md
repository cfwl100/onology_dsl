---
name: delete-object
description: 处理按条件删除已有对象的写入请求。仅在需要删除一个或一批既有对象时使用。
---
# 删除对象

## 本层职责
1. 只处理按条件删除已有对象。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测删除范围或默认条件。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
至少需要：
- `objects`
- `conditions`
- `mutation.scope`

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- `objects`
- `conditions`
- `mutation.scope`
- `options`
- `extensions`

## 不出现的模块
- `returns`
- `orders`
- `relationships`
- `linkQuery`
- `sourceQuery`
- `mutation.set`
- `mutation.data`

## 操作特有约束
- 只允许一个目标对象。
- 必须明确删除范围是一条还是多条。
- 禁止无条件删除。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
