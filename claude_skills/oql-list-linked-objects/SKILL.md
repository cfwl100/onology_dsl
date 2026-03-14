---
name: oql_list_linked_objects
description: "Generate strict OQL DSL JSON for operation LIST_LINKED_OBJECTS. Use when user intent maps to LIST_LINKED_OBJECTS and needs machine-consumable ontology object operation payload with minimal ambiguity."
---

# OQL LIST_LINKED_OBJECTS Skill

按以下流程生成 OQL DSL：

1. 先输出且仅输出一个 JSON 对象，不要输出 Markdown、注释、解释文本。
2. 固定包含顶层字段：`version`、`operation`，并按需补充 `objects`、`relationships`、`conditions`、`returns`、`orders`、`maxResults`、`query`、`aggregations`、`associationQuery`、`linkQuery`、`mutation`、`sourceQuery`、`options`、`extensions`。
3. `version` 固定为 `"1.8.0"`。
4. `operation` 固定为 `"LIST_LINKED_OBJECTS"`。
5. `objects[].objectType` 必填；跨块引用必须通过 `alias` 与 `returns[].param/orders[].param` 对齐。
6. 条件叶子统一结构：`objectType + property + operator + values`。
7. 对于未使用的操作专用块，不要输出或输出空对象（优先不输出）。
8. 字段名与枚举值严格区分大小写。

## Operation-Specific Rules

- 必须提供源对象定位（`objects[].by|byList|byComposite` 之一）。
- 在 `linkQuery` 中声明 `relationship` 与 `targetObjectType`。
- 语义是“返回列表”。

## Output Contract

- 输出必须是合法 JSON（UTF-8，无尾随逗号）。
- 不得发明未定义字段；如确需扩展，请放入 `extensions`。
- 若输入信息不足，优先在 `conditions` / `mutation` 中保留最小安全结构，不得猜测业务主键。

## Minimal Example

```json
{
  "version": "1.8.0",
  "operation": "LIST_LINKED_OBJECTS",
  "objects": [{"objectType": "Order", "alias": "o", "by": {"id": "order_001"}}],
  "linkQuery": {"relationship": "belongsTo", "targetObjectType": "Product"},
  "returns": [{"type": "object", "param": "target", "fields": ["id", "name"]}]
}
```
