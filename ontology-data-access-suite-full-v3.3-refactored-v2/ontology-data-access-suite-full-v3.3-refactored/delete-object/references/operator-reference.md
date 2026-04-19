# 删除对象操作符参考

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

## mutation 字段
- `scope`：`ONE` / `MANY`

## 删除要求
- 删除必须有明确条件。
- `scope=ONE` 只在明确唯一命中时使用。
