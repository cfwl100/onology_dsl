# OQL 模板与样例

> 说明：以下样例聚焦 `ASSOCIATION_QUERY` 的路径构建、条件过滤与常见误用。每个样例都附带“常见错误点”，便于在开发和联调时快速排查。

---

## 样例 1：2 跳路径（设备 -> 服务器 -> 机房）

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

**常见错误点**
- 将 `relationships` 写成 `d -> dc` 直接连接，跳过 `s`，导致路径不可达。
- `conditions.ref` 误写成 `r1`（关系别名）却过滤对象字段（如 `status`）。

---

## 样例 2：2 跳路径（员工 -> 部门 -> 园区）

```json
{
  "version": "1.0",
  "schemaRef": "corp@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "employee", "alias": "e"},
    {"objectType": "department", "alias": "dep"},
    {"objectType": "campus", "alias": "c"}
  ],
  "relationships": [
    {"relationshipType": "works_in", "alias": "r_work", "from": "e", "to": "dep"},
    {"relationshipType": "located_at", "alias": "r_loc", "from": "dep", "to": "c"}
  ],
  "conditions": {
    "kind": "PREDICATE",
    "ref": "c",
    "field": "city",
    "operator": "EQ",
    "values": ["杭州"]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "e", "fields": ["id", "name", "employeeNo"]},
    {"kind": "FIELDS", "ref": "c", "fields": ["id", "city"]}
  ]
}
```

**常见错误点**
- `relationships` 的 `from/to` 方向写反，导致查询结果为空。
- `returns.ref` 使用了不存在的 alias（如 `dept` 而非 `dep`）。

---

## 样例 3：3 跳路径（用户 -> 角色 -> 应用 -> 环境）

```json
{
  "version": "1.0",
  "schemaRef": "iam@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "user", "alias": "u"},
    {"objectType": "role", "alias": "r"},
    {"objectType": "application", "alias": "app"},
    {"objectType": "environment", "alias": "env"}
  ],
  "relationships": [
    {"relationshipType": "assigned_role", "alias": "ur", "from": "u", "to": "r"},
    {"relationshipType": "role_grants_app", "alias": "ra", "from": "r", "to": "app"},
    {"relationshipType": "app_deployed_env", "alias": "ae", "from": "app", "to": "env"}
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {"kind": "PREDICATE", "ref": "u", "field": "status", "operator": "EQ", "values": ["active"]},
      {"kind": "PREDICATE", "ref": "env", "field": "tier", "operator": "IN", "values": ["prod", "staging"]}
    ]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "u", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "app", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "env", "fields": ["id", "tier"]}
  ],
  "maxResults": 500
}
```

**常见错误点**
- 3 跳时漏写中间一段 relationship（如缺 `ra`），导致链路断开。
- 将 `IN` 的 `values` 误写成字符串而非数组。

---

## 样例 4：3 跳路径 + relationship alias 条件过滤（带关系属性）

```json
{
  "version": "1.0",
  "schemaRef": "supply@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "supplier", "alias": "sup"},
    {"objectType": "contract", "alias": "ct"},
    {"objectType": "project", "alias": "p"},
    {"objectType": "company", "alias": "co"}
  ],
  "relationships": [
    {"relationshipType": "signed_contract", "alias": "r_sc", "from": "sup", "to": "ct"},
    {"relationshipType": "contract_for_project", "alias": "r_cp", "from": "ct", "to": "p"},
    {"relationshipType": "project_owned_by", "alias": "r_po", "from": "p", "to": "co"}
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {"kind": "PREDICATE", "ref": "r_sc", "field": "effectiveStatus", "operator": "EQ", "values": ["valid"]},
      {"kind": "PREDICATE", "ref": "r_cp", "field": "budgetShare", "operator": "GT", "values": [0.3]},
      {"kind": "PREDICATE", "ref": "co", "field": "country", "operator": "EQ", "values": ["CN"]}
    ]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "sup", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "p", "fields": ["id", "name"]}
  ]
}
```

**常见错误点**
- 忘记给 relationship 配置 `alias`，后续无法按 `ref: "r_sc"` 过滤。
- 关系字段（如 `effectiveStatus`）误写到对象 alias（如 `sup`）上过滤。

---

## 样例 5：4 跳路径（主机 -> 集群 -> 业务 -> 系统 -> 区域）

```json
{
  "version": "1.0",
  "schemaRef": "ops@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "host", "alias": "h"},
    {"objectType": "cluster", "alias": "cl"},
    {"objectType": "service", "alias": "svc"},
    {"objectType": "system", "alias": "sys"},
    {"objectType": "region", "alias": "rg"}
  ],
  "relationships": [
    {"relationshipType": "host_in_cluster", "alias": "r1", "from": "h", "to": "cl"},
    {"relationshipType": "cluster_runs_service", "alias": "r2", "from": "cl", "to": "svc"},
    {"relationshipType": "service_belongs_system", "alias": "r3", "from": "svc", "to": "sys"},
    {"relationshipType": "system_in_region", "alias": "r4", "from": "sys", "to": "rg"}
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {"kind": "PREDICATE", "ref": "h", "field": "osType", "operator": "EQ", "values": ["linux"]},
      {"kind": "PREDICATE", "ref": "rg", "field": "code", "operator": "EQ", "values": ["cn-east-1"]}
    ]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "h", "fields": ["id", "hostname"]},
    {"kind": "FIELDS", "ref": "sys", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "rg", "fields": ["id", "code"]}
  ],
  "maxResults": 2000
}
```

**常见错误点**
- 4 跳路径中对象数量应为 relationship 数量 + 1，少一个对象会导致链路不完整。
- 误把 `maxResults` 设太小（如 10），导致误判“无数据”。

---

## 样例 6：4 跳路径 + relationship alias 多条件组合

```json
{
  "version": "1.0",
  "schemaRef": "net@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "user", "alias": "u"},
    {"objectType": "device", "alias": "d"},
    {"objectType": "subnet", "alias": "sn"},
    {"objectType": "vpc", "alias": "v"},
    {"objectType": "zone", "alias": "z"}
  ],
  "relationships": [
    {"relationshipType": "login_from", "alias": "r_login", "from": "u", "to": "d"},
    {"relationshipType": "device_in_subnet", "alias": "r_ds", "from": "d", "to": "sn"},
    {"relationshipType": "subnet_in_vpc", "alias": "r_sv", "from": "sn", "to": "v"},
    {"relationshipType": "vpc_in_zone", "alias": "r_vz", "from": "v", "to": "z"}
  ],
  "conditions": {
    "kind": "GROUP",
    "relation": "AND",
    "children": [
      {"kind": "PREDICATE", "ref": "r_login", "field": "riskLevel", "operator": "GTE", "values": [3]},
      {"kind": "PREDICATE", "ref": "r_ds", "field": "lastSeenHours", "operator": "LTE", "values": [24]},
      {"kind": "PREDICATE", "ref": "z", "field": "name", "operator": "EQ", "values": ["可用区A"]}
    ]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "u", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "d", "fields": ["id", "ip"]},
    {"kind": "FIELDS", "ref": "z", "fields": ["id", "name"]}
  ]
}
```

**常见错误点**
- `GTE/LTE` 数值过滤时将 `values` 写成字符串（如 `"3"`）造成类型不匹配。
- 同时过滤多个关系 alias 时，误把不同关系字段写在同一个 `ref` 下。

---

## 样例 7：路径断裂反例（2 段关系互不连通）

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "device", "alias": "d"},
    {"objectType": "server", "alias": "s"},
    {"objectType": "datacenter", "alias": "dc"},
    {"objectType": "project", "alias": "p"}
  ],
  "relationships": [
    {"relationshipType": "installed_on", "alias": "r1", "from": "d", "to": "s"},
    {"relationshipType": "managed_by", "alias": "r2", "from": "dc", "to": "p"}
  ],
  "returns": [{"kind": "FIELDS", "ref": "d", "fields": ["id"]}]
}
```

**常见错误点**
- `d -> s` 与 `dc -> p` 是两段孤立子图，不是单条可达路径，会被判定为路径断裂。
- 仅靠 `objects` 同时声明多个 alias，并不会自动建立跳转关系。

---

## 样例 8：路径断裂反例（3 跳中间 alias 拼写错误）

```json
{
  "version": "1.0",
  "schemaRef": "iam@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "user", "alias": "u"},
    {"objectType": "role", "alias": "r"},
    {"objectType": "application", "alias": "app"},
    {"objectType": "environment", "alias": "env"}
  ],
  "relationships": [
    {"relationshipType": "assigned_role", "alias": "rel1", "from": "u", "to": "r"},
    {"relationshipType": "role_grants_app", "alias": "rel2", "from": "rr", "to": "app"},
    {"relationshipType": "app_deployed_env", "alias": "rel3", "from": "app", "to": "env"}
  ],
  "returns": [{"kind": "FIELDS", "ref": "u", "fields": ["id", "name"]}]
}
```

**常见错误点**
- `rel2.from` 使用了不存在 alias `rr`，导致链路在第 2 跳断裂。
- alias 拼写问题通常不会被业务数据掩盖，应优先做 schema/语义校验。

---

## 样例 9：sourceQuery + fromSource（先限定起点设备，再扩展 2 跳）

```json
{
  "version": "1.0",
  "schemaRef": "infra@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "device", "alias": "d", "fromSource": true},
    {"objectType": "server", "alias": "s"},
    {"objectType": "datacenter", "alias": "dc"}
  ],
  "sourceQuery": {
    "operation": "OBJECT_QUERY",
    "objectType": "device",
    "conditions": {
      "kind": "PREDICATE",
      "field": "criticality",
      "operator": "EQ",
      "values": ["P1"]
    },
    "returns": ["id"],
    "maxResults": 200
  },
  "relationships": [
    {"relationshipType": "installed_on", "alias": "r1", "from": "d", "to": "s"},
    {"relationshipType": "deployed_in", "alias": "r2", "from": "s", "to": "dc"}
  ],
  "returns": [
    {"kind": "FIELDS", "ref": "d", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "dc", "fields": ["id", "region"]}
  ]
}
```

**常见错误点**
- 使用 `sourceQuery` 但忘记在起点对象上标记 `fromSource: true`。
- `sourceQuery.objectType` 与起点对象类型不一致（如查询 `server` 却映射到 `device`）。

---

## 样例 10：sourceQuery + fromSource（先限定部门，再找员工与园区）

```json
{
  "version": "1.0",
  "schemaRef": "corp@1.0",
  "strict": true,
  "operation": "ASSOCIATION_QUERY",
  "objects": [
    {"objectType": "department", "alias": "dep", "fromSource": true},
    {"objectType": "employee", "alias": "e"},
    {"objectType": "campus", "alias": "c"}
  ],
  "sourceQuery": {
    "operation": "OBJECT_QUERY",
    "objectType": "department",
    "conditions": {
      "kind": "PREDICATE",
      "field": "costCenter",
      "operator": "IN",
      "values": ["CC1001", "CC1002"]
    },
    "returns": ["id"],
    "maxResults": 50
  },
  "relationships": [
    {"relationshipType": "works_in", "alias": "r1", "from": "e", "to": "dep"},
    {"relationshipType": "located_at", "alias": "r2", "from": "dep", "to": "c"}
  ],
  "returns": [
    {"kind": "FIELDS", "ref": "e", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "dep", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "c", "fields": ["id", "city"]}
  ]
}
```

**常见错误点**
- 将 `fromSource: true` 配在非锚点对象（如 `e`）上，语义不成立。
- `sourceQuery.maxResults` 过小，导致后续关联结果被过度裁剪。

---

## 样例 11：单跳应走 LINK_QUERY 的反例（不推荐用 ASSOCIATION_QUERY）

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
  "conditions": {
    "kind": "PREDICATE",
    "ref": "d",
    "field": "name",
    "operator": "EQ",
    "values": ["研发部"]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "e", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "d", "fields": ["id", "name"]}
  ]
}
```

**常见错误点**
- 单跳且仅关注 link 关系时，仍使用 `ASSOCIATION_QUERY`，会增加不必要的解析与执行负担。
- 没有 profile 明确要求单跳走 association 时，应优先改为 `LINK_QUERY`。

---

## 样例 12：单跳应走 LINK_QUERY 的正例（推荐写法）

```json
{
  "version": "1.0",
  "schemaRef": "ams_topology@1.0",
  "strict": true,
  "operation": "LINK_QUERY",
  "sourceObject": {"objectType": "employee", "alias": "e"},
  "targetObject": {"objectType": "department", "alias": "d"},
  "link": {"relationshipType": "works_in", "alias": "r"},
  "conditions": {
    "kind": "PREDICATE",
    "ref": "d",
    "field": "name",
    "operator": "EQ",
    "values": ["研发部"]
  },
  "returns": [
    {"kind": "FIELDS", "ref": "e", "fields": ["id", "name"]},
    {"kind": "FIELDS", "ref": "d", "fields": ["id", "name"]}
  ],
  "maxResults": 1000
}
```

**常见错误点**
- 把 `LINK_QUERY` 的 `sourceObject/targetObject/link` 误写成 `objects/relationships` 结构。
- 没有将单跳场景统一收敛到 `LINK_QUERY`，导致接口使用风格不一致。
