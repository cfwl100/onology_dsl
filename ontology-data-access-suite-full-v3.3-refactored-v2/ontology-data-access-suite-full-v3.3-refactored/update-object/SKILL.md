---
name: update-object
description: 处理按条件修改已有对象的写入请求。仅在需要更新对象字段而不是创建、删除或批量处理时使用。
---
# 更新对象

## 本层职责
1. 只处理按条件更新已有对象。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测更新范围、目标字段或默认值。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
至少需要：
- `objects`
- `conditions`
- `mutation.scope`
- `mutation.set`

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- `objects`
- `conditions`
- `mutation.scope`
- `mutation.set`
- `options`
- `extensions`

## 不出现的模块
- `returns`
- `orders`
- `relationships`
- `linkQuery`
- `sourceQuery`

## 操作特有约束
- 只允许一个目标对象。
- 必须明确更新范围是一条还是多条。
- 更新内容必须非空。
- 禁止无条件全表更新。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
