# OQL Schema

This directory stores operation-level schema files.

## Schema and reference mapping

| Operation | Schema | Operation reference |
| --- | --- | --- |
| `QUERY` | `schemas/oql-query.schema.json` | `references/oac-query.md` |
| `ASSOCIATION_QUERY` | `schemas/oql-association-query.schema.json` | `references/oac-association-query.md` |
| `AGGREGATE` | `schemas/oql-aggregate.schema.json` | `references/oac-aggregate.md` |

Use `scripts/validate_oql.py` to validate generated OQL JSON. Operation references already include minimal examples, so agents do not need to read a separate examples directory.

## Shell compatibility

When checking validator usage or running validation, do not assume the terminal is Bash.

Windows PowerShell 5.1 does not support `&&` and `||` as command separators. Use separate lines or `$LASTEXITCODE`.

```powershell
Set-Location "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
python .\scripts\validate_oql.py --help
```

```powershell
Set-Location "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
if (Test-Path ".\scripts\validate_oql.py") {
  python .\scripts\validate_oql.py --help
} else {
  Write-Output "Script not found"
}
```

Bash-only examples may use `&&`, `||` or `printf`, but agents must not emit those forms unless the runtime shell is known to be Bash.
