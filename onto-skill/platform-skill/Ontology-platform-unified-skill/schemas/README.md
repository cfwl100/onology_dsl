# OQL JSON Schema（Draft-07）

本目录提供面向 Agent / 大模型生成 OQL JSON 的结构约束，遵循 JSON Schema draft-07。

## 文件说明

| 文件 | 说明 |
|---|---|
| `oql-query-association-aggregate.schema.json` | QUERY、ASSOCIATION_QUERY、AGGREGATE 三类查询操作的统一 schema。顶层 `oneOf` 自动按 `operation` 匹配；也可以直接引用 `#/definitions/queryOperation`、`#/definitions/associationQueryOperation`、`#/definitions/aggregateOperation`。 |

## 使用建议

1. Agent 生成 OQL 前，先根据用户意图选择唯一 operation。
2. QUERY 使用 `#/definitions/queryOperation`。
3. ASSOCIATION_QUERY 使用 `#/definitions/associationQueryOperation`。
4. AGGREGATE 使用 `#/definitions/aggregateOperation`。
5. 生成 JSON 时必须省略未使用字段，不输出 `null`、空对象或空数组。

## 需要继续由 OAC 语义校验补充的规则

JSON Schema 负责结构校验；以下规则仍需要 OAC validator 或执行前语义校验补充：

- `objects[].alias`、`relationships[].alias` 的全局唯一性；
- `ref`、`from`、`to`、`metricAlias` 是否引用已声明 alias；
- 对象、关系、字段是否存在于绑定 schema；
- 扩展函数是否已在 OAC 函数注册表注册；
- `aggregateFilter.metricAlias` 是否引用 `returns.kind = "METRIC"` 的 alias。

## 校验示例

```bash
python - <<'PY'
import json
from jsonschema import Draft7Validator

schema = json.load(open('schemas/oql-query-association-aggregate.schema.json', encoding='utf-8'))
oql = {
  'version': '2.0',
  'schemaRef': 'sales-v1',
  'strict': True,
  'operation': 'QUERY',
  'objects': [{'objectType': 'Order', 'alias': 'o'}],
  'returns': [{'kind': 'FIELDS', 'ref': 'o', 'fields': ['id', 'orderNo']}]
}
Draft7Validator.check_schema(schema)
Draft7Validator(schema).validate(oql)
print('ok')
PY
```
