# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：最小两跳路径
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    },
    {
      "objectType": "Order",
      "alias": "o"
    },
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "relationships": [
    {
      "relationshipType": "PLACED",
      "alias": "r1",
      "from": "c",
      "to": "o"
    },
    {
      "relationshipType": "CONTAINS",
      "alias": "r2",
      "from": "o",
      "to": "p"
    }
  ],
  "returns": [
    [
      "FIELDS",
      "p",
      [
        "id",
        "name"
      ]
    ]
  ]
}
```

## 示例 2：节点与边联合筛选
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    },
    {
      "objectType": "Order",
      "alias": "o"
    },
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "relationships": [
    {
      "relationshipType": "PLACED",
      "alias": "r1",
      "from": "c",
      "to": "o"
    },
    {
      "relationshipType": "CONTAINS",
      "alias": "r2",
      "from": "o",
      "to": "p"
    }
  ],
  "conditions": {
    "all": [
      [
        "c.level",
        "EQ",
        "vip"
      ],
      [
        "r2.quantity",
        "GT",
        1
      ]
    ]
  },
  "returns": [
    [
      "FIELDS",
      "p",
      [
        "id",
        "name"
      ]
    ],
    [
      "FIELDS",
      "r2",
      [
        "quantity"
      ]
    ]
  ]
}
```

## 示例 3：返回派生列
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
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
  "relationships": [
    {
      "relationshipType": "PLACED",
      "alias": "r1",
      "from": "c",
      "to": "o"
    }
  ],
  "returns": [
    [
      "FIELDS",
      "o",
      [
        "id",
        "status"
      ]
    ],
    [
      "EXPR",
      {
        "$fn": "UPPER",
        "args": [
          "o.status"
        ]
      },
      "statusUpper"
    ]
  ]
}
```

## 示例 4：带排序和限制条数
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
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
  "relationships": [
    {
      "relationshipType": "PLACED",
      "alias": "r1",
      "from": "c",
      "to": "o"
    }
  ],
  "conditions": [
    "c.id",
    "EQ",
    "cust-001"
  ],
  "returns": [
    [
      "FIELDS",
      "o",
      [
        "id",
        "amount",
        "createdAt"
      ]
    ]
  ],
  "orders": [
    [
      "ORDER_BY",
      "o",
      "createdAt",
      "DESC"
    ]
  ],
  "maxResults": 20
}
```

## 示例 5：路径读取使用子查询结果
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
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
  "relationships": [
    {
      "relationshipType": "PLACED",
      "alias": "r1",
      "from": "c",
      "to": "o"
    }
  ],
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
