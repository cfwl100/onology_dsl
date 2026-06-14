# SEC 时间语义与分表时间规则

## 1. 职责

本文件定义 SEC 多维查询中，自然语言时间表达到 OQL 条件和 `extensions.sec.partitionTime` 的映射规则。

业务 Skill 负责识别用户原始问题中的时间语义，并将结果注入到 `completeOql.conditions` 与 `completeOql.extensions.sec.partitionTime`。

---

## 2. 时间模式

SEC 场景支持两类分表时间：

| timeMode | 含义 | 适用场景 |
|---|---|---|
| `LOCAL_TIME` | 本地时间 | 用户明确说“本地时间”、业务默认按本地账期/本地自然日切分 |
| `UTC` | UTC 时间 | 用户明确说“UTC”、数据源按 UTC 时间戳分表 |

如果用户未明确指定，按场景配置决定默认值。建议 SEC 默认：

```yaml
defaultTimeMode: UTC
defaultSourceTimeZone: Asia/Shanghai
```

---

## 3. OQL 条件注入

时间范围必须进入 `conditions`：

```yaml
conditions:
  - ref: o
    field: "3600"
    operator: GTE
    values: ["<startEpoch>"]
  - ref: o
    field: "3600"
    operator: LT
    values: ["<endEpoch>"]
```

---

## 4. extensions 注入

SEC 分表时间相关扩展参数必须放到：

```yaml
extensions:
  sec:
    partitionTime:
      timeMode: UTC
      sourceTimeZone: Asia/Shanghai
      partitionField: "3600"
```

字段说明：

| 字段 | 说明 |
|---|---|
| `timeMode` | `UTC` 或 `LOCAL_TIME` |
| `sourceTimeZone` | 原始业务时间所属时区，例如 `Asia/Shanghai` |
| `partitionField` | 分表时间字段，例如 `3600` |
| `timeRangeSource` | 可选，说明时间来自用户输入、业务默认值或上一步结果 |

---

## 5. 约束

1. 时间范围必须写入 `conditions`，不能只写入 `extensions`。
2. `extensions.sec.partitionTime` 只描述分表时间策略，不能替代过滤条件。
3. 不得在 `extensions` 中写物理查询语句。
4. 如果用户没有给时间，且业务场景要求必须给时间，应返回缺失信息。
5. 如果业务场景允许默认时间，必须在 `extensions.sec.partitionTime.timeRangeSource` 标明默认来源。
