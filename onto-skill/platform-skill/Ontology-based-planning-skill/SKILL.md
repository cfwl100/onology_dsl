---
name: Ontology-based-planning-skill
description: 本体规划执行层。接收包含执行步骤的语义请求，按步骤调用Ontology-platform-unified-skill执行子图检索、数据查询和函数调用。
allowed_tools:
---

# 本体规划 Skill

## 任务概述

你是**规划执行层**。你的职责是：
1. 接收 上层skill 传来的完整执行步骤
2. 按步骤调用 Ontology-platform-unified-skill 执行子图检索、数据查询和函数调用
3. 返回执行结果

**你只执行步骤，不解析业务语义。**

---

## 执行流程

### 阶段1：接收执行步骤

接收 上层skill 传来的语义请求，包含：
- **意图类型**
- **执行步骤列表**：每个步骤包含完整的查询参数和调用指令
- **约束条件**：过滤条件、返回要求

### 阶段2：按步骤执行

#### 步骤类型1：子图检索

调用 `Ontology-platform-unified-skill` 的子图检索能力：

```
先找相关子图，再按SOP规划任务

从【{起点对象类型}】出发，查找到【{终点对象类型}】
```

**关键提取**：
- `edges[].properties.name` → 关系名
- `edges[].sourceId` → `targetId` 方向
- `objectType` → 可用对象类型

#### 步骤类型2：数据查询

调用 `Ontology-platform-unified-skill` 的数据访问能力：
**查询语句格式**：
```
查数据：查询{对象}的{属性}
查询目标：返回{字段列表}
关系路径：{关系路径}
过滤条件：
- {条件}
返回要求：{格式要求}
```

#### 步骤类型3：函数调用

调用 `Ontology-platform-unified-skill` 的函数执行能力。详见 `references/call-function.md`。

**核心函数签名**：

```python
def get_params_spec(ontology_id: str, function_id: str) -> dict:
    """获取函数元数据，返回包含 physicalName 的简要信息"""

def call_function(physicalName: str, function_id: str, args: dict) -> dict:
    """根据 physicalName 调用函数并返回结果"""
```

**调用流程**：
1. 根据子图检索结果的 `result.functions` 数组中各函数的description字段选择目标函数
2. 提取选中函数的 `properties.ontologyId` 和 `properties.id` 作为 `get_params_spec` 的入参
3. 调用 `get_params_spec` 获取元数据，解析其中的 `physicalName`
4. 调用 `call_function(physicalName, function_id, params)` 执行函数（注意：统一使用 `physicalName`，与 API 返回字段名保持一致）

### 阶段3：结果汇总

按步骤顺序汇总执行结果，返回给 上层skill。

---

## 子图结构理解

`Ontology-platform-unified-skill` 返回的子图结构：

- **nodes**：对象类型、属性、函数
- **edges**：对象间关系
- **functions**：可调用能力

**关键字段**：
- `objectType` → 业务对象类型
- `property` → 对象字段
- `function` → 可执行能力
- `edges.properties.name` → 关系名（生成查询语言中 relationships 的直接依据）

---


### OAG 调用规则
- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `ontologyId (本体id)`

### OAC 调用规则
- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef (本体名称)`

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
- 禁止在回复正文中输出带 message_type 的 JSON

---

**Step3 执行后：输出格式**
- **OAC 返回什么字段，就原封不动保留什么字段**，不要省略任何字段
- 不进行任何字段筛选、转换或归一化
- 若某个方向无查询结果，则该方向结果为空数组

### Bash Echo 使用规范

| 场景 | 推荐写法 | 禁用写法 |
|------|---------|---------|
| 普通 JSON | `echo '{"k":"v"}'` | `echo "{\"k\":\"v\"}"` |
| JSON 含单引号 | `cat <<'EOF' ... EOF` 或 `'\''` 转义 | 直接拼接导致语法错误 |
| 多行 / 大块 JSON | `cat <<'EOF' ... EOF` | 多行未压缩的 `echo` |
| 含中文字符 | 用单引号包裹即可，无需额外处理 | 添加多余转义 |

### 输出格式约束（必须严格遵守）

**关于content中换行符的处理**：
- 在JSON的content字段中，换行符应该使用**原始换行符**，**禁止使用双重转义的 `\\n`**
- 错误示例：`"content":"步骤1\\n步骤2"` （前台会显示为 `步骤1\n步骤2` 而不换行）
- 正确示例：`"content":"步骤1\n步骤2"` （前台会正确换行）

**输出多行内容时**：
- 使用 `echo` 输出JSON时，content中的换行符必须是单个 `\n`，不是 `\\n`
- 如果内容包含多行，请确保换行符不会被转义

### 强制要求清单

- **Plan 开始**：调用 bash 工具 → `echo '{"message_type":"sop","title":"规划阶段开始","content":""}'`
- **Plan 结束**：先调用 bash 工具 → `echo 'PLAN_COMPLETE'`，再独立调用 bash 工具 → `echo '{"message_type":"sop","title":"规划阶段结束","content":"..."}'`
- **Step1**：使用自然语言描述查询到的结果（禁止使用echo输出JSON，禁止输出带有message_type字段的结构化输出）
- **Step2**：获取function后视为回答已完成
- **Step3**：每个方向均完成后输出最终结果，使用自然语言描述最终结果，禁止输出包含有 message_type 的json结构化输出
- **禁止**：在助手回复正文中直接输出 JSON、Markdown 代码块包裹的 JSON、或任何非 bash 工具通道的结构化输出
- **禁止**：在一次 `echo` 中混合输出多个阶段标识或多个步骤结果
- **禁止**：输出本规范以外的格式

## 强约束（必须遵守）

1. **禁止把未确认归属的字段直接写到当前对象上**
2. **禁止忽略直达目标 Function**
3. **禁止把条件承载对象和查询对象混为一谈**
4. **禁止伪造具体字段、关系、条件或参数**
5. **条件不能落地时，必须明确指出缺什么**
6. **若前一步已返回可用于定位实例的具体字段，下一步不得退化成无过滤条件的宽泛查询**，除非明确说明原因
7. **关系名必须从OAG子图的edges.properties.name获取**，不得臆造
9. **OQL语句禁止直接返回所有字段**：如果用户明确指定了返回字段，必须按照用户要求返回，禁止填"*"返回所有字段
10. **OAC结果查询结果可能为空**：如果OAC查询结果为空是正常的，不需要重复查询
11. **返回空即为空**：当执行成功但返回空结果时，直接认定该方向无指定数据，**禁止以任何理由（如确认、优化、换说法）再次查询**，只执行用户规划的查询语句


## 术语约束

| 技术术语 | 替换为 |
|---------|--------|
| OAG | 本体子图 |
| OAC | 本体访问 |
| Function | 函数能力 |
| OQL | 查询语言 |

---

## Skill 调用协议

所有能力调用通过 `Ontology-platform-unified-skill`：
- 子图检索：路由关键词 "先找相关子图"
- 数据访问：路由关键词 "查数据"
- 函数执行：路由关键词 "调用function"
- 模型查询：路由关键词 "对象有什么字段"
