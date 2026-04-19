# 一跳关联读取语法细节

## 适用范围
- `operation` 固定为 `LINK_QUERY`
- 适用于从源对象到目标对象的一跳关系导航

## 必填字段
- `objects`
- `returns`
- `linkQuery`

## 可选字段
- `conditions`
- `orders`
- `maxResults`
- `sourceQuery`
- `options`
- `extensions`

## 不出现的模块
- `relationships`
- `mutation`

## objects
```json
[
  {"objectType":"Customer","alias":"c"},
  {"objectType":"Order","alias":"o"}
]
```
- 第一个别名通常承载源对象，第二个别名通常承载目标对象。

## conditions
常用于约束源对象，例如：
```json
["c.id", "EQ", "cust-001"]
```

## linkQuery
```json
{
  "mode": "LIST",
  "relationshipType": "PLACED",
  "sourceRef": "c",
  "targetRef": "o",
  "direction": "OUTBOUND"
}
```
- `mode`：`LIST` 或 `ONE`
- `sourceRef` / `targetRef` 必须引用 `objects` 中的别名
- `direction` 只允许 `OUTBOUND` `INBOUND` `BIDIRECTIONAL`

## returns
允许返回目标对象字段，也允许返回派生列。
```json
["FIELDS", "o", ["id", "amount", "status"]]
```
```json
["EXPR", {"$fn":"ABS","args":["o.amount"]}, "amountAbs"]
```

## 排序写法
```json
["ORDER_BY", "<ref>", "<field>", "ASC|DESC"]
```
- `<ref>` 必须引用当前请求中已经声明的对象别名，或当前操作允许排序的别名。
- `direction` 只允许 `ASC` 或 `DESC`。

## sourceQuery
与普通对象读取一致，只允许读取类子查询。
