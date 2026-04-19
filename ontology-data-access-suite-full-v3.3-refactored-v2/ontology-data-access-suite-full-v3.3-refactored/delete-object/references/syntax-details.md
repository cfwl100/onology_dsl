# 删除对象语法细节

## 适用范围
- `operation` 固定为 `DELETE`
- 适用于按条件删除已有对象

## 必填字段
- `objects`
- `conditions`
- `mutation`

## 可选字段
- `options`
- `extensions`

## 不出现的模块
- `returns`
- `orders`
- `relationships`
- `linkQuery`
- `sourceQuery`
- `mutation.set`
- `mutation.data`

## conditions
条件写法与读取类操作一致，可使用字段谓词、逻辑组与函数表达式。

## mutation
```json
{
  "scope": "MANY"
}
```
- `scope` 只允许 `ONE` 或 `MANY`
- 不允许出现 `set` 或 `data`
