# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：最小创建
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "mutation": {
    "data": {
      "name": "Alice"
    }
  }
}
```

## 示例 2：多字段创建
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "mutation": {
    "data": {
      "name": "Alice",
      "email": "alice@example.com",
      "status": "active"
    }
  }
}
```

## 示例 3：创建订单
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "mutation": {
    "data": {
      "customerId": "cust-001",
      "amount": 299.5,
      "status": "pending"
    }
  }
}
```

## 示例 4：带 options 的创建
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "mutation": {
    "data": {
      "name": "Bob"
    }
  },
  "options": {
    "dryRun": true
  }
}
```

## 示例 5：带 extensions 的创建
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "mutation": {
    "data": {
      "name": "Carol"
    }
  },
  "extensions": {
    "traceId": "trace-create-001"
  }
}
```
