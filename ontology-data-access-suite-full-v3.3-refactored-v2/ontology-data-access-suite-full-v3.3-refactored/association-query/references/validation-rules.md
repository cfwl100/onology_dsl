# 路径读取校验规则

1. `operation` 必须为 `ASSOCIATION_QUERY`。
2. `objects`、`relationships`、`returns` 必填。
3. `relationships` 顺序必须能解释为一条稳定路径。
4. `relationships[].from/to` 必须引用已声明对象别名。
5. `conditions` 与 `returns` 中的别名引用必须闭合。
6. `linkQuery`、`mutation` 不得出现。
7. 用户没有给出路径、关系类型或关键节点时，应返回结构化错误。
