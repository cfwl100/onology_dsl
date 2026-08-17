from pathlib import Path
import re
import sys

DOC = Path(sys.argv[1])
TASK_API = Path(sys.argv[2])
text = DOC.read_text(encoding='utf-8')

# Work only on the current latest document and bump the design version.
if '# 3. 索引构建与 DataSync Bulk Import' not in text or '# 4. Query Understanding 与 6 路召回' not in text:
    raise SystemExit('chapter boundary not found')
text = text.replace('> 版本：V5.9  ', '> 版本：V5.10  ', 1)

# 1) Interface list: task management becomes batch-first.
old_list = '''| 查询任务 | GET | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}` | `getIndexTask` | 查询持久化任务状态和进度 |
| 重试任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry` | `retryIndexTask` | 对失败任务重新执行 |
| 取消任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel` | `cancelIndexTask` | 请求取消未完成任务 |'''
new_list = '''| 批量查询任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/batch-query` | `batchQueryIndexTasks` | Body 传 taskIds，批量查询持久化任务状态和进度 |
| 批量重试任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/batch-retry` | `batchRetryIndexTasks` | 逐 task 判断 retryable，允许部分成功 |
| 批量取消任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/batch-cancel` | `batchCancelIndexTasks` | 逐 task 请求取消，允许部分成功 |'''
if old_list not in text:
    raise SystemExit('task API list marker changed')
text = text.replace(old_list, new_list, 1)
text = text.replace('`AsyncTaskAcceptedResponse` / `TaskOperationAcceptedResponse`', '`AsyncTaskAcceptedResponse` / `BatchTaskOperationResponse`', 1)

# 2) METADATA_ENUM REST schema: remove name and flatten synonyms.
text = re.sub(r'^\| `name` \| String \| 否 \| - \| `maxLength: 4096` \| Enum Value name \(TODO:待删除\)\s*\|\n', '', text, count=1, flags=re.M)
old_syn_row = '| `synonyms` | Map[String, Array[String]] | 否 | `{}` | `maxProperties: 3` | 当前 Enum Value 的多语言同义词；语言 key 最多 3 个    |'
new_syn_row = '| `synonyms` | String | 否 | `""` | 换行分隔文本 | 同义词平铺字符串；逻辑分隔符固定为 LF（`\\n`），不再使用 JSON Map/Array 嵌套 |'
if old_syn_row not in text:
    raise SystemExit('synonyms table row marker changed')
text = text.replace(old_syn_row, new_syn_row, 1)
text = text.replace('''```text
TODO：
上面的synonyms 使用\\n拼接，不使用json嵌套，避免再次反序列化解析耗费性能
```

''', '''`synonyms` 在接口层直接使用平铺字符串，避免 OAG 收到请求后再次对 JSON Map/Array 做反序列化。调用方按稳定顺序展开同义词并使用换行符连接；OAG 只执行一次 `split(LF) → trim → 去空 → 去重（保持首次出现顺序）`。动态导入协议不再携带语言 Map，语言分组在上游 SynonymType 展开阶段完成。

传输规则：

```text
逻辑值：红<LF>赤色<LF>Red<LF>Rojo
REST JSON："红\\n赤色\\nRed\\nRojo"
OAG Runtime：框架完成 JSON 转义后直接得到包含 LF 的 String，不进行第二次 JSON 解析
```

''', 1)

# 3) Replace the UPSERT TODO example with an implementable GaussVector idempotency design.
upsert_todo = re.compile(r'''\n\n\n```\nTODO: 按照如下描述，upsert的时候，增加GaussVector按照组合键覆盖能力，使用 INSERT ON DUPLICATE KEY UPDATE\n.*?gaussdb=# DROP TABLE test_t4;\n```\n''', re.S)
upsert_design = r'''

##### GaussVector 组合键幂等 UPSERT

REST、MinIO、Chunk 重试最终都必须落到数据库级唯一约束，不能只依赖 JVM 内存 Dedup。OAG Writer 在写入前必须先补齐 `objectTypeId`；接口允许省略该字段，但持久化阶段不得为 `NULL`。

为避免重新引入 `normalized_value` 物理列，`KeyNormalizer` 在 Writer 前完成不会改变业务语义的基础规范化（trim、Unicode normalize、全半角归一）；大小写归一只在 Property 明确声明大小写不敏感时启用。规范化后的 `value` 进入唯一组合键。

GaussVector / GaussDB 唯一索引：

```sql
-- Enum Value
CREATE UNIQUE INDEX UK_METADATA_EVIDENCE_BIZ
ON t_metadata_evidence_{ontology_id} (objectTypeId, propertyId, value);

-- Instance Value
CREATE UNIQUE INDEX UK_INSTANCE_EVIDENCE_BIZ
ON t_instance_evidence_{ontology_id} (objectTypeId, propertyid, value);
```

`UPSERT` 使用 `INSERT ... ON DUPLICATE KEY UPDATE`，Chunk 内可以一次提交多条 VALUES：

```sql
INSERT INTO t_metadata_evidence_{ontology_id}
(vector, type, propertyId, objectTypeId, value,
 display_zh, display_en, display_lang_1, display_lang_2,
 description_zh, description_en, description_lang_1, description_lang_2,
 synonyms)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
vector             = VALUES(vector),
display_zh         = VALUES(display_zh),
display_en         = VALUES(display_en),
display_lang_1     = VALUES(display_lang_1),
display_lang_2     = VALUES(display_lang_2),
description_zh     = VALUES(description_zh),
description_en     = VALUES(description_en),
description_lang_1 = VALUES(description_lang_1),
description_lang_2 = VALUES(description_lang_2),
synonyms           = VALUES(synonyms);
```

```sql
INSERT INTO t_instance_evidence_{ontology_id}
(vector, type, propertyid, objectTypeId, value)
VALUES (?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
vector = VALUES(vector);
```

行为约束：

```text
同一组合键首次写入      → INSERT
同一组合键再次 UPSERT   → UPDATE 原记录，不新增向量
同一 Chunk 重放         → 幂等覆盖
DELETE                  → 按相同组合键删除
```

OpenSearch 使用同一业务组合键计算确定性 `_id`（例如 SHA-256），确保 GaussVector 和 OpenSearch 的重复提交语义一致；`_id` 只属于检索实现，不作为业务返回字段。

'''
text, n = upsert_todo.subn('\n' + upsert_design, text, count=1)
if n != 1:
    raise SystemExit('GaussVector UPSERT TODO marker changed')

# 4) Dynamic enum request example: no name, no nested JSON synonyms.
text = text.replace('''      "name": "red",
      "display_zh": "红色",''', '''      "display_zh": "红色",''', 1)
old_json_syn = '''      "synonyms": { // TODO: 按照平铺结构修改成按照换行符拼接
        "zh": ["红", "赤色"],
        "en": ["Red"],
        "es": ["Rojo"]
      },'''
new_json_syn = '''      "synonyms": "红\\n赤色\\nRed\\nRojo",'''
if old_json_syn not in text:
    raise SystemExit('dynamic enum synonyms example marker changed')
text = text.replace(old_json_syn, new_json_syn, 1)

# Dynamic import no longer accepts name. Static OMS assets may still contain name; Embedding skips absent dynamic fields.
insert_note_marker = '如果 `objectTypeId` 未传，OAG 可以根据 `propertyId` 的本体归属补齐；若调用方传入，则必须校验与 OMS 本体映射一致，不一致返回 `OBJECT_TYPE_MISMATCH`。'
text = text.replace(insert_note_marker, insert_note_marker + '\n\n动态导入协议不再接收 `name`。静态 OMS 枚举资产仍可保留 `values[].name`；动态导入的 EmbeddingInputBuilder 对不存在的 `name` 项直接跳过，不为兼容而复制 `value` 造成重复权重。', 1)

# 5) CSV: keep one physical record per line, use escaped newline text for synonyms, remove name column.
text = text.replace('`synonyms` 使用 JSON Object 字符串写入单个 CSV 字段。', '`synonyms` 不再保存 JSON Object。逻辑上仍以 LF 分隔；为保证“一条业务记录对应一条 CSV 物理行”，CSV 中推荐写入两个字符 `\\n` 作为转义分隔，OAG 读取字段后一次性转换为 LF，再执行 trim/去空/去重。', 1)
text = text.replace('propertyId,objectTypeId,value,name,display_zh,display_en,display_lang_1,display_lang_2,description_zh,description_en,description_lang_1,description_lang_2,synonyms,op', 'propertyId,objectTypeId,value,display_zh,display_en,display_lang_1,display_lang_2,description_zh,description_en,description_lang_1,description_lang_2,synonyms,op', 2)
text = text.replace('| `name` | `name` | Enum Value name |\n', '', 1)
text = text.replace('| `synonyms` | `synonyms` | JSON Object，最多 3 种语言 |', '| `synonyms` | `synonyms` | 换行分隔的平铺同义词字符串；CSV 使用 `\\n` 转义分隔 |', 1)
old_csv_example = 'prop:ont:vehicle:sp:bodyColor,obj:ont:vehicle:Vehicle,red,red,红色,Red,Rojo,,红色,Red color,Color rojo,,"{""zh"":[""红"",""赤色""],""en"":[""Red""],""es"":[""Rojo""]}",UPSERT'
new_csv_example = 'prop:ont:vehicle:sp:bodyColor,obj:ont:vehicle:Vehicle,red,红色,Red,Rojo,,红色,Red color,Color rojo,,"红\\n赤色\\nRed\\nRojo",UPSERT'
if old_csv_example not in text:
    raise SystemExit('CSV enum example marker changed')
text = text.replace(old_csv_example, new_csv_example, 1)

# 6) Replace single-task query/retry/cancel definitions with batch versions.
start = '#### 3.8.4.1 查询索引任务'
end = '#### 3.8.4.4 查询索引任务错误'
if start not in text or end not in text:
    raise SystemExit('task API section markers changed')
before, rest = text.split(start, 1)
_, after = rest.split(end, 1)
text = before + TASK_API.read_text(encoding='utf-8').rstrip() + '\n\n' + end + after

# 7) OpenAPI components: flattened Enum schema, batch task schemas, retryable.
text = re.sub(r'^        name: \{ type: string, maxLength: 4096 \}\n', '', text, count=1, flags=re.M)
old_component_syn = '''        synonyms:
          type: object
          maxProperties: 3
          additionalProperties:
            type: array
            items: { type: string }'''
new_component_syn = '''        synonyms:
          type: string
          description: 同义词平铺字符串，逻辑分隔符为 LF；REST JSON 使用 \\n 转义'''
if old_component_syn not in text:
    raise SystemExit('OpenAPI synonyms schema marker changed')
text = text.replace(old_component_syn, new_component_syn, 1)
text = text.replace('required: [ontologyId, taskId, requestId, dataType, sourceType, status, stage, createTime, updateTime]', 'required: [ontologyId, taskId, requestId, dataType, sourceType, status, stage, retryable, createTime, updateTime]', 1)
text = text.replace('        errorMessage: { type: string, nullable: true }\n        createTime:', '        errorMessage: { type: string, nullable: true }\n        retryable: { type: boolean, default: false }\n        createTime:', 1)

batch_schemas = '''    BatchTaskIdsRequest:
      type: object
      required: [taskIds]
      properties:
        taskIds:
          type: array
          minItems: 1
          uniqueItems: true
          items: { type: string, maxLength: 256 }
      additionalProperties: false

    BatchTaskQueryResponse:
      type: object
      required: [ontologyId, requestedCount, foundCount, tasks, notFoundTaskIds]
      properties:
        ontologyId: { type: string }
        requestedCount: { type: integer, minimum: 0 }
        foundCount: { type: integer, minimum: 0 }
        tasks:
          type: array
          items: { $ref: '#/components/schemas/IndexTaskResponse' }
        notFoundTaskIds:
          type: array
          items: { type: string }

    TaskOperationResult:
      type: object
      required: [taskId, accepted, retryable]
      properties:
        taskId: { type: string }
        accepted: { type: boolean }
        status: { type: integer, enum: [0, 1, 2, 3], nullable: true }
        stage: { type: string, nullable: true }
        retryable: { type: boolean }
        reasonCode: { type: string, nullable: true }
        message: { type: string, nullable: true }

    BatchTaskOperationResponse:
      type: object
      required: [ontologyId, operation, requestedCount, acceptedCount, rejectedCount, results]
      properties:
        ontologyId: { type: string }
        operation: { type: string, enum: [RETRY, CANCEL] }
        requestedCount: { type: integer, minimum: 0 }
        acceptedCount: { type: integer, minimum: 0 }
        rejectedCount: { type: integer, minimum: 0 }
        results:
          type: array
          items: { $ref: '#/components/schemas/TaskOperationResult' }

'''
pattern = re.compile(r'    TaskOperationAcceptedResponse:\n.*?(?=    IndexTaskErrorItem:)', re.S)
text, n = pattern.subn(batch_schemas, text, count=1)
if n != 1:
    raise SystemExit('TaskOperationAcceptedResponse schema marker changed')

# Component example cleanup.
text = text.replace('            name: red\n', '', 1)
text = text.replace('            display_en: Red\n            op: UPSERT', '            display_en: Red\n            synonyms: "红\\n赤色\\nRed\\nRojo"\n            op: UPSERT', 1)

# 8) Error section: explicit retry policy for business guidance.
old_errors = '''统一错误分类：

```text
INVALID_REQUEST
INVALID_DATA_TYPE
ONTOLOGY_NOT_FOUND
PROPERTY_NOT_FOUND
OBJECT_TYPE_MISMATCH
CSV_SCHEMA_ERROR
MINIO_OBJECT_NOT_FOUND
CHECKSUM_MISMATCH
EMBEDDING_FAILED
VECTOR_WRITE_FAILED
SEARCH_WRITE_FAILED
VERIFY_FAILED
PUBLISH_FAILED
```

任务级错误通过 `ERROR_CODE / ERROR_MESSAGE` 写入 `T_OAG_INDEX_TASK`；记录级错误至少保留 taskId、objectKey/rowNumber 或 recordIndex、Property 标识（Enum 为 propertyId，Instance 为 propertyid）、objectTypeId、必要时脱敏后的 value、errorCode、errorMessage。'''
new_errors = '''统一错误分类，同时维护服务端 `retryable` 判断：

| 错误码 | 默认 retryable | 说明 |
|---|---:|---|
| `INVALID_REQUEST` | false | 请求结构错误 |
| `INVALID_DATA_TYPE` | false | dataType 非法 |
| `ONTOLOGY_NOT_FOUND` | false | 本体不存在 |
| `PROPERTY_NOT_FOUND` | false | Property 不存在 |
| `OBJECT_TYPE_MISMATCH` | false | ObjectType 与 Property 归属冲突 |
| `CSV_SCHEMA_ERROR` | false | CSV Header/字段格式错误 |
| `MINIO_OBJECT_NOT_FOUND` | false | MinIO 源对象不存在，需要重新上传/提交 |
| `CHECKSUM_MISMATCH` | false | 文件 checksum 不一致，需要重新生成/提交 |
| `MINIO_READ_FAILED` | true | 已存在对象的临时读取失败 |
| `EMBEDDING_FAILED` | true | Embedding 服务超时/5xx 等临时失败 |
| `VECTOR_WRITE_FAILED` | true | GaussVector 临时写入失败 |
| `SEARCH_WRITE_FAILED` | true | OpenSearch 临时写入失败 |
| `VERIFY_FAILED` | true | 双写后校验失败，可幂等补写并重新 Verify |
| `PUBLISH_FAILED` | true | Generation 发布阶段临时失败 |

业务侧批量查询任务时读取 `retryable`，批量重试接口也由 OAG 再次校验该值；客户端不需要解析 `errorMessage` 判断是否重试。若一个高层错误码因根因不同需要不同策略，以服务端计算后的 `retryable` 为准。

任务级错误通过 `ERROR_CODE / ERROR_MESSAGE` 写入 `T_OAG_INDEX_TASK`；记录级错误至少保留 taskId、objectKey/rowNumber 或 recordIndex、Property 标识（Enum 为 propertyId，Instance 为 propertyid）、objectTypeId、必要时脱敏后的 value、errorCode、errorMessage。'''
if old_errors not in text:
    raise SystemExit('error classification marker changed')
text = text.replace(old_errors, new_errors, 1)
text = text.replace('`GET /v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors` 返回记录级错误', '`GET /v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors` 继续按单任务分页返回记录级错误', 1)
text = text.replace('任务查询接口必须以 GaussDB 为事实来源', '批量任务查询接口必须以 GaussDB 为事实来源', 1)

# 9) Import pipeline / consistency wording.
text = text.replace('唯一业务范围：`objectTypeId + propertyId + normalized(value)`。Embedding 严格复用第 2.9 节：`value + name + display_* + description_* + synonyms_value + synonyms_description`。', '唯一业务范围：`objectTypeId + propertyId + normalized(value)`。动态导入不再接收 `name`，EmbeddingInputBuilder 拼接 `value + display_* + description_* + synonyms`；静态 OMS 构建仍可使用第 2.9 节中存在的 `name`。', 1)
text = text.replace('> **所有导入路径都必须保证同一个业务唯一键最终在 GaussVector 和 OpenSearch 中各只有一条有效记录。**', '> **所有导入路径都必须保证同一个业务唯一键最终在 GaussVector 和 OpenSearch 中各只有一条有效记录；GaussVector 由组合唯一索引 + `INSERT ... ON DUPLICATE KEY UPDATE` 提供数据库级兜底。**', 1)
text = text.replace('INCREMENTAL 对同一业务唯一键在 GaussVector/OpenSearch 执行 UPSERT/DELETE；', 'INCREMENTAL 对同一业务唯一键在 GaussVector 使用 `INSERT ... ON DUPLICATE KEY UPDATE`、在 OpenSearch 使用确定性 `_id` 执行幂等 UPSERT/DELETE；', 1)

# 10) Final chapter constraints / conclusion.
text = text.replace('5. **REST/CSV 字段必须与第 2.8/2.10 节物理业务字段一致，不接受外部 vector。**', '5. **REST/CSV 核心定位字段与第 2.8/2.10 节一致，不接受外部 vector/type；动态 Enum 导入不再接收 name，synonyms 使用换行分隔平铺字符串。**', 1)
constraint_anchor = '12. **GaussVector/OpenSearch 不使用分布式事务，通过唯一键、幂等、Verify 和任务重试保证一致性。**'
text = text.replace(constraint_anchor, constraint_anchor + '''
13. **GaussVector 使用 `(objectTypeId, propertyId/propertyid, value)` 组合唯一索引和 `INSERT ... ON DUPLICATE KEY UPDATE`，保证重复导入覆盖而不是新增向量。**
14. **任务查询、重试、取消统一提供批量接口；批量操作逐 task 返回结果，允许部分成功。**
15. **批量重试以服务端 `retryable` 为最终判断，并公开可重试/不可重试错误码分类。**
16. **批量取消幂等处理已经取消的任务；终态成功/失败任务不再进入取消流程。**''', 1)

text = text.replace('动态枚举和实例列值共享协议、任务、去重、Embedding 和双存储能力，同时保留 REST 的动态性和 MinIO CSV 的规模能力。', '动态枚举和实例列值共享协议、任务、去重、Embedding 和双存储能力，同时保留 REST 的动态性和 MinIO CSV 的规模能力。任务管理采用 batch-query / batch-retry / batch-cancel，数据写入采用数据库级组合键 UPSERT，使接口幂等与存储幂等形成闭环。', 1)

# Validate the whole chapter 3 after patching.
chapter3 = text.split('# 3. 索引构建与 DataSync Bulk Import', 1)[1].split('# 4. Query Understanding 与 6 路召回', 1)[0]
if 'TODO' in chapter3:
    raise SystemExit('TODO remains in chapter 3')
required = [
    '> 版本：V5.10',
    'INSERT ... ON DUPLICATE KEY UPDATE',
    'UK_METADATA_EVIDENCE_BIZ',
    'UK_INSTANCE_EVIDENCE_BIZ',
    '"synonyms": "红\\n赤色\\nRed\\nRojo"',
    '/index-tasks/batch-query',
    '/index-tasks/batch-retry',
    '/index-tasks/batch-cancel',
    'operationId: batchQueryIndexTasks',
    'operationId: batchRetryIndexTasks',
    'operationId: batchCancelIndexTasks',
    'BatchTaskIdsRequest',
    'BatchTaskQueryResponse',
    'BatchTaskOperationResponse',
    'retryable',
]
missing = [x for x in required if x not in text]
if missing:
    raise SystemExit(f'missing expected content: {missing}')
for stale in [
    '/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry',
    '/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel',
    'operationId: getIndexTask',
    'operationId: retryIndexTask',
    'operationId: cancelIndexTask',
    'Map[String, Array[String]]',
    'name: { type: string, maxLength: 4096 }',
]:
    if stale in chapter3:
        raise SystemExit(f'stale content remains in chapter 3: {stale}')
if text.count('```') % 2:
    raise SystemExit('unbalanced markdown fences')

DOC.write_text(text, encoding='utf-8')
print('V5.10 TODO optimization patch applied and validated')
