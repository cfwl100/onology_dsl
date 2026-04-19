# 普通对象读取校验规则

1. `operation` 必须为 `QUERY`。
2. `objects` 必填且非空，别名唯一。
3. `returns` 必填且至少包含一个结果项。
4. `returns` 只允许 `FIELDS` 与 `EXPR`。
5. `conditions` 中出现的对象别名必须已经在 `objects` 中声明。
6. `orders` 中引用的别名与字段必须可解释。
7. `relationships`、`linkQuery`、`mutation` 不得出现。
8. `sourceQuery` 只允许读取类请求，且 `outputAs` 在同层唯一。
9. 信息不足时返回结构化错误，不猜测字段或关系。
