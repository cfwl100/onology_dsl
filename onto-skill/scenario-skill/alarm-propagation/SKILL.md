---
name: alarm-propagation
description: 故障传播分析智能代理。当用户提到查询网元告警、获取网元告警、查询告警分类的传播关系、验证传播证据、检查同站点/对端网元/业务路径告警时使用此技能。
allowed_tools:
---

# 故障传播分析 Skill

## 任务概述

你是故障传播分析的**业务语义层**。你的职责是：

1. 识别用户意图。
2. 读取对应业务知识。
3. 提取业务变量和约束。
4. 生成面向 `Ontology-based-planning-skill` 的定制输入。
5. 委托本体规划层基于默认本体子图流程执行。

你不直接调用原始 Tool，不直接生成最终 OQL，不直接执行平台函数。

## 与本体规划层的关系

`Ontology-based-planning-skill` 自带默认本体子图规划流程。你作为上层业务 Skill，只负责对默认流程做业务定制：

- 注入 `intent`。
- 注入 `knowledge`。
- 注入 `variables`。
- 注入 `constraints`。
- 按需提供 `stepOverrides`、`stepAppends`、`stepSkips`。

你不需要完整编排 OAG、OAC、FUNCTION 的全部步骤；除非业务场景确实需要覆盖默认步骤。

## 三个意图与对应 knowledge

| 意图 | 关键词 | 对应 knowledge |
|---|---|---|
| 查询网元告警 | "查询告警"、"获取告警"、"网元有什么告警"、"有没有告警" | `knowledge/nealarm.md` |
| 传播关系分析 | "传播关系"、"传播链"、"故障传播" | `knowledge/propagation.md` |
| 传播证据验证 | "同站点"、"对端网元"、"业务路径"、"验证证据"、"检查传播" | `knowledge/evidence.md` |

## 业务知识文件

业务知识位于 `knowledge/` 目录：

- `knowledge/nealarm.md`：获取网元告警的知识。
- `knowledge/propagation.md`：获取传播关系的知识。
- `knowledge/evidence.md`：验证传播证据的知识。

## 执行流程

### 步骤1：意图识别

在读取 knowledge 之前，必须先识别唯一主意图。

### 步骤2：读取匹配 knowledge

只读取当前意图对应的一个 knowledge 文件：

- 查询网元告警 → `knowledge/nealarm.md`
- 传播关系分析 → `knowledge/propagation.md`
- 传播证据验证 → `knowledge/evidence.md`

### 步骤3：提取业务变量

从用户输入和 knowledge 中提取：

- `intent`：业务意图。
- `entities`：网元 ID、网元名称、告警 ID、告警名称。
- `variables`：时间范围、工单范围、站点、对端网元、业务路径等。
- `constraints`：过滤条件、查询范围、证据校验范围。
- `goal`：最终分析目标。

### 步骤4：生成规划层定制输入

生成传给 `Ontology-based-planning-skill` 的定制输入，格式如下：

```json
{
  "intent": "传播关系分析",
  "goal": "分析指定网元和告警的故障传播关系",
  "knowledge": {
    "scenario": "alarm-propagation",
    "source": "knowledge/propagation.md",
    "summary": "当前意图对应的业务知识摘要"
  },
  "entities": {
    "neId": "用户输入的网元ID",
    "alarmName": "用户输入的告警名称"
  },
  "variables": {
    "timeRange": "用户输入或知识约束中的时间范围"
  },
  "constraints": {
    "scope": "工单范围或证据范围"
  },
  "stepOverrides": [
    {
      "stepId": "S2_search_subgraph",
      "input": {
        "query": "检索告警、网元、传播关系和证据验证相关本体子图"
      }
    }
  ]
}
```

如果某个字段没有从用户输入或 knowledge 中得到，不要编造，交给本体规划层返回结构化缺失项。

### 步骤5：委托本体规划层

将定制输入委托给 `Ontology-based-planning-skill`。本体规划层会基于默认流程完成：

1. 本体子图检索。
2. 对象、关系、函数候选识别。
3. 数据访问步骤生成。
4. 函数发现或调用。
5. 结果汇总。

## 术语替换约束

面向用户输出时禁止出现技术术语：

| 技术术语 | 替换为 |
|---|---|
| OAG | 本体子图 |
| OAC | 本体访问 |
| FUNCTION / Function | 函数能力 |
| OQL | 查询语言 |
| 知识本体 | 事件本体 |

严格禁止在用户最终输出中出现：OAG、OAC、FUNCTION、Function、OQL、subgraph、query、调用xxx工具/能力。

## 输入格式

支持以下输入格式：

```text
帮我分析网元 MC-PADANG 的告警传播
```

或包含工单信息：

```text
网元ID: 601851d2fcf2df6cca73d6d883fd1c15cdc7
告警: Ethernet Physical (ETPI) Send bandwidth usage rate threshold crossed
```

## Skill 调用协议

你不能直接调用任何原始 Tool。所有执行请求必须委托给 `Ontology-based-planning-skill`。

传入内容包括：

- `intent`
- `goal`
- `knowledge`
- `entities`
- `variables`
- `constraints`
- 可选的 `stepOverrides`、`stepAppends`、`stepSkips`
