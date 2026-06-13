# 共享约束规则库

本文档集中存放所有技能共享的约束规则，各 SKILL.md 文件应引用本文档而非重复这些内容。

---

## OAG 调用规则

### 子图搜索（ontology-subgraph-search）

- **Ontology ID**：调用 OAG 查询子图时，**必须**传入 `Ontology ID = network@1.0`
- **脚本调用**：`python scripts/semantic_subgraph_search.py --ontology-id network@1.0 --query '<query>'`
- **关系名获取**：必须从子图响应中的 `edges[].properties.name` 获取，不得臆造

---

## OAC 调用规则

### 数据访问（oac-data-access）

- **schemaRef**：调用 OAC 执行实例查询时，**必须**传入 `schemaRef = network@1.0`
- **objectType 值**：必须小写（如 `ne`, `alarm`, `site`），不得使用大写或驼峰命名
- **返回字段**：如果用户明确指定返回字段，必须精确使用，不能用 `*`

### 操作类型路由

| 用户关键词 | 操作类型 | 文档 |
|-----------|---------|------|
| "查XX有哪些属性"、"统计XX数量"、"没有提到对象间关系" | QUERY | `references/oac-query.md` |
| "聚合"、"分组"、"统计"、"求和"、"平均"、"计数"、"按XX分组" | AGGREGATE | `references/oac-aggregate.md` |
| "关系"、"路径"、"遍历"、"连接"、"经过"、"一跳"、"多跳" | ASSOCIATION_QUERY | `references/oac-association-query.md` |

---

## OQL JSON 格式规则

- **紧凑单行格式**：OQL JSON 必须为紧凑单行格式，**禁止**添加不必要的空格、缩进或换行
- **return 字段**：必须包含所有关系路径（r1, r2 等），不得遗漏
- **values 数组**：必须是字符串数组，如 `["value1"]`
- **操作符白名单（OQL v2.0）**：`EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `NOT_IN`, `BETWEEN`, `LIKE`, `CONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `IS_NULL`, `IS_NOT_NULL`, `IS_EMPTY`, `IS_NOT_EMPTY`

---

## 术语替换表

面向用户输出时，必须使用以下替换：

| 技术术语 | 替换为 |
|---------|--------|
| OAG | 本体子图 |
| OAC | 本体访问 |
| Function / FUNCTION | 函数能力 |
| OQL | 查询语言 |
| 知识本体 | 事件本体 |

**严格禁止在用户输出中出现**：OAG、OAC、FUNCTION、Function、OQL、subgraph、query

---

## 输出格式规则

### Echo 命令规范

| 场景 | 推荐写法 | 禁用写法 |
|------|---------|---------|
| 普通 JSON | `echo '{"k":"v"}'` | `echo "{\"k\":\"v\"}"` |
| JSON 含换行 | `echo '{"content":"line1\nline2"}'` | `echo '{"content":"line1\\nline2"}'` |
| 多行/大块 JSON | `cat <<'EOF' ... EOF` | 多行未压缩的 `echo` |
| 含中文字符 | 用单引号包裹即可 | 添加多余转义 |

### 禁止的模式

- **禁止**在助手回复文本中输出带 `message_type` 的结构化 JSON
- **禁止**在单次 echo 中混合多个阶段输出
- **禁止**在 JSON content 字段中使用 `\\n` 表示换行（应使用原始 `\n`）

### 输出格式约定

- **Plan 开始**：`echo '{"message_type":"sop","title":"规划阶段开始","content":""}'`
- **Plan 结束**：先 `echo 'PLAN_COMPLETE'`，再 `echo '{"message_type":"sop","title":"规划阶段结束","content":"..."}'`
- **Exec 阶段**：使用自然语言描述执行结果

---

## 文件路径规范

- **脚本调用**：从技能根目录调用，如 `python scripts/<script_name>.py`
- **证书路径**：使用 `SCRIPTS_ROOT / "tools" / "client.crt.pem"` 模式
- **知识文件**：位于各技能的 `knowledge/` 或 `references/` 目录

---

## 安全注意事项

- **禁止**记录或输出秘密、令牌或凭证
- 证书和密钥存储在 `tools/` 目录中
- 使用 `warnings.filterwarnings("ignore")` 抑制 HTTPS 警告

---

## 约束规则编号

本文档中的约束规则编号用于追踪：

1. OAG 调用必须使用 `network@1.0`
2. OAC 调用必须使用 `network@1.0`
3. objectType 必须小写
4. OQL JSON 必须紧凑单行
5. return 必须包含所有关系路径
6. 术语替换必须遵守替换表
7. JSON content 使用原始 `\n` 非 `\\n`
