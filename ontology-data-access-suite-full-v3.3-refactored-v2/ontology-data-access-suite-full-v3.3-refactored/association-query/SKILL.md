---
name: association-query
description: 处理需要显式关系路径或多跳遍历的对象读取请求。仅在用户明确给出路径语义、节点约束或边约束时使用。
---
# 路径读取

## 本层职责
1. 只处理显式关系路径、多跳遍历、起点终点与中间节点联合约束。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测路径、方向、对象或关系类型。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
至少需要：
- `objects`
- `relationships`
- `returns`

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- `objects`
- `relationships`
- `conditions`
- `returns`
- `orders`
- `maxResults`
- `sourceQuery`

## 不出现的模块
- `linkQuery`
- `mutation`

## 操作特有约束
- 关系路径必须按遍历顺序声明。
- 条件与返回项既可以指向对象别名，也可以指向关系别名。
- 不把显式多跳路径降级为一跳导航。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
