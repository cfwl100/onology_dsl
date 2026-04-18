# ontology-data-access-suite-v3.3-soql-aligned

本目录中的 Skills 现在统一采用“**先生成 S-OQL，再确定性转换**”的工作方式：

- Skill 文本层只描述第 9 章的 **S-OQL** 语法与操作边界
- `conditions`、`returns`、`mutation` 使用 S-OQL 简化语法
- `scripts/soql_to_oql.py` 负责把 S-OQL 恢复为 canonical OQL
- 主转换实现位于 `shared/soql_to_oql.py`（可读 Python 源码，主路径仅依赖此文件）
- `shared/soql_to_oql_payload.b85` 仅保留为空占位文件，已弃用
- `scripts/oql_validator.py` 负责对转换后的 canonical OQL 做校验

## 目录说明

- `ontology-data-access/`：自然语言入口与路由
- `object-query/`：`QUERY` 的 S-OQL 生成
- `aggregate-query/`：`AGGREGATE` 的 S-OQL 生成
- `association-query/`：`ASSOCIATION_QUERY` 的 S-OQL 生成
- `link-query/`：`LINK_QUERY` 的 S-OQL 生成
- `create-object/`：`CREATE` 的 S-OQL 生成
- `update-object/`：`UPDATE` 的 S-OQL 生成
- `delete-object/`：`DELETE` 的 S-OQL 生成
- `upsert-batch/`：`UPSERT` / `BATCH` 的 S-OQL 生成
- `execute-request/`：执行已完成转换与校验的可执行请求

## 统一规则

1. 顶层字段名保持统一，不新增并行顶层语法。
2. Skill 描述层只体现 S-OQL，不展开 canonical OQL 结构。
3. 任何可执行请求都必须先经过 `scripts/soql_to_oql.py` 转换，再进入校验或执行。
