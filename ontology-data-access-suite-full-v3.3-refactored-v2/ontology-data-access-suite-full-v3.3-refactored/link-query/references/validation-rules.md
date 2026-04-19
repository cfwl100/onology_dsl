# 一跳关联读取校验规则

1. `operation` 必须为 `LINK_QUERY`。
2. `objects` 必须恰好两个。
3. `linkQuery` 必填，且 `sourceRef` / `targetRef` 必须引用已声明对象别名。
4. `mode` 只允许 `LIST` 或 `ONE`。
5. `relationships`、`mutation` 不得出现。
6. 如果用户没有说明关系类型、方向或源对象定位条件，应返回结构化错误。
