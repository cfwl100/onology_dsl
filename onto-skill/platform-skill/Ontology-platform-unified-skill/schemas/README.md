# OQL Schema

This directory stores operation-level schema files.

## Schema and reference mapping

| Operation | Schema | Operation reference |
| --- | --- | --- |
| `QUERY` | `schemas/oql-query.schema.json` | `references/oac-query.md` |
| `ASSOCIATION_QUERY` | `schemas/oql-association-query.schema.json` | `references/oac-association-query.md` |
| `AGGREGATE` | `schemas/oql-aggregate.schema.json` | `references/oac-aggregate.md` |

Use `scripts/validate_oql.py` to validate generated OQL JSON. Operation references already include minimal examples, so agents do not need to read a separate examples directory.

## Input mode preference

- Complex or long OQL JSON should be serialized to a UTF-8 JSON file and validated with `--input <json-file>`.
- Short compact JSON may use `--oac-json`, but only when the current shell quoting rules are known to be safe.
- If JSON parsing fails after passing a shell variable to `--oac-json`, switch to `--input <json-file>` and reuse the same file for validation and execution.

## Shell compatibility

When checking validator usage or running validation, do not assume the terminal is Bash or PowerShell. Choose the command style according to the actual shell.

| Environment | Directory change | Script path style | Notes |
| --- | --- | --- | --- |
| Windows PowerShell | `Set-Location "C:\\path"` | `.\scripts\validate_oql.py` | Use separate lines or `$LASTEXITCODE` for status checks. Prefer `--input` for complex JSON. |
| Windows CMD | `cd /d "C:\\path"` | `scripts\validate_oql.py` | `&&` and `||` are CMD separators. Prefer `--input` for complex JSON. |
| Bash / zsh / Linux / macOS / WSL / Git Bash | `cd "/path"` | `scripts/validate_oql.py` | Pipes and POSIX separators are allowed. `--input` is still preferred for long JSON. |
| Unknown shell | Plain step-by-step text | Avoid shell-specific syntax | Do not emit `&&`, `||`, pipes, or shell-specific variables. Use `--input`. |

Minimal cross-platform-safe instruction:

```text
Enter the Ontology-platform-unified-skill directory.
Run: python scripts/validate_oql.py --input <json-file>
```

Shell-specific examples belong in `references/oac-data-access.md`. This README only defines the compatibility rule.
