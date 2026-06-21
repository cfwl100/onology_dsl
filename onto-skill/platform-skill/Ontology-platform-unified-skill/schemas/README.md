# OQL Schema

This directory stores operation-level schema files.

## Schema and reference mapping

| Operation | Schema | Operation reference |
| --- | --- | --- |
| `QUERY` | `schemas/oql-query.schema.json` | `references/oac-query.md` |
| `ASSOCIATION_QUERY` | `schemas/oql-association-query.schema.json` | `references/oac-association-query.md` |
| `AGGREGATE` | `schemas/oql-aggregate.schema.json` | `references/oac-aggregate.md` |

Use `scripts/validate_oql.py` to validate generated OQL JSON. Operation references already include minimal examples, so agents do not need to read a separate examples directory.