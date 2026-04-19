# 普通对象读取语法细节

## 适用范围
- `operation` 固定为 `QUERY`
- 适用于单类对象读取、条件筛选、字段投影、派生列返回、排序、限制条数、同层级子查询引入结果

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

## objects
```json
[{"objectType":"Customer","alias":"c"}]
```
- `alias` 在当前请求内唯一。
- 当对象来自同层 `sourceQuery` 输出时，可写 `fromSource`。

## conditions
### 简单谓词
```json
["c.status", "EQ", "active"]
```

### 空值判断
```json
["c.deletedAt", "IS_NULL"]
```

### 逻辑组
```json
{"all":[["c.status","EQ","active"],["c.level","IN",["gold","vip"]]]}
```

### 左侧函数表达式
```json
[{"$fn":"LENGTH","args":["c.name"]}, "GT", 3]
```

## returns
仅允许以下两类结果项。

### 字段投影
```json
["FIELDS", "c", ["id", "name", "status"]]
```

### 派生列
```json
["EXPR", {"$fn":"UPPER","args":["c.name"]}, "nameUpper"]
```

## 排序写法
```json
["ORDER_BY", "<ref>", "<field>", "ASC|DESC"]
```
- `<ref>` 必须引用当前请求中已经声明的对象别名，或当前操作允许排序的别名。
- `direction` 只允许 `ASC` 或 `DESC`。

## maxResults
```json
100
```
- 必须是正整数。

## sourceQuery
```json
[
  {
    "outputAs": "activeCustomerIds",
    "version": "1.0",
    "schemaRef": "crm",
    "strict": true,
    "operation": "QUERY",
    "objects": [{"objectType":"Customer","alias":"sc"}],
    "conditions": ["sc.status","EQ","active"],
    "returns": [["FIELDS","sc",["id"]]]
  }
]
```
- 只允许读取类子查询。
- 子查询深度受校验器限制。
- `objects[].fromSource` 只能引用同层 `outputAs`。
