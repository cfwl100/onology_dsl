# 删除对象校验规则

1. `operation` 必须为 `DELETE`。
2. `objects` 必须且仅有一个对象。
3. `conditions` 与 `mutation.scope` 必填。
4. `scope` 只允许 `ONE` 或 `MANY`。
5. `returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery`、`mutation.set`、`mutation.data` 不得出现。
6. 缺筛选条件或删除范围不清时，应返回结构化错误。
