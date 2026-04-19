# 路径读取语法细节

## 适用范围
- `operation` 固定为 `ASSOCIATION_QUERY`
- 适用于显式多跳路径、路径中对象与关系联合筛选、关系字段返回

## 必填字段
- `objects`
- `relationships`
- `returns`

## 可选字段
- `conditions`
- `orders`
- `maxResults`
- `sourceQuery`
- `options`
- `extensions`

## 不出现的模块
- `linkQuery`
- `mutation`

## objects
```json
[
  {"objectType":"Customer","alias":"c"},
  {"objectType":"Order","alias":"o"},
  {"objectType":"Product","alias":"p"}
]
```

## relationships
```json
[
  {"relationshipType":"PLACED","alias":"r1","from":"c","to":"o"},
  {"relationshipType":"CONTAINS","alias":"r2","from":"o","to":"p"}
]
```
- `from` / `to` 必须引用已声明对象别名。
- 顺序即遍历顺序。

## conditions
条件写法与普通对象读取一致，但左侧可以引用对象别名或关系别名，例如：
```json
{"all":[["c.level","EQ","vip"],["r2.quantity","GT",1]]}
```

## returns
允许字段投影与派生列，返回项可以指向对象别名或关系别名。
```json
["FIELDS", "p", ["id", "name"]]
```
```json
["FIELDS", "r2", ["quantity"]]
```
```json
["EXPR", {"$fn":"UPPER","args":["p.name"]}, "productNameUpper"]
```

## 排序写法
```json
["ORDER_BY", "<ref>", "<field>", "ASC|DESC"]
```
- `<ref>` 必须引用当前请求中已经声明的对象别名，或当前操作允许排序的别名。
- `direction` 只允许 `ASC` 或 `DESC`。

## sourceQuery
与普通对象读取一致，只允许读取类子查询。
