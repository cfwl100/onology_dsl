# 确定性脚本说明

本目录当前采用“**先生成 S-OQL，再确定性转换**”的模式：

- `soql_to_oql.py`：把第 9 章定义的 S-OQL 转换为 canonical OQL。仅负责 `conditions`、`returns`、`mutation.data` 的简化语法恢复，并递归处理 `sourceQuery` 与 `BATCH.items`。
- `oql_validator.py`：对转换后的 canonical OQL 做结构校验，检查对象数、关系块、条件树、返回投影、写操作块、`sourceQuery` 深度等关键约束。
- `oql_builder.py`：保留为 canonical OQL 的顺序整理与默认值补齐工具；当输入已经是 canonical 结构时可继续使用，但生成主路径应优先使用 `soql_to_oql.py`。

## 推荐使用顺序

1. 先由模型把自然语言意图整理为 S-OQL。
2. 调用 `soql_to_oql.py` 产出 canonical OQL。
3. 调用 `oql_validator.py` 校验。
4. 仅在校验通过后输出结果，或交给下游执行插件。
