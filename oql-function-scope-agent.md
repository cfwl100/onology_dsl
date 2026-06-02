# OQL Function Scope for Semantic Data Access

This document supplements the OQL specification for AI Agent generation. OQL is a semantic data access language over ontology objects, relationships, and properties. `FUNCTION` is not a database-function passthrough and must not become a general SQL expression layer.

## 1. Function positioning

`FUNCTION` is allowed only for lightweight semantic expression over object properties:

- property normalization before filtering;
- dynamic values in conditions, such as current time or recent time windows;
- derived return values;
- functional grouping, such as hourly or daily time buckets;
- dynamic mutation values, such as `updatedAt = NOW()`;
- governed domain extension functions, such as normalized cell ID.

`FUNCTION` must not be used to dynamically generate `objectType`, `relationshipType`, `alias`, `ref`, `field`, `metricAlias`, relationship endpoints, or operation names.

## 2. Allowed function positions

| OQL position | Allowed | Purpose | High-frequency functions |
| --- | --- | --- | --- |
| `conditions.left` | Yes | transform a property before comparison | `LENGTH`, `LOWER`, `UPPER`, `TRIM`, `DATE_TRUNC`, `COALESCE` |
| `conditions.values[]` | Yes | dynamic comparison value | `NOW`, `DATE_ADD`, `DATE_SUB` |
| `returns[kind=EXPR].expr` | Yes | derived return value | `ABS`, `ROUND`, `LOWER`, `UPPER`, `TRIM`, `COALESCE`, registered extension functions |
| `returns[kind=GROUP_BY].expr` | Yes | functional grouping / time bucket | `DATE_TRUNC`, `YEAR`, `MONTH`, `DAY`, `HOUR` |
| `mutation.data.properties` | Yes | dynamic create value | `NOW`, registered extension functions |
| `mutation.set` | Yes | dynamic update value | `NOW`, registered extension functions |
| `orders.field` | No | must reference an object field or return alias | N/A |
| `aggregateFilter.metricAlias` | No | must reference a metric alias | N/A |
| `objects.objectType` / `objects.alias` | No | must be static | N/A |
| `relationships.relationshipType` | No | must be static | N/A |
| `relationships.from` / `relationships.to` | No | must reference object aliases | N/A |

## 3. Core built-in function whitelist

The core built-in functions should be high-frequency, low-ambiguity, portable, and easy to validate.

| Type | Core functions | Purpose |
| --- | --- | --- |
| Numeric | `ABS`, `ROUND` | numeric normalization and metric display precision |
| String | `LENGTH`, `LOWER`, `UPPER`, `TRIM`, `SUBSTRING` | text length filtering, case normalization, trimming, code segment extraction |
| Time | `NOW`, `DATE_TRUNC`, `YEAR`, `MONTH`, `DAY`, `HOUR`, `MINUTE`, `DATE_ADD`, `DATE_SUB`, `DATEDIFF` | current time, time windows, time buckets, date difference |
| Null handling | `COALESCE`, `IFNULL` | null fallback and value normalization |

The following functions are not core built-ins. They may be supported only through the OAC function registry when needed:

```text
CEIL
FLOOR
CONCAT
SECOND
DATE_FORMAT
REPLACE
LPAD
RPAD
IF
TO_STRING
TO_NUMBER
TO_DATE
TO_DATETIME
```

The following function types should not be supported by OQL:

```text
database dialect functions
window functions
script functions
ungoverned UDFs
random functions
system environment functions
relationship traversal functions
aggregate functions as FUNCTION
```

Aggregate functions must use `returns.kind = "METRIC"`, not `kind = "FUNCTION"`.

## 4. Function expression syntax

### 4.1 Field expression

```json
{
  "kind": "FIELD",
  "ref": "o",
  "field": "amount"
}
```

### 4.2 Value expression

```json
{
  "kind": "VALUE",
  "value": 100
}
```

For time intervals, use ISO-8601 duration strings:

```json
{
  "kind": "VALUE",
  "value": "P7D"
}
```

Examples:

- `P7D`: 7 days;
- `PT1H`: 1 hour;
- `PT30M`: 30 minutes.

### 4.3 Core function expression

```json
{
  "kind": "FUNCTION",
  "name": "ABS",
  "args": [
    {
      "kind": "FIELD",
      "ref": "o",
      "field": "deltaAmount"
    }
  ]
}
```

### 4.4 Extension function expression

```json
{
  "kind": "FUNCTION",
  "namespace": "domain",
  "name": "NORMALIZE_CELL_ID",
  "args": [
    {
      "kind": "FIELD",
      "ref": "c",
      "field": "cellId"
    }
  ]
}
```

Syntax rules:

1. Core built-in functions omit `namespace`.
2. Extension functions must include `namespace`.
3. Function names should be uppercase.
4. `args` must contain valid expressions or literal values.
5. Do not encode a function call as a string, such as `"DATE_SUB(NOW(), 7 DAY)"`.
6. Do not put functions in `ref`, `field`, `alias`, or `metricAlias`.

## 5. Unambiguous examples

### 5.1 Function in `conditions.left`

Business meaning: query orders whose comment length is greater than 100.

```json
{
  "conditions": {
    "kind": "PREDICATE",
    "left": {
      "kind": "FUNCTION",
      "name": "LENGTH",
      "args": [
        {
          "kind": "FIELD",
          "ref": "o",
          "field": "comment"
        }
      ]
    },
    "operator": "GT",
    "values": [100]
  }
}
```

### 5.2 Function in `conditions.values[]`

Business meaning: query CellKpi records from the last 7 days.

```json
{
  "conditions": {
    "kind": "PREDICATE",
    "ref": "ck",
    "field": "collectTime",
    "operator": "GTE",
    "values": [
      {
        "kind": "FUNCTION",
        "name": "DATE_SUB",
        "args": [
          {
            "kind": "FUNCTION",
            "name": "NOW",
            "args": []
          },
          {
            "kind": "VALUE",
            "value": "P7D"
          }
        ]
      }
    ]
  }
}
```

### 5.3 Function in return expression

Business meaning: return absolute order amount difference.

```json
{
  "returns": [
    {
      "kind": "EXPR",
      "expr": {
        "kind": "FUNCTION",
        "name": "ABS",
        "args": [
          {
            "kind": "FIELD",
            "ref": "o",
            "field": "deltaAmount"
          }
        ]
      },
      "alias": "absDeltaAmount"
    }
  ]
}
```

### 5.4 Function in group-by expression

Business meaning: calculate average PRB usage by hour and cell.

```json
{
  "operation": "AGGREGATE",
  "objects": [
    {
      "objectType": "CellKpi",
      "alias": "ck"
    }
  ],
  "returns": [
    {
      "kind": "GROUP_BY",
      "expr": {
        "kind": "FUNCTION",
        "name": "DATE_TRUNC",
        "args": [
          {
            "kind": "VALUE",
            "value": "hour"
          },
          {
            "kind": "FIELD",
            "ref": "ck",
            "field": "collectTime"
          }
        ]
      },
      "alias": "collectHour"
    },
    {
      "kind": "GROUP_BY",
      "ref": "ck",
      "field": "cellId",
      "alias": "cellId"
    },
    {
      "kind": "METRIC",
      "function": "AVG",
      "ref": "ck",
      "field": "prbUsage",
      "alias": "avgPrbUsage"
    }
  ]
}
```

### 5.5 Function in mutation value

Business meaning: update object timestamp to current time.

```json
{
  "mutation": {
    "scope": "ONE",
    "set": {
      "updatedAt": {
        "kind": "FUNCTION",
        "name": "NOW",
        "args": []
      }
    }
  }
}
```

### 5.6 Registered extension function

Business meaning: return a normalized Cell ID.

```json
{
  "returns": [
    {
      "kind": "EXPR",
      "expr": {
        "kind": "FUNCTION",
        "namespace": "domain",
        "name": "NORMALIZE_CELL_ID",
        "args": [
          {
            "kind": "FIELD",
            "ref": "c",
            "field": "cellId"
          }
        ]
      },
      "alias": "normalizedCellId"
    }
  ]
}
```

## 6. Aggregate filter boundary

`conditions` filters object instances or detail records before aggregation. `aggregateFilter` filters metric aliases after aggregation.

Correct:

```json
{
  "aggregateFilter": {
    "kind": "METRIC_PREDICATE",
    "metricAlias": "avgPrbUsage",
    "operator": "GT",
    "values": [80]
  }
}
```

Wrong:

```json
{
  "conditions": {
    "kind": "PREDICATE",
    "ref": "ck",
    "field": "avgPrbUsage",
    "operator": "GT",
    "values": [80]
  }
}
```

Reason: `avgPrbUsage` is a metric alias generated after aggregation, so it must not appear in `conditions`.

## 7. Extension function registry

OAC may expose extension functions through a registry. Extension functions must be registered before Agent use.

Recommended registry fields:

| Field | Meaning |
| --- | --- |
| `namespace` | Function namespace, such as `domain`, `custom`, or `vendor` |
| `name` | Function name |
| `description` | Semantic description |
| `args` | Argument count, type, and nullability |
| `returnType` | Return type |
| `deterministic` | Whether the function is deterministic |
| `allowedIn` | Allowed positions, such as `conditions.left`, `returns.expr`, `returns.groupByExpr`, `mutation.set` |
| `nullPolicy` | Null handling policy |
| `pushdownMappings` | Optional datasource pushdown mappings |
| `fallback` | Whether OAC execution fallback is allowed |
| `owner` | Function owner |
| `version` | Function version |

Registry example:

```json
{
  "namespace": "domain",
  "name": "NORMALIZE_CELL_ID",
  "description": "Normalize telecom cell identifier format.",
  "args": [
    {
      "name": "cellId",
      "type": "string",
      "nullable": false
    }
  ],
  "returnType": "string",
  "deterministic": true,
  "allowedIn": [
    "conditions.left",
    "returns.expr"
  ],
  "nullPolicy": "RETURN_NULL_IF_ANY_ARG_NULL",
  "pushdownMappings": {
    "mysql": "NORMALIZE_CELL_ID({0})",
    "clickhouse": "normalizeCellId({0})"
  },
  "fallback": "OAC_EXECUTION",
  "owner": "telecom-domain-team",
  "version": "1.0"
}
```

## 8. Agent generation rules

1. Prefer object, relationship, and property semantics before using functions.
2. Use functions only in explicitly allowed positions.
3. Use only core built-ins or registered extension functions.
4. Do not generate unregistered extension functions.
5. Do not generate datasource dialect functions.
6. Do not encode function calls as strings.
7. Do not place metric aliases in `conditions`.
8. Do not express aggregate functions as `FUNCTION`; use `METRIC` instead.
9. For high-frequency time windows, use `DATE_SUB(NOW(), "P7D")` style structured expressions.
10. For time-bucket aggregation, use `GROUP_BY.expr` with `DATE_TRUNC`.
