# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：按字段分组计数
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "returns": [
    [
      "GROUP_BY",
      "o.status",
      "status"
    ],
    [
      "METRIC",
      "COUNT",
      "o.id",
      "orderCount"
    ]
  ]
}
```

## 示例 2：按日期桶分组求和
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "o.status",
    "EQ",
    "paid"
  ],
  "returns": [
    [
      "GROUP_BY",
      {
        "$fn": "DATE_TRUNC",
        "args": [
          "DAY",
          "o.createdAt"
        ]
      },
      "dayBucket"
    ],
    [
      "METRIC",
      "SUM",
      "o.amount",
      "totalAmount"
    ]
  ],
  "orders": [
    [
      "ORDER_BY",
      "o",
      "createdAt",
      "ASC"
    ]
  ]
}
```

## 示例 3：多指标聚合
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "returns": [
    [
      "GROUP_BY",
      "o.customerId",
      "customerId"
    ],
    [
      "METRIC",
      "COUNT",
      "o.id",
      "orderCount"
    ],
    [
      "METRIC",
      "AVG",
      "o.amount",
      "avgAmount"
    ],
    [
      "METRIC",
      "MAX",
      "o.amount",
      "maxAmount"
    ]
  ]
}
```

## 示例 4：带函数条件的聚合
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    {
      "$fn": "ABS",
      "args": [
        "o.discountAmount"
      ]
    },
    "GT",
    0
  ],
  "returns": [
    [
      "METRIC",
      "SUM",
      "o.discountAmount",
      "discountSum"
    ]
  ]
}
```

## 示例 5：聚合前先做子查询筛选
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "AGGREGATE",
  "sourceQuery": [
    {
      "outputAs": "paidOrders",
      "version": "1.0",
      "schemaRef": "crm",
      "strict": true,
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "Order",
          "alias": "po"
        }
      ],
      "conditions": [
        "po.status",
        "EQ",
        "paid"
      ],
      "returns": [
        [
          "FIELDS",
          "po",
          [
"id",
"customerId",
"amount"
          ]
        ]
      ]
    }
  ],
  "objects": [
    {
      "objectType": "Order",
      "alias": "o",
      "fromSource": "paidOrders"
    }
  ],
  "returns": [
    [
      "GROUP_BY",
      "o.customerId",
      "customerId"
    ],
    [
      "METRIC",
      "SUM",
      "o.amount",
      "totalAmount"
    ]
  ]
}
```
