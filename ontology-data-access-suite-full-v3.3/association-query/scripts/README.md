# 脚本说明

本目录的主转换链路统一为三步：

1. 先生成 S-OQL。
2. 调用 `soql_to_oql.py` 将 S-OQL 转为 canonical OQL。
3. 调用 `oql_validator.py` 做最终校验。

## soql_to_oql.py

作用：

- 将 S-OQL 映射为 canonical OQL。
- 规范顶层结构并补齐转换阶段所需的标准字段。
- 产出后续校验可直接消费的 canonical 输入。

## oql_validator.py

作用：

- 验证 canonical OQL 结构。
- 验证本操作的必填字段与边界。
- 验证 `conditions` / `returns` / `orders` / `sourceQuery` / `mutation`。
- 验证可选 profile 覆盖约束。

## oql_builder.py（定位说明）

- `oql_builder.py` 仅用于 canonical 输入整理/兼容。
- `oql_builder.py` 不是主转换链路的一环，不替代 `soql_to_oql.py`。
- 在需要兼容历史输入或做额外规范化整理时可按需使用。
