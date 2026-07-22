# OAG 本体子图检索

## 职责
用上层传入的 query 检索本体子图，再结合 SOP 与子图规划下一步任务。先检索再规划，不得跳过检索直接假设子图。

## 调用
```bash
python scripts/semantic_subgraph_search.py --query "<问题/业务主题>" --ontology-id "<本体ID>"
```
也可 `--query-json '<json>'` 传可选参数。

## 输入
必填：`query`（用户问题/业务主题）、`ontology-id`。
可选：`similarity-threshold`(0.6)、`include-functions`(0/1)、`seed-retrieval-mode`(vector)、`topK`(3)、`graph-expansion-strategy`(minimal)、`adaptive-retrieval`(1)、`hopLimit`(3)。

## query 规范
- 查对象间关系：`从【对象1】到【对象2】之间的路径`
- 查对象+属性关系：`从【对象1】到【对象2】之间的路径，其中[对象1]携带【属性1】，[对象2]携带【属性2】【属性3】`

## 输出
先概括子图重点，再列出基于"子图 + SOP"的下一步任务规划。检索为空或噪声大时明确说明结果不足，不虚构子图。

## 边界
- 不把子图检索当数据查询；不在无子图结果时给确定性路径结论；不直接执行函数或写数据。
- 子图为空不输出确定性对象关系；任务规划必须显式基于"检索结果 + SOP"。
