# 获取网元告警

## 目标

识别输入网元是否存在告警，并返回告警信息。

## 核心概念

### 告警与异常事件的区别

- **告警**和**异常事件**不同
- **不要**去查找 `AbnormalStatus`（异常事件）
- 要查询**活动告警**

### 告警标识符

- 告警的 `alarmName` 实际上是**告警类型**
- 告警的**唯一标识符**是 `identifier`
- 查询特定某条或某几条告警时，应该使用 `identifier` 字段，**不要使用 `alarmName` 作为筛选条件**

### 网元层级（neLayer）属性

| 层级 | 名称 | ne_layer 值 |
|-----|------|------------|
| CN | 核心路由（Core Network） | 30 |
| AN | 汇聚路由（Aggregation Network） | 20 |
| EN | 接入路由（Edge Network） | 10 |

## 返回字段约束

### 必须返回的8个告警属性

在一次 OAC 查询中，**必须返回以下全部8个字段**：

| 字段名 | 说明 |
|-------|------|
| ownerVid | 告警所属 vid |
| severity | 告警严重程度 |
| alarmName | 告警名称（类型） |
| identifier | 告警唯一标识符 |
| firstOccurrence | 首次发生时间 |
| lastOccurrence | 最后发生时间 |
| node | 关联节点 |

**注意**：以上8个字段**全部是告警（alarm）的属性**，在一次 OAC 查询中**全部返回**，禁止遗漏任何一个。

## 查询约束

### 直接使用网元名称查询

查询网元告警时，**直接使用 `ne.name` 作为过滤条件**，不需要先查询网元ID。

**示例**：
```
过滤条件：ne.name = "DLE_AIRHITAM_GEBANG_MT"
```

（无需先查 ne_id 再查告警）

### 条件归属

| 条件字段 | 归属对象 | 说明 |
|---------|---------|------|
| name | Ne | 网元名称，直接条件 |
| alarmName | Alarm | 告警类型，关联条件 |

## 告警类型示例

以下告警类型仅供参考：

- Ethernet Physical (ETPI) LOS
- Ethernet Physical (ETPI) Port down
- Ethernet Physical (ETPI) Interface down
- BN EMS Alarm NE Communication Failure
