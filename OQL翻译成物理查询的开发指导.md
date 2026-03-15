按 **“OQL → 逻辑执行计划 → 物理查询语句”** 的方式来写，方便 OAC 开发人员直接落地。

**不是每个 OQL 都能直接翻译成“一条 MySQL SQL”或“一条 nGQL”。**
当出现下面任一情况时，OAC 必须走**分解执行 + 中间结果拼接**：

1. 同一个对象的属性分布在不同数据库
2. 不同对象分布在不同数据库
3. 一个查询同时涉及关系遍历和属性过滤
4. 一个查询同时要访问关系库和图数据库

所以 OAC 要做的不是“字符串翻译器”，而是：

> **OQL 编译器 + 逻辑优化器 + 跨源执行编排器**

------

# 1. 建议先定义一套映射模型

为了说明样例，我先假设如下本体到物理层的映射。

------

## 1.1 对象与属性映射假设

### Order

- 逻辑对象：`Order`
- 主键：`id`

属性映射：

| 逻辑属性     | 物理库 | 物理表 | 物理字段      |
| ------------ | ------ | ------ | ------------- |
| id           | MySQL  | orders | id            |
| orderNo      | MySQL  | orders | order_no      |
| status       | MySQL  | orders | status        |
| amount       | MySQL  | orders | amount        |
| customerName | MySQL  | orders | customer_name |
| createdAt    | MySQL  | orders | created_at    |
| region       | MySQL  | orders | region        |
| customerId   | MySQL  | orders | customer_id   |
| sourceSystem | MySQL  | orders | source_system |

------

### Product

- 逻辑对象：`Product`
- 主键：`id`

属性映射：

| 逻辑属性  | 物理库 | 物理表   | 物理字段   |
| --------- | ------ | -------- | ---------- |
| id        | MySQL  | products | id         |
| name      | MySQL  | products | name       |
| price     | MySQL  | products | price      |
| category  | MySQL  | products | category   |
| createdAt | MySQL  | products | created_at |
| updatedAt | MySQL  | products | updated_at |

------

### User

- 逻辑对象：`User`
- 主键：`id`

属性映射：

| 逻辑属性  | 物理库     | 物理表       | 物理字段   |
| --------- | ---------- | ------------ | ---------- |
| id        | MySQL      | users        | id         |
| firstName | MySQL      | users        | first_name |
| lastName  | MySQL      | users        | last_name  |
| email     | PostgreSQL | user_profile | email      |

这个例子故意做了**单对象跨库分片**，后面用于说明 OAC 不一定能生成单条 SQL。

------

### Invoice

- 逻辑对象：`Invoice`
- 主键：`id`

属性映射：

| 逻辑属性  | 物理库 | 物理表   | 物理字段   |
| --------- | ------ | -------- | ---------- |
| id        | MySQL  | invoices | id         |
| invoiceNo | MySQL  | invoices | invoice_no |
| amount    | MySQL  | invoices | amount     |
| status    | MySQL  | invoices | status     |
| orderNo   | MySQL  | invoices | order_no   |

------

### Employee / Department

- Employee 属性表：MySQL
- Department 属性表：MySQL
- Employee-Department 关系：NebulaGraph 边 `works_in`

------

### Device / Server / DataCenter

- 属性表：MySQL
- 图关系：
  - `installed_on`
  - `deployed_in`
    都放在 NebulaGraph

------

# 2. OAC 的执行模型建议

建议把 OQL 转换分成 5 层。

## 2.1 解析层

输入 OQL JSON，生成 AST。

## 2.2 语义绑定层

把：

- objectType
- field
- relationshipType
  绑定到本体模型与物理映射。

得到逻辑计划，例如：

- `Order.status -> mysql.orders.status`
- `Employee --works_in--> Department -> nebula edge works_in`

## 2.3 分组规划层

按物理源拆分成若干子计划：

- MySQL 子计划
- PostgreSQL 子计划
- NebulaGraph 子计划

## 2.4 执行编排层

决定：

- 哪个子计划先跑
- 哪个子计划接受上一步 id 集合作为输入
- 如何做半连接、广播、回表、聚合下推

## 2.5 结果装配层

把物理结果还原成 OQL 逻辑结果结构。

------

# 3. 推荐的转换规则总纲

------

## 3.1 QUERY 的转换原则

### 情况 A：单对象、所有字段同库同表

直接翻译成单条 SQL。

### 情况 B：单对象、字段同库不同表

如果有统一主键，可做 SQL JOIN。

### 情况 C：单对象、字段跨库（不支持）

拆成：

1. 主筛选源查询 id 集合
2. 其他源按 id 回查
3. OAC 在中间层 hash join

### 情况 D：多对象、同库可联接

可下推成单条 SQL JOIN。

### 情况 E：多对象、跨库

拆分执行，中间层 join。

------

## 3.2 AGGREGATE 的转换原则

### 能下推就下推

如果 group by 字段和 metric 字段在同一物理源，直接下推。

### 不能下推时

先抽取最细粒度数据，再在 OAC 层做聚合。
但这通常代价高，建议：

- 要么限制
- 要么要求建宽表 / 物化视图 / 数据服务层

------

## 3.3 ASSOCIATION_QUERY 的转换原则

这类查询最适合图数据库。

推荐两种模式：

### 模式 A：关系在图库，属性在关系库

1. 先用 nGQL 找到路径上的 VID 集合
2. 再去 MySQL 按 id 批量查属性
3. OAC 组装结果

### 模式 B：关系和属性都在图库

可直接一个 nGQL 完成。

------

## 3.4 LINK_QUERY 的转换原则

本质是单跳关系查询，优先翻成一条 nGQL。
如果还要返回属性：

- Nebula 只返回 VID
- 再按 VID 去关系库回查属性

------

## 3.5 UPDATE / DELETE / UPSERT 的转换原则

### 单源

直接翻译。

### 多源对象

需要定义**主写源**与**扩展写源**：

- 主写源：决定对象主键与对象存在性
- 扩展写源：以主键同步写入其他存储

否则会产生：

- 哪边先写
- 哪边失败如何回滚
- UPSERT 判断存在性看哪边

所以建议 OAC 必须在元数据里为每个对象定义：

- `primary_source`
- `identity_source`
- `property_sources`
- `write_policy`

------

# 4. OQL 样例到 MySQL / nGQL 的转换样例

下面我按你前面规范中的高频样例来给。

------

# 4.1 QUERY：查询已完成订单

## OQL

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    { "objectType": "Order", "alias": "o" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "o", "fields": ["id", "orderNo", "amount", "status"] }
  ],
  "orders": [
    { "ref": "o", "field": "createdAt", "direction": "DESC" }
  ],
  "maxResults": 1000
}
```

## MySQL SQL

```sql
SELECT
  o.id AS id,
  o.order_no AS orderNo,
  o.amount AS amount,
  o.status AS status
FROM orders o
WHERE o.status = 'completed'
ORDER BY o.created_at DESC
LIMIT 1000;
```

## NebulaGraph nGQL

如果 `Order` 被映射成 tag，VID 为 `id`：

```ngql
MATCH (o:Order)
WHERE o.status == "completed"
RETURN
  id(o) AS id,
  o.order_no AS orderNo,
  o.amount AS amount,
  o.status AS status
ORDER BY o.created_at DESC
LIMIT 1000;
```

> 如果 `Order` 仅在 MySQL，不在 Nebula 建点，则这个 OQL **不应生成 nGQL**，应标注“该对象不支持图查询下推”。

------

# 4.2 QUERY：金额大于 1000 且客户名包含“张”的订单

## MySQL SQL

```sql
SELECT
  o.id AS id,
  o.order_no AS orderNo,
  o.amount AS amount,
  o.customer_name AS customerName
FROM orders o
WHERE o.amount >= 1000
  AND o.customer_name LIKE '%张%'
LIMIT 1000;
```

## NebulaGraph nGQL

```ngql
MATCH (o:Order)
WHERE o.amount >= 1000 AND o.customer_name CONTAINS "张"
RETURN
  id(o) AS id,
  o.order_no AS orderNo,
  o.amount AS amount,
  o.customer_name AS customerName
LIMIT 1000;
```

------



可以，建议你在 **第 3 章 QUERY** 里专门补一个小节，明确说明：

1. **多个对象可以映射到同一个库的同一张表**
2. **多个对象可以映射到同一个库的不同表**
3. `QUERY` 本身不要求对象必须物理独立；对象是**逻辑对象声明**
4. OAC 可以根据映射关系决定是：
   - 同表自连接
   - 同表不同别名扫描
   - 跨表 JOIN
   - 单表过滤后投影成多个逻辑对象

下面我直接给你一版**可直接补进规范文档**的正式文本。

------

# 3.9 多对象同库查询场景补充说明

`QUERY` 支持在同一请求中声明多个对象。
这些对象在物理层可以映射为：

1. **同一个数据库的同一张物理表**
2. **同一个数据库的不同物理表**
3. **同一个数据库的同一张视图或同一宽表**
4. **同一个数据库中由同一基础表派生出的多个逻辑对象**

因此，`QUERY` 中的多个对象声明并不等价于“必须对应多个物理表”。
OAC 应根据本体映射定义，将逻辑对象映射为实际的物理访问计划。

------

## 3.9.1 转换原则

### 场景 A：多个对象对应同一个库的同一张表

当多个逻辑对象映射到同一个数据库的同一张物理表时，OAC 应根据对象别名生成：

- 同表不同别名扫描
- 同表自连接
- 或基于同一张表的多角色过滤

典型场景包括：

- 同一对象类型的自关联查询
- 同一宽表中拆分出的多个逻辑对象
- 同一实体表中不同角色对象的联合查询

### 场景 B：多个对象对应同一个库的不同表

当多个逻辑对象映射到同一个数据库的不同表时，OAC 可将 OQL 下推为一条 SQL JOIN。
前提是映射关系中已定义对象之间的物理连接键或可推导连接路径。

------

## 3.9.2 场景 A：多个对象对应同一个库的同一张表

### 说明

在某些本体建模场景中，多个逻辑对象可能共享同一张物理表。例如：

- `Employee` 与 `Manager` 都映射到 `employees`
- `OrderBuyer` 与 `OrderSeller` 都映射到 `order_participants`
- `ParentDevice` 与 `ChildDevice` 都映射到 `devices`

此时，`QUERY` 中可以声明多个逻辑对象，OAC 在 SQL 生成时使用不同表别名。

------

### 示例 A1：同一张表中的两个逻辑角色对象

#### 逻辑映射假设

| 逻辑对象 | 物理库 | 物理表    |
| -------- | ------ | --------- |
| Employee | MySQL  | employees |
| Manager  | MySQL  | employees |

其中：

- `Employee.managerId -> employees.manager_id`
- `Manager.id -> employees.id`

------

#### OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "org@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Employee",
      "alias": "e"
    },
    {
      "objectType": "Manager",
      "alias": "m"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "e",
        "field": "status",
        "operator": "EQ",
        "values": ["active"]
      },
      {
        "kind": "PREDICATE",
        "ref": "m",
        "field": "department",
        "operator": "EQ",
        "values": ["R&D"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "e",
      "fields": ["id", "name", "employeeNo"]
    },
    {
      "kind": "FIELDS",
      "ref": "m",
      "fields": ["id", "name"]
    }
  ],
  "maxResults": 1000
}
```

------

#### MySQL SQL 示例

```sql
SELECT
  e.id AS e_id,
  e.name AS e_name,
  e.employee_no AS e_employeeNo,
  m.id AS m_id,
  m.name AS m_name
FROM employees e
JOIN employees m
  ON e.manager_id = m.id
WHERE e.status = 'active'
  AND m.department = 'R&D'
LIMIT 1000;
```

#### MySQL SQL 示例？？？场景是这种吗？ 不存在。

```sql
SELECT
  e.id AS e_id,
  e.name AS e_name,
  e.employee_no AS e_employeeNo,
  e.id AS m_id,
  e.name AS m_name
FROM employees e
WHERE e.status = 'active'
  AND e.department = 'R&D'
LIMIT 1000;
```

------

## 正确判断标准

看你的 OQL 语义到底是哪一种。

### 语义 1：员工及其经理

如果 OQL 是这种意思：

- `Employee` = 普通员工
- `Manager` = 员工的上级
- 两者是同表不同角色
- 有 `e.managerId -> m.id`

那必须保留自连接，不能改成单表查询。

### 语义 2：同一张表上的两个逻辑视图，但没有角色关系

如果 OQL 只是想表达：

- 从 `employees` 表里找符合某些条件的人
- 不需要“员工 -> 经理”的关系

那就不该生成 join，而应直接生成单表查询。

------

## 你这个例子里更准确的说法

原 SQL 对应的是：

```text
Employee(e) JOIN Manager(m) ON e.manager_id = m.id
WHERE e.status = 'active' AND m.department = 'R&D'
```

你替换后的 SQL 对应的是：

```text
Employee(e)
WHERE e.status = 'active' AND e.department = 'R&D'
```

这两个不是等价变换。

------

## 如果你只是想表达“员工和经理都来自同一张表”，正确结论是

**同一张表，不等于可以去掉自连接。**
只要两个 alias 代表不同逻辑角色，并且存在角色间约束，就仍然需要：

```sql
FROM employees e
JOIN employees m ON e.manager_id = m.id
```

------

## 一个最直观的反例

假设数据如下：

| id   | name  | employee_no | status | department | manager_id |
| ---- | ----- | ----------- | ------ | ---------- | ---------- |
| 1    | Alice | E001        | active | Sales      | 10         |
| 2    | Bob   | E002        | active | Finance    | 11         |
| 10   | Carol | M010        | active | R&D        | null       |
| 11   | David | M011        | active | HR         | null       |

原 SQL 会返回：

- Alice，因为她是 active，且她的经理 Carol 在 R&D
- Bob 不返回，因为他的经理 David 不在 R&D

你替换后的 SQL 会返回谁？

- 只返回 department = R&D 的员工，也就是 Carol
- Alice 反而不会返回，因为 Alice 自己不在 R&D

所以结果完全不同。

------

## 给 OAC 开发的建议

可以在规范里加一条很明确的规则：

> 当多个逻辑对象映射到同一张物理表时，如果对象之间存在角色关系、连接条件或路径语义，则必须保留多别名访问或自连接；不得因为物理表相同而折叠为单一别名扫描。

------

## 结论

你的替换写法 **不等价**，不能替换。
除非你要表达的业务语义已经从“员工及其经理”变成了“员工自己属于 R&D”。

如果你愿意，我可以继续帮你把“**同表多对象场景下，什么时候能折叠成单表扫描，什么时候必须保留自连接**”整理成一个判断表。

### 示例 A2：同一张表中同类型对象的自连接查询

#### 逻辑映射假设

| 逻辑对象     | 物理库 | 物理表  |
| ------------ | ------ | ------- |
| ParentDevice | MySQL  | devices |
| ChildDevice  | MySQL  | devices |

其中：

- `ChildDevice.parentId -> devices.parent_id`
- `ParentDevice.id -> devices.id`

------

#### OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "ParentDevice",
      "alias": "p"
    },
    {
      "objectType": "ChildDevice",
      "alias": "c"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "p",
        "field": "deviceType",
        "operator": "EQ",
        "values": ["gateway"]
      },
      {
        "kind": "PREDICATE",
        "ref": "c",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "p",
      "fields": ["id", "name", "deviceType"]
    },
    {
      "kind": "FIELDS",
      "ref": "c",
      "fields": ["id", "name", "status"]
    }
  ],
  "maxResults": 1000
}
```

------

#### MySQL SQL 示例

```sql
SELECT
  p.id AS p_id,
  p.name AS p_name,
  p.device_type AS p_deviceType,
  c.id AS c_id,
  c.name AS c_name,
  c.status AS c_status
FROM devices p
JOIN devices c
  ON c.parent_id = p.id
WHERE p.device_type = 'gateway'
  AND c.status = 'running'
LIMIT 1000;
```

------

## 3.9.3 场景 B：多个对象对应同一个库的不同表

### 说明

当多个逻辑对象映射到同一个数据库的不同物理表时，OAC 可将其转换为同库 JOIN 查询。
典型场景包括：

- `Customer -> customers`
- `Order -> orders`
- `Invoice -> invoices`
- `Product -> products`

只要映射中已知：

- 对象主键
- 外键
- 或可推导关联字段

即可生成单条 SQL。

------

### 示例 B1：订单与客户查询（不同表）

#### 逻辑映射假设

| 逻辑对象 | 物理库 | 物理表    |
| -------- | ------ | --------- |
| Order    | MySQL  | orders    |
| Customer | MySQL  | customers |

其中：

- `Order.customerId -> orders.customer_id`
- `Customer.id -> customers.id`

------

#### OQL 示例

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
    },
    {
      "objectType": "Customer",
      "alias": "c"
    }
  ],
  "conditions": {
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
        "ref": "c",
        "field": "region",
        "operator": "EQ",
        "values": ["华东"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount", "status"]
    },
    {
      "kind": "FIELDS",
      "ref": "c",
      "fields": ["id", "name", "region"]
    }
  ],
  "orders": [
    {
      "ref": "o",
      "field": "createdAt",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

------

#### MySQL SQL 示例

```sql
SELECT
  o.id AS o_id,
  o.order_no AS o_orderNo,
  o.amount AS o_amount,
  o.status AS o_status,
  c.id AS c_id,
  c.name AS c_name,
  c.region AS c_region
FROM orders o
JOIN customers c
  ON o.customer_id = c.id
WHERE o.status = 'completed'
  AND c.region = '华东'
ORDER BY o.created_at DESC
LIMIT 1000;
```

------

### 示例 B2：订单、客户、发票三表联合查询

#### 逻辑映射假设

| 逻辑对象 | 物理库 | 物理表    |
| -------- | ------ | --------- |
| Order    | MySQL  | orders    |
| Customer | MySQL  | customers |
| Invoice  | MySQL  | invoices  |

其中：

- `Order.customerId -> orders.customer_id`
- `Customer.id -> customers.id`
- `Invoice.orderNo -> invoices.order_no`
- `Order.orderNo -> orders.order_no`

------

#### OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "billing@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "Order",
      "alias": "o"
    },
    {
      "objectType": "Customer",
      "alias": "c"
    },
    {
      "objectType": "Invoice",
      "alias": "i"
    }
  ],
  "conditions": {
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
        "ref": "i",
        "field": "status",
        "operator": "EQ",
        "values": ["issued"]
      }
    ]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "o",
      "fields": ["id", "orderNo", "amount"]
    },
    {
      "kind": "FIELDS",
      "ref": "c",
      "fields": ["id", "name"]
    },
    {
      "kind": "FIELDS",
      "ref": "i",
      "fields": ["id", "invoiceNo", "status"]
    }
  ],
  "maxResults": 1000
}
```

------

#### MySQL SQL 示例

```sql
SELECT
  o.id AS o_id,
  o.order_no AS o_orderNo,
  o.amount AS o_amount,
  c.id AS c_id,
  c.name AS c_name,
  i.id AS i_id,
  i.invoice_no AS i_invoiceNo,
  i.status AS i_status
FROM orders o
JOIN customers c
  ON o.customer_id = c.id
JOIN invoices i
  ON i.order_no = o.order_no
WHERE o.status = 'completed'
  AND i.status = 'issued'
LIMIT 1000;
```

------

## 3.9.4 OAC 转换要求

对于 `QUERY` 中多个对象的场景，OAC 应按以下规则处理：

### 规则 1：先判断物理分布

对 `objects[]` 中每个对象，解析：

- 所属数据源
- 所属表
- 主键
- 可用连接键

### 规则 2：相同库且同表时

若多个对象映射到同一张表，则：

- 为每个对象分配独立表别名
- 按映射关系生成自连接或同表多角色查询

### 规则 3：相同库但不同表时

若多个对象映射到同库不同表，则：

- 使用 JOIN 下推
- 连接条件来自本体映射定义，不由 OQL 显式提供

### 规则 4：过滤条件应按对象别名下推

例如：

```json
{
  "kind": "PREDICATE",
  "ref": "c",
  "field": "region",
  "operator": "EQ",
  "values": ["华东"]
}
```

应下推到 `c` 所映射的物理表，而不是误下推到主对象表。

### 规则 5：返回字段必须带逻辑别名前缀

为了避免多对象返回时字段重名，建议 OAC 内部执行计划和结果装配时使用：

- `o_id`
- `c_id`
- `i_id`

这样的物理别名，再映射回逻辑响应。

可以。下面我专门把 **`sourceQuery`** 拆开讲，给出：

1. 它到底解决什么问题
2. 什么时候该用，什么时候不该用
3. 不同类型的典型场景
4. 多个完整 OQL 示例
5. OAC 如何理解和执行 `sourceQuery`

我会尽量按你前面这套 **canonical OQL** 风格来写，方便直接纳入规范或设计文档。

------

# sourceQuery 是什么

`sourceQuery` 的作用可以概括成一句话：

> **先做一个子查询，得到一个中间结果集，再把这个结果集作为外层查询的输入。**

它本质上相当于 SQL 里的：

- 子查询
- 派生表
- CTE（Common Table Expression）
- 中间视图

但在 OQL 里，`sourceQuery` 是显式结构化表达，而不是拼成字符串。

------

# sourceQuery 的适用场景

最适合 `sourceQuery` 的场景有 5 类：

## 1）先筛选，再做外层查询

例如：

- 先找出“已完成订单”
- 再从这些订单中取金额前 100 的记录

## 2）先查询明细，再聚合

例如：

- 先查近 30 天有效订单
- 再按地区统计总金额

## 3）先聚合，再做外层过滤或排序

例如：

- 先按客户汇总订单金额
- 再查总金额大于 10 万的客户排行

## 4）先查一跳结果，再做更复杂关联

例如：

- 先查某批设备
- 再对这些设备做关联路径查询

## 5）跨源编排时先缩小数据集

这对 OAC 特别重要：

- 先在一个源里把数据范围缩小
- 再去另一个源补字段或做进一步查询

------

# 什么时候不该用 sourceQuery

如果只是普通单层查询，不要为了“看起来高级”而用 `sourceQuery`。

例如这些场景通常不需要：

- 单对象简单过滤
- 单层聚合
- 单跳关系查询
- 可以直接一条 SQL / nGQL 下推的查询

原则是：

> **能直接表达就直接表达，只有当“外层真的依赖子查询结果”时才用 `sourceQuery`。**

------

# sourceQuery 的基本结构

典型结构如下：

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "Order",
          "alias": "o"
        }
      ],
      "conditions": {
        "kind": "PREDICATE",
        "ref": "o",
        "field": "status",
        "operator": "EQ",
        "values": ["completed"]
      },
      "returns": [
        {
          "kind": "FIELDS",
          "ref": "o",
          "fields": ["id", "orderNo", "amount", "customerId", "region"]
        }
      ]
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "co",
      "fields": ["id", "orderNo", "amount", "customerId", "region"]
    }
  ]
}
```

这里的关键点是：

- `sourceQuery[].outputAs` 定义子查询结果名字
- 外层 `objects[].fromSource` 绑定这个结果集
- 外层对象 `co` 就是对子查询结果的逻辑引用

------

# 使用场景与例子

下面给你 6 种典型例子。

------

# 场景 1：先筛选，再做普通查询

## 业务描述

先找出“已完成订单”，再从这些订单里返回需要的字段，并按金额排序。

## 为什么用 sourceQuery

因为你想显式表达“外层输入不是原始对象，而是子查询结果”。

## OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "Order",
          "alias": "o"
        }
      ],
      "conditions": {
        "kind": "PREDICATE",
        "ref": "o",
        "field": "status",
        "operator": "EQ",
        "values": ["completed"]
      },
      "returns": [
        {
          "kind": "FIELDS",
          "ref": "o",
          "fields": ["id", "orderNo", "amount", "customerId", "region", "createdAt"]
        }
      ],
      "maxResults": 10000
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "co",
      "fields": ["id", "orderNo", "amount", "customerId", "region", "createdAt"]
    }
  ],
  "orders": [
    {
      "ref": "co",
      "field": "amount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

## 对应 SQL 思路

相当于：

```sql
SELECT
  t.id,
  t.order_no,
  t.amount,
  t.customer_id,
  t.region,
  t.created_at
FROM (
  SELECT
    id,
    order_no,
    amount,
    customer_id,
    region,
    created_at
  FROM orders
  WHERE status = 'completed'
  LIMIT 10000
) t
ORDER BY t.amount DESC
LIMIT 1000;
```

------

# 场景 2：先查明细，再聚合

## 业务描述

先筛选出“已完成订单”，然后按地区统计总金额和订单数。

## 为什么用 sourceQuery

聚合基于一个“先过滤过的逻辑数据集”，而不是直接对原始表聚合。

## OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "CompletedOrder",
      "alias": "co",
      "fromSource": "completed_orders"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "Order",
          "alias": "o"
        }
      ],
      "conditions": {
        "kind": "PREDICATE",
        "ref": "o",
        "field": "status",
        "operator": "EQ",
        "values": ["completed"]
      },
      "returns": [
        {
          "kind": "FIELDS",
          "ref": "o",
          "fields": ["id", "region", "amount"]
        }
      ],
      "maxResults": 100000
    }
  ],
  "returns": [
    {
      "kind": "GROUP_BY",
      "ref": "co",
      "field": "region",
      "alias": "region"
    },
    {
      "kind": "METRIC",
      "ref": "co",
      "field": "amount",
      "function": "SUM",
      "alias": "totalAmount"
    },
    {
      "kind": "METRIC",
      "ref": "co",
      "field": "*",
      "function": "COUNT",
      "alias": "orderCount"
    }
  ],
  "orders": [
    {
      "ref": "co",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 100
}
```

## 对应 SQL 思路

```sql
SELECT
  t.region AS region,
  SUM(t.amount) AS totalAmount,
  COUNT(*) AS orderCount
FROM (
  SELECT id, region, amount
  FROM orders
  WHERE status = 'completed'
) t
GROUP BY t.region
ORDER BY totalAmount DESC
LIMIT 100;
```

------

# 场景 3：先聚合，再在外层筛选或排序

## 业务描述

先按客户统计累计订单金额，再筛选出总金额大于 100000 的客户。

## 为什么用 sourceQuery

外层操作基于“聚合后的结果集”，而不是原始订单表。

## OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "CustomerOrderStat",
      "alias": "cs",
      "fromSource": "customer_stats"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "customer_stats",
      "operation": "AGGREGATE",
      "objects": [
        {
          "objectType": "Order",
          "alias": "o"
        }
      ],
      "returns": [
        {
          "kind": "GROUP_BY",
          "ref": "o",
          "field": "customerId",
          "alias": "customerId"
        },
        {
          "kind": "METRIC",
          "ref": "o",
          "field": "amount",
          "function": "SUM",
          "alias": "totalAmount"
        }
      ],
      "maxResults": 100000
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "cs",
    "field": "totalAmount",
    "operator": "GT",
    "values": [100000]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "cs",
      "fields": ["customerId", "totalAmount"]
    }
  ],
  "orders": [
    {
      "ref": "cs",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

## 对应 SQL 思路

```sql
SELECT
  s.customerId,
  s.totalAmount
FROM (
  SELECT
    customer_id AS customerId,
    SUM(amount) AS totalAmount
  FROM orders
  GROUP BY customer_id
) s
WHERE s.totalAmount > 100000
ORDER BY s.totalAmount DESC
LIMIT 1000;
```

------

# 场景 4：先查对象集合，再做关联查询

## 业务描述

先找出状态为 running 的设备，再查这些设备部署在哪些服务器和机房。

## 为什么用 sourceQuery

你不想对所有设备做图遍历，而只想对一个子集做后续关联路径查询。

## OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {
      "objectType": "RunningDevice",
      "alias": "d",
      "fromSource": "running_devices"
    },
    {
      "objectType": "Server",
      "alias": "s"
    },
    {
      "objectType": "DataCenter",
      "alias": "dc"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "running_devices",
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "Device",
          "alias": "rd"
        }
      ],
      "conditions": {
        "kind": "PREDICATE",
        "ref": "rd",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      },
      "returns": [
        {
          "kind": "FIELDS",
          "ref": "rd",
          "fields": ["id", "name", "status"]
        }
      ],
      "maxResults": 50000
    }
  ],
  "relationships": [
    {
      "relationshipType": "installed_on",
      "alias": "r1",
      "from": "d",
      "to": "s"
    },
    {
      "relationshipType": "deployed_in",
      "alias": "r2",
      "from": "s",
      "to": "dc"
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["id", "name", "status"]
    },
    {
      "kind": "FIELDS",
      "ref": "s",
      "fields": ["id", "hostname"]
    },
    {
      "kind": "FIELDS",
      "ref": "dc",
      "fields": ["id", "name", "region"]
    }
  ],
  "maxResults": 5000
}
```

## OAC 执行思路

1. 先执行子查询，得到 running 设备 id 集合
2. 再以这些 id 为起点执行图路径查询
3. 最后拼装设备、服务器、机房结果

这个例子对 OAC 很有代表性，因为它说明：

> `sourceQuery` 不只是 SQL 子查询，也可以是**跨源执行计划中的前置数据集裁剪器**。

------

# 场景 5：跨库属性场景下先缩小主键集合，再补字段

## 业务描述

`User` 的基础属性在 MySQL，`email` 在 PostgreSQL。
先查出姓 Zhang 的用户 id，再去 PostgreSQL 补 email。

## 为什么用 sourceQuery

先在一个源筛选 id，避免跨库全表 join。

## OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "iam@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "SelectedUser",
      "alias": "u",
      "fromSource": "selected_users"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "selected_users",
      "operation": "QUERY",
      "objects": [
        {
          "objectType": "User",
          "alias": "u0"
        }
      ],
      "conditions": {
        "kind": "PREDICATE",
        "ref": "u0",
        "field": "lastName",
        "operator": "EQ",
        "values": ["Zhang"]
      },
      "returns": [
        {
          "kind": "FIELDS",
          "ref": "u0",
          "fields": ["id", "firstName", "lastName", "email"]
        }
      ],
      "maxResults": 10000
    }
  ],
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "u",
      "fields": ["id", "firstName", "lastName", "email"]
    }
  ],
  "maxResults": 1000
}
```

## OAC 实际执行计划

虽然 OQL 看起来像一层，但 OAC 可做：

1. MySQL：查 `id, first_name, last_name`
2. PostgreSQL：按 id 回查 `email`
3. 中间层 merge
4. 外层返回 `u`

这个例子说明：

> `sourceQuery` 可以作为 **逻辑中间结果集**，不要求物理上一条 SQL 就能完成。

------

# 场景 6：多层 sourceQuery

## 业务描述

先查已完成订单，再在其上按客户聚合金额，最后筛选高价值客户。

## 为什么用多层 sourceQuery

每一层都把上层输入收敛得更清晰：

- 第 1 层：明细过滤
- 第 2 层：聚合
- 第 3 层：外层筛选与排序

## OQL 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "HighValueCustomerStat",
      "alias": "hcs",
      "fromSource": "customer_stats"
    }
  ],
  "sourceQuery": [
    {
      "outputAs": "customer_stats",
      "operation": "AGGREGATE",
      "objects": [
        {
          "objectType": "CompletedOrder",
          "alias": "co",
          "fromSource": "completed_orders"
        }
      ],
      "sourceQuery": [
        {
          "outputAs": "completed_orders",
          "operation": "QUERY",
          "objects": [
            {
              "objectType": "Order",
              "alias": "o"
            }
          ],
          "conditions": {
            "kind": "PREDICATE",
            "ref": "o",
            "field": "status",
            "operator": "EQ",
            "values": ["completed"]
          },
          "returns": [
            {
              "kind": "FIELDS",
              "ref": "o",
              "fields": ["id", "customerId", "amount"]
            }
          ],
          "maxResults": 100000
        }
      ],
      "returns": [
        {
          "kind": "GROUP_BY",
          "ref": "co",
          "field": "customerId",
          "alias": "customerId"
        },
        {
          "kind": "METRIC",
          "ref": "co",
          "field": "amount",
          "function": "SUM",
          "alias": "totalAmount"
        }
      ],
      "maxResults": 100000
    }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "hcs",
    "field": "totalAmount",
    "operator": "GT",
    "values": [100000]
  },
  "returns": [
    {
      "kind": "FIELDS",
      "ref": "hcs",
      "fields": ["customerId", "totalAmount"]
    }
  ],
  "orders": [
    {
      "ref": "hcs",
      "field": "totalAmount",
      "direction": "DESC"
    }
  ],
  "maxResults": 1000
}
```

------

# sourceQuery 的几个关键使用规则

建议你在规范里写清楚这些。

## 规则 1：外层对象必须显式绑定 sourceQuery 结果

通过：

- `sourceQuery[].outputAs`
- `objects[].fromSource`

来绑定

不能隐式推断。

------

## 规则 2：sourceQuery 适合作为“逻辑数据集”，不要求是物理表

也就是说 `outputAs` 不是物理表名，而是：

- 中间结果集名
- 派生数据集名
- 编排阶段的数据流节点名

------

## 规则 3：子查询的返回字段决定外层可见字段

如果子查询没有返回某个字段，外层对象就不应再引用它。

例如：
子查询只返回：

- `id`
- `amount`

那外层就不能再拿这个结果集去按 `region` 排序。

------

## 规则 4：sourceQuery 不建议过深

规范上可以支持递归，但工程上建议：

- 默认最多 2 层
- 非必要不要超过 2 层

因为层数一深：

- 大模型更容易生成错
- OAC 优化与回溯也更复杂

------

## 规则 5：sourceQuery 最适合和 OAC 执行计划绑定

你可以把 `sourceQuery` 理解成 OAC 的“逻辑子计划节点”：

- 一个 sourceQuery = 一个中间数据集
- 外层 objects = 该数据集的消费节点

这比把它仅仅看成“语法糖”更有用。

> `sourceQuery` 用于定义当前查询所依赖的中间结果集。
> 每个 `sourceQuery` 子句都会生成一个命名输出 `outputAs`，外层对象通过 `objects[].fromSource` 显式引用该结果集。
> `sourceQuery` 既可表示单源子查询，也可表示 OAC 在多源编排中的逻辑子计划节点。
> 因此，`sourceQuery` 的语义不局限于 SQL 子查询，也适用于跨库、跨表、跨图数据源的中间结果组织与后续处理。

------

# 最后给一个速查表

| 场景                     | 是否适合用 sourceQuery | 原因                       |
| ------------------------ | ---------------------- | -------------------------- |
| 简单单表查询             | 否                     | 直接 QUERY 即可            |
| 先过滤再查               | 是                     | 子查询定义输入集           |
| 先查明细再聚合           | 是                     | 聚合基于子查询结果         |
| 先聚合再过滤             | 是                     | 外层基于聚合结果继续筛选   |
| 先筛一批对象再做路径遍历 | 是                     | 可先缩小图遍历输入         |
| 跨库先缩主键集合再补字段 | 是                     | OAC 编排很受益             |
| 很深的多层嵌套           | 谨慎                   | 复杂度高，生成和执行都更难 |



# 4.3 AGGREGATE：按地区统计订单总金额

## OQL

```json
{
  "operation": "AGGREGATE",
  "objects": [
    { "objectType": "Order", "alias": "o" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "status",
    "operator": "EQ",
    "values": ["completed"]
  },
  "returns": [
    { "kind": "GROUP_BY", "ref": "o", "field": "region", "alias": "region" },
    { "kind": "METRIC", "ref": "o", "field": "amount", "function": "SUM", "alias": "totalAmount" }
  ],
  "orders": [
    { "ref": "o", "field": "totalAmount", "direction": "DESC" }
  ]
}
```

## MySQL SQL

```sql
SELECT
  o.region AS region,
  SUM(o.amount) AS totalAmount
FROM orders o
WHERE o.status = 'completed'
GROUP BY o.region
ORDER BY totalAmount DESC
LIMIT 100;
```

## NebulaGraph nGQL

Nebula 的聚合可这样写：

```ngql
MATCH (o:Order)
WHERE o.status == "completed"
RETURN
  o.region AS region,
  SUM(o.amount) AS totalAmount
ORDER BY totalAmount DESC
LIMIT 100;
```

> 实际 Nebula 对不同版本 openCypher 支持细节不一样。
> OAC 实现时建议把 **图查询模板能力表** 做成元数据配置，不要写死假设所有 openCypher 语法都可用。

------

# 4.4 ASSOCIATION_QUERY：查询员工所属部门

## OQL

```json
{
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    { "objectType": "Employee", "alias": "e" },
    { "objectType": "Department", "alias": "d" }
  ],
  "relationships": [
    { "relationshipType": "works_in", "alias": "r", "from": "e", "to": "d" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "e",
    "field": "employeeNo",
    "operator": "EQ",
    "values": ["E1002"]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "e", "fields": ["id", "name", "employeeNo"] },
    { "kind": "FIELDS", "ref": "d", "fields": ["id", "name"] }
  ]
}
```

------

## MySQL SQL（如果关系也落表）

假设有关系表 `employee_department_rel(employee_id, department_id)`：

```sql
SELECT
  e.id AS e_id,
  e.name AS e_name,
  e.employee_no AS e_employeeNo,
  d.id AS d_id,
  d.name AS d_name
FROM employees e
JOIN employee_department_rel r
  ON r.employee_id = e.id
JOIN departments d
  ON d.id = r.department_id
WHERE e.employee_no = 'E1002'
LIMIT 1;
```

------

## NebulaGraph nGQL（推荐）

假设：

- `Employee` tag
- `Department` tag
- `works_in` edge
- vertex VID 就是业务 id

```ngql
MATCH (e:Employee)-[r:works_in]->(d:Department)
WHERE e.employee_no == "E1002"
RETURN
  id(e) AS e_id,
  e.name AS e_name,
  e.employee_no AS e_employeeNo,
  id(d) AS d_id,
  d.name AS d_name
LIMIT 1;
```

------

## 推荐的 OAC 执行方式

如果 Employee/Department 属性在 MySQL，关系在 Nebula：

### 第一步：nGQL 只取 id

```ngql
MATCH (e:Employee)-[:works_in]->(d:Department)
WHERE e.employee_no == "E1002"
RETURN id(e) AS e_id, id(d) AS d_id
LIMIT 1;
```

### 第二步：MySQL 回查属性

```sql
SELECT id, name, employee_no
FROM employees
WHERE id IN (?);

SELECT id, name
FROM departments
WHERE id IN (?);
```

### 第三步：OAC 组装

这才是最通用的真实实现。

------

# 4.5 ASSOCIATION_QUERY：设备 → 服务器 → 机房 多跳

## OQL

```json
{
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    { "objectType": "Device", "alias": "d" },
    { "objectType": "Server", "alias": "s" },
    { "objectType": "DataCenter", "alias": "dc" }
  ],
  "relationships": [
    { "relationshipType": "installed_on", "alias": "r1", "from": "d", "to": "s" },
    { "relationshipType": "deployed_in", "alias": "r2", "from": "s", "to": "dc" }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      { "kind": "PREDICATE", "ref": "d", "field": "status", "operator": "EQ", "values": ["running"] },
      { "kind": "PREDICATE", "ref": "dc", "field": "region", "operator": "EQ", "values": ["华东"] }
    ]
  }
}
```

------

## MySQL SQL（如果关系也表化）

假设：

- `devices`
- `servers`
- `data_centers`
- `device_server_rel`
- `server_dc_rel`

```sql
SELECT
  d.id AS d_id,
  d.name AS d_name,
  d.status AS d_status,
  s.id AS s_id,
  s.hostname AS s_hostname,
  dc.id AS dc_id,
  dc.name AS dc_name,
  dc.region AS dc_region
FROM devices d
JOIN device_server_rel r1
  ON r1.device_id = d.id
JOIN servers s
  ON s.id = r1.server_id
JOIN server_dc_rel r2
  ON r2.server_id = s.id
JOIN data_centers dc
  ON dc.id = r2.dc_id
WHERE d.status = 'running'
  AND dc.region = '华东'
LIMIT 5000;
```

------

## NebulaGraph nGQL（推荐）

```ngql
MATCH (d:Device)-[r1:installed_on]->(s:Server)-[r2:deployed_in]->(dc:DataCenter)
WHERE d.status == "running" AND dc.region == "华东"
RETURN
  id(d) AS d_id, d.name AS d_name, d.status AS d_status,
  id(s) AS s_id, s.hostname AS s_hostname,
  id(dc) AS dc_id, dc.name AS dc_name, dc.region AS dc_region
LIMIT 5000;
```

------

# 4.6 LINK_QUERY：获取订单关联发票

## OQL

```json
{
  "operation": "LINK_QUERY",
  "objects": [
    { "objectType": "Order", "alias": "o" },
    { "objectType": "Invoice", "alias": "i" }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "o",
    "field": "orderNo",
    "operator": "EQ",
    "values": ["ORD-001"]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "i", "fields": ["id", "invoiceNo", "amount", "status"] }
  ],
  "linkQuery": {
    "mode": "ONE",
    "relationshipType": "has_invoice",
    "sourceRef": "o",
    "targetRef": "i",
    "direction": "OUTBOUND"
  }
}
```

------

## MySQL SQL（如果关系字段落在发票表）

假设 `invoices.order_no = orders.order_no`：

```sql
SELECT
  i.id AS id,
  i.invoice_no AS invoiceNo,
  i.amount AS amount,
  i.status AS status
FROM orders o
JOIN invoices i
  ON i.order_no = o.order_no
WHERE o.order_no = 'ORD-001'
LIMIT 1;
```

------

## NebulaGraph nGQL

```ngql
MATCH (o:Order)-[:has_invoice]->(i:Invoice)
WHERE o.order_no == "ORD-001"
RETURN
  id(i) AS id,
  i.invoice_no AS invoiceNo,
  i.amount AS amount,
  i.status AS status
LIMIT 1;
```

------

# 4.7 CREATE：创建产品

## MySQL SQL

```sql
INSERT INTO products (
  name,
  price,
  category,
  created_at
) VALUES (
  'iPhone 16',
  8999,
  'phone',
  NOW()
);
```

## NebulaGraph nGQL

如果 Product 也映射为点：

```ngql
INSERT VERTEX Product(name, price, category, created_at)
VALUES "prod_001":("iPhone 16", 8999, "phone", datetime());
```

> 注意：Nebula 通常要求明确 VID。
> 所以 OAC 若对图库执行 CREATE，必须先解决 id 生成策略：
>
> - 业务侧传入
> - OAC 统一生成
> - 主写源先生成 id 再同步到图库

------

# 4.8 UPDATE：更新产品价格

## MySQL SQL

```sql
UPDATE products
SET
  price = 7999,
  updated_at = NOW()
WHERE id = 'prod_001'
LIMIT 1;
```

## NebulaGraph nGQL

Nebula 对点属性更新可用：

```ngql
UPDATE VERTEX ON Product "prod_001"
SET price = 7999, updated_at = datetime();
```

------

# 4.9 UPSERT：按 matchBy 更新或插入订单

## OQL

```json
{
  "operation": "UPSERT",
  "objects": [
    { "objectType": "Order", "alias": "o" }
  ],
  "mutation": {
    "matchBy": ["sourceSystem", "orderNo"],
    "data": {
      "properties": {
        "sourceSystem": "ERP",
        "orderNo": "ORD-001",
        "status": "shipped",
        "amount": 19999
      }
    }
  }
}
```

------

## MySQL SQL

前提：有唯一索引 `(source_system, order_no)`

```sql
INSERT INTO orders (
  source_system,
  order_no,
  status,
  amount
) VALUES (
  'ERP',
  'ORD-001',
  'shipped',
  19999
)
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  amount = VALUES(amount);
```

------

## NebulaGraph nGQL

Nebula 没有和 MySQL 完全等价的 `ON DUPLICATE KEY UPDATE`。
真实实现一般要走：

### 方案 A：查后写

1. `LOOKUP` / `FETCH` 查点是否存在
2. 存在则 `UPDATE VERTEX`
3. 不存在则 `INSERT VERTEX`

例如：

```ngql
FETCH PROP ON Order "order_vid";
```

存在：

```ngql
UPDATE VERTEX ON Order "order_vid"
SET status = "shipped", amount = 19999;
```

不存在：

```ngql
INSERT VERTEX Order(source_system, order_no, status, amount)
VALUES "order_vid":("ERP", "ORD-001", "shipped", 19999);
```

> 所以对 OAC 来说：
> **UPSERT 在图库上通常不是“一条语句翻译”，而是一个执行模板。**

------

# 5. 关键：单对象跨属性多库时怎么翻

这是你特别强调的场景：
比如 `User.id / firstName / lastName` 在 MySQL，`email` 在 PostgreSQL。

## OQL

```json
{
  "operation": "QUERY",
  "objects": [
    { "objectType": "User", "alias": "u" }
  ],
  "returns": [
    { "kind": "FIELDS", "ref": "u", "fields": ["id", "firstName", "lastName", "email"] }
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "u",
    "field": "id",
    "operator": "EQ",
    "values": ["user_001"]
  }
}
```

------

## 不能直接翻译成单条 MySQL SQL

因为 `email` 不在 MySQL。

## OAC 应生成执行计划

### Step 1：在 identity / primary source 查主对象

MySQL:

```sql
SELECT
  id,
  first_name,
  last_name
FROM users
WHERE id = 'user_001'
LIMIT 1;
```

### Step 2：在 PostgreSQL 查扩展属性

```sql
SELECT
  user_id AS id,
  email
FROM user_profile
WHERE user_id = 'user_001';
```

### Step 3：OAC 中间层按 id merge

最终逻辑返回：

```json
{
  "u": {
    "id": "user_001",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com"
  }
}
```

------

## 对 OAC 的实现建议

每个对象需要定义：

```yaml
objectType: User
identity:
  source: mysql_user
  table: users
  key: id
propertyMappings:
  id:
    source: mysql_user
    table: users
    column: id
  firstName:
    source: mysql_user
    table: users
    column: first_name
  lastName:
    source: mysql_user
    table: users
    column: last_name
  email:
    source: pg_user_profile
    table: user_profile
    column: email
    joinKey:
      local: id
      remote: user_id
```

然后 OAC 决定：

- `conditions` 优先下推到哪个源
- `returns` 需要从哪些源回表
- 最后怎么 merge

------

# 6. 多对象同库时的下推规则

比如 `Customer` 和 `Order` 都在 MySQL，且存在可识别连接关系。
OAC 可以直接下推 JOIN。

## 规则

如果满足以下条件，可直接翻单条 SQL：

1. 两个对象都在同一数据库实例
2. 连接键映射明确
3. 查询字段和过滤字段都可在该实例中求值
4. 不涉及图路径遍历

否则拆分。

------

# 7. NebulaGraph 场景的推荐开发模式

对于 Nebula，我强烈建议 OAC 不要把它当成“另一个 SQL 方言”，而要分 3 类模板：

## 7.1 顶点属性查询

- 单 tag 查询
- 多 tag 条件过滤
- 顶点属性返回

## 7.2 单跳关系查询

- `MATCH (a)-[:edge]->(b)`

## 7.3 多跳路径查询

- `MATCH path=(a)-[:e1]->(b)-[:e2]->(c)`

然后再叠加：

- WHERE
- RETURN
- ORDER BY
- LIMIT

这样更适合做模板化编译器。

------

# 8. OAC 转换引擎的建议架构

我建议开发时把引擎做成下面 8 个模块。

## 8.1 AST Builder

解析 OQL JSON。

## 8.2 Ontology Binder

把：

- objectType
- field
- relationshipType
  绑定到本体和映射定义。

## 8.3 Source Grouper

按物理源分组：

- mysql
- postgres
- nebula

## 8.4 Predicate Splitter

把 `conditions` 拆成：

- 可下推谓词
- 需中间层求值谓词

## 8.5 Query Planner

决定：

- 先查哪个源
- 哪些按 id 回查
- 哪些在中间层 join / filter / aggregate

## 8.6 Dialect Generator

分别生成：

- MySQL SQL
- PostgreSQL SQL
- Nebula nGQL

## 8.7 Executor

并发 / 串行执行物理子查询。

## 8.8 Result Assembler

按 alias 和字段装配结果。

------

# 9. 一组很实用的转换规则表

------

## 9.1 条件下推规则

| 场景                     | 处理方式                                       |
| ------------------------ | ---------------------------------------------- |
| 叶子条件字段都在同一源   | 整体下推                                       |
| AND 两侧都可下推到同一源 | 合并下推                                       |
| AND 两侧在不同源         | 各自下推后中间层 intersect                     |
| OR 两侧在不同源          | 各自下推后中间层 union                         |
| NOT 跨源                 | 一般在中间层做                                 |
| 图关系条件 + 属性条件    | 关系下推到图库，属性按 id 回表或先查属性再筛点 |

------

## 9.2 返回字段装配规则

| 场景                       | 处理方式              |
| -------------------------- | --------------------- |
| 所有字段同表               | 单 SQL                |
| 同库不同表                 | SQL JOIN              |
| 跨库                       | 多查询 + OAC merge    |
| 图对象属性全在图库         | 单 nGQL               |
| 图关系在图库、属性在关系库 | nGQL 取 id + SQL 回查 |

------

## 9.3 写操作规则

| operation | 推荐主写模式                                           |
| --------- | ------------------------------------------------------ |
| CREATE    | 主源插入后同步其他源                                   |
| UPDATE    | 先按 conditions 在 identity source 定位 id，再分源更新 |
| DELETE    | 先定位 id，再按删除策略级联删                          |
| UPSERT    | 必须基于 identity / unique source 判存在               |
| BATCH     | OAC 统一事务边界或补偿策略                             |

------

# 10. 给 OAC 开发人员的最终建议

如果目标是支持“各种对象查询语法组合”，那实现重点不是多写几种 SQL 模板，而是先把 **查询分解规则** 建好。

最值得先做的 4 件事：

1. **建立标准映射元模型**
   - 对象 → 属性 → 数据源 → 表/列
   - 关系 → 图边 / 关系表
   - identity source / primary source
2. **把 OQL 编译成逻辑计划**
   - 不直接拼 SQL/nGQL
3. **做多源谓词下推与中间层 join**
   - 尤其支持跨属性多库
4. **把 Nebula 做成模板化图查询后端**
   - 单跳、多跳、属性过滤、VID 回查

------

如果你愿意，我下一步可以继续给你两份更落地的东西之一：
第一份是 **“OQL → 逻辑执行计划 IR” 设计草案**，第二份是 **“MySQL / Nebula / PostgreSQL 三后端的编译伪代码框架”**。

