# OQL 关键模板与样例

本文件提供最常用的操作模板与样例。优先套用与当前意图最接近的模板，再填充具体对象、字段与条件。

## QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "QUERY",
  "objects": [{"objectType": "X", "alias": "x"}],
  "conditions": {"...": "..."},
  "returns": [{"kind": "FIELDS", "ref": "x", "fields": ["id", "name"]}],
  "orders": [{"ref": "x", "field": "createdAt", "direction": "DESC"}],
  "maxResults": 1000
}
```

## AGGREGATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "AGGREGATE",
  "objects": [{"objectType": "X", "alias": "x"}],
  "conditions": {"...": "..."},
  "returns": [
    {"kind": "GROUP_BY", "ref": "x", "field": "category", "alias": "category"},
    {"kind": "METRIC", "ref": "x", "field": "amount", "function": "SUM", "alias": "totalAmount"}
  ],
  "orders": [{"ref": "x", "field": "totalAmount", "direction": "DESC"}],
  "maxResults": 1000
}
```

## ASSOCIATION_QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "A", "alias": "a"},
    {"objectType": "B", "alias": "b"}
  ],
  "relationships": [
    {"relationshipType": "rel_ab", "alias": "r1", "from": "a", "to": "b"}
  ],
  "conditions": {"...": "..."},
  "returns": [
    {"kind": "FIELDS", "ref": "a", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "b", "fields": ["id", "name"]}
  ],
  "maxResults": 1000
}
```

## LINK_QUERY 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "LINK_QUERY",
  "objects": [
    {"objectType": "A", "alias": "a"},
    {"objectType": "B", "alias": "b"}
  ],
  "conditions": {"...": "..."},
  "returns": [{"kind": "FIELDS", "ref": "b", "fields": ["id", "name"]}],
  "linkQuery": {
    "mode": "LIST",
    "relationshipType": "rel_ab",
    "sourceRef": "a",
    "targetRef": "b",
    "direction": "OUTBOUND"
  },
  "maxResults": 1000
}
```

## CREATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "CREATE",
  "objects": [{"objectType": "X", "alias": "x"}],
  "mutation": {
    "data": {
      "properties": {
        "name": "value"
      }
    }
  }
}
```

## UPDATE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPDATE",
  "objects": [{"objectType": "X", "alias": "x"}],
  "conditions": {"...": "..."},
  "mutation": {
    "scope": "ONE",
    "set": {
      "name": "newValue"
    }
  }
}
```

## DELETE 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "DELETE",
  "objects": [{"objectType": "X", "alias": "x"}],
  "conditions": {"...": "..."},
  "mutation": {
    "scope": "ONE"
  }
}
```

## UPSERT 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "UPSERT",
  "objects": [{"objectType": "X", "alias": "x"}],
  "mutation": {
    "matchBy": ["key1", "key2"],
    "data": {
      "properties": {
        "key1": "v1",
        "key2": "v2",
        "name": "value"
      }
    }
  }
}
```

## BATCH 模板

```json
{
  "version": "1.0",
  "schemaRef": "<SCHEMA_REF>",
  "strict": true,
  "operation": "BATCH",
  "mutation": {
    "atomic": true,
    "items": [
      {
        "operation": "UPDATE",
        "objects": [{"objectType": "X", "alias": "x"}],
        "conditions": {"...": "..."},
        "mutation": {
          "scope": "ONE",
          "set": {"status": "done"}
        }
      }
    ]
  }
}
```

## `sourceQuery` 示例

```json
{
  "version": "1.0",
  "schemaRef": "sales@1.0",
  "strict": true,
  "operation": "QUERY",
  "objects": [{"objectType": "CompletedOrder", "alias": "co", "fromSource": "completed_orders"}],
  "sourceQuery": [
    {
      "outputAs": "completed_orders",
      "operation": "QUERY",
      "objects": [{"objectType": "Order", "alias": "o"}],
      "conditions": {
        "kind": "PREDICATE",
        "ref": "o",
        "field": "status",
        "operator": "EQ",
        "values": ["completed"]
      },
      "returns": [{"kind": "FIELDS", "ref": "o", "fields": ["id", "customerId", "region", "amount"]}],
      "maxResults": 5000
    }
  ],
  "returns": [{"kind": "FIELDS", "ref": "co", "fields": ["id", "customerId", "region", "amount"]}],
  "orders": [{"ref": "co", "field": "amount", "direction": "DESC"}],
  "maxResults": 1000
}
```
