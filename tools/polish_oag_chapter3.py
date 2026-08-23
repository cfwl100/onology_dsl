from pathlib import Path
import re

DOC = Path('docs/OAG本体锚点语义检索与向量索引设计方案.md')
text = DOC.read_text(encoding='utf-8')
CH3 = '# 3. 语义索引管理：构建、数据接入、任务、MinIO 与一致性'
CH4 = '# 4. 实体提取、Entity Linking 与 6 路混合召回'
start = text.index(CH3)
end = text.index(CH4)
ch = text[start:end]

# Put architecture first; keep cross-system model alignment as a scoped note after the diagram.
note_re = re.compile(r'\n#### DataSeek / NL2SQL 语义值模型对齐\n\n(.*?)\n\n(?=```mermaid)', re.S)
m = note_re.search(ch)
if m:
    note_body = m.group(1).strip()
    ch = ch[:m.start()] + '\n' + ch[m.end():]
    marker = '\n\n### 3.1.3 统一 Import Pipeline 边界'
    assert marker in ch
    note = f'\n\n#### 与 DataSeek / NL2SQL 的模型边界\n\n{note_body}\n'
    ch = ch.replace(marker, note + marker, 1)

# Remove compatibility wording from the formal current task model.
ch = ch.replace('手动构建、OAC 抽取、兼容 MinIO 文件通知和 OMS 全量索引构建', '手动构建、OAC 抽取、MinIO 文件通知和 OMS 全量索引构建')
ch = ch.replace('以下 Components 与 3.3～3.8 的 Path 定义组合后', '以下 Components 与本节 Path 定义组合后')

# OAC-source tasks also bind MinIO files; file metadata semantics depend on file input, not sourceType=MINIO.
ch = ch.replace('MINIO Task 的全部 objectKey；其他来源返回空数组', '有 MinIO 文件输入 Task 的全部 objectKey；无文件输入时返回空数组')
ch = ch.replace('MinIO 源文件硬 TTL 对应的最晚恢复时间；其他来源为空', 'MinIO 源文件硬 TTL 对应的最晚恢复时间；无文件输入时为空')
ch = ch.replace('当前 Task 的全部 objectKey，MINIO 任务使用', '当前 Task 的全部 objectKey；有 MinIO 文件输入的任务使用')
ch = ch.replace('对于 MINIO Task', '对于有 MinIO 文件输入的 Task')
ch = ch.replace('MINIO Task 额外校验', '有 MinIO 文件输入的 Task 额外校验')
ch = ch.replace('对于 MINIO Task，业务侧如果选择 retry', '对于有 MinIO 文件输入的 Task，业务侧如果选择 retry')

# STATUS/STAGE authoritative definition belongs to 3.5.2, not duplicated at the end of 3.5.1.
ch = re.sub(
    r'\n`STATUS=0/1/2` 继续兼容现有构建中/成功/失败语义，`STATUS=3` 表示取消；更细执行阶段写入 `STAGE`：`CREATED / WAITING_SOURCE / EXTRACTING / VALIDATING / READING / DEDUPLICATING / EMBEDDING / WRITING_VECTOR / WRITING_SEARCH / VERIFYING / PUBLISHING / CANCEL_REQUESTED / FINISHED`。\n',
    '\n', ch, count=1
)

# Final assertions.
assert '兼容 MinIO 文件通知' not in ch
assert 'MINIO Task 的全部 objectKey' not in ch
assert '以下 Components 与 3.3～3.8' not in ch
assert ch.count('任务状态采用“粗状态 + 细阶段”') == 1
assert '#### 与 DataSeek / NL2SQL 的模型边界' in ch
assert ch.index('```mermaid', ch.index('### 3.1.2 总体索引构建架构')) < ch.index('#### 与 DataSeek / NL2SQL 的模型边界')

DOC.write_text(text[:start] + ch + text[end:], encoding='utf-8')
print('chapter 3 semantic linkage cleanup: PASS')
