# 业务 Skill 定制契约

本文件定义上层业务 Skill 如何在不侵入平台 Skill 的情况下定制 `Ontology-based-planning-skill` 的默认流程。

## 定制目标

`Ontology-based-planning-skill` 自带默认本体子图规划流程。上层业务 Skill 可以在默认流程上做业务定制，而不是复制或改写平台 Skill 本身。

## 可定制内容

| 字段 | 类型 | 作用 |
|---|---|---|
| `intent` | string | 业务意图，例如告警查询、传播关系分析、证据验证。 |
| `knowledge` | object/string | 业务知识、规则、SOP、判断依据。 |
| `variables` | object | 变量值，例如网元 ID、告警名称、时间范围、工单范围。 |
| `constraints` | object | 过滤条件、范围限制、执行约束。 |
| `stepOverrides` | array | 替换默认步骤。 |
| `stepAppends` | array | 在默认流程后追加步骤。 |
| `stepSkips` | array | 跳过默认步骤，必须给出原因。 |
| `failurePolicy` | string/object | 覆盖默认失败策略。 |

## 合并优先级

从高到低：

1. 用户在当前请求中显式给出的值。
2. 上层业务 Skill 传入的 `variables`。
3. 上层业务 Skill 传入的 `knowledge`。
4. 上层业务 Skill 传入的步骤改写。
5. 默认本体子图规划流程。

冲突时必须说明冲突来源，不得静默覆盖用户显式输入。

## 定制输入示例

```json
{
  "intent": "传播关系分析",
  "knowledge": {
    "scenario": "alarm-propagation",
    "rules": ["先找告警相关对象和传播关系", "再查询实例告警和传播证据"]
  },
  "variables": {
    "neId": "601851d2fcf2df6cca73d6d883fd1c15cdc7",
    "alarmName": "Ethernet Physical Send bandwidth usage rate threshold crossed"
  },
  "stepOverrides": [
    {
      "stepId": "S2_search_subgraph",
      "input": {
        "query": "检索告警、网元、传播关系、证据验证相关本体子图"
      }
    }
  ],
  "stepAppends": [
    {
      "stepId": "S8_business_summary",
      "actionType": "SUMMARY",
      "input": {
        "format": "面向故障传播分析的用户结论"
      },
      "expectedOutput": ["businessConclusion"]
    }
  ]
}
```

## stepOverrides 规则

- 只能覆盖默认步骤的 `input`、`expectedOutput`、`failurePolicy`、`notes`。
- 不得把 `OAG` 步骤覆盖成直接原始工具调用。
- 不得删除检查点。
- 如果覆盖 `actionType`，必须说明原因，并重新满足步骤契约。

## stepAppends 规则

- 追加步骤必须包含 `stepId`、`actionType`、`input`、`expectedOutput`。
- 追加步骤可以依赖默认步骤输出。
- 追加步骤不得引用不存在的输出字段。

## stepSkips 规则

跳过默认步骤必须提供：

```json
{
  "stepId": "S5_discover_function",
  "reason": "当前任务只需要数据查询，不需要函数执行"
}
```

不得因为缺少输入而跳过必要步骤；缺少输入应返回缺失项。

## 输出要求

最终输出中应保留：

- 使用了哪些默认步骤。
- 哪些步骤被业务 Skill 覆盖。
- 哪些业务知识被用于规划。
- 哪些变量被绑定到平台能力输入。
- 哪些步骤未执行以及原因。
