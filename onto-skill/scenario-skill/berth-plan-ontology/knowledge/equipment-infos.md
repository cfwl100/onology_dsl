# 桥吊对象查询 (equipment_infos)

## 目标
不带条件查询时返回所有桥吊信息，依据条件查询时返回符合要求的桥吊信息

## 本体信息
- **对象名**：equipment_infos
- **对象ID**：dtmi.560d88f7.object-type.bcd8cb5256e0a38a.1
- **Ontology-ID**：dtmi.ontology.560d88f7.1

## 核心经验性知识
进行特定某条或某几条桥吊查询时需要使用 `traveling_crane_no`（桥吊的唯一标识符）

## 工作顺序（每步都必须执行）
1、阅读本文件，了解该操作的输入/输出契约。
2、通过OAG、OAC调用规则查询。

### OAG 调用规则
- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `Ontology ID = dtmi.ontology.560d88f7.1`

### OAC 调用规则
- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef = dtmi.ontology.560d88f7.1`
- **拼OQL强制要求**：objectType 的 value 字母必须全小写（如 traveling_crane_no）

**【关键约束 - 必须严格遵守】返回字段（全部为桥吊(equipment_infos)的属性】**：
- **桥吊属性**：traveling_crane_no、manufacturer、beg_bollard_no、end_bollard_no
- **注意**：以上字段**全部是桥吊(equipment_infos)的属性**，在一次OAC查询中**全部返回**，禁止遗漏任何一个

**查询语句格式**：
```
查数据：依据{桥吊代码}查询桥吊信息
查询目标：返回桥吊的traveling_crane_no等属性
关系路径：严格通过OAG返回结果推断
过滤条件：
- equipment_infos.traveling_crane_no = "{桥吊代码}"
返回要求：返回消息格式message_type为equipment_infos，必须返回桥吊的traveling_crane_no字段
```

## 执行建议

1. **首选**：通过 OAG 查询获取 Function（从 has_function 边），优先使用 Function，默认调用每个Function一次，若调用未返回数据或调用异常时不允许重复调用。

2. **备选**：通过 OAG 查询子图确认关系路径，再生成查询实例

**关键约束**：
- **直接使用桥吊代码查询**：查询桥吊时，**直接使用 `equipment_infos.traveling_crane_no` 作为过滤条件**
- 例如：`过滤条件：equipment_infos.traveling_crane_no = "1"`

**条件归属**：
- traveling_crane_no：直接条件，属于 equipment_infos 对象