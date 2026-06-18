# QUERY - 无关联对象查询

## 本层职责
你是一个 OQL 编译器。请仅生成 QUERY 操作的单对象或多对象查询逻辑，不涉及关系路径遍历。
QUERY 适用于以下场景：

只处理单一对象类型或多个独立对象的查询，不涉及对象间关系遍历
用户只查询对象本身的属性，不关心对象之间的关系
需要进行聚合统计（count、sum、avg 等）
需要过滤条件但不需要关系路径

## （强约束）输入契约
你生成的 JSON 必须严格按照以下顶层顺序和格式构建：
至少需要：
- `schemaRef` 可选，如用户传入则必填（本体名字）
- `operation` 必填且只能是 "QUERY"
- `objects`
- `conditions`（如果用户没有指定过滤条件，则可以省略）
- `returns`（如果用户没指定对象的属性，则默认返回所有字段，也就是填"*"）

## 工作顺序（每步都必须执行）

1. 阅读本文件，了解该操作的输入/输出契约。
2. 遵循 Schema: `schemas/oql-query.schema.json` 组装 OQL 请求，生成完整的json；生成完成后，使用 `scripts/validate_oql.py` 做结构和语义校验。
3. 运行 `python scripts/execute_oac_operation.py --oac-json '<oql_json>' --message-type '<类型>'` 执行查询（必须填用户指定的message-type）。
4. 返回结果。

## OQL 骨架生成准则 (Skeleton Rules)
你生成的 JSON 必须严格按照以下顶层顺序和格式构建：
1. **基础配置**：顶层包含 `"version": "1.0"`, `"schemaRef": "<具体的本体名>"`, `"strict": true`, `"operation": "QUERY"`。
2. **声明对象 (`objects`)**：声明所有参与查询的对象类型。必须为每个对象分配 `alias`。
3. **过滤条件 (`conditions`)**：使用标准的 AST 逻辑树表达过滤逻辑。
4. **返回投影 (`returns`)**：显式枚举要返回的字段，`kind` 取值必须是 `FIELDS`。

## 关键模块解释

| 模块          | 核心字段        | 作用                                             | 适用操作                                                   |
| ------------- | --------------- |------------------------------------------------| ---------------------------------------------------------- |
| 对象声明模块  | `objects`       | 声明参与本次操作的对象类型与别名                               | QUERY / ASSOCIATION_QUERY                                 |
| 条件模块      | `conditions`    | **采用**递归逻辑树**表达布尔条件。逻辑节点与叶子节点通过 `kind` 显式区分。** | 查询、聚合、关联查询、更新、删除                           |
| 投影模块      | `returns`       | 定义返回字段、分组字段、聚合指标，用于定义查询结果的投影方式，统一采用对象数组，不提供简写                              | `QUERY` / `ASSOCIATION_QUERY` |

## 条件构建规则 (Conditions Builder)
OQL 抛弃了扁平的 WHERE 子句，采用强类型的递归语法树。
- **叶子节点 (`PREDICATE`)**：必须包含 `ref` (指向对象别名), `field` (原生逻辑字段名), `operator` (如 `EQ`, `IN`, `GT`), `values` (必须是数组，且数组中的值必须是**字符串**, 如 `["10"]` 或 `["PBR-BKNG-AN1-ZM3SP"]`)。
  *注意：严禁根据对象名捏造字段前缀。*
- **组合节点 (`GROUP`)**：如果有多个条件，必须用 `GROUP` 包裹。必须包含 `relation` (`AND`/`OR`) 和 `children` (包含多个 PREDICATE 或嵌套 GROUP 的数组)。

## 返回值规则 (Returns Builder)
- `returns` 必须是一个对象数组，指定要获取哪些对象的哪些字段。
- 格式必须为 `{"kind": "FIELDS", "ref": "对象别名", "fields": ["字段1", "字段2"]}`。
- **【强制要求】**如果用户没有指定返回字段，默认返回所有字段 `["*"]`。

## OQL 返回字段类型指定函数 ID / NAME

`id(field)` 与 `name(field)` 是 OQL 在 `returns` 中使用的字段类型指定函数，用于多维模型维度字段的语义标注：

- `id(field)` 表示字段 `field` 是多维模型中的“ID”维度。
- `name(field)` 表示字段 `field` 是多维模型中的“名称”维度。

这两个函数用于返回字段声明，不表示数据库函数调用，不改变字段原始值，也不通过 `returns.kind = EXPR` 表达。

### 识别规则

- 用户表达“ID、标识、编号、编码、主键、唯一标识、id(field)”等语义时，Agent 应生成 `ID(field)` 字段类型指定。
- 用户表达“名称、名字、显示名、中文名、name(field)”等语义时，Agent 应生成 `NAME(field)` 字段类型指定。
- 用户自然语言或伪代码中的 `id()`、`name()` 应规范化为 OQL JSON 中的 `ID(field)`、`NAME(field)`，并写入 `returns[].field`。

### returns 生成格式

`ID` / `NAME` 在 `returns` 中的标准格式如下：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

字段说明：

| 字段 | 必填 | 说明 |
|---|:--:|---|
| `kind` | 是 | 固定为 `FUNCTION`，表示返回字段类型指定函数。 |
| `ref` | 是 | 字段所属对象 alias。 |
| `field` | 是 | 使用 `ID(fieldName)` 或 `NAME(fieldName)` 表示维度语义。 |
| `alias` | 是 | 返回结果别名。ID 维度通常使用原字段名或 `_id` 后缀，名称维度通常使用 `_name` 后缀。 |

### 示例

返回 release_cause 的名称维度：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

返回 release_cause 的 ID 维度：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "ID(release_cause)",
  "alias": "release_cause_id"
}
```

### 生成约束

1. `field` 中只能使用 `ID(<fieldName>)` 或 `NAME(<fieldName>)`。
2. `<fieldName>` 必须是当前 `ref` 对象下的字段名，不得写成关系路径、聚合指标、字面量或嵌套函数。
3. `ID` / `NAME` 只用于 `returns` 字段类型指定，不用于 `conditions`、`orders`、`mutation`。
4. 不要生成旧式 `EXPR + expr.kind = FUNCTION + args` 写法。
5. 不要生成小写函数名：`id`、`name`。
6. 不要把 `ID` / `NAME` 写成 SQL 函数或数据源方言函数。
7. 不要用 `ID` / `NAME` 表达聚合指标；聚合指标必须使用 `returns.kind = METRIC`。

## 额外的硬性规则 (Additional hard rules)
1. 始终完全保留当前处于激活状态的 `schemaRef`。绝不要捏造新的 `schemaRef`。
2. 前置步骤的结果只能用于提取过滤值，绝不能用于定义 OQL 字段名。
3. 必须严格使用 schema 中定义的对象类型；不要捏造未经验证的对象类型。

## 输出约定 (Output contract)
- 仅输出严格规范的 OQL JSON。
- 不要输出 Markdown 格式、解释、注释或散文文本。
- 不要输出 `null`、空对象或空数组。
- 对所有跨块的引用使用 `alias`（别名）。
- 如果缺失关键信息，请输出结构化的错误 JSON，而不是凭空猜测。

### QUERY 完整结构定义模版样例

```json
{
  "version": "1.0",
  "schemaRef": "<本体名字>",
  "strict": true,
  "operation": "QUERY",
  "maxResults": 1000,
  "objects": [
    { "objectType": "<对象类型>", "alias": "<对象类型别名>" }
  ],
  "conditions": {
    "kind": "<`GROUP`或`PREDICATE`>", 
    "children": [
      {
        "kind": "<`GROUP`或`PREDICATE`>",
        "ref": "<必须来自于objects中的alias>",
        "field": "<条件字段名>",
        "operator": "<操作符，详细见操作符定义表格>",
        "values": ["value1", "value2", ...]
      }
    ]
  },
  "returns": [
    { "kind": "FIELDS", "ref": "<对象别名>", "fields": ["*"] }
  ]
}
```

### 操作符定义表格
| 操作符                                     | `values` 取值规则 | 说明                              |
|-----------------------------------------| ----------------- | --------------------------------- |
| `EQ` / `NE`                             | 恰好 1 个值       | 等于 / 不等于                     |
| `GT` / `GTE` / `LT` / `LTE`             | 恰好 1 个值       | 大于 / 大于等于 / 小于 / 小于等于 |
| `IN` / `NOT_IN`                         | 至少 1 个值       | 属于 / 不属于                     |
| `CONTAINS`                              | 恰好 1 个字符串值 | 字符串包含匹配                    |
| `BETWEEN`                               | 恰好 2 个值       | 范围（包含边界），如 `BETWEEN [10, 100]` |
| `STARTS_WITH`                           | 恰好 1 个字符串值 | 前缀匹配                          |
| `ENDS_WITH`                             | 恰好 1 个字符串值 | 后缀匹配                          |
| `IS_NULL`                               | 不允许            | 空值判断                          |
| `IS_NOT_NULL`                           | 不允许            | 非空判断                          |
| `IS_EMPTY`                              | 不允许            | 空字符串判断                      |
| `IS_NOT_EMPTY`                          | 不允许            | 非空字符串判断                    |

### `conditions` 统一条件表达式注意事项
1. `conditions` 统一表达查询筛选、更新目标与删除目标。
2. 其结构为递归逻辑树，而非自由拼装对象。
3. `conditions`中的`values`数组，必须结合上下文已知的真实数据进行显式赋值。

## 示例 

### 示例1：查询所有状态为running的设备

```json
{
  "version": "1.0",
  "schemaRef": "<本体名字>",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "device",
      "alias": "d"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "d",
        "field": "status",
        "operator": "EQ",
        "values": ["running"]
      }
    ]
  },
  "returns": [
    { 
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["*"]
    }
  ],
  "maxResults": 100000
}
```

### 示例2：查询指定站点的所有设备

```json
{
  "version": "1.0",
  "schemaRef": "ams_topology@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [
    {
      "objectType": "device",
      "alias": "d"
    },
    {
      "objectType": "site",
      "alias": "s"
    }
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {
        "kind": "PREDICATE",
        "ref": "s",
        "field": "name",
        "operator": "EQ",
        "values": ["华东站"]
      }
    ]
  },
  "returns": [
    { 
      "kind": "FIELDS",
      "ref": "d",
      "fields": ["*"]
    }
  ],
  "maxResults": 100000
}
```

## 边界
- 本桥接层不展开所有语法细节。
- 本桥接层不把读取类与写入类手册混用。
- 本桥接层不在执行前擅自修补完整请求。

## 校验规则（结构硬约束）
1. `operation` 必须为 `QUERY`。
2. `objects`、`returns` 必填。
3. `relationships` 不得出现。
4. `returns` 只允许 `FIELDS`。
5. 不允许 `EXPR`、`GROUP_BY`、`METRIC`。

## 信息不足时不要猜测
- 用户没有明确查询对象时，不要捏造对象类型。
- 用户没说明返回字段时，默认返回所有字段。
- 用户没说明过滤条件时，可以省略 conditions。

信息不足时应返回结构化错误，至少指出缺少：
- 查询对象类型
- 返回内容
- 过滤条件

生成前必须确认：
- 要查询哪些对象
- 过滤条件落在哪个对象上
- 最终要返回哪些字段

不要这样做：
- 不要生成 `EXPR`、`GROUP_BY`、`METRIC`
- 不要添加 `relationships`
- **不要使用未经验证的字段名**