# ID / NAME 维度函数语义

## 1. 背景

SEC 多维模型中，同一个维度字段可能需要区分“ID 维度”和“名称维度”。业务 Skill 需要在 OQL 的 `returns` 中显式表达字段类型，避免 OAC / DAC 无法判断返回的是标识还是名称。

---

## 2. 语义规则

| 用户表达 | 语义 | 推荐 OQL 表达 |
|---|---|---|
| ID、标识、编号、id(field) | ID 维度 | `sec.ID(field)` |
| 名称、名字、name(field) | 名称维度 | `sec.NAME(field)` |
| 普通指标、度量 | 指标字段 | `FIELDS` |

---

## 3. 推荐函数表达式

业务 Skill 应使用 OQL 结构化函数表达式，不要把函数写成普通字符串。

### 名称维度

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "namespace": "sec",
    "name": "NAME",
    "args": [
      { "kind": "FIELD", "ref": "o", "field": "release_cause" }
    ]
  },
  "alias": "release_cause_name"
}
```

### ID 维度

```json
{
  "kind": "EXPR",
  "expr": {
    "kind": "FUNCTION",
    "namespace": "sec",
    "name": "ID",
    "args": [
      { "kind": "FIELD", "ref": "o", "field": "interface" }
    ]
  },
  "alias": "interface_id"
}
```

---

## 4. 维度样式映射

OAC / DAC 适配时可将函数语义转换为维度样式：

```yaml
sec.ID(field):
  type: DIMENSION
  style: IDENTIFIER

sec.NAME(field):
  type: DIMENSION
  style: NAME
```

---

## 5. 约束

1. `sec.ID` 和 `sec.NAME` 必须是 OAC 函数注册表中的受控函数。
2. 业务 Skill 不得生成未注册函数。
3. 如果函数未注册，应返回缺少函数能力，不得降级为字符串拼接。
4. 普通指标和度量不应使用 `ID` / `NAME` 函数。
