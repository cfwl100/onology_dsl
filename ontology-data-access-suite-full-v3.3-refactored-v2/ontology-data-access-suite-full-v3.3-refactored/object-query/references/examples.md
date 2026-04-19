# 示例集合

以下示例覆盖最小有效结构、常见变体与边界场景。

## 示例 1：最小有效读取
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
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

## 示例 2：带函数条件与派生列
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "QUERY",
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
        {
          "$fn": "LENGTH",
          "args": [
"c.name"
          ]
        },
        "GT",
        3
      ]
    ]
  },
  "returns": [
    [
      "FIELDS",
      "c",
      [
        "id",
        "name",
        "status"
      ]
    ],
    [
      "EXPR",
      {
        "$fn": "UPPER",
        "args": [
          "c.name"
        ]
      },
      "nameUpper"
    ]
  ],
  "orders": [
    [
      "ORDER_BY",
      "c",
      "name",
      "ASC"
    ]
  ],
  "maxResults": 100
}
```

## 示例 3：空值判断与多值匹配
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": {
    "any": [
      [
        "c.deletedAt",
        "IS_NULL"
      ],
      [
        "c.level",
        "IN",
        [
          "gold",
          "vip"
        ]
      ]
    ]
  },
  "returns": [
    [
      "FIELDS",
      "c",
      [
        "id",
        "level",
        "deletedAt"
      ]
    ]
  ]
}
```

## 示例 4：带同层子查询来源
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "QUERY",
  "sourceQuery": [
    {
      "outputAs": "activeCustomers",
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
        "sc.status",
        "EQ",
        "active"
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
      "fromSource": "activeCustomers"
    }
  ],
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

## 示例 5：范围筛选与降序排序
```json
{
  "version": "1.0",
  "schemaRef": "crm",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": [
    "o.createdAt",
    "BETWEEN",
    [
      "2026-01-01",
      "2026-01-31"
    ]
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
  "maxResults": 50
}
```
