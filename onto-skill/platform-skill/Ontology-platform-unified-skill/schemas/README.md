# OQL Schema

This directory stores operation-level schema files.

## Schema and reference mapping

| Operation | Schema | Operation reference |
| --- | --- | --- |
| `QUERY` | `schemas/oql-query.schema.json` | `references/oac-query.md` |
| `ASSOCIATION_QUERY` | `schemas/oql-association-query.schema.json` | `references/oac-association-query.md` |
| `AGGREGATE` | `schemas/oql-aggregate.schema.json` | `references/oac-aggregate.md` |

Use `scripts/validate_oql.py` to validate generated OQL JSON. Operation references already include minimal examples, so agents do not need to read a separate examples directory.

## Return wildcard rule

- `returns.kind=FIELDS.fields` supports `["*"]` in `QUERY` and `ASSOCIATION_QUERY` schemas.
- `["*"]` means return all fields of the referenced object or relationship alias.
- Relationship aliases are valid `ref` values in `ASSOCIATION_QUERY` returns, for example `{ "kind": "FIELDS", "ref": "r2", "fields": ["*"] }`.
- `*` is only valid in `returns.kind=FIELDS.fields[]`.
- Conditions, orders, FIELD expressions, GROUP_BY fields, and non-COUNT aggregate metric fields must not use `*`.

## Input mode preference

- Complex or long OQL JSON should be serialized to a UTF-8 JSON file and validated with `--input <json-file>`.
- Short compact JSON may use `--oac-json`, but only when the current shell quoting rules are known to be safe.
- If JSON parsing fails after passing a shell variable to `--oac-json`, switch to `--input <json-file>` and reuse the same file for validation and execution.

## Shell compatibility

When checking validator usage or running validation, do not assume the terminal is Bash, CMD, or PowerShell. Choose the command style according to the actual shell, but default to step-by-step commands.

| Environment | Path style | Default command style |
| --- | --- | --- |
| Windows PowerShell / PowerShell 7+ | `C:\...` or `.\scripts\...` | Use separate lines or absolute script paths. Do not use Bash-style chaining by default. |
| Windows CMD | `C:\...` or `scripts\...` | Use separate lines or absolute script paths unless the user explicitly requests CMD chaining. |
| Bash / zsh / Linux / macOS / WSL / Git Bash | `/path/...` or `scripts/...` | Use separate lines or absolute script paths unless the user explicitly requests POSIX chaining. |
| Unknown shell | Unknown | Do not emit chained commands, pipes, or shell-specific variables. |

Minimal cross-platform-safe instruction:

```text
python <Ontology-platform-unified-skill目录>/scripts/validate_oql.py --input <json-file>
```

Shell-specific examples belong in `references/oac-data-access.md`. This README only defines the compatibility rule.
