# 更新对象校验规则

1. `operation` 必须为 `UPDATE`。
2. `objects` 必须且仅有一个对象。
3. `conditions`、`mutation.scope`、`mutation.set` 必填。
4. `scope` 只允许 `ONE` 或 `MANY`。
5. `set` 不可为空。
6. `returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery` 不得出现。
7. 缺筛选条件或更新内容时，应返回结构化错误。
