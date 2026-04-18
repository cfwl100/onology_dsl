# 路径模式与边界

## 适用模式

- 从对象 A 经一跳或多跳关系找到对象 B / C
- 用户显式描述路径、关系链、上游 / 下游
- 需要对路径起点、终点或中间节点进行筛选
- 当前 schema/profile 要求即使单跳也必须显式声明 `relationships`

## 常见线索

- “从设备经过 installed_on 找到服务器，再经过 deployed_in 找到机房”
- “沿着 contains 关系向下找到所有站点”
- “查询告警关联到链路再关联到端口的路径”
- “即使只是一跳，也要用显式路径查询”

## 与 link-query 的边界

- 默认情况下，如果是单跳、单关系、直接相邻对象访问，优先考虑 `LINK_QUERY`
- 如果用户表达了路径顺序、链式关系或多跳语义，使用 `ASSOCIATION_QUERY`
- 如果调用方或 schema/profile 已明确要求“单跳也走 `ASSOCIATION_QUERY`”，则必须使用 `ASSOCIATION_QUERY`

## 示例

### 正例 1

用户：查询设备通过 installed_on 到 server，再通过 deployed_in 到 dataCenter

应生成：`ASSOCIATION_QUERY`

### 正例 2

用户：查询员工通过 works_in 关联到部门，并且当前 schema 规定单跳也走显式路径查询

应生成：`ASSOCIATION_QUERY`

### 反例

用户：查询订单对应的发票

如果只是一条直接关系且无路径链语义，且当前 profile 无特殊要求，更适合 `LINK_QUERY`。
