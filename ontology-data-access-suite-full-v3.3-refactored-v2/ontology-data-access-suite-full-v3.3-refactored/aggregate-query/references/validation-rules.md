# 聚合读取校验规则

1. `operation` 必须为 `AGGREGATE`。
2. `objects` 与 `returns` 必填。
3. `returns` 只允许 `GROUP_BY` 与 `METRIC`。
4. 至少存在一个 `METRIC`。
5. 分组别名与指标别名必须稳定可引用。
6. `relationships`、`linkQuery`、`mutation` 不得出现。
7. 如用户要求统计但未说明统计口径或目标字段，应返回结构化错误。
8. 如用户要求排行但缺少排序基准，也应返回结构化错误。
