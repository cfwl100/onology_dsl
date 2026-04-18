# 9. 生成层语法（S-OQL）

本章定义面向生成端（如大模型、NL2DSL 转换器、SDK Builder）的 **S-OQL（Syntax OQL）**。
S-OQL 是一种**与 canonical OQL 共用相同顶层结构**的生成层语法，仅对以下三个高复杂度内部模块提供简化写法：

* `conditions`
* `returns`
* `mutation`

S-OQL 的目标是：

1. 降低大模型生成歧义
2. 缩短生成路径，减少无信息层级
3. 保持对 canonical OQL 的**无损映射**
4. 不改变 OQL 的执行边界与执行模型

> **强约束**：
> S-OQL 不是执行入口。
> 任意 S-OQL 请求在进入 OAC 执行阶段前，**必须先映射为 canonical OQL**。

---

## 9.1 定位与边界

### 9.1.1 S-OQL 的定位

S-OQL 是 canonical OQL 的**生成层等价表示**。
它不改变 OQL 的逻辑模型，也不引入新的顶层语义模块；它仅用于在生成阶段以更短、更稳定、更确定的形式表达：

* 条件逻辑
* 返回投影
* 写入数据结构

### 9.1.2 与 canonical OQL 的关系

1. S-OQL 与 canonical OQL **共用同一套顶层字段名**
2. S-OQL 仅允许对 `conditions`、`returns`、`mutation` 使用本章定义的简化语法
3. 除上述三个模块外，其余字段必须继续使用 canonical OQL 写法
4. S-OQL 到 canonical OQL 的映射必须是**确定性、无损、可校验**的

### 9.1.3 执行边界

1. `validate` 可接收 S-OQL，并返回生成层诊断信息
2. `explain` 不直接解释 S-OQL；应先映射为 canonical OQL，再解释
3. `execute` **禁止**接收 S-OQL；若收到，必须返回 `SLOT_EXECUTION_FORBIDDEN`
4. 任意网关、SDK、Agent 插件不得绕过该约束直接执行 S-OQL

---

## 9.2 顶层结构保持不变

S-OQL 顶层字段与 canonical OQL 完全一致：

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

### 9.2.1 使用原则

1. 顶层字段名不得变化
2. 顶层字段顺序仍应遵循第 2 章推荐顺序
3. `objects`、`relationships`、`orders`、`sourceQuery`、`linkQuery`、`options`、`extensions` 若出现，应继续使用 canonical 写法
4. `conditions`、`returns`、`mutation` 可使用本章定义的 S-OQL 简化写法
5. 未使用字段必须省略；不得输出 `null`、`{}`、`[]` 占位

---

## 9.3 适用范围

### 9.3.1 可简化模块

| 模块           | 是否允许 S-OQL 简化 | 说明                                       |
| ------------ | ------------- | ---------------------------------------- |
| `conditions` | 是             | 使用三元组 / 二元组 / `all` / `any` / `not` 简化语法 |
| `returns`    | 是             | 使用固定元组数组简化语法                             |
| `mutation`   | 是             | 简化 `data.properties` 的内部层级               |

### 9.3.2 不可简化模块

以下字段在 S-OQL 中**不得**另定义并行写法：

* `objects`
* `relationships`
* `orders`
* `sourceQuery`
* `linkQuery`
* `options`
* `extensions`

> **说明**：
> S-OQL 不再引入 `where`、`select`、`data`、`set` 等新的顶层字段名。
> 生成层必须继续使用 canonical 顶层字段，只允许简化其内部结构。

---

## 9.4 `conditions` 的 S-OQL 简化语法

`conditions` 在 canonical OQL 中采用递归逻辑树结构。
S-OQL 将其简化为：

* **叶子条件数组**
* **逻辑组合对象**

---

### 9.4.1 叶子条件：三元组

#### 语法

```json
["<alias>.<field>", "<operator>", <value>]
```

#### 示例

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

### 9.4.2 空值判断：二元组

#### 语法

```json
["<alias>.<field>", "IS_NULL"]
```

```json
["<alias>.<field>", "IS_NOT_NULL"]
```

#### 示例

```json
["o.deletedAt", "IS_NULL"]
```

```json
["o.deletedAt", "IS_NOT_NULL"]
```

---

### 9.4.3 AND 逻辑组

#### 语法

```json
{
  "all": [
    <condition>,
    <condition>,
    ...
  ]
}
```

#### 示例

```json
{
  "all": [
    ["o.status", "EQ", "completed"],
    ["o.amount", "GTE", 1000]
  ]
}
```

---

### 9.4.4 OR 逻辑组

#### 语法

```json
{
  "any": [
    <condition>,
    <condition>,
    ...
  ]
}
```

#### 示例

```json
{
  "any": [
    ["d.status", "EQ", "running"],
    ["d.status", "EQ", "warning"]
  ]
}
```

---

### 9.4.5 NOT 逻辑组

#### 语法

```json
{
  "not": <condition>
}
```

#### 示例

```json
{
  "not": ["o.status", "EQ", "cancelled"]
}
```

---

### 9.4.6 嵌套示例

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

### 9.4.7 `conditions` 的允许形态

S-OQL 中，`conditions` 仅允许以下五类形态：

1. 三元组叶子条件
2. 二元组空值条件
3. `{ "all": [...] }`
4. `{ "any": [...] }`
5. `{ "not": ... }`

不允许任何其他对象式平行写法。

---

### 9.4.8 `conditions` 的约束

1. 字段引用必须写成 `<alias>.<field>`
2. 不允许裸字段名
3. 不允许 `{ "ref": "...", "field": "...", "operator": "...", "value": ... }` 之类对象式简写
4. `IN` / `NOT_IN` 的第 3 项必须为非空数组
5. `BETWEEN` 的第 3 项必须为长度为 2 的数组
6. `IS_NULL` / `IS_NOT_NULL` 不得出现第 3 项
7. `all` / `any` 的值必须为非空数组
8. `not` 的值必须为单个合法条件节点
9. `<alias>` 必须引用当前层已声明的对象 alias 或关系 alias
10. 操作符枚举值与 canonical OQL 保持一致，不得扩展私有操作符

---

### 9.4.9 `conditions` 到 canonical OQL 的映射

#### 三元组 → `PREDICATE`

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

#### 二元空值判断 → `PREDICATE`

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

#### `all` → `GROUP(AND)`

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

#### `any` → `GROUP(OR)`

S-OQL：

```json
{
  "any": [
    ["o.status", "EQ", "completed"],
    ["o.status", "EQ", "paid"]
  ]
}
```

canonical：

```json
{
  "kind": "GROUP",
  "relation": "OR",
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
      "field": "status",
      "operator": "EQ",
      "values": ["paid"]
    }
  ]
}
```

#### `not` → `GROUP(NOT)`

S-OQL：

```json
{
  "not": ["o.status", "EQ", "cancelled"]
}
```

canonical：

```json
{
  "kind": "GROUP",
  "relation": "NOT",
  "children": [
    {
      "kind": "PREDICATE",
      "ref": "o",
      "field": "status",
      "operator": "EQ",
      "values": ["cancelled"]
    }
  ]
}
```

---

## 9.5 `returns` 的 S-OQL 简化语法

`returns` 在 canonical OQL 中采用对象数组，且 `FIELDS`、`GROUP_BY`、`METRIC` 三类项结构不同。
S-OQL 将其统一为**定长元组数组**。

---

### 9.5.1 `FIELDS` 项

#### 语法

```json
["FIELDS", "<ref>", ["field1", "field2", "..."]]
```

#### 示例

```json
["FIELDS", "o", ["id", "orderNo", "amount", "status"]]
```

---

### 9.5.2 `GROUP_BY` 项

#### 语法

```json
["GROUP_BY", "<alias>.<field>", "<resultAlias>"]
```

#### 示例

```json
["GROUP_BY", "o.region", "region"]
```

---

### 9.5.3 `METRIC` 项

#### 语法

```json
["METRIC", "<function>", "<alias>.<field>|<alias>.*", "<resultAlias>"]
```

#### 示例

```json
["METRIC", "SUM", "o.amount", "totalAmount"]
```

```json
["METRIC", "COUNT", "o.*", "orderCount"]
```

---

### 9.5.4 `returns` 的完整示例

#### 普通查询

```json
{
  "returns": [
    ["FIELDS", "o", ["id", "orderNo", "amount", "status", "customerName", "createdAt"]]
  ]
}
```

#### 关联查询

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

#### 聚合查询

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

### 9.5.5 `returns` 的约束

1. `returns` 仍必须为非空数组
2. 每一项必须为数组；不得与 canonical 对象写法混用
3. `FIELDS` 项长度必须为 3
4. `GROUP_BY` 项长度必须为 3
5. `METRIC` 项长度必须为 4
6. `FIELDS` 第 2 项必须为单个 alias
7. `FIELDS` 第 3 项必须为显式字段数组，不允许 `*`
8. `GROUP_BY` 第 2 项必须为 `<alias>.<field>`
9. `METRIC` 第 2 项必须为 `COUNT / SUM / AVG / MIN / MAX`
10. `COUNT` 允许 `<alias>.*`
11. 非 `COUNT` 不允许 `*`
12. `GROUP_BY` 与 `METRIC` 的结果别名必须在当前层唯一
13. `QUERY` / `LINK_QUERY` / `ASSOCIATION_QUERY` 中不得出现 `GROUP_BY` 或 `METRIC`
14. `AGGREGATE` 中不得出现 `FIELDS`

---

### 9.5.6 `returns` 到 canonical OQL 的映射

#### `FIELDS`

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

#### `GROUP_BY`

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

#### `METRIC`

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

## 9.6 `mutation` 的 S-OQL 简化语法

`mutation` 在 canonical OQL 中的主要复杂度来自：

```json
{
  "data": {
    "properties": {
      ...
    }
  }
}
```

其中 `properties` 仅承担包装作用。
S-OQL 保留 `mutation` 块本身，但允许将 `data.properties` 简化为**直接属性对象**。

---

### 9.6.1 `CREATE` / `UPSERT` 的 `data`

#### S-OQL 语法

```json
{
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

### 9.6.2 `UPDATE` 的 `set`

`set` 在 S-OQL 中保持与 canonical 相同写法：

```json
{
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

### 9.6.3 `DELETE` 的 `scope`

```json
{
  "mutation": {
    "scope": "ONE"
  }
}
```

---

### 9.6.4 `UPSERT` 的 `matchBy + data`

```json
{
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

### 9.6.5 `BATCH`

S-OQL 中，`BATCH` 顶层 `mutation` 继续保持 canonical 形态：

```json
{
  "mutation": {
    "atomic": true,
    "items": [...]
  }
}
```

其中 `items[]` 的子项内部也允许使用本章定义的 S-OQL 简化语法。

---

### 9.6.6 `mutation` 的约束

1. `CREATE` 必须包含 `mutation.data`
2. `UPDATE` 必须包含 `mutation.scope` 与 `mutation.set`
3. `DELETE` 必须包含 `mutation.scope`
4. `UPSERT` 必须包含 `mutation.matchBy` 与 `mutation.data`
5. `BATCH` 必须包含 `mutation.atomic` 与非空 `mutation.items`
6. S-OQL 中 `mutation.data` 必须直接为属性键值对象
7. `mutation.set` 必须为属性键值对象
8. `matchBy` 中列出的字段必须全部出现在 `mutation.data` 中
9. `BATCH.items[]` 不允许 `BATCH`
10. 除 `data` 的内部层级外，`mutation` 的其余结构不得变形

---

### 9.6.7 `mutation` 到 canonical OQL 的映射

#### `CREATE`

S-OQL：

```json
{
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

canonical：

```json
{
  "mutation": {
    "data": {
      "properties": {
        "name": "iPhone 16",
        "price": 8999,
        "category": "phone",
        "createdAt": {
          "$fn": "now"
        }
      }
    }
  }
}
```

#### `UPDATE`

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

与 S-OQL 相同。

#### `UPSERT`

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

## 9.7 各 operation 的最小槽位（同壳简化版）

以下最小槽位描述的是：
在使用 S-OQL 简化语法时，各 operation 在映射为 canonical OQL 之前必须具备的信息集合。

| operation           | 最小槽位（S-OQL）                                                        | 说明                                   |
| ------------------- | ------------------------------------------------------------------ | ------------------------------------ |
| `QUERY`             | `operation`、`objects`、`returns`                                    | `returns` 应为 `FIELDS` 元组数组           |
| `AGGREGATE`         | `operation`、`objects`、`returns`                                    | `returns` 中至少一个 `METRIC`             |
| `ASSOCIATION_QUERY` | `operation`、`objects`、`relationships`、`returns`                    | `relationships` 继续使用 canonical 写法    |
| `LINK_QUERY`        | `operation`、`objects`、`conditions`、`returns`、`linkQuery`           | `conditions` / `returns` 可用 S-OQL 简化 |
| `CREATE`            | `operation`、`objects`、`mutation.data`                              | `mutation.data` 为直接属性对象              |
| `UPDATE`            | `operation`、`objects`、`conditions`、`mutation.scope`、`mutation.set` | `conditions` 可用 S-OQL 简化             |
| `DELETE`            | `operation`、`objects`、`conditions`、`mutation.scope`                | `conditions` 可用 S-OQL 简化             |
| `UPSERT`            | `operation`、`objects`、`mutation.matchBy`、`mutation.data`           | `mutation.data` 为直接属性对象              |
| `BATCH`             | `operation`、`mutation.atomic`、`mutation.items`                     | 子项非空，且子项不得为 `BATCH`                  |

---

## 9.8 映射到 canonical 的规则与冲突优先级

### 9.8.1 映射规则

1. **顶层外壳透传**：顶层字段名不变，未简化部分按 canonical 透传
2. **条件归一化**：将 S-OQL `conditions` 简化节点递归映射为 canonical 逻辑树
3. **返回归一化**：将 S-OQL `returns` 元组数组映射为 canonical 对象数组
4. **写块归一化**：将 S-OQL `mutation.data` 直接属性对象映射为 canonical `mutation.data.properties`
5. **递归映射**：`sourceQuery` 与 `BATCH.items[]` 中若出现 S-OQL 简化块，也必须递归完成同样映射
6. **默认值补齐**：仅允许补齐规范定义的默认字段，不得引入私有字段

### 9.8.2 冲突优先级（高 → 低）

1. 显式 `operation` 约束
2. 显式 schema 元数据约束
3. 用户显式字段值
4. 系统推断值
5. 规范默认值

若高优先级与低优先级冲突，必须以高优先级覆盖低优先级，并在 `details` 中记录：

* 冲突路径
* 被覆盖值
* 覆盖来源

---

## 9.9 S-OQL 示例

### 9.9.1 QUERY

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

### 9.9.2 AGGREGATE

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

### 9.9.3 CREATE

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

### 9.9.4 UPDATE

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

### 9.9.5 UPSERT

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

### 9.9.6 BATCH

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

## 9.10 缺失槽位标准错误码

当 S-OQL 无法满足最小槽位时，应在生成/映射阶段直接失败，不进入执行阶段。

| 错误码                          | 含义                                                 |
| ---------------------------- | -------------------------------------------------- |
| `SLOT_MISSING_OPERATION`     | 缺少 `operation` 槽位                                  |
| `SLOT_MISSING_OBJECT`        | 缺少对象槽位                                             |
| `SLOT_MISSING_RETURNS`       | 查询类操作缺少 `returns`                                  |
| `SLOT_MISSING_CONDITIONS`    | `UPDATE` / `DELETE` / `LINK_QUERY` 缺少 `conditions` |
| `SLOT_MISSING_MUTATION_DATA` | `CREATE` / `UPSERT` 缺少 `mutation.data`             |
| `SLOT_MISSING_MATCHBY`       | `UPSERT` 缺少 `mutation.matchBy`                     |
| `SLOT_MISSING_BATCH_ITEMS`   | `BATCH` 缺少 `mutation.items` 或为空                    |
| `SLOT_CONFLICT`              | 槽位冲突且无法自动消解                                        |
| `SLOT_EXECUTION_FORBIDDEN`   | 试图将 S-OQL 直接提交到执行入口                                |

> **说明**：
> 本节错误码仅用于生成层。
> S-OQL 映射完成后，进入 canonical 校验阶段时，继续使用第 8 章标准错误码。

---

## 9.11 执行约束（必须遵守）

1. S-OQL 不得直接作为执行输入
2. 进入执行前，必须先完成：

    * S-OQL 结构校验
    * S-OQL → canonical OQL 映射
    * canonical OQL 标准校验
3. 若映射失败，必须返回生成层错误，而不是进入执行器猜测修复
4. 任何实现都不得同时接受：

    * S-OQL 直接执行
    * canonical OQL 直接执行
      而不做显式区分

---

## 9.12 实现建议

为提升生成稳定性，建议生成器按如下顺序构造 S-OQL：

1. 先生成 `operation`
2. 再生成 `objects`
3. 再生成 `conditions`
4. 再生成 `returns`
5. 最后生成 `mutation` 或其他专用块

为提升修正能力，建议在生成层错误响应中尽可能提供：

* `expected`
* `actual`
* `allowedValues`
* `missingFields`
* `conflictPath`
* `declaredAliases`

---

## 9.13 与附录 A.6 的关系说明

附录 A.6 中若存在使用 `type`、`as`、`ATOM`、`op`、`value`、`linkType` 等字段名的示意骨架，应视为**非正式示意**，不作为本章定义的正式 S-OQL。
正式 S-OQL 应仅以本章定义为准，即：

* 顶层字段名保持 canonical OQL 不变
* 仅允许对 `conditions`、`returns`、`mutation` 使用本章定义的简化语法

---

## 9.14 小结

S-OQL 同壳简化版的核心约束如下：

1. **顶层结构不变**
2. **仅简化 `conditions`、`returns`、`mutation`**
3. **`conditions` 使用“三元组 / 二元组 + all / any / not”**
4. **`returns` 使用固定元组数组**
5. **`mutation.data` 直接写属性对象**
6. **映射完成后必须恢复为 canonical OQL**
7. **S-OQL 不可直接执行**

---
