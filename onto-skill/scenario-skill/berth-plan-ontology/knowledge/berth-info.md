# 泊位对象查询 (berth_info)

## 目标
不带条件查询时返回所有泊位信息，依据条件查询时返回符合要求的泊位信息

## 本体信息
- **对象名**：berth_info
- **对象ID**：dtmi.560d88f7.object-type.99fd288c0f2bb909.1
- **Ontology-ID**：dtmi.ontology.560d88f7.1

## 核心经验性知识
泊位对象为berth_info。进行特定某个泊位查询时需要使用 `berth_no`（泊位的唯一标识符）

## 工作顺序（每步都必须执行）
1、阅读本文件，了解该操作的输入/输出契约。
2、通过OAG、OAC调用规则查询。

### OAG 调用规则
- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `Ontology ID = dtmi.ontology.560d88f7.1`

### OAC 调用规则
- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef = dtmi.ontology.560d88f7.1`
- **拼OQL强制要求**：objectType 的 value 字母必须全小写（如 berth_no, terminal_code）

**【关键约束 - 必须严格遵守】返回字段（共10个，全部为泊位(berth_info)的属性】**：
- **泊位属性**：
| 序号 | 字段名 | 所属对象 | 说明 |
|------|--------|---------|------|
| 1 | berth_no | 泊位（berth_info） | 泊位代码 |
| 2 | terminal_code | 泊位（berth_info） | 码头代码 |
| 3 | forefront_water_depth | 泊位（berth_info） | 前沿水深 |
| 4 | berth_capacity | 泊位（berth_info） | 靠泊能力 |
| 5 | geo_location | 泊位（berth_info） | 地理位置 |
| 6 | deadweight_tonnage | 泊位（berth_info） | 载重吨 |
| 7 | berth_ew_orientation | 泊位（berth_info） | 泊位东西向 |
| 8 | berth_length | 泊位（berth_info） | 泊位长度 |
| 9 | berth_level | 泊位（berth_info） | 泊位等级 |
| 10 | shoreline_no | 泊位（berth_info） | 岸线代码 |
- **注意**：以上字段**全部是泊位(berth_info)的属性**，在一次OAC查询中**全部返回**，禁止遗漏任何一个

**查询语句格式**：
```
查数据：依据{泊位代码}查询泊位信息
查询目标：返回泊位的berth_no,terminal_code,forefront_water_depth,berth_capacity,
geo_location,deadweight_tonnage,berth_ew_orientation,berth_length,berth_level,shoreline_no10个属性
关系路径：严格通过OAG返回结果推断
过滤条件：
- berth_info.berth_no== "{泊位代码}"
返回要求：返回消息格式message_type为berth_info，必须返回泊位的berth_no,terminal_code,forefront_water_depth,berth_capacity,
geo_location,deadweight_tonnage,berth_ew_orientation,berth_length,berth_level,shoreline_no共10个字段
```

## 执行建议

1. **首选**：通过 OAG 查询获取 Function（从 has_function 边），优先使用 Function，默认调用每个Function 1次，若调用未返回数据或调用异常时不允许重复调用。
2. **备选**：通过 OAG 查询子图确认关系路径，再生成查询实例

**关键约束**：
- **直接使用泊位代码查询**：查询泊位时，**直接使用 `berth_info.berth_no` 作为过滤条件**
- 例如：`过滤条件：berth_info.berth_no = "101"`

**条件归属**：
- berth_no：直接条件，属于berth_info对象