---
name: ontology-planning
description: 本体规划执行层。接收包含执行步骤的语义请求，按步骤调用ontology-platform执行子图检索、数据查询和函数调用。
allowed_tools:
---

# 本体规划 Skill

> **共享约束规则**：参见 `platform-skill/shared-constraints.md`

## 快速路由参考

| 步骤类型 | 调用目标 | 说明 |
|---------|---------|------|
| 子图检索 | ontology-platform → OAG | 调用 `semantic_subgraph_search.py` |
| 数据查询 | ontology-platform → OAC | 调用 `execute_oac_operation.py` |
| 函数调用 | ontology-platform → Function | 先获取参数规格，再执行 |

## Skill 边界

```
ontology-planning 只执行步骤，不解析业务语义
                      ↓
         ┌────────────────────────────┐
         │ 接收上层 skill 传来的：     │
         │ - 意图类型                 │
         │ - 执行步骤列表             │
         │ - 约束条件                 │
         └────────────────────────────┘
                      ↓
         按步骤调用 ontology-platform
                      ↓
         汇总结果返回上层 skill
```

## 任务概述

你是**规划执行层**。你的职责是：
1. 接收上层 skill 传来的完整执行步骤
2. 按步骤调用 ontology-platform 执行子图检索、数据查询和函数调用
3. 返回执行结果

**你只执行步骤，不解析业务语义。**

---

## 执行流程

### 阶段1：接收执行步骤

接收上层 skill 传来的语义请求，包含：
- **意图类型**
- **执行步骤列表**：每个步骤包含完整的查询参数和调用指令
- **约束条件**：过滤条件、返回要求

### 阶段2：按步骤执行

#### 步骤类型1：子图检索

调用 `ontology-platform` 的子图检索能力：
```
先找相关子图，再按SOP规划任务

从【{起点对象类型}】出发，查找到【{终点对象类型}】
```

**关键提取**：
- `edges[].properties.name` → 关系名
- `edges[].sourceId` → `targetId` 方向
- `objectType` → 可用对象类型

#### 步骤类型2：数据查询

调用 `ontology-platform` 的数据访问能力：
```
查数据：查询{对象}的{属性}
查询目标：返回{字段列表}
关系路径：{关系路径}
过滤条件：
- {条件}
返回要求：{格式要求}
```

#### 步骤类型3：函数调用

调用 `ontology-platform` 的函数执行能力：

**第一步：获取参数规格**
```
调用function

function_id: {function_id}
```

**第二步：执行Function**
```
调用function

function_id: {function_id}
params: {params}
```

### 阶段3：结果汇总

按步骤顺序汇总执行结果，返回给上层 skill。

---

## 子图结构理解

`ontology-platform` 返回的子图结构：

| 结构元素 | 说明 |
|---------|------|
| nodes | 对象类型、属性、函数 |
| edges | 对象间关系 |
| functions | 可调用能力 |

**关键字段**：
- `objectType` → 业务对象类型
- `property` → 对象字段
- `function` → 可执行能力
- `edges.properties.name` → 关系名（生成查询语言中 relationships 的直接依据）

---

## 约束规则

> **重要**：以下约束的详细说明请参见 `platform-skill/shared-constraints.md`

1. **禁止把未确认归属的字段直接写到当前对象上**
2. **禁止忽略直达目标 Function**
3. **禁止把条件承载对象和查询对象混为一谈**
4. **禁止伪造具体字段、关系、条件或参数**
5. **条件不能落地时，必须明确指出缺什么**
6. **若前一步已返回可用于定位实例的具体字段，下一步不得退化成无过滤条件的宽泛查询**，除非明确说明原因
7. **关系名必须从 OAG 子图的 `edges.properties.name` 获取**，不得臆造
8. **OQL 语句禁止直接返回所有字段**：如果用户明确指定了返回字段，必须按照用户要求返回，禁止填 `*` 返回所有字段
9. **OAC 结果查询结果可能为空**：如果 OAC 查询结果为空是正常的，不需要重复查询
10. **返回空即为空**：当执行成功但返回空结果时，直接认定该方向无指定数据，**禁止以任何理由再次查询**，只执行用户规划的查询语句

---

## 输出格式

### Plan 开始
```bash
echo '{"message_type":"sop","title":"规划阶段开始","content":""}'
```

### Plan 结束
```bash
echo 'PLAN_COMPLETE'
echo '{"message_type":"sop","title":"规划阶段结束","content":"<执行步骤列表>"}'
```

### Exec 阶段
- 使用自然语言描述执行结果
- 禁止在回复正文中输出带 `message_type` 的 JSON

### Step3 执行后输出格式
- **OAC 返回什么字段，就原封不动保留什么字段**，不要省略任何字段
- 不进行任何字段筛选、转换或归一化
- 若某个方向无查询结果，则该方向结果为空数组

---

## 术语约束

| 技术术语 | 替换为 |
|---------|--------|
| OAG | 本体子图 |
| OAC | 本体访问 |
| Function | 函数能力 |
| OQL | 查询语言 |
