# OQL Examples

本目录保存 OQL 三类查询操作的最小可校验示例。

| Operation | Example | Schema | Reference |
| --- | --- | --- | --- |
| `QUERY` | `query.example.json` | `../schemas/oql-query.schema.json` | `../references/oac-query.md` |
| `ASSOCIATION_QUERY` | `association-query.example.json` | `../schemas/oql-association-query.schema.json` | `../references/oac-association-query.md` |
| `AGGREGATE` | `agg.example.json` | `../schemas/oql-aggregate.schema.json` | `../references/oac-aggregate.md` |

使用方式：

1. Agent 先根据用户意图选择 operation。
2. 进入对应 reference 文件读取生成规则。
3. 读取对应 example 文件作为最小结构样例。
4. 生成 OQL JSON 后交给 `../scripts/validate_oql.py` 做结构和语义校验。

示例文件只表达最小结构，不绑定真实业务 schema。实际生成时，必须用当前业务本体中的对象、关系和字段替换示例占位内容。
