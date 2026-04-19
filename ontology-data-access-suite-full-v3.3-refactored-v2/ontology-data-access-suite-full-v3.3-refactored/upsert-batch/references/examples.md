# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：最小存在则更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "mutation": {
    "matchBy": [
      "email"
    ],
    "data": {
      "email": "alice@example.com",
      "name": "Alice"
    }
  }
}
```

## 示例 2：复合匹配键的存在则更新
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Subscription",
      "alias": "s"
    }
  ],
  "mutation": {
    "matchBy": [
      "customerId",
      "planCode"
    ],
    "data": {
      "customerId": "cust-001",
      "planCode": "pro",
      "status": "active"
    }
  }
}
```

## 示例 3：原子批量写入
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "CREATE",
        "objects": [
          {
"objectType": "Customer",
"alias": "c1"
          }
        ],
        "mutation": {
          "data": {
"name": "Alice"
          }
        }
      },
      {
        "operation": "UPDATE",
        "objects": [
          {
"objectType": "Order",
"alias": "o1"
          }
        ],
        "conditions": [
          "o1.id",
          "EQ",
          "ord-001"
        ],
        "mutation": {
          "scope": "ONE",
          "set": {
"status": "paid"
          }
        }
      }
    ]
  }
}
```

## 示例 4：非原子批量写入
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": false,
    "items": [
      {
        "operation": "UPSERT",
        "objects": [
          {
"objectType": "Customer",
"alias": "c1"
          }
        ],
        "mutation": {
          "matchBy": [
"email"
          ],
          "data": {
"email": "bob@example.com",
"name": "Bob"
          }
        }
      },
      {
        "operation": "DELETE",
        "objects": [
          {
"objectType": "Order",
"alias": "o1"
          }
        ],
        "conditions": [
          "o1.status",
          "EQ",
          "draft"
        ],
        "mutation": {
          "scope": "MANY"
        }
      }
    ]
  }
}
```

## 示例 5：混合写入批次
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "CREATE",
        "objects": [
          {
"objectType": "Invoice",
"alias": "i1"
          }
        ],
        "mutation": {
          "data": {
"invoiceNo": "INV-001",
"status": "pending"
          }
        }
      },
      {
        "operation": "UPDATE",
        "objects": [
          {
"objectType": "Order",
"alias": "o1"
          }
        ],
        "conditions": [
          "o1.id",
          "EQ",
          "ord-001"
        ],
        "mutation": {
          "scope": "ONE",
          "set": {
"invoiceNo": "INV-001"
          }
        }
      },
      {
        "operation": "UPSERT",
        "objects": [
          {
"objectType": "Customer",
"alias": "c1"
          }
        ],
        "mutation": {
          "matchBy": [
"email"
          ],
          "data": {
"email": "carol@example.com",
"name": "Carol"
          }
        }
      }
    ]
  }
}
```
