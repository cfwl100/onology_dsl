# SEC OQL 扩展参数自然语言注入策略

本文说明业务 Skill 如何通过自然语言方式向平台表达 OQL 扩展诉求。这里不要求平台 Skill 支持新的输入模板，也不要求平台识别 `completeOql`、`oacSkillInput`、`executionPlan` 等协议。

## 1. 基本原则

1. 业务 Skill 不直接修改平台 Skill。
2. 业务 Skill 不直接生成 DAC 私有请求。
3. 业务 Skill 可以在自然语言委托中明确要求：生成 OQL 时，如果支持 `extensions`，请把 SEC 扩展诉求放入 `extensions.sec`。
4. 时间、后端倾向、维度升维、关系解析等扩展诉求，都以自然语言说明。
5. 如果平台或 OAC 当前不支持某个扩展参数，应返回能力缺失说明，不得伪造执行结果。

## 2. SEC 扩展诉求表达方式

### 分表时间

自然语言表达：

```text
这是 SEC 分表时间查询。生成 OQL 时，如果支持 extensions，请在 extensions.sec.partitionTime 中表达 timeMode、sourceTimeZone、partitionField；同时仍需把时间范围作为 conditions 条件。
```

### DAC 后端倾向

自然语言表达：

```text
这是 SEC 多维模型查询，优先按 DAC 多维模型映射执行；不要直接生成 DAC 私有请求，由 OAC 根据本体映射决定是否下发到 DAC。
```

### 维度升维

自然语言表达：

```text
这是归属过滤的多维查询。如果多维模型支持通过栅格维度过滤并返回小区维度，请使用 QUERY，并在生成 OQL 时通过扩展参数表达 dimensionLift=true；如果不支持，则由本业务 Skill 改走两步查询。
```

### 关系主键解析

自然语言表达：

```text
这是关系主键发现步骤。请通过 ASSOCIATION_QUERY 从 grid 沿 locateIn 关系查询 cell 的 CELL_ID；如 OQL 支持 extensions，请表达 relationResolve=GRID_TO_CELL。
```

### ID / NAME 维度函数

自然语言表达：

```text
返回字段需要区分 ID 维度和名称维度。生成 OQL 时，如果支持维度函数，请使用 ID(field) 或 NAME(field)；如果不支持，请明确能力缺失。
```

## 3. 禁止事项

1. 禁止把 `extensions` 当成绕过 schema、mapping、能力校验的通道。
2. 禁止在 `extensions` 中写物理 SQL、GQL、TQL。
3. 禁止直接写 DAC 私有请求结构。
4. 禁止把跨步骤变量绑定交给平台 Skill；变量读取和填充由业务 Skill 自己完成。
5. 禁止因为用户说“归属”就一律改成 `ASSOCIATION_QUERY`，必须先判断是否支持多维模型维度升维。
