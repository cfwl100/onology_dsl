# Skill 重构提示词 - OQL 分层设计

## 重构目标

将当前 Skill 按照**分层设计思想**进行重构，实现以下目标：

1. **稳定的用户意图放在上层** - 描述"做什么"，不涉及"怎么做"
2. **易变的结构规则放在下层** - 承载 OQL 语法细节，可独立演进
3. **有副作用的执行能力收口到末端** - 执行能力统一由 `execute-request` 处理
4. **支撑 OQL 规范承载** - 能够完整承载《本体对象操作语言(OQL)-DSL规范v1.2-agent最终版.md》中的语法描述
5. **支持 S-OQL 到 OQL 的完整链路** - Agent/LLM 生成 S-OQL → 转换 → 执行

---

## 一、分层架构设计

### 第 1 层：意图层（Top Layer）- `ontology-data-access/SKILL.md`

**职责**：用户意图识别与路由

**设计原则**：
- 只表达"做什么"，不暴露"怎么做"
- 不出现 upsert、batch 等具体实现细节
- 根据用户意图路由到对应的操作类别 Skill
- 识别用户意图缺失的关键信息

**输出内容示例**：
```markdown
# 本体对象数据访问

## 意图识别
- 读取数据 → 路由到 object-query
- 统计/聚合 → 路由到 aggregate-query
- 创建对象 → 路由到 create-object
- 修改对象 → 路由到 update-object
- 删除对象 → 路由到 delete-object
- 关联路径查询 → 路由到 association-query
- 关系导航查询 → 路由到 link-query
```

### 第 2 层：操作层（Operation Layer）- 各目录的 `SKILL.md`

**职责**：特定操作的入口，承载该操作的 OQL 语法边界

**设计原则**：
- 引用 OQL 规范中的具体章节
- 定义该操作的输入输出契约
- 包含该操作特有的约束检查清单
- 调用下层的 references 和 scripts 完成具体工作

**当前 9 个操作类别**：
| 目录 | 操作类型 | OQL Operation |
|------|----------|----------------|
| object-query | 普通对象查询 | QUERY |
| aggregate-query | 聚合查询 | AGGREGATE |
| association-query | 关联路径查询 | ASSOCIATION_QUERY |
| link-query | 关系导航查询 | LINK_QUERY |
| create-object | 创建对象 | CREATE |
| update-object | 更新对象 | UPDATE |
| delete-object | 删除对象 | DELETE |
| upsert-batch | 批量操作 | UPSERT / BATCH |
| execute-request | 执行请求 | - |

### 第 3 层：语法层（References）- `references/*.md`

**职责**：承载 OQL 规范的语法描述

**设计原则**：
- 每个操作类别有独立的 references 目录
- 只包含该操作类别的语法描述，不包含其他类别
- 从《本体对象操作语言(OQL)-DSL规范v1.2-agent最终版.md》中提取相关章节
- 包含 S-OQL 与 canonical OQL 的对照说明

**文件命名规范**：
```
references/
├── syntax-details.md      # 核心语法细节（必选）
├── operator-reference.md  # 操作符参考
├── examples.md            # 示例集合
└── validation-rules.md    # 校验规则说明
```

### 第 4 层：转换层（Scripts）- `scripts/*.py`

**职责**：结构转换、组装、校验

**设计原则**：
- `soql_to_oql.py` - S-OQL 到 canonical OQL 的转换
- `oql_builder.py` - OQL 补全与组装
- `oql_validator.py` - OQL 结构校验

---

## 二、S-OQL 语法设计

### S-OQL 设计目标

S-OQL（Simplified OQL）是比 canonical OQL 更简洁的语法，专为 LLM/Agent 生成设计。

### S-OQL 简化规则

| 模块 | Canonical OQL | S-OQL |
|------|---------------|-------|
| conditions | `{"kind":"PREDICATE","ref":"a","field":"name","operator":"EQ","values":["test"]}` | `["a.name","EQ","test"]` |
| conditions (null) | `{"kind":"PREDICATE","ref":"a","field":"name","operator":"IS_NULL"}` | `["a.name","IS_NULL"]` |
| conditions (group) | `{"kind":"GROUP","relation":"AND","children":[...]}` | `{"all":[...]}` |
| returns (FIELDS) | `{"kind":"FIELDS","ref":"a","fields":["id","name"]}` | `["FIELDS","a",["id","name"]]` |
| returns (METRIC) | `{"kind":"METRIC","function":"COUNT","ref":"a","field":"id","alias":"cnt"}` | `["METRIC","COUNT","a.id","cnt"]` |
| mutation.data | `{"data":{"properties":{"name":"test"}}}` | `{"data":{"name":"test"}}` |

### S-OQL 保留字段（不简化）

以下字段保持 canonical OQL 格式，不做简化：
- `version`
- `schemaRef`
- `strict`
- `operation`
- `objects`
- `relationships`
- `orders`
- `maxResults`
- `options`
- `extensions`
- `sourceQuery`
- `linkQuery`
- `mutation.scope`

---

## 三、重构清单

### 3.1 重构 `ontology-data-access/SKILL.md`

- [ ] 移除具体实现细节（upsert、batch 等）
- [ ] 仅保留意图识别与路由逻辑
- [ ] 添加意图缺失信息识别能力

### 3.2 重构各操作目录的 `SKILL.md`

- [ ] 添加对 OQL 规范具体章节的引用
- [ ] 明确输入契约（需要用户提供什么信息）
- [ ] 明确输出契约（生成什么格式的 S-OQL）
- [ ] 添加该操作特有的约束检查清单

### 3.3 重构 `references/` 目录

- [ ] 为每个操作类别创建独立的 references 目录
- [ ] 从 OQL 规范中提取相关语法描述
- [ ] 添加 S-OQL 语法示例
- [ ] 区分"必填"与"可选"字段

### 3.4 重构 `scripts/` 目录

- [ ] 确保 `soql_to_oql.py` 处理所有 S-OQL 简化场景
- [ ] 确保 `oql_validator.py` 覆盖所有校验规则
- [ ] 添加详细的转换/校验错误信息

### 3.5 统一输出约定

- [ ] 所有操作层 Skill 只输出 S-OQL JSON
- [ ] 结构化错误使用统一格式
- [ ] 不输出 Markdown 解释

---

## 四、文件结构示例

```
ontology-data-access-suite-full-v3.3/
├── CLAUDE.md
├── ontology-data-access/
│   └── SKILL.md                    # 第1层：意图识别与路由
├── object-query/
│   ├── SKILL.md                    # 第2层：QUERY 操作入口
│   ├── references/
│   │   ├── syntax-details.md       # 第3层：QUERY 语法细节
│   │   ├── operator-reference.md
│   │   └── examples.md
│   └── scripts/
│       ├── soql_to_oql.py          # S-OQL → OQL
│       ├── oql_builder.py          # OQL 组装
│       └── oql_validator.py        # OQL 校验
├── aggregate-query/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── create-object/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── update-object/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── delete-object/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── association-query/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── link-query/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── upsert-batch/
│   ├── SKILL.md
│   ├── references/
│   │   └── ...
│   └── scripts/
│       └── ...
├── execute-request/
│   ├── SKILL.md
│   └── scripts/
│       └── ...
└── shared/
    └── soql_to_oql.py              # 公共转换逻辑
```

---

## 五、SKILL.md 模板

### 5.1 顶层入口模板（ontology-data-access）

```markdown
---
name: ontology-data-access
description: 处理本体对象数据访问的通用自然语言意图，将请求路由到对应的操作实现。
---
# 本体对象数据访问

## 职责
1. 识别用户意图（读取/统计/创建/修改/删除/关联）
2. 判断意图是否完整，识别缺失的关键信息
3. 路由到对应的操作类别 Skill

## 意图类型与路由
| 用户意图 | 路由目标 |
|----------|----------|
| 查询对象数据 | object-query |
| 统计/聚合 | aggregate-query |
| 路径关联查询 | association-query |
| 关系导航 | link-query |
| 创建新对象 | create-object |
| 修改对象 | update-object |
| 删除对象 | delete-object |
| 批量操作 | upsert-batch |

## 约束
- 不暴露具体的实现细节（如 upsert、batch 的参数）
- 只表达用户意图，不做技术实现决策
- 缺失信息时请求用户补充
```

### 5.2 操作层模板（以 object-query 为例）

```markdown
---
name: object-query
description: 处理普通对象查询请求，生成 S-OQL 并转换为 OQL。
---
# 普通对象查询

## 规范来源
- 参见《本体对象操作语言(OQL)-DSL规范v1.2-agent最终版.md》第 X 章

## 输入要求
用户需要提供：
- 查询对象（objects）
- 返回字段（returns）

## S-OQL 生成规则
根据 references/syntax-details.md 生成 S-OQL 结构：
- conditions: 使用简化三元组格式
- returns: 使用简化元组格式
- orders/maxResults: 保持 canonical 格式

## 转换流程
1. 生成 S-OQL JSON
2. 调用 scripts/soql_to_oql.py 转换为 canonical OQL
3. 调用 scripts/oql_validator.py 校验
4. 输出校验通过后的 JSON

## 约束
- 仅生成 QUERY 操作
- 不涉及聚合、关联、mutation
- 缺失 objects 或 returns 时返回结构化错误
```

### 5.3 References 语法模板

```markdown
# {操作类型} 语法细节

## 适用操作
- OQL Operation: {QUERY/AGGREGATE/CREATE/...}
- 规范章节：第 X 章

## 字段说明

### 必填字段
| 字段 | 类型 | 说明 |
|------|------|------|
| operation | string | 操作类型 |
| objects | array | 查询对象列表 |

### 可选字段
| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| conditions | array | [] | 筛选条件 |
| returns | array | [] | 返回字段 |
| orders | array | [] | 排序规则 |

## S-OQL 语法

### conditions
- 三元组: `["ref.field", "operator", "value"]`
- 二元组: `["ref.field", "IS_NULL"]`
- 逻辑组: `{"all":[...]}` / {"any":[...]} / {"not":...}`

### returns
- 字段投影: `["FIELDS", "ref", ["field1", "field2"]]`

## 校验规则
1. operation 必须为 {QUERY}
2. objects 不能为空
3. ...
```

---

## 六、执行流程

```
用户自然语言
    ↓
ontology-data-access（意图识别）
    ↓
object-query（生成 S-OQL）
    ↓
soql_to_oql.py（S-OQL → OQL）
    ↓
oql_validator.py（校验）
    ↓
execute-request（执行 OQL）
    ↓
返回结果
```

---

## 七、注意事项

1. **不要重复描述** - references 只描述该操作类别特有的语法，不要包含其他类别
2. **保持简洁** - SKILL.md 是入口，不是完整文档，详细内容下沉到 references
3. **版本同步** - OQL 规范更新时，只需修改对应的 references 文件
4. **错误信息** - 校验失败时返回结构化错误，包含缺失字段和错误原因
5. **S-OQL 优先** - 所有操作层 Skill 输出 S-OQL，由转换层处理 canonical 格式