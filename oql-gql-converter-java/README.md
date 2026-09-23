# OQL GQL-like Profile Java Converter

This module provides a small Java converter from the GQL-like OQL Profile surface syntax to Canonical JSON OQL.

It implements the conservative subset documented in `../oql-gql-profile-spec.md`:

- `MATCH`
- `WHERE`
- `RETURN`
- `GROUP BY`
- `AGGREGATE FILTER`
- `ORDER BY`
- `LIMIT`
- `OFFSET`

The converter is intentionally not a full GQL/Cypher parser. Unsupported or ambiguous constructs fail fast.

## Design goals

- Let AI agents generate concise, human-readable GQL-like OQL.
- Normalize the surface syntax into the existing Canonical JSON OQL.
- Keep OAC execution based on structured JSON IR rather than free-form query text.
- Prevent unsafe constructs such as `RETURN *`, unbounded path traversal, and database dialect functions.

## License-friendly dependencies

The module uses:

- Jackson Databind, Apache License 2.0
- JUnit 5, Eclipse Public License 2.0 for tests

No GPL dependency is introduced.

## Build and test

```bash
cd oql-gql-converter-java
mvn test
```

## CLI usage

```bash
cat <<'OQL' | mvn -q exec:java -Dexec.args="telecom-v1"
MATCH (a:Alarm)-[r:happenOn]->(ne:Ne)
WHERE a.alarmName LIKE "LinkDown"
RETURN ne.neId AS neId, ne.name AS name
LIMIT 1000
OQL
```

Output:

```json
{
  "version" : "2.0",
  "schemaRef" : "telecom-v1",
  "strict" : true,
  "operation" : "ASSOCIATION_QUERY",
  "objects" : [ ... ]
}
```

## Java API

```java
GqlLikeOqlConverter converter = new GqlLikeOqlConverter();
GqlLikeOqlConverter.ConverterOptions options =
    GqlLikeOqlConverter.ConverterOptions.defaults().withSchemaRef("telecom-v1");

String json = converter.convertToJson("""
    MATCH (a:Alarm)-[r:happenOn]->(ne:Ne)
    WHERE a.alarmName LIKE "LinkDown"
    RETURN ne.neId AS neId, ne.name AS name
    LIMIT 1000
    """, options);
```

## Current capabilities

### Object query

```text
MATCH (o:Order)
WHERE o.status == "completed"
RETURN o.id AS id, o.orderNo AS orderNo, o.amount AS amount
ORDER BY o.createdAt DESC
LIMIT 1000
```

### Association query

```text
MATCH (a:Alarm)-[r:happenOn]->(ne:Ne)
WHERE a.alarmName LIKE "LinkDown"
RETURN ne.neId AS neId, ne.name AS name
LIMIT 1000
```

### Aggregate query

```text
MATCH (ck:CellKpi)
WHERE ck.collectTime >= DATE_SUB(NOW(), "PT1H")
RETURN ck.cellId AS cellId, AVG(ck.prbUsage) AS avgPrbUsage, COUNT(*) AS sampleCount
GROUP BY ck.cellId
AGGREGATE FILTER avgPrbUsage > 80 AND sampleCount >= 100
ORDER BY avgPrbUsage DESC
LIMIT 1000
```

### Function group-by

```text
MATCH (ck:CellKpi)
WHERE ck.collectTime >= DATE_SUB(NOW(), "P1D")
RETURN DATE_TRUNC("hour", ck.collectTime) AS collectHour, ck.cellId AS cellId, AVG(ck.prbUsage) AS avgPrbUsage
GROUP BY DATE_TRUNC("hour", ck.collectTime) AS collectHour, ck.cellId
ORDER BY collectHour ASC
LIMIT 1000
```

## Limitations

The first implementation is intentionally small and deterministic.

Not supported yet:

- `CREATE` / `UPDATE` / `DELETE` / `UPSERT`
- `OPTIONAL MATCH`
- `WITH`
- `UNION`
- arbitrary variable-length paths such as `[:trigger*]`
- database dialect functions
- full schema binding against ontology metadata
- physical query generation

Schema binding should be handled by a later semantic binder that validates object types, relationship types, properties, and functions against the ontology registry.
