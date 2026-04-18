可以。你的约束可以理解为：

* **顶层字段集合完全不变**
* **不新增新的顶层语法名**
* **只把 `conditions`、`returns`、`mutation` 的内部结构做生成层简化**
* **映射后仍然得到原 canonical OQL**

这意味着，S-OQL 不再是“换一套顶层 DSL”，而是：

**沿用 canonical OQL 的外壳，只在 3 个最重的内部块上定义更适合大模型生成的短语法。**

下面给出一版可直接落到第 9 章的方案。

---

# 9. 生成层语法（S-OQL）- 同壳简化版

## 9.1 设计原则

S-OQL 同壳简化版遵循以下原则：

1. **保留 canonical OQL 的全部顶层字段名与顶层结构**
2. **仅简化 `conditions`、`returns`、`mutation` 的内部表示**
3. **`objects`、`relationships`、`orders`、`sourceQuery`、`linkQuery` 等未列入简化范围的模块，继续沿用 canonical 写法**
4. **S-OQL 仍不可直接执行，必须先映射为 canonical OQL**
5. **同一语义在 S-OQL 中也只保留一种简化写法**

---

## 9.2 顶层结构保持不变

S-OQL 顶层仍然使用原规范字段：

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "<OPERATION>",

  "objects": [...],
  "relationships": [...],
  "conditions": ...,
  "returns": ...,
  "orders": [...],
  "maxResults": 1000,

  "sourceQuery": [...],

  "linkQuery": {...},
  "mutation": ...,

  "options": {...},
  "extensions": {...}
}
```

这里的变化只有：

* `conditions` 的值允许使用 **S-OQL 条件短语法**
* `returns` 的值允许使用 **S-OQL 返回短语法**
* `mutation` 的值允许使用 **S-OQL 写入短语法**

其余字段保持 canonical 结构不变。

---

# 一、`conditions` 的 S-OQL 简化语法

---

## 1.1 设计目标

canonical `conditions` 的问题主要是层级深：

* `kind`
* `relation`
* `children`
* `ref`
* `field`
* `operator`
* `values`

对大模型来说，最难的是反复生成：

* `GROUP / PREDICATE`
* `relation / children`
* `values` 永远是数组

因此 S-OQL 里建议把 `conditions` 简化为：

* **叶子条件：定长数组**
* **逻辑组合：固定 key 对象**

---

## 1.2 叶子条件语法

### 语法

```json
["<alias>.<field>", "<operator>", <value>]
```

### 示例

```json
["o.status", "EQ", "completed"]
```

```json
["o.amount", "GTE", 1000]
```

```json
["o.region", "IN", ["华东", "华北"]]
```

```json
["o.createdAt", "BETWEEN", ["2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z"]]
```

---

## 1.3 空值条件语法

对 `IS_NULL` / `IS_NOT_NULL`，使用二元数组：

```json
["o.deletedAt", "IS_NULL"]
```

```json
["o.deletedAt", "IS_NOT_NULL"]
```

---

## 1.4 逻辑组合语法

### AND

```json
{
  "all": [
    ["o.status", "EQ", "completed"],
    ["o.amount", "GTE", 1000]
  ]
}
```

### OR

```json
{
  "any": [
    ["d.status", "EQ", "running"],
    ["d.status", "EQ", "warning"]
  ]
}
```

### NOT

```json
{
  "not": ["o.status", "EQ", "cancelled"]
}
```

### 嵌套示例

```json
{
  "all": [
    ["d.region", "EQ", "华东"],
    {
      "any": [
        ["d.status", "EQ", "running"],
        {
          "all": [
            ["d.status", "EQ", "warning"],
            ["d.alertLevel", "LTE", 2]
          ]
        }
      ]
    }
  ]
}
```

---

## 1.5 `conditions` 的唯一允许形态

S-OQL 中，`conditions` 只允许以下 5 种形态之一：

1. 叶子条件三元组

```json
["<alias>.<field>", "<operator>", <value>]
```

2. 空值判断二元组

```json
["<alias>.<field>", "IS_NULL"]
```

```json
["<alias>.<field>", "IS_NOT_NULL"]
```

3. AND 组

```json
{ "all": [ ... ] }
```

4. OR 组

```json
{ "any": [ ... ] }
```

5. NOT 组

```json
{ "not": ... }
```

---

## 1.6 `conditions` 的约束

1. 字段引用必须写成 `<alias>.<field>`
2. 不允许裸字段名
3. 不允许 `{field, op, value}` 对象式平行写法
4. `IN` / `NOT_IN` 的值必须是非空数组
5. `BETWEEN` 的值必须是长度为 2 的数组
6. `IS_NULL` / `IS_NOT_NULL` 不允许第 3 项
7. `all` / `any` 的值必须是非空数组
8. `not` 的值必须是单个合法条件节点

---

## 1.7 `conditions` 到 canonical 的映射

### 叶子条件

S-OQL：

```json
["o.status", "EQ", "completed"]
```

canonical：

```json
{
  "kind": "PREDICATE",
  "ref": "o",
  "field": "status",
  "operator": "EQ",
  "values": ["completed"]
}
```

### 空值条件

S-OQL：

```json
["o.deletedAt", "IS_NULL"]
```

canonical：

```json
{
  "kind": "PREDICATE",
  "ref": "o",
  "field": "deletedAt",
  "operator": "IS_NULL"
}
```

### `all`

S-OQL：

```json
{
  "all": [
    ["o.status", "EQ", "completed"],
    ["o.amount", "GTE", 1000]
  ]
}
```

canonical：

```json
{
  "kind": "GROUP",
  "relation": "AND",
  "children": [
    {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "status",
      "operator": "EQ",
      "values": ["completed"]
    },
    {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "amount",
      "operator": "GTE",
      "values": [1000]
    }
  ]
}
```

### `any`

映射为：

```json
{
  "kind": "GROUP",
  "relation": "OR",
  "children": [...]
}
```

### `not`

映射为：

```json
{
  "kind": "GROUP",
  "relation": "NOT",
  "children": [ ... ]
}
```

---

# 二、`returns` 的 S-OQL 简化语法

---

## 2.1 设计目标

canonical `returns` 的问题是：

* 每项都要写 `kind`
* `FIELDS` 和 `GROUP_BY / METRIC` 的结构不同
* `field / fields / function / alias` 很容易串位

因此建议：

* `returns` 仍然保持数组
* 每一项使用**固定长度元组**
* 第 1 项始终作为类型判别位

---

## 2.2 `returns` 的三种简化项

### 2.2.1 字段投影项

```json
["FIELDS", "<ref>", ["field1", "field2", "..."]]
```

示例：

```json
["FIELDS", "o", ["id", "orderNo", "amount", "status"]]
```

---

### 2.2.2 分组项

```json
["GROUP_BY", "<alias>.<field>", "<resultAlias>"]
```

示例：

```json
["GROUP_BY", "o.region", "region"]
```

---

### 2.2.3 聚合指标项

```json
["METRIC", "<function>", "<alias>.<field>|<alias>.*", "<resultAlias>"]
```

示例：

```json
["METRIC", "SUM", "o.amount", "totalAmount"]
```

```json
["METRIC", "COUNT", "o.*", "orderCount"]
```

---

## 2.3 `returns` 的完整示例

### 普通查询

```json
{
  "returns": [
    ["FIELDS", "o", ["id", "orderNo", "amount", "status", "customerName", "createdAt"]]
  ]
}
```

### 关联查询

```json
{
  "returns": [
    ["FIELDS", "d", ["id", "name", "status"]],
    ["FIELDS", "s", ["id", "hostname"]],
    ["FIELDS", "dc", ["id", "name", "region"]],
    ["FIELDS", "r1", ["relationshipType"]]
  ]
}
```

### 聚合查询

```json
{
  "returns": [
    ["GROUP_BY", "o.region", "region"],
    ["METRIC", "SUM", "o.amount", "totalAmount"],
    ["METRIC", "COUNT", "o.*", "orderCount"]
  ]
}
```

---

## 2.4 `returns` 的约束

1. `returns` 仍必须为非空数组
2. 每一项必须是数组，不允许对象形式与简写字符串混用
3. `FIELDS` 项长度必须为 3
4. `GROUP_BY` 项长度必须为 3
5. `METRIC` 项长度必须为 4
6. `FIELDS` 第 2 项必须是单个 alias
7. `FIELDS` 第 3 项必须是显式字段数组，不允许 `*`
8. `GROUP_BY` 第 2 项必须是 `<alias>.<field>`
9. `METRIC` 第 2 项必须为 `COUNT / SUM / AVG / MIN / MAX`
10. `COUNT` 可使用 `<alias>.*`
11. 非 `COUNT` 不允许 `*`
12. `GROUP_BY` 和 `METRIC` 的结果别名必须唯一

---

## 2.5 `returns` 到 canonical 的映射

### `FIELDS`

S-OQL：

```json
["FIELDS", "o", ["id", "orderNo", "amount"]]
```

canonical：

```json
{
  "kind": "FIELDS",
  "ref": "o",
  "fields": ["id", "orderNo", "amount"]
}
```

### `GROUP_BY`

S-OQL：

```json
["GROUP_BY", "o.region", "region"]
```

canonical：

```json
{
  "kind": "GROUP_BY",
  "ref": "o",
  "field": "region",
  "alias": "region"
}
```

### `METRIC`

S-OQL：

```json
["METRIC", "SUM", "o.amount", "totalAmount"]
```

canonical：

```json
{
  "kind": "METRIC",
  "ref": "o",
  "field": "amount",
  "function": "SUM",
  "alias": "totalAmount"
}
```

S-OQL：

```json
["METRIC", "COUNT", "o.*", "orderCount"]
```

canonical：

```json
{
  "kind": "METRIC",
  "ref": "o",
  "field": "*",
  "function": "COUNT",
  "alias": "orderCount"
}
```

---

# 三、`mutation` 的 S-OQL 简化语法

---

## 3.1 设计目标

canonical `mutation` 里最重的是：

```json
{
  "data": {
    "properties": { ... }
  }
}
```

对模型来说，这一层 `properties` 基本没有信息价值，只会增加出错率。

因此建议：

* 保留 `mutation` 顶层块
* 保留 `scope / matchBy / atomic / items`
* **只简化 `data` 的内部层级**
* `set` 保持原样，因为已经足够简单

---

## 3.2 `mutation` 的简化规则

### CREATE / UPSERT

S-OQL 中：

```json
"mutation": {
  "data": {
    "name": "iPhone 16",
    "price": 8999,
    "category": "phone",
    "createdAt": { "$fn": "now" }
  }
}
```

而不是 canonical 的：

```json
"mutation": {
  "data": {
    "properties": {
      "name": "iPhone 16",
      "price": 8999,
      "category": "phone",
      "createdAt": { "$fn": "now" }
    }
  }
}
```

---

### UPDATE

`set` 不变：

```json
"mutation": {
  "scope": "ONE",
  "set": {
    "price": 7999,
    "updatedAt": { "$fn": "now" }
  }
}
```

---

### DELETE

保持不变：

```json
"mutation": {
  "scope": "ONE"
}
```

---

### UPSERT

```json
"mutation": {
  "matchBy": ["sourceSystem", "orderNo"],
  "data": {
    "sourceSystem": "ERP",
    "orderNo": "ORD-20240301-001",
    "status": "shipped",
    "amount": 19999,
    "shippedAt": { "$fn": "now" }
  }
}
```

---

### BATCH

顶层 `mutation` 继续保留：

```json
"mutation": {
  "atomic": true,
  "items": [...]
}
```

其中每个子项内部也允许使用 S-OQL 简化的 `conditions / returns / mutation`。

---

## 3.3 `mutation` 的约束

1. `CREATE` 必须包含 `mutation.data`
2. `UPDATE` 必须包含 `mutation.scope` 与 `mutation.set`
3. `DELETE` 必须包含 `mutation.scope`
4. `UPSERT` 必须包含 `mutation.matchBy` 与 `mutation.data`
5. `BATCH` 必须包含 `mutation.atomic` 与非空 `mutation.items`
6. `mutation.data` 在 S-OQL 中必须直接是属性键值对象
7. `mutation.set` 继续是属性键值对象
8. `matchBy` 中字段必须同时出现在 `mutation.data` 中
9. `BATCH.items[]` 不允许 `BATCH`

---

## 3.4 `mutation` 到 canonical 的映射

### CREATE

S-OQL：

```json
{
  "mutation": {
    "data": {
      "name": "iPhone 16",
      "price": 8999,
      "category": "phone",
      "createdAt": { "$fn": "now" }
    }
  }
}
```

canonical：

```json
{
  "mutation": {
    "data": {
      "properties": {
        "name": "iPhone 16",
        "price": 8999,
        "category": "phone",
        "createdAt": { "$fn": "now" }
      }
    }
  }
}
```

### UPDATE

S-OQL：

```json
{
  "mutation": {
    "scope": "ONE",
    "set": {
      "price": 7999
    }
  }
}
```

canonical：

完全相同。

### UPSERT

S-OQL：

```json
{
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "sourceSystem": "ERP",
      "orderNo": "ORD-20240301-001",
      "status": "shipped"
    }
  }
}
```

canonical：

```json
{
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "properties": {
        "sourceSystem": "ERP",
        "orderNo": "ORD-20240301-001",
        "status": "shipped"
      }
    }
  }
}
```

---

# 四、各 operation 的 S-OQL 示例

---

## 4.1 QUERY

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": {
    "all": [
      ["o.status", "EQ", "completed"],
      ["o.amount", "GTE", 1000]
    ]
  },
  "returns": [
    ["FIELDS", "o", ["id", "orderNo", "amount", "status", "customerName", "createdAt"]]
  ],
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    }
  ],
  "maxResults": 10000
}
```

---

## 4.2 AGGREGATE

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "conditions": ["o.status", "EQ", "completed"],
  "returns": [
    ["GROUP_BY", "o.region", "region"],
    ["METRIC", "SUM", "o.amount", "totalAmount"],
    ["METRIC", "COUNT", "o.*", "orderCount"]
  ],
  "orders": [
    {
      "ref": "o",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

---

## 4.3 CREATE

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
  "strict": true,
  "operation": "CREATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "mutation": {
    "data": {
      "name": "iPhone 16",
      "price": 8999,
      "category": "phone",
      "createdAt": {
        "$fn": "now"
      }
    }
  }
}
```

---

## 4.4 UPDATE

```json
{
  "version": "1.0",
  "schemaRef": "catalog@1.0",
  "strict": true,
  "operation": "UPDATE",
  "objects": [
    {
      "objectType": "Product",
      "alias": "p"
    }
  ],
  "conditions": ["p.id", "EQ", "prod_001"],
  "mutation": {
    "scope": "ONE",
    "set": {
      "price": 7999,
      "updatedAt": {
        "$fn": "now"
      }
    }
  }
}
```

---

## 4.5 UPSERT

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "UPSERT",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    }
  ],
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "sourceSystem": "ERP",
      "orderNo": "ORD-20240301-001",
      "status": "shipped",
      "amount": 19999,
      "shippedAt": {
        "$fn": "now"
      }
    }
  }
}
```

---

## 4.6 BATCH

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
        "objects": [
          {
            "objectType": "Order",
            "alias": "o"
          }
        ],
        "conditions": ["o.orderNo", "EQ", "ORD-20240301-001"],
        "mutation": {
          "scope": "ONE",
          "set": {
            "status": "paid",
            "paidAt": {
              "$fn": "now"
            }
          }
        }
      },
      {
        "operation": "CREATE",
        "objects": [
          {
            "objectType": "Invoice",
            "alias": "i"
          }
        ],
        "mutation": {
          "data": {
            "invoiceNo": "INV-20240301-001",
            "orderNo": "ORD-20240301-001",
            "amount": 19999
          }
        }
      }
    ]
  }
}
```

---

# 五、S-OQL 到 canonical OQL 的统一转换规则

---

## 5.1 顶层规则

1. `version` 直接复制
2. `schemaRef` 直接复制
3. `strict` 直接复制
4. `operation` 直接复制
5. `objects / relationships / orders / sourceQuery / linkQuery / options / extensions` 若未简化，则按 canonical 透传
6. `conditions / returns / mutation` 进入专用转换器

---

## 5.2 `conditions` 转换器

### 输入

S-OQL 条件节点

### 输出

canonical `conditions`

### 规则

1. 三元组 → `PREDICATE + values:[v]`
2. 二元空值判断 → `PREDICATE` 且省略 `values`
3. `all` → `GROUP(AND)`
4. `any` → `GROUP(OR)`
5. `not` → `GROUP(NOT)` 且 `children` 长度为 1

---

## 5.3 `returns` 转换器

### 输入

S-OQL `returns[]`

### 输出

canonical `returns[]`

### 规则

1. `["FIELDS", ref, fields]` → `kind=FIELDS`
2. `["GROUP_BY", "a.b", alias]` → `kind=GROUP_BY`
3. `["METRIC", fn, "a.b", alias]` → `kind=METRIC`
4. `["METRIC", "COUNT", "a.*", alias]` → `field="*"`

---

## 5.4 `mutation` 转换器

### 输入

S-OQL `mutation`

### 输出

canonical `mutation`

### 规则

1. `mutation.data = {...}` → `mutation.data.properties = {...}`
2. `mutation.set` 直接复制
3. `mutation.scope` 直接复制
4. `mutation.matchBy` 直接复制
5. `mutation.atomic` 直接复制
6. `mutation.items[]` 递归转换其内部的 `conditions / returns / mutation`

---

# 六、校验建议

由于顶层字段没有变化，S-OQL 的校验分为两段：

## 6.1 生成层校验

只校验：

* `conditions` 是否满足 S-OQL 短语法
* `returns` 是否满足元组语法
* `mutation.data` 是否为直接属性对象
* 与 operation 是否匹配

## 6.2 canonical 校验

转换完成后，继续走第 8 章已有校验：

* 结构校验
* 引用校验
* 语义校验
* 执行期校验

---

# 七、建议补到第 9 章的结论

你可以把第 9 章收束成一句很清晰的话：

> **S-OQL 同壳简化版保留 canonical OQL 的全部顶层字段，仅对 `conditions`、`returns`、`mutation` 的内部结构提供唯一的生成层短语法。**
> `conditions` 使用“三元组 + all/any/not”逻辑树；
> `returns` 使用固定元组数组；
> `mutation` 仅将 `data.properties` 简化为直接属性对象；
> 在映射为 canonical OQL 后，必须恢复为标准 `conditions / returns / mutation` 结构，再进入校验与执行流程。

---
