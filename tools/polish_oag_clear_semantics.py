from pathlib import Path

p = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
s = p.read_text(encoding='utf-8')

old = '| 已有全量文件导入/重建 | putObject → notice → query | `BUSINESS_NOTICE` | `FULL_REPLACE` | MinIO CSV |\n'
new = old + '| 清理当前本体全量实例索引 | `index-data/notice` → query | - | `CLEAR` | 无需文件；`dataType=INSTANCE_VALUE` |\n'
assert old in s
s = s.replace(old, new, 1)

s = s.replace(
    'summary: 从 MinIO CSV 导入枚举值或实例列值',
    'summary: 从 MinIO CSV 导入枚举/实例值，或清理全量实例值索引',
    1,
)

s = s.replace(
    '1. 动态 Enum / Instance 统一使用 **MinIO CSV + `index-data/notice`**，不再区分小数据直返和大数据文件两套实现；',
    '1. 除 `dataType=INSTANCE_VALUE, importMode=CLEAR` 外，动态 Enum / Instance 统一使用 **MinIO CSV + `index-data/notice`**；`CLEAR` 复用同一任务接口但不要求 `files`；',
    1,
)

s = s.replace(
    '阶段 4 的输出不是最终语义检索结果，而是可供 LLM Fine Rank 使用的**真实候选集合 + 归属 + 证据**：',
    '本章粗排阶段的输出不是最终语义检索结果，而是可供 LLM Fine Rank 使用的**真实候选集合 + 归属 + 证据**：',
    1,
)

assert '| 清理当前本体全量实例索引 |' in s
assert '除 `dataType=INSTANCE_VALUE, importMode=CLEAR` 外' in s
assert 'summary: 从 MinIO CSV 导入枚举/实例值，或清理全量实例值索引' in s
assert '阶段 4 的输出不是最终语义检索结果' not in s
p.write_text(s, encoding='utf-8')
print('CLEAR consistency polish: PASS')
