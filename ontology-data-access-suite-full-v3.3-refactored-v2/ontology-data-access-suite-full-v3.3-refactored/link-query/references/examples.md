# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：最小一跳列表导航
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    },
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "c.id",
    "EQ",
    "cust-001"
  ],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "PLACED",
    "sourceRef": "c",
    "targetRef": "o",
    "direction": "OUTBOUND"
  },
  "returns": [
    [
      "FIELDS",
      "o",
      [
        "id",
        "status",
        "amount"
      ]
    ]
  ]
}
```

## 示例 2：唯一目标的一跳导航
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    },
    {
      "objectType": "Invoice",
      "alias": "i"
    }
  ],
  "conditions": [
    "o.id",
    "EQ",
    "ord-001"
  ],
  "linkQuery": {
    "mode": "ONE",
    "relationshipType": "HAS_INVOICE",
    "sourceRef": "o",
    "targetRef": "i",
    "direction": "OUTBOUND"
  },
  "returns": [
    [
      "FIELDS",
      "i",
      [
        "id",
        "invoiceNo",
        "status"
      ]
    ]
  ]
}
```

## 示例 3：带派生列与排序
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    },
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "c.email",
    "EQ",
    "alice@example.com"
  ],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "PLACED",
    "sourceRef": "c",
    "targetRef": "o"
  },
  "returns": [
    [
      "FIELDS",
      "o",
      [
        "id",
        "amount"
      ]
    ],
    [
      "EXPR",
      {
        "$fn": "ABS",
        "args": [
          "o.amount"
        ]
      },
      "amountAbs"
    ]
  ],
  "orders": [
    [
      "ORDER_BY",
      "o",
      "amount",
      "DESC"
    ]
  ]
}
```

## 示例 4：反向关系导航
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    },
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": [
    "o.id",
    "EQ",
    "ord-001"
  ],
  "linkQuery": {
    "mode": "ONE",
    "relationshipType": "PLACED",
    "sourceRef": "o",
    "targetRef": "c",
    "direction": "INBOUND"
  },
  "returns": [
    [
      "FIELDS",
      "c",
      [
        "id",
        "name"
      ]
    ]
  ]
}
```

## 示例 5：一跳导航结合子查询
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "LINK_QUERY",
  "sourceQuery": [
    {
      "outputAs": "vipCustomers",
      "version": "1.0",
      "schemaRef": "crm",
      "strict": true,
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "Customer",
          "alias": "sc"
        }
      ],
      "conditions": [
        "sc.level",
        "EQ",
        "vip"
      ],
      "returns": [
        [
          "FIELDS",
          "sc",
          [
"id"
          ]
        ]
      ]
    }
  ],
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c",
      "fromSource": "vipCustomers"
    },
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "PLACED",
    "sourceRef": "c",
    "targetRef": "o",
    "direction": "OUTBOUND"
  },
  "returns": [
    [
      "FIELDS",
      "o",
      [
        "id",
        "status"
      ]
    ]
  ]
}
```
