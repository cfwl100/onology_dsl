# SEC OQL 扩展参数与 OAC 输入生成策略

## 1. 完整 OQL 优先

SEC 业务 Skill 能够确定查询动作、对象、字段、条件和返回内容时，应直接生成完整 `completeOql`，并按照 OAC Skill 输入模板传递给平台本体访问能力。

推荐输入结构：

```yaml
oacSkillInput:
  requestType: COMPLETE_OQL
  description: <本次 SEC 多维查询目的>
  completeOql: {...}
  messageType: <可选>
  validateOnly: false
```

平台 Skill 收到 `completeOql` 后，只做校验、紧凑化和执行，不应重新按关键词改写 `operation`。

---

## 2. extensions 命名空间

SEC 场景所有扩展参数必须放在 `completeOql.extensions.sec` 下：

```yaml
completeOql:
  extensions:
    sec:
      <key>: <value>
```

禁止将 SEC 扩展参数直接放到 OQL 顶层，也禁止放到 `oacSkillInput` 顶层。

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

不推荐在 `extensions.sec` 中表达跨步骤绑定，例如 `inputBinding`。跨步骤绑定属于业务 Skill 内部逻辑，应由业务 Skill 在生成下一步 `completeOql` 前完成。

---

## 4. SEC 分表时间扩展示例

```yaml
completeOql:
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

## 6. 后端倾向

业务 Skill 可以在 `completeOql.extensions.sec.targetBackend` 中声明后端倾向。

推荐：

```yaml
completeOql:
  extensions:
    sec:
      targetBackend: DAC
```

平台侧仍需根据 OAC 能力、schema mapping 和数据源 capability 做最终校验。后端倾向不是绕过 OAC 编译或能力校验的强制指令。

---

## 7. 多步查询策略

如果 OAC 不支持单条查询，业务 Skill 应自行拆分多步调用：

1. 为第一步生成独立 `oacSkillInput`。
2. 调用 OAC 并读取结果。
3. 将结果填入第二步 `completeOql`。
4. 为第二步生成独立 `oacSkillInput`。

禁止将业务 `workflow`、`executionPlan`、`stepId`、`dependsOn`、`variableBinding`、`fallbackPolicy` 传给平台 OAC。

---

## 8. 约束

1. `extensions` 只传递受控业务参数，不传物理查询语句。
2. `extensions.sec.targetBackend` 是后端倾向，不是强制绕过 OAC 编译。
3. `completeOql` 中的 object、field、relationship 必须来自本体模型或业务 Skill 已确认的模型配置。
4. 若使用扩展函数，函数必须在 OAC 扩展函数注册表中存在。
5. 多步执行顺序和变量绑定属于业务 Skill 内部逻辑，不属于平台 OAC 输入协议。