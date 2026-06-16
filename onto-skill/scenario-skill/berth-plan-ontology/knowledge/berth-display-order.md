# 泊位显示顺序对象查询 (berth_display_order)

## 目标
不带条件查询时返回所有泊位显示顺序信息，依据条件查询时返回符合要求的泊位显示顺序信息

## 本体信息
- **对象名**：berth_display_order
- **对象ID**：dtmi.560d88f7.object-type.8bfeef9d48919dd2.1
- **Ontology-ID**：dtmi.ontology.560d88f7.1

## 核心经验性知识
泊位显示顺序用于确定泊位在界面上的显示排列顺序

## 工作顺序（每步都必须执行）
1、阅读本文件，了解该操作的输入/输出契约。
2、通过OAG、OAC调用规则查询。

### OAG 调用规则
- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `Ontology ID = dtmi.ontology.560d88f7.1`

### OAC 调用规则
- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef = dtmi.ontology.560d88f7.1`
- **拼OQL强制要求**：objectType 的 value 字母必须全小写

**返回字段**：
- berth_display_order 相关属性

**查询语句格式**：
```
查数据：查询泊位显示顺序信息
查询目标：返回泊位显示顺序属性
关系路径：严格通过OAG返回结果推断
过滤条件：
- berth_display_order.berth_no = "{泊位代码}"
返回要求：返回消息格式message_type为berth_display_order
```

## 执行建议

1. **首选**：通过 OAG 查询获取 Function（从 has_function 边），优先使用 Function
2. **备选**：通过 OAG 查询子图确认关系路径，再生成查询实例

**条件归属**：
- berth_no：直接条件，属于 berth_display_order 对象