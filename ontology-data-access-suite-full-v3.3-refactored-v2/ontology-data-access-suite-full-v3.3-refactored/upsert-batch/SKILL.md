---
name: upsert-batch
description: 处理存在则更新否则创建，或多个写步骤需要一起提交的请求。仅在需要复合写入语义时使用。
---
# 存在则更新 / 批量写入

## 本层职责
1. 处理存在则更新否则创建，或多个写步骤一起提交的场景。
2. 生成当前操作所需的结构化 JSON。
3. 信息不足时返回结构化错误，不猜测匹配键、批次顺序或写入内容。
4. 需要执行时，交给本目录脚本完成转换、组装与校验，再进入执行层。

## 输入契约
场景一：存在则更新
- `objects`
- `mutation.matchBy`
- `mutation.data`

场景二：批量写入
- `mutation.atomic`
- `mutation.items`

## 输出契约
- 只输出当前操作的结构化 JSON，或结构化错误 JSON。
- 不输出 Markdown 解释、注释或教学性散文。
- 不输出 `null`、空对象或空数组。

## 当前目录关心的结构
- 存在则更新：`objects`、`mutation.matchBy`、`mutation.data`
- 批量写入：`mutation.atomic`、`mutation.items`
- `options`
- `extensions`

## 不出现的模块
- 普通读取结果项、排序、路径关系块、一跳导航块

## 操作特有约束
- 存在则更新只允许一个目标对象。
- 匹配键必须全部出现在写入数据中。
- 批量写入的子项不能再次嵌套批量写入。
- 每个子项都必须独立完整、独立闭包。

## 参考与脚本
- 先读 `references/syntax-details.md`
- 再按需读 `references/operator-reference.md`、`references/examples.md`、`references/validation-rules.md`
- 转换脚本：`scripts/soql_to_oql.py`
- 组装脚本：`scripts/oql_builder.py`
- 校验脚本：`scripts/oql_validator.py`
