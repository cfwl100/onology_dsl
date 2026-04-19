# 聚合读取语法细节

## 适用范围
- `operation` 固定为 `AGGREGATE`
- 适用于统计、分组、排行、聚合指标输出

## 必填字段
- `objects`
- `returns`

## 可选字段
- `conditions`
- `orders`
- `maxResults`
- `sourceQuery`
- `options`
- `extensions`

## 不出现的模块
- `relationships`
- `linkQuery`
- `mutation`

## conditions
条件写法与普通对象读取一致，可使用字段谓词、逻辑组与函数表达式。

## returns
仅允许以下两类结果项，且至少出现一个聚合指标。

### 分组项（字段）
```json
["GROUP_BY", "o.status", "status"]
```

### 分组项（表达式）
```json
["GROUP_BY", {"$fn":"DATE_TRUNC","args":["DAY", "o.createdAt"]}, "dayBucket"]
```

### 聚合指标
```json
["METRIC", "SUM", "o.amount", "totalAmount"]
```
- `function` 只允许 `COUNT` `SUM` `AVG` `MIN` `MAX`
- `alias` 必填，供下游使用

## 排序写法
```json
["ORDER_BY", "<ref>", "<field>", "ASC|DESC"]
```
- `<ref>` 必须引用当前请求中已经声明的对象别名，或当前操作允许排序的别名。
- `direction` 只允许 `ASC` 或 `DESC`。

## sourceQuery
与普通对象读取一致，只允许读取类子查询。
