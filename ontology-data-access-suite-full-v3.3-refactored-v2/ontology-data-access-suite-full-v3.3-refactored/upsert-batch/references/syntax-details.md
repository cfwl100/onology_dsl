# 存在则更新 / 批量写入语法细节

## 适用范围
- `operation` 为 `UPSERT`：存在则更新，否则创建
- `operation` 为 `BATCH`：多个写步骤一起提交

## 场景一：存在则更新
### 必填字段
- `objects`
- `mutation.matchBy`
- `mutation.data`

### 不出现的模块
- `conditions`
- `returns`
- `orders`
- `relationships`
- `linkQuery`
- `sourceQuery`

### 写法
```json
{
  "operation": "UPSERT",
  "objects": [{"objectType":"Customer","alias":"c"}],
  "mutation": {
    "matchBy": ["email"],
    "data": {
      "email": "alice@example.com",
      "name": "Alice",
      "status": "active"
    }
  }
}
```

## 场景二：批量写入
### 必填字段
- `mutation.atomic`
- `mutation.items`

### 写法
```json
{
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "CREATE",
        "objects": [{"objectType":"Customer","alias":"c1"}],
        "mutation": {"data": {"name": "Alice"}}
      },
      {
        "operation": "UPDATE",
        "objects": [{"objectType":"Order","alias":"o1"}],
        "conditions": ["o1.id", "EQ", "ord-001"],
        "mutation": {"scope": "ONE", "set": {"status": "paid"}}
      }
    ]
  }
}
```
- `items` 只允许创建、更新、删除、存在则更新。
- 不允许再次嵌套批量写入。
