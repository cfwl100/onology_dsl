# 船舶对象查询（ship_info）

## 本体信息

- 对象名：`ship_info`
- ontologyId：`dtmi.ontology.560d88f7.1`
- schemaRef：`dtmi.ontology.560d88f7.1`
- OQL 初始版本：`1.0`

## 字段映射

字段是否可用于最终查询，必须以本体子图中 `ship_info --has_property--> property` 的归属关系为准。

| 用户表达 | 平台字段 | 归属对象 |
|---|---|---|
| 船舶编号、船号、船舶代码 | `ship_no` | `ship_info` |
| 船舶类型、船的类型 | `ship_type` | `ship_info` |
| 船高 | `ship_height` | `ship_info` |
| 吃水深度、船的吃水深度 | `draft` | `ship_info` |
| 船长、总长、LOA | `loa` | `ship_info` |

当用户查询船舶信息且未指定返回字段时，默认返回：

```text
ship_no, ship_type, ship_height, draft, loa
```

## 查询生成规则

- 船高范围条件映射到 `ship_height`。
- 船舶类型条件映射到 `ship_type`。
- 吃水深度条件映射到 `draft`。
- 用户输入中的米、m 等单位在条件值中只保留数值部分。
- 本样例属于单对象明细查询，应路由为 `QUERY`。
- 最终 OQL 必须使用 `version: "1.0"`。

## 强约束

1. 字段必须属于 `ship_info`，且必须能从本体子图的 `has_property` 关系确认归属。
2. 不得把 `ship_plan.vessel_type` 当成 `ship_info.ship_type`。
3. 不得因为用户使用中文字段名就直接写入中文字段，必须映射到平台字段名。
4. OAC 返回空结果是有效结果，不自动放宽条件或重复查询。