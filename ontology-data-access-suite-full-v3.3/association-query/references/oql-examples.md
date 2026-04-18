# OQL 模板与样例

## 多跳路径查询

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "device", "alias": "d"},
    {"objectType": "server", "alias": "s"},
    {"objectType": "datacenter", "alias": "dc"}
  ],
  "relationships": [
    {"relationshipType": "installed_on", "alias": "r1", "from": "d", "to": "s"},
    {"relationshipType": "deployed_in", "alias": "r2", "from": "s", "to": "dc"}
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {"kind": "PREDICATE", "ref": "d", "field": "status", "operator": "EQ", "values": ["running"]},
      {"kind": "PREDICATE", "ref": "dc", "field": "region", "operator": "EQ", "values": ["华东"]}
    ]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "d", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "dc", "fields": ["id", "region"]}
  ],
  "maxResults": 1000
}
```

## 单跳但按 profile 仍走 ASSOCIATION_QUERY

```json
{
  "version": "1.0",
  "schemaRef": "ams_topology@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "employee", "alias": "e"},
    {"objectType": "department", "alias": "d"}
  ],
  "relationships": [
    {"relationshipType": "works_in", "alias": "r", "from": "e", "to": "d"}
  ],
  "conditions": {"kind": "PREDICATE", "ref": "d", "field": "name", "operator": "EQ", "values": ["研发部"]},
  "returns": [
    {"kind": "FIELDS", "ref": "e", "fields": ["*"]},
    {"kind": "FIELDS", "ref": "d", "fields": ["*"]}
  ],
  "orders": [
    {"ref": "e", "field": "employeeNo", "direction": "ASC"}
  ],
  "maxResults": 100000,
  "extensions": {
    "profile": {
      "name": "ams_topology_association",
      "singleHopUsesAssociation": true,
      "allowWildcardFieldsInAssociation": true,
      "stringifyConditionValues": true,
      "requireLowerCaseTypes": true,
      "defaultMaxResults": 20
    }
  }
}
```
