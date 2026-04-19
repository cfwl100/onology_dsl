# 创建对象校验规则

1. `operation` 必须为 `CREATE`。
2. `objects` 必须且仅有一个对象。
3. `mutation.data` 必填且非空。
4. `conditions`、`returns`、`orders`、`relationships`、`linkQuery`、`sourceQuery` 不得出现。
5. 如缺少创建数据或对象类型，应返回结构化错误。
