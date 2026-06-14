# SEC OQL 扩展参数与 completeOql 生成策略

## 1. completeOql 优先

SEC 业务 Skill 能够确定查询动作、对象、字段、条件和返回内容时，应直接生成 `completeOql`，并通过 `executionPlan.steps[].completeOql` 传递给 `Ontology-based-planning-skill`。

平台 Skill 收到 `completeOql` 后，只做校验、紧凑化和执行，不应重新按关键词改写 operation。

---

## 2. extensions 命名空间

SEC 场景所有扩展参数必须放在：

```yaml
extensions:
  sec:
    <key>: <value>
```

禁止将 SEC 扩展参数直接放到 OQL 顶层。

---

## 3. 推荐扩展字段

| 字段 | 说明 |
|---|---|
| `extensions.sec.queryScene` | 业务查询场景，如 `COMPOSITE_DIMENSION` |
| `extensions.sec.targetBackend` | 后端倾向，如 `DAC`、`OntoAccess` |
| `extensions.sec.dacAction` | DAC 操作类型，如 `AGGRE_XDR` |
| `extensions.sec.partitionTime` | 分表时间策略 |
| `extensions.sec.dimensionLift` | 是否使用多维模型升维能力 |
| `extensions.sec.relationResolve` | 关系主键解析策略 |
| `extensions.sec.deduplicateMetrics` | 是否需要指标去重 |
| `extensions.sec.inputBinding` | 多步骤输入绑定说明 |

---

## 4. SEC 分表时间扩展示例

```yaml
extensions:
  sec:
    targetBackend: DAC
    dacAction: AGGRE_XDR
    partitionTime:
      timeMode: UTC
      sourceTimeZone: Asia/Shanghai
      partitionField: "3600"
```

---

## 5. ID / NAME 维度函数策略

推荐使用结构化函数表达式：

```yaml
kind: EXPR
expr:
  kind: FUNCTION
  namespace: sec
  name: NAME
  args:
    - kind: FIELD
      ref: o
      field: release_cause
alias: release_cause_name
```

不推荐写成普通字符串：

```yaml
kind: FUNCTION
field: NAME(release_cause)
```

---

## 6. sourcePolicy 与后端倾向

业务 Skill 可以在 `semanticHints.sourcePolicy` 或 `completeOql.extensions.sec.targetBackend` 中声明后端倾向。

推荐策略：

```yaml
sourcePolicy:
  preferredBackend: DAC
  fallbackBackend: OntoAccess
  splitIfUnsupported: true
```

平台侧仍需根据 OAC 能力、schema mapping 和数据源 capability 做最终校验。

---

## 7. 约束

1. `extensions` 只传递受控业务参数，不传物理查询语句。
2. `extensions.sec.targetBackend` 是后端倾向，不是强制绕过 OAC 编译。
3. `completeOql` 中的 object、field、relationship 必须来自本体模型或业务 Skill 已确认的模型配置。
4. 如果 OAC 不支持单条查询，应由业务 Skill 生成多步 `executionPlan`，而不是把复杂物理逻辑塞进 `extensions`。
5. 若使用扩展函数，函数必须在 OAC 扩展函数注册表中存在。
