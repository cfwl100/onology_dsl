# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：单条删除
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "DELETE",
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
    "scope": "ONE"
  }
}
```

## 示例 2：批量删除
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "o.status",
    "EQ",
    "cancelled"
  ],
  "mutation": {
    "scope": "MANY"
  }
}
```

## 示例 3：函数条件删除
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "DELETE",
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
    "LT",
    1
  ],
  "mutation": {
    "scope": "MANY"
  }
}
```

## 示例 4：逻辑组删除
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "all": [
      [
        "o.status",
        "EQ",
        "draft"
      ],
      [
        "o.createdAt",
        "LT",
        "2025-01-01"
      ]
    ]
  },
  "mutation": {
    "scope": "MANY"
  }
}
```

## 示例 5：带 options 的删除
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "DELETE",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": [
    "c.email",
    "EQ",
    "ghost@example.com"
  ],
  "mutation": {
    "scope": "ONE"
  },
  "options": {
    "dryRun": true
  }
}
```
