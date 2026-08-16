## 3.5 MinIO CSV 文件导入接口

对于百万/千万级实例值及大规模枚举数据，默认使用 MinIO 文件通道：

```text
DataSync → 生成 CSV → 上传双方约定 MinIO Bucket → POST file-import → OAG 创建任务 → S3 getObject 流式读取 → Normalize/Dedup/Embedding/Bulk Write
```

### 3.5.1 文件注册请求

```http
POST /v1/onto-retrieval/{ontologyId}/index-data/file-import
```

```json
{
  "requestId": "datasync-20260816-000001",
  "dataType": "INSTANCE_VALUE",
  "importMode": "FULL_REPLACE",
  "files": [
    {
      "bucket": "oag-retrieval-import",
      "objectKey": "onto-retrieval/tenant-a/dtmi.ontology.xxx.1/INSTANCE_VALUE/datasync-20260816-000001/part-00000.csv",
      "fileFormat": "CSV",
      "encoding": "UTF-8",
      "hasHeader": true,
      "rowCount": 1200000,
      "size": 183421234,
      "sha256": "..."
    }
  ]
}
```

`dataType` 同样只能为 `METADATA_ENUM` 或 `INSTANCE_VALUE`，因此 MinIO 和 REST 共享同一数据模型。

DataSync/调用方负责生成 CSV、计算 sha256、上传 MinIO、调用 file-import；OAG 负责校验 bucket/objectKey/checksum/CSV Header、创建并持久化任务、流式读取、Schema 选择、Normalize/Dedup/Embedding、GaussVector/OpenSearch 写入以及 Verify/Publish。MinIO 的 endpoint/accessKey/secretKey 属于部署配置，不通过业务导入 API 传输。

---

## 3.6 CSV 文件结构

所有 DataSync → MinIO 的索引数据文件统一采用：

```text
CSV
UTF-8
首行 Header
逗号分隔
双引号作为 quote character
LF 作为推荐换行符
```

CSV 不包含 `vector`，因为向量必须由 OAG 使用当前配置的 Embedding 模型统一生成；CSV 也不要求携带物理 `type`，因为 `file-import.dataType` 已唯一确定目标类型。

文本中出现逗号、双引号或换行时按标准 CSV quoting 规则转义；双引号使用 `""` 表示。`synonyms` 使用 JSON Object 字符串写入单个 CSV 字段。

### 3.6.1 METADATA_ENUM CSV

Header：

```csv
propertyid,objectTypeId,value,name,display_zh,display_en,display_lang_1,display_lang_2,description_zh,description_en,description_lang_1,description_lang_2,synonyms,op
```

| CSV 字段 | 目标字段 | 说明 |
|---|---|---|
| `propertyid` | `propertyid` | 引用 Enum 的 Property.id |
| `objectTypeId` | `objectTypeId` | Property 所属 ObjectType.id |
| `value` | `value` | 真实枚举值 |
| `name` | `name` | Enum Value name |
| `display_zh` | `display_zh` | 中文 display |
| `display_en` | `display_en` | 英文 display |
| `display_lang_1` | `display_lang_1` | 额外语言 1 |
| `display_lang_2` | `display_lang_2` | 额外语言 2 |
| `description_zh` | `description_zh` | 中文描述 |
| `description_en` | `description_en` | 英文描述 |
| `description_lang_1` | `description_lang_1` | 额外语言 1 描述 |
| `description_lang_2` | `description_lang_2` | 额外语言 2 描述 |
| `synonyms` | `synonyms` | JSON Object，最多 3 种语言 |
| `op` | 导入操作 | `UPSERT` / `DELETE` |

示例：

```csv
propertyid,objectTypeId,value,name,display_zh,display_en,display_lang_1,display_lang_2,description_zh,description_en,description_lang_1,description_lang_2,synonyms,op
prop:ont:vehicle:sp:bodyColor,obj:ont:vehicle:Vehicle,red,red,红色,Red,Rojo,,红色,Red color,Color rojo,,"{""zh"":[""红"",""赤色""],""en"":[""Red""],""es"":[""Rojo""]}",UPSERT
```

### 3.6.2 INSTANCE_VALUE CSV

Header：

```csv
propertyid,objectTypeId,value,language,op
```

| CSV 字段 | 目标字段 | 说明 |
|---|---|---|
| `propertyid` | `propertyid` | 所属 Property.id |
| `objectTypeId` | `objectTypeId` | 所属 ObjectType.id |
| `value` | `value` | 真实 Instance Value |
| `language` | `language` | 可选；未知使用 `und` |
| `op` | 导入操作 | `UPSERT` / `DELETE` |

```csv
propertyid,objectTypeId,value,language,op
prop:subscriber:subLevel,obj:subscriber:Subscriber,VIP,und,UPSERT
prop:subscriber:subLevel,obj:subscriber:Subscriber,GOLD,und,UPSERT
```

OAG 最终按 `objectTypeId + propertyid + normalized(value)` 保证 GaussVector 和 OpenSearch 中不存在重复业务记录。

---

## 3.7 MinIO 文件交互协议

OAG 文件导入参考 BDI/DataFactory 已有 MinIO 交互模式：生产者通过 S3 兼容 API 上传对象，消费者通过统一 S3 Client 读取；双方预先约定 Bucket，并启用 MinIO 所需的 Path-style 访问。OAG 不复用日志业务的 `bdi/minio/` 路径，而定义独立索引导入 Bucket/Prefix。

### 3.7.1 Bucket 与 Object Key

双方通过部署配置约定专用 Bucket，例如 `oag-retrieval-import`，Bucket 名称不能硬编码。推荐 Object Key：

```text
onto-retrieval/{tenantId}/{ontologyId}/{dataType}/{requestId}/part-00000.csv
```

### 3.7.2 S3 协议

DataSync 上传：`S3 putObject(bucket, objectKey, csvFile)`；OAG 读取：`S3 getObject(bucket, objectKey)`。

MinIO Client 启用：

```java
S3Configuration.builder()
    .pathStyleAccessEnabled(true)
    .build();
```

连接配置包括 endpoint/accessKey/secretKey/bucket，凭证通过平台配置或 Secret 管理，不写入 CSV，也不放在 import API Body 中。

### 3.7.3 文件不可变与校验

文件上传成功并提交 `file-import` 后，同一个 objectKey 在任务结束前不得覆盖。OAG 至少校验 Bucket 允许列表、Object 是否存在、size、sha256、CSV Header、dataType 对应 Schema 和可选 rowCount。百万/千万级数据必须流式读取，不允许一次性加载完整 CSV 到 JVM Heap。任务成功后按保留策略延迟清理；失败时默认保留文件用于重试和定位。
