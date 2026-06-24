# 本体数据访问（OAC）

## 1. 角色定位

OAC 是本体平台的数据访问总控入口，负责把自然语言数据访问需求路由到唯一的 OQL 操作手册，并组织 schema、validator、executor 的闭环。

OAC 只负责“生成、校验、必要时执行 OQL，并返回对象结构结果”。它不负责本体子图检索，不负责业务意图识别，不负责函数调用。

对上层自然语言模板只暴露公共 `本体ID`。平台内部生成 OQL 时，将该 `本体ID` 作为 OQL 的 `schemaRef` 来源。

## 2. 输入来源和优先级

OAC 输入由两类信息结合生成：

1. 本体子图依据：来自 OAG 的 `result.nodes`、`result.edges`、`result.functions` 等结构结果。
2. 业务定制知识：来自业务 Skill 注入文件，包括查询内容、查询类型、返回字段、过滤条件、排序分组、空结果策略等。

业务定制文件中的步骤级 OAC 规则优先级最高，可覆盖本文件中的默认输入模板、返回要求、执行规则和空结果策略。

但业务定制不能凭空制造平台事实：查询对象必须来自子图确认的 `objectType`，字段必须来自子图确认的 `property + has_property`，关系必须来自子图确认的 `defines_relation.properties.name`，OQL 结构必须通过 schema 和 validator。

## 3. 操作类型

| 操作类型 | 适用场景 | 子文档 |
|---|---|---|
| `QUERY` | 单对象或多个独立对象明细查询，不沿关系路径遍历 | `oac-query.md` |
| `ASSOCIATION_QUERY` | 一跳、多跳、归属、连接、路径遍历 | `oac-association-query.md` |
| `AGGREGATE` | 统计、分组、计数、求和、平均、最大、最小、聚合后过滤 | `oac-aggregate.md` |

## 4. 面向自然语言的固定输入模板

Planning 层委托 OAC 时默认使用以下模板；如果业务定制文件提供了步骤级 OAC 模板，以业务定制文件为准。

```text
查数据
本体ID：<公共本体ID，平台侧作为 schemaRef 来源>
操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE / 模型查询，如可判断>
查询对象：<对象类型和别名建议，来自子图 objectType>
关系路径：<仅在关系查询时填写，关系名必须来自 defines_relation.properties.name>
过滤条件：<用户条件及其对应字段依据；单位换算和枚举值说明>
返回要求：<返回字段、排序、分组、maxResults、空结果策略；可被业务定制文件覆盖>
执行要求：先生成并校验 OQL；通过后再执行；结果为空视为有效结果，不自动放宽条件重试。
期望输出：只返回对象结构结果，包含 objects 和 relationships；不输出 operationDecision、oql、validation。
```

最小输入应包含：

```text
本体ID：<公共本体ID>
操作类型：<QUERY / ASSOCIATION_QUERY / AGGREGATE，如可判断>
查询对象：<来自子图 objectType>
本体子图依据：<至少包含对象和字段归属；关系查询还要包含关系名>
返回要求：<需要返回什么>
```

## 5. 最终输出格式

OAC 最终输出必须是对象结构。

```json
{
  "objects": [],
  "relationships": []
}
```

输出规则：

- `objects[]` 表示查询返回的对象实例。
- `objects[].id` 表示对象实例 ID。
- `objects[].type` 表示对象类型。
- `objects[].props` 表示返回属性。
- `relationships[]` 表示对象间关系结果；没有关系时返回空数组。
- 查询成功但结果为空时返回 `{ "objects": [], "relationships": [] }`。
- 错误或缺失信息由外层步骤状态或 S7 汇总说明，不混入对象结构字段。

## 6. 执行流程

1. 根据自然语言数据访问需求判断唯一 OAC 操作类型。
2. 读取对应 operation 操作手册。
3. 读取对应 schema。operation 手册内已包含最小示例。
4. 基于本体ID、操作类型、查询对象、关系路径、过滤条件、返回要求、执行要求、期望输出生成 OQL JSON。
5. 使用 `scripts/validate_oql.py` 校验。默认通过 `--oac-json` 或 `--input -` 传入 OQL，不写 `temp_oql*.json` 临时文件。
6. 校验失败时修复，不得执行。
7. 用户或 planning 明确要求执行时，调用 `scripts/execute_oac_operation.py`。默认通过 `--oac-json` 或 `--input -` 传入 OQL，不写临时输入文件。
8. 将执行结果转换为 `{objects, relationships}` 对象结构返回。

## 7. Schema 权威规则

OQL 顶层结构、`version`、`schemaRef`、`returns` 类型、字段语法、`maxResults` 格式等以对应 schema 为准。

当前本体 Skill 的 OQL 初始版本统一为 `version: "1.0"`。生成 OQL 时必须使用 schema 中声明的版本，不得从历史样例沿用其他版本号。

## 8. 路由判断

- 只查对象属性、明细、列表、字段值 → `QUERY`。
- 明确提到关系、路径、遍历、归属、连接、一跳、多跳 → `ASSOCIATION_QUERY`。
- 明确提到统计、聚合、分组、计数、求和、平均、最大、最小 → `AGGREGATE`。

## 9. 输入边界

- `本体ID` 是自然语言模板的必需输入，并作为生成 OQL 时的 `schemaRef` 来源。
- 查询对象必须来自 OAG 子图确认的 `objectType`。
- 字段必须来自 OAG 子图确认的 `property`，并通过 `has_property` 确认归属。
- 关系必须来自 OAG 子图确认的 `defines_relation.properties.name`。
- 自然语言中的单位、同义词、业务别名可以由业务 Skill 说明，但最终 OQL 字段名必须是平台字段。
- 业务定制知识中的查询类型和返回字段可覆盖默认模板，但不能越过 schema、validator 和子图确认结果。

## 10. 校验与执行：无临时文件优先

| 脚本 | 作用 | 默认推荐调用 |
|---|---|---|
| `scripts/validate_oql.py` | 对 OQL JSON 做结构和语义校验。 | `python scripts/validate_oql.py --oac-json '<compact-json>'` |
| `scripts/execute_oac_operation.py` | 在用户或 planning 明确要求执行时调用 OAC 服务。 | `python scripts/execute_oac_operation.py --oac-json '<compact-json>' --message-type '<type>'` |

执行前必须先完成 `validate_oql.py` 校验。校验失败时只修复 OQL，不直接执行。

### 10.1 跨平台 Shell 兼容规则

不要生成跨 Shell 混合命令。先识别当前环境，再选择命令样式。

#### Windows PowerShell 5.1 / PowerShell 7+

```powershell
Set-Location "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
python .\scripts\validate_oql.py --oac-json '<compact-single-line-oql-json>'
if ($LASTEXITCODE -eq 0) {
  python .\scripts\execute_oac_operation.py --oac-json '<compact-single-line-oql-json>' --message-type '<message_type>'
}
```

#### Windows CMD

```bat
cd /d "C:\Users\a\.config\opencode\skills\Ontology-platform-unified-skill"
python scripts\validate_oql.py --oac-json "<compact-single-line-oql-json>" && python scripts\execute_oac_operation.py --oac-json "<compact-single-line-oql-json>" --message-type "<message_type>"
```

#### Bash / zsh / Linux / macOS / WSL / Git Bash

```bash
cd "/path/to/Ontology-platform-unified-skill"
printf '%s' '<compact-single-line-oql-json>' | python scripts/validate_oql.py --input -
```

#### 未知 Shell 的最低风险写法

```text
进入 Ontology-platform-unified-skill 目录
python scripts/validate_oql.py --oac-json '<compact-single-line-oql-json>'
```

未知 Shell 时只输出逐行命令，不输出 `&&`、`||`、管道或 Shell 专属变量。
