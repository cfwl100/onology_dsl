# OQL Schema

This directory stores operation-level schema files.

## Schema and example mapping

| Operation | Schema | Example |
| --- | --- | --- |
| `QUERY` | `schemas/oql-query.schema.json` | `examples/query.example.json` |
| `ASSOCIATION_QUERY` | `schemas/oql-association-query.schema.json` | `examples/association-query.example.json` |
| `AGGREGATE` | `schemas/oql-aggregate.schema.json` | `examples/agg.example.json` |

Use `scripts/validate_oql.py` to validate generated OQL JSON or the built-in examples.
