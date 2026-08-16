## 3.3 统一 REST API 规范

OAG 对外接口统一使用 Namespace：

```text
/v1/onto-retrieval/{ontologyId}
```

不再新增 `/v1/ontologies/{ontologyId}/...` 或 `/instance-evidence/import-jobs/...` 风格接口。

### 3.3.1 语义检索接口

```java
@PostMapping("/v1/onto-retrieval/{ontologyId}/subgraph/semantic-search")
```

```http
POST /v1/onto-retrieval/{ontologyId}/subgraph/semantic-search
```

该接口负责 Query Understanding、混合召回、RRF、LLM 精排和子图生成，不承担索引数据导入。

### 3.3.2 索引导入与任务接口

| 场景 | Method | URI | 说明 |
|---|---|---|---|
| REST 批量导入 | POST | `/v1/onto-retrieval/{ontologyId}/index-data/batch-import` | Body 直接提交 Enum/Instance records |
| MinIO 文件导入 | POST | `/v1/onto-retrieval/{ontologyId}/index-data/file-import` | 注册已经上传到 MinIO 的 CSV 文件 |
| 查询任务 | GET | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}` | 查询持久化任务状态和进度 |
| 重试任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry` | 对失败任务重新执行 |
| 取消任务 | POST | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel` | 请求取消未完成任务 |
| 查询错误 | GET | `/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors` | 查询任务错误明细 |

对应 Spring 接口：

```java
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-data/batch-import")
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-data/file-import")
@GetMapping("/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}")
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/retry")
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/cancel")
@GetMapping("/v1/onto-retrieval/{ontologyId}/index-tasks/{taskId}/errors")
```

所有导入接口采用异步任务模型：

```text
提交请求 → 基础参数校验 → GaussDB 创建 T_OAG_INDEX_TASK → HTTP 202 + taskId → 后台执行
```

`requestId` 是调用方幂等键；同一个 `ontologyId + requestId` 重复提交时不得创建重复任务。

统一的数据类型：`METADATA_ENUM`、`INSTANCE_VALUE`；统一导入模式：`FULL_REPLACE`、`INCREMENTAL`；统一记录操作：`UPSERT`、`DELETE`。

---

## 3.4 REST 批量导入接口

REST Batch Import 是 MinIO 文件导入的补充，主要面向动态枚举值实时/准实时增加、删除或修订，以及少量/中等规模实例值增量。超大数据不应通过 HTTP JSON Body 替代 MinIO 文件通道。`maxRecordsPerRequest` 作为 OAG 工程配置，建议默认从 1000 条起步并通过压测调整。

### 3.4.1 请求公共结构

```json
{
  "requestId": "req-20260816-000001",
  "dataType": "METADATA_ENUM",
  "importMode": "INCREMENTAL",
  "records": []
}
```

| 字段 | 必选 | 说明 |
|---|---|---|
| `requestId` | ✔ | 调用幂等键 |
| `dataType` | ✔ | `METADATA_ENUM` / `INSTANCE_VALUE` |
| `importMode` | ✔ | `FULL_REPLACE` / `INCREMENTAL` |
| `records` | ✔ | 与 `dataType` 对应的业务记录 |

OAG 不接受调用方提交 `vector`；物理 `type` 由 `dataType` 确定：`METADATA_ENUM → ENUM_VALUE`，`INSTANCE_VALUE → INSTANCE_VALUE`。

### 3.4.2 METADATA_ENUM 请求

请求参数与第 2.8 节 `t_metadata_evidence_{ontology_id}` 的业务字段一致：

```json
{
  "requestId": "req-enum-001",
  "dataType": "METADATA_ENUM",
  "importMode": "INCREMENTAL",
  "records": [
    {
      "propertyid": "prop:ont:vehicle:sp:bodyColor",
      "objectTypeId": "obj:ont:vehicle:Vehicle",
      "value": "red",
      "name": "red",
      "display_zh": "红色",
      "display_en": "Red",
      "display_lang_1": "Rojo",
      "display_lang_2": null,
      "description_zh": "红色",
      "description_en": "Red color",
      "description_lang_1": "Color rojo",
      "description_lang_2": null,
      "synonyms": {"zh": ["红", "赤色"], "en": ["Red"], "es": ["Rojo"]},
      "op": "UPSERT"
    }
  ]
}
```

OAG 按 `objectTypeId + propertyid + normalized(value)` 去重，按第 2.9 节 Enum Value 模板构建 Embedding 文本，再写入 `t_metadata_evidence_{ontology_id}` 的 GaussVector/OpenSearch。

### 3.4.3 INSTANCE_VALUE 请求

```json
{
  "requestId": "req-instance-001",
  "dataType": "INSTANCE_VALUE",
  "importMode": "INCREMENTAL",
  "records": [
    {
      "propertyid": "prop:subscriber:subLevel",
      "objectTypeId": "obj:subscriber:Subscriber",
      "value": "VIP",
      "language": "und",
      "op": "UPSERT"
    }
  ]
}
```

Instance 继续按 `objectTypeId + propertyid + normalized(value)` 去重，EmbeddingInput 严格为 `{value}`。

### 3.4.4 异步响应

```http
HTTP/1.1 202 Accepted
```

```json
{
  "ontologyId": "dtmi.ontology.xxx.1",
  "taskId": "idx-task-20260816-000001",
  "requestId": "req-enum-001",
  "dataType": "METADATA_ENUM",
  "sourceType": "REST",
  "status": 0
}
```

任务创建成功只表示已持久化并接受任务，不表示索引已经可检索。
