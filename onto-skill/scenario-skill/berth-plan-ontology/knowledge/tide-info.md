# 潮汐对象查询 (tide_info)

## 目标
不带条件查询时返回所有潮汐信息，依据条件查询时返回符合要求的潮汐信息

## 本体信息
- **对象名**：tide_info
- **对象ID**：dtmi.560d88f7.object-type.d528c8b1c4e78b41.1
- **Ontology-ID**：dtmi.ontology.560d88f7.1

## 核心经验性知识
潮汐对象为tide_info。进行潮汐查询时需要使用 `tide_time`（潮汐时间的唯一标识符）

## 工作顺序（每步都必须执行）
1、阅读本文件，了解该操作的输入/输出契约。
2、通过OAG、OAC调用规则查询。

### OAG 调用规则
- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `Ontology ID = dtmi.ontology.560d88f7.1`

### OAC 调用规则
- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef = dtmi.ontology.560d88f7.1`
- **拼OQL强制要求**：objectType 的 value 字母必须全小写

**【关键约束 - 必须严格遵守】返回字段（共3个，全部为潮汐(tide_info)的属性】**：
- **潮汐属性**：tide_time、height_tide、mark
- **注意**：以上字段**全部是潮汐(tide_info)的属性**，在一次OAC查询中**全部返回**，禁止遗漏任何一个

**查询语句格式**：
```
查数据：查询潮汐信息
查询目标：返回潮汐的tide_time、height_tide、mark属性
关系路径：严格通过OAG返回结果推断
过滤条件：
- tide_info.tide_time = "{潮汐时间}"
返回要求：返回消息格式message_type为tide_info，必须返回潮汐的tide_time、height_tide、mark字段
```

## 执行建议

1. **首选**：通过 OAG 查询获取 Function（从 has_function 边），优先使用 Function
2. **备选**：通过 OAG 查询子图确认关系路径，再生成查询实例

**关键约束**：
- **直接使用潮汐时间查询**：查询潮汐时，**直接使用 `tide_info.tide_time` 作为过滤条件**

**条件归属**：
- tide_time：直接条件，属于 tide_info 对象