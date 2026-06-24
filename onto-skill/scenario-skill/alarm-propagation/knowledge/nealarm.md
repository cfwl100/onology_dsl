# 获取网元告警

## 目标
识别输入网元是否存在告警，并返回告警信息

## 核心经验性知识

### 告警基础
- **告警和异常事件不同**，不要去查找 AbnormalStatus
- 告警的 `alarmName` 实际上是告警类型，进行特定某条或某几条告警时**不要使用该字段作为筛选条件**，需要使用 `identifier`（告警的唯一标识符）
- 告警的实例数据可能会很多，如果有合适的 Function 的话，可以通过 Function 来查询告警

### 网元层级（neLayer）属性
- CN：核心路由（Core Network），ne_layer = 30
- AN：汇聚路由（Aggregation Network），ne_layer = 20
- EN：接入路由（Edge Network），ne_layer = 10

**【关键约束 - 必须严格遵守】返回字段（共8个，全部为告警alarm的属性】**：
- **告警属性**：ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、node
- **注意**：以上8个字段**全部是告警(alarm)的属性**，在一次OAC查询中**全部返回**，禁止遗漏任何一个

**查询语句格式**：
```
查数据：查询{网元名称}的告警
查询目标：返回告警的ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、node属性
关系路径：严格通过OAG返回结果推断
过滤条件：
- ne.name = "{网元名称}"
返回要求：返回消息格式message_type为alarm，必须返回告警的ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、node共8个字段
```

### 告警类型示例参考
- Ethernet Physical (ETPI) LOS
- Ethernet Physical (ETPI) Port down
- Ethernet Physical (ETPI) Interface down
- BN EMS Alarm NE Communication Failure

## 执行建议

1. **首选**：通过 OAG 查询获取 Function（从 has_function 边），优先使用 Function
2. **备选**：通过 OAG 查询子图确认关系路径，再生成查询实例

**关键约束**：
- **直接使用网元名称查询**：查询网元告警时，**直接使用 `ne.name` 作为过滤条件**，不需要先查询网元ID
- 例如：`过滤条件：ne.name = "DLE_AIRHITAM_GEBANG_MT"`，无需先查 ne_id 再查告警

**条件归属**：
- name：直接条件，属于 Ne 对象
- alarmName：关联到 Alarm ，是Alarm的属性