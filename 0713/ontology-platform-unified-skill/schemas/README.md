# OQL Schema

| 操作 | Schema | 操作手册 |
|---|---|---|
| `QUERY` | `oql-query.schema.json` | `references/oac-query.md` |
| `ASSOCIATION_QUERY` | `oql-association-query.schema.json` | `references/oac-association-query.md` |
| `AGGREGATE` | `oql-aggregate.schema.json` | `references/oac-aggregate.md` |

用 `scripts/validate_oql.py` 校验生成的 OQL JSON；手册内已含最小示例。

## 通配符
- `returns.kind=FIELDS.fields` 支持 `["*"]`（返回该 ref 全部字段），仅此处允许；条件/排序/表达式/GROUP_BY/非 COUNT 聚合字段禁用。
- 关系 alias 可作 `ref`：`{ "kind":"FIELDS","ref":"r2","fields":["*"] }`。

## 输入与命令
- 复杂/长 OQL 用 `json.dumps(ensure_ascii=False)` 写 UTF-8 文件，`validate_oql.py --input <file>`；短 JSON 且 Shell 引号安全才用 `--oac-json`，解析报错改用 `--input` 复用同一文件。
- 默认逐行命令 + 绝对脚本路径，禁用 `&&`/`||`/管道/Shell 专属变量。各 Shell 路径示例见 `references/oac-data-access.md`。
