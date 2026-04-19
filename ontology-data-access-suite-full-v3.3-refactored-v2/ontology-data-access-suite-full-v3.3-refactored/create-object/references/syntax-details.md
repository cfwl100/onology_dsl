# 创建对象语法细节

## 适用范围
- `operation` 固定为 `CREATE`
- 适用于创建单个对象实例

## 必填字段
- `objects`
- `mutation`

## 可选字段
- `options`
- `extensions`

## 不出现的模块
- `conditions`
- `returns`
- `orders`
- `relationships`
- `linkQuery`
- `sourceQuery`

## objects
```json
[{"objectType":"Customer","alias":"c"}]
```
- 只允许一个对象。

## mutation
### 写入数据（简化写法）
```json
{
  "data": {
    "name": "Alice",
    "status": "active"
  }
}
```
- 转换后会归入 `data.properties`。
- `data` 必须是非空对象。
