# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：单条更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": [
    "c.id",
    "EQ",
    "cust-001"
  ],
  "mutation": {
    "scope": "ONE",
    "set": {
      "status": "inactive"
    }
  }
}
```

## 示例 2：批量更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "o.status",
    "EQ",
    "pending"
  ],
  "mutation": {
    "scope": "MANY",
    "set": {
      "status": "expired"
    }
  }
}
```

## 示例 3：函数条件更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": [
    {
      "$fn": "LENGTH",
      "args": [
        "c.name"
      ]
    },
    "GT",
    20
  ],
  "mutation": {
    "scope": "MANY",
    "set": {
      "tag": "long-name"
    }
  }
}
```

## 示例 4：逻辑组更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": {
    "all": [
      [
        "c.status",
        "EQ",
        "active"
      ],
      [
        "c.level",
        "EQ",
        "silver"
      ]
    ]
  },
  "mutation": {
    "scope": "MANY",
    "set": {
      "level": "gold"
    }
  }
}
```

## 示例 5：带 extensions 的更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "o.id",
    "EQ",
    "ord-001"
  ],
  "mutation": {
    "scope": "ONE",
    "set": {
      "status": "paid"
    }
  },
  "extensions": {
    "traceId": "trace-update-001"
  }
}
```
