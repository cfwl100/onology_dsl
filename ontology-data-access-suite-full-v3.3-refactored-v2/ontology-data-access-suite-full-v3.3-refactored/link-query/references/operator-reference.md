# 一跳关联读取操作符参考

## 条件操作符
- 单值比较：`EQ` `NE` `GT` `GTE` `LT` `LTE`
- 多值比较：`IN` `NOT_IN` `BETWEEN`
- 文本匹配：`LIKE` `CONTAINS` `STARTS_WITH` `ENDS_WITH`
- 空值判断：`IS_NULL` `IS_NOT_NULL`

## 常见内置函数
以下函数可用于当前目录允许表达式出现的位置：
- 数值：`ABS(x)` `ROUND(x, n)` `CEIL(x)` `FLOOR(x)`
- 字符串：`LENGTH(x)` `LOWER(x)` `UPPER(x)` `TRIM(x)` `SUBSTRING(x, start, len)`
- 时间：`NOW()` `DATE(x)` `DATE_TRUNC(unit, x)` `YEAR(x)` `MONTH(x)` `DAY(x)`
- 空值处理：`COALESCE(a, b, ...)`
- 允许嵌套调用，但参数个数与顺序必须正确。

## 排序写法
```json
["ORDER_BY", "<ref>", "<field>", "ASC|DESC"]
```
- `<ref>` 必须引用当前请求中已经声明的对象别名，或当前操作允许排序的别名。
- `direction` 只允许 `ASC` 或 `DESC`。

## linkQuery 字段
- `mode`：`LIST` / `ONE`
- `relationshipType`：关系类型
- `sourceRef`：源对象别名
- `targetRef`：目标对象别名
- `direction`：方向，可省略

## 返回项写法
- 字段投影：`["FIELDS", "<ref>", ["field1", "field2"]]`
- 派生列：`["EXPR", <表达式>, "<alias>"]`
