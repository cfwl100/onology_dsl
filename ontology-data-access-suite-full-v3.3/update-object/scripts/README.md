# 确定性脚本说明

本目录包含两类脚本：

- `oql_builder.py`：将已归一化的结构化输入组装为稳定顺序、带默认值的 canonical OQL JSON。
- `oql_validator.py`：对 OQL JSON 做结构校验，检查对象数、关系块、条件树、返回投影、写操作块、`sourceQuery` 深度等关键约束。

## 推荐使用顺序

1. 先由模型把自然语言意图整理为结构化计划。
2. 调用 `oql_builder.py` 产出 canonical OQL。
3. 调用 `oql_validator.py` 校验。
4. 仅在校验通过后输出结果，或交给下游执行插件。
