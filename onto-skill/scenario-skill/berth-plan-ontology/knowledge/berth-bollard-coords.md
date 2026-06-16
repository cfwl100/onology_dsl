# 岸线-泊位-揽桩-桥吊坐标对象查询 (berth_bollard_coords)

## 目标
查询岸线-泊位-揽桩-桥吊的坐标数据，用于计算不同区域（泊位）缆桩的统一绝对坐标（unified_abs_coords）

## 本体信息
- **对象名**：berth_bollard_coords
- **对象ID**：dtmi.560d88f7.object-type.37064170af561116.1
- **Ontology-ID**：dtmi.ontology.560d88f7.1

## 核心经验性知识
脚本核心功能是计算不同区域（泊位）缆桩的统一绝对坐标（unified_abs_coords）。数据关联路径：岸线(group) → 泊位(berth_no) → 缆桩(bollard_no) → 桥吊(traveling_crane_no)

## 工作顺序（每步都必须执行）
1、阅读本文件，了解该操作的输入/输出契约。
2、先通过OAG子图检索再通过OAC调用规则查询数据。

### OAG 调用规则
- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `Ontology ID = dtmi.ontology.560d88f7.1`

### OAC 调用规则
- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef = dtmi.ontology.560d88f7.1`
- **拼OQL强制要求**：objectType 的 value 字母必须全小写

**返回字段**：
- area: 岸线分组（A、B、C、D）
- berth_no: 泊位编号
- bollard_no: 缆桩编号
- bollard_pos: 揽桩位置
- unified_abs_coords: 统一绝对坐标
- traveling_crane_no_list: 桥吊编号列表

**查询语句格式**：
```
查数据：查询岸线-泊位-揽桩-桥吊坐标信息
查询目标：返回unified_abs_coords等属性
关系路径：严格通过OAG返回结果推断
过滤条件：
- berth_bollard_coords.group = "{岸线分组}"
返回要求：返回消息格式message_type为berth_bollard_coords，必须返回unified_abs_coords字段
```

## 执行建议

1. **首选**：通过 OAG 查询获取 Function（从 has_function 边），优先使用 Function
2. **备选**：通过 OAG 查询子图确认关系路径，再生成查询实例

**关键约束**：
- **统一绝对坐标计算**：unified_abs_coords 是核心计算字段，基于岸线分组间隔计算