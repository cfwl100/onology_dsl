# OQL v1.2 ID / NAME 返回字段类型指定函数修订

本文是对《本体对象操作语言（OQL）DSL 规范 v1.2-agent 最终版》中 `ID` / `NAME` 函数表达方式的修订说明。

## 1. 修订目标

新增 `id(field)` 与 `name(field)` 函数，作为 `returns` 中的字段类型指定，用于多维模型维度字段语义标注：

- `id(field)` 表示字段 `field` 是多维模型中的“ID”维度。
- `name(field)` 表示字段 `field` 是多维模型中的“名称”维度。

该函数只用于返回字段类型指定，不表示数据库函数调用，不改变字段原始值。

## 2. 标准 returns 格式

`id(field)` / `name(field)` 在 OQL JSON 中统一规范化为大写 `ID(field)` / `NAME(field)`，并写入 `returns[].field`。

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
| `field` | 是 | 使用 `ID(fieldName)` 或 `NAME(fieldName)` 表示多维模型维度语义。 |
| `alias` | 是 | 返回结果别名。名称维度建议使用 `_name` 后缀，ID 维度建议使用 `_id` 后缀或保留原字段名。 |

## 3. 示例

### 3.1 返回名称维度

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "NAME(release_cause)",
  "alias": "release_cause_name"
}
```

### 3.2 返回 ID 维度

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "ID(release_cause)",
  "alias": "release_cause_id"
}
```

## 4. 生成规则

1. 用户表达“ID、标识、编号、编码、主键、唯一标识、id(field)”时，生成 `ID(field)`。
2. 用户表达“名称、名字、显示名、中文名、name(field)”时，生成 `NAME(field)`。
3. 用户自然语言或伪代码中的小写 `id()` / `name()`，生成 OQL 时统一规范化为大写 `ID()` / `NAME()`。
4. `ID()` / `NAME()` 只出现在 `returns[].field` 中。
5. `<fieldName>` 必须是当前 `ref` 对象下的字段名。
6. `alias` 必须显式填写。

## 5. 禁止写法

不得继续使用旧的 `EXPR + expr.kind = FUNCTION + args` 写法表达 `ID` / `NAME`。

错误示例：

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "name": "NAME",
    "args": [
      {
        "kind": "FIELD",
        "ref": "o",
        "field": "release_cause"
      }
    ]
  },
  "alias": "release_cause_name"
}
```

原因：`ID` / `NAME` 本次修订后不是表达式函数，而是 `returns` 中的字段类型指定函数。

不得生成以下写法：

```json
{
  "kind": "FUNCTION",
  "ref": "o",
  "field": "name(release_cause)",
  "alias": "release_cause_name"
}
```

原因：函数名必须规范化为大写 `NAME`。

## 6. 与聚合和条件的关系

- `ID` / `NAME` 不用于 `conditions`。
- `ID` / `NAME` 不用于 `orders`。
- `ID` / `NAME` 不用于 `mutation`。
- `ID` / `NAME` 不表达聚合指标；聚合指标仍使用 `returns.kind = "METRIC"`。

## 7. 对原规范的覆盖说明

若原《本体对象操作语言（OQL）DSL 规范 v1.2-agent 最终版》中存在 `ID` / `NAME` 使用 `returns.kind = "EXPR"`、`expr.kind = "FUNCTION"`、`args` 的描述，应以本修订文件为准。
