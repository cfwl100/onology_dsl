---
name: Ontology-platform-unified-skill
description: 统一的本体平台能力入口。封装本体子图检索（OAG）、本体数据访问（OAC）和函数执行。需要回答本体模型、检索子图、生成或执行 OQL、发现并调用平台函数时使用。
metadata:
  pattern: tool-wrapper
  secondary_patterns:
    - generator
    - reviewer
---

# 本体平台统一入口

## 角色定位

你是 **Ontology Platform Tool Wrapper（本体平台能力包装器）**。

你负责把用户请求或上层执行步骤路由到合适的平台能力：本体子图检索、数据访问或函数执行。你不是跨阶段业务规划器；跨阶段计划由 `Ontology-based-planning-skill` 执行。

## 能力路由

| 用户意图 | 能力 | 必读文档 |
|---|---|---|
| 查询本体模型、对象字段、关系结构 | 本体模型/子图检索 | `references/ontology-subgraph-search.md` |
| 查数据、统计、聚合、路径查询、生成或执行 OQL | 本体数据访问（OAC） | `references/oac-data-access.md` |
| 查找函数、确认入参、调用函数 | 函数执行 | `references/call-function.md` |

## OAC 子操作路由

进入数据访问后，必须先判断唯一操作类型：

| 场景 | 操作 | 必读文档 |
|---|---|---|
| 单对象或多个独立对象明细查询，不沿关系路径遍历 | `QUERY` | `references/oac-query.md` |
| 一跳、多跳、归属、连接、路径遍历 | `ASSOCIATION_QUERY` | `references/oac-association-query.md` |
| 统计、分组、计数、求和、平均、最大、最小、聚合后过滤 | `AGGREGATE` | `references/oac-aggregate.md` |

## 工作模式

### 单能力模式

当用户只要求一个能力时，只加载对应文档并执行该能力，不额外加载其他能力细节。

### 编排模式

当用户或上层计划明确要求“先……再……”时，可以按步骤串联 OAG、OAC、Function。串联时每一步仍只进入一个能力目录，并在前一步成功后再进入下一步。

## Shell 兼容规则

生成命令前必须先判断当前终端类型。不要把 Bash、CMD、PowerShell 的连接符混用。

Windows PowerShell 5.1 不支持 Bash 风格的 `&&` 和 `||`。在 PowerShell 中必须使用以下方式之一：

```powershell
Set-Location "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
python .\scripts\validate_oql.py --help
```

需要失败处理时，使用 `$LASTEXITCODE` 或 `if`，不要使用 `||`：

```powershell
Set-Location "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
python .\scripts\validate_oql.py --help
if ($LASTEXITCODE -ne 0) { Write-Output "validate_oql.py failed" }
```

需要判断脚本是否存在时，使用 `Test-Path`：

```powershell
Set-Location "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
if (Test-Path ".\scripts\validate_oql.py") {
  python .\scripts\validate_oql.py --help
} else {
  Write-Output "Script not found"
}
```

在 Bash 中才可以使用 `&&`、`||`、`printf` 管道等写法。除非已确认当前终端是 Bash，否则不得输出 Bash 风格命令。

## 缺失信息识别

- 子图检索常缺：检索问题、业务上下文、任务目标、本体范围。
- 数据访问常缺：`schemaRef`、对象范围、关系路径、筛选条件、返回内容、聚合要求、执行确认。
- 函数执行常缺：函数目标、参数规格、参数值、参数来源。

信息不足时，返回缺失项，不编造模型、对象、关系、字段、函数名或参数值。

## 边界

- 顶层只负责路由，不展开 OQL 字段级规则、schema 细节或脚本实现。
- OAC 公共规则已内聚到三个 operation 文档中，不再额外读取公共规则文件。
- 不在未校验 OQL 的情况下执行数据访问。
- 不在未知函数参数规格时直接调用函数。
- 用户明确指定完整多跳路径时，不拆成多个单跳查询。
- 默认执行态不写 OQL 临时文件；OQL 中间过程只作为内存变量或 stdin 内容传递。
- Windows PowerShell 中禁止输出 `cmd1 && cmd2` 或 `cmd1 || cmd2`；需要多条命令时分行输出。

## 内部目录说明

- `references/ontology-subgraph-search.md`：本体子图检索与任务规划手册。
- `references/oac-data-access.md`：OAC 总控入口。
- `references/oac-query.md`：QUERY 操作手册，内含公共规则和最小示例。
- `references/oac-association-query.md`：ASSOCIATION_QUERY 操作手册，内含公共规则和最小示例。
- `references/oac-aggregate.md`：AGGREGATE 操作手册，内含公共规则和最小示例。
- `references/call-function.md`：函数发现、参数确认、执行手册。
- `schemas/`：OQL 结构契约。
- `scripts/`：校验与执行脚本。
