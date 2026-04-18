# 确定性脚本说明

## 统一主流程（三步）

1. 先生成 S-OQL。
2. 调用 `soql_to_oql.py` 将 S-OQL 转为 canonical OQL。
3. 调用 `oql_validator.py` 校验 canonical OQL。

## 脚本定位

- `soql_to_oql.py`：主转换脚本，负责从 S-OQL 到 canonical OQL 的标准转换。
- `oql_validator.py`：结构与约束校验脚本，用于最终校验。
- `oql_builder.py`：仅用于 canonical 输入整理/兼容，不是主转换链路。

## 使用建议

- 以三步主流程为默认调用顺序。
- 仅在需要处理兼容输入或做额外整理时，按需使用 `oql_builder.py`。
