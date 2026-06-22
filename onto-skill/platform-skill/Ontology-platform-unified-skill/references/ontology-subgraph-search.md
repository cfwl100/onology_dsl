# OAG 本体子图检索

## 1. 本层职责

OAG 是本体子图检索能力，负责根据自然语言业务意图和公共 `本体ID` 检索对象、属性、关系、函数候选，为 Planning、OAC、Function 提供可信结构依据。

OAG 只负责“找本体能力和结构依据”，不负责生成 OQL、不负责执行数据查询、不直接调用函数。

## 2. 输入来源和优先级

OAG 输入可以来自：

- 用户问题或 Planning 层整理后的详细 `业务意图`。
- 公共 `本体ID`。
- 业务定制的子图检索规则文件。
- 业务定制的子图返回结构要求。
- Planning 层基于默认流程或业务规则生成的检索目标。

业务定制文件可以自然语言描述，不要求拆成 JSON。常见内容包括：固定 query 模板、语义扩展策略、优先对象、方向、最大跳数、是否返回函数候选、返回哪些子图字段等。

业务定制文件中的 S2 子图检索规则优先级最高，可覆盖本文件中的默认输入模板、检索策略、检索目标、返回结构要求和失败策略。

## 3. 面向自然语言的输入模板

Planning 层委托 OAG 时默认使用以下模板；如果业务定制文件提供了 S2 子图检索模板，以业务定制文件为准。

```text
先找相关子图。
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题，用于检索对象、属性、关系、函数候选>
业务定制文件：<已读取的子图检索规则文件或场景知识文件；业务定制模式必填>
子图检索规则：<业务定制的检索策略、固定 query 模板、扩展方向、最大跳数、是否返回函数候选等；可覆盖默认规则>
检索目标：<需要检索哪些对象、属性、关系、函数候选；不得提前编造平台字段名>
子图返回结构要求：<业务希望从 result.seedNodes / nodes / edges / functions / actions 中保留哪些字段内容；未指定时保留完整原始 result>
期望输出：返回 OAG 原始图结构 JSON，包括 result.seedNodes、result.nodes、result.edges、result.functions、result.actions；同时按业务返回结构要求输出可用于后续规划的对象、字段归属、关系候选和函数候选摘要。
```

最小输入为：

```text
本体ID：<公共本体ID>
业务意图：<改写后的详细自然语言问题>
业务定制文件：<业务定制模式下必填；默认规划模式可写无>
```

脚本调用时，将 `业务意图`、`子图检索规则`、`检索目标` 和 `业务知识补充` 整理为自然语言 query，并传入 `--ontologyId`：

```bash
python scripts/semantic_subgraph_search.py --query "<自然语言检索问题>" --ontologyId "<本体ID>"
```

## 4. 参数契约

必填参数：

- `query`：由业务意图、检索规则、检索目标和业务知识补充整理后的自然语言检索问题。
- `ontologyId`：公共本体ID。

可选参数：

- `similarityThreshold`：相似度阈值，默认 `0.6`，可被业务定制文件覆盖。
- `includeFunctions`：是否返回 Function，默认由业务意图和检索规则决定。
- `includeActions`：是否返回 Action，默认 `0`。
- `seedRetrievalMode`：种子节点检索模式，默认 `vector`，可被业务定制文件覆盖。
- `topK`：种子节点语义检索 topK，默认 `3`，可被业务定制文件覆盖。
- `graphExpansionStrategy`：子图扩展策略，默认 `minimal`，可被业务定制文件覆盖。
- `hopLimit`：`khop` 策略下的扩散深度，默认 `3`，可被业务定制文件覆盖。

## 5. 输出格式

OAG 输出必须保留原始图结构，并按业务定制返回结构要求生成规划摘要。

推荐输出：

```text
## OAG 输出

### 1. 原始图结构
- result.seedNodes：<原始 seedNodes>
- result.nodes：<原始 nodes>
- result.edges：<原始 edges>
- result.functions：<原始 functions>
- result.actions：<原始 actions>

### 2. 检索摘要
- 命中的业务主题：...
- 相关对象：...
- 相关属性：...
- 相关关系：...
- 相关函数候选：...

### 3. 规划可用依据
- 可用于 OAC 的对象类型：来自 nodes[label=objectType]
- 可用于 OAC 的字段及归属对象：来自 nodes[label=property] + has_property
- 可用于 ASSOCIATION_QUERY 的关系名：来自 edges[edgeType=defines_relation].properties.name
- 可用于 Function 调用的函数候选：来自 result.functions

### 4. 按业务返回结构要求输出
- <业务指定需要额外保留或摘要的 seedNodes/nodes/edges/functions/actions 字段>

### 5. 下一步建议
- 是否需要基于子图规划 OAC：是/否，原因：...
- 是否需要 Function：是/否，原因：...
- 缺失信息：...
- 风险说明：...
```

## 6. 子图解析规则

- 对象类型必须来自 `result.nodes` 中的 `label=objectType` 节点或等价对象定义。
- 字段必须来自 `label=property` 节点，并通过 `has_property` 边确认归属。
- 关系必须来自 `edgeType=defines_relation`，关系名必须使用 `edges[].properties.name`。
- Function 必须来自 `result.functions` 候选，不得编造。
- `has_property` 只能证明字段归属，不能生成 OAC 的 `relationships`。

## 7. 本层边界

- 不把子图检索替代成数据查询。
- 不在未获得子图结果时直接给出确定性路径结论。
- 不直接执行函数或写入数据。
- 不编造对象、字段、关系或函数。
- 不删改原始子图结果中的 id、name、qualifiedName、properties。

## 8. 校验规则

1. 先检索，再规划；不能反过来。
2. 子图结果只能作为本体结构依据，不能说成完整事实库。
3. 子图为空时，不输出确定性路径或对象关系结论。
4. 后续任务规划必须显式基于“子图结果 + 业务规则/SOP”。
5. 业务要求返回特定子图字段时，优先在摘要中保留，但不得改写原始 result。
