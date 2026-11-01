# Agentic Operation Center 27.3.0 功能设计说明书（IRxxx 软件Q4需求）

> 版本：V1.2（2026-11-01 TODO 闭环、需求追溯与研发评审稿）  
> 日期：2026-11-01  
> 范围：OMS、OAG、DFx、安全、语义索引构建/检索、DataSync/Spark 联调及内部 Skill  
> 依据：本次最新 Q4 20 项需求；附件《新增Value参数统计_2026-10-31.md》《子图检索的查询性能规格(10-26).md》。原工作量 7.9 来源于旧版，**最新清单不含工作量，不再沿用**。  
> 定位：单文档覆盖 Q4 20 项原始需求、详细设计、已有验证数据、兼容边界、接口/SQL、异常处理和验收；**不是已上线或已达标证明**。

**相关设计**：[软件场景准确性和性能优化增强需求设计说明书](./软件场景准确性和性能优化增强需求设计说明书.md) · [OAG 本体锚点语义检索与向量索引设计方案 V6.7](./OAG本体锚点语义检索与向量索引设计方案.md) · [本体维值建模与检索需求分析](./需求分析Spec_本体维值建模与检索.md) · [V2 请求 Schema](./schemas/oag-software-subgraph-request.schema.json) · [V2 响应 Schema](./schemas/oag-software-subgraph-response.schema.json)。

**阅读与证据规则**：第 1 章保留全部 20 条原始要求及差异；第 2～7 章按“需求→设计→数据/接口→异常→验收”说明；第 8 章按需求编号闭环。**来源分级**：原始需求（不可遗漏）、GitHub V2/临时表/Notice 现有参考文档、旧实验实测数据、方案设计建议、待评审项互不等同。与 GDE 公共恢复/模型加密专项相关的详细实现不在本文重新定义。全文仅维护本文件，不新增其他文件。

---

## 1. 设计目标、场景与需求基线

### 1.1 业务背景与目标

CBS 面向运营商问账、集团客户问账，以及经营、销售、运营、运维人员的问计、问因和辅助决策。例如预付费账户数量、优惠余额、套餐月活 TOP3、账单风险等。业务 IRB 目标为**准确率 90%、业务端到端 5 分钟**；这不是 OAG 单接口 SLA。当前 CBS 本体参考规模为 **144 个 ObjectType、2896 个 Property、370 个 Relationship、11 个业务域**，模型仍在迭代。
模型参考：[CBS 场景的本体模型](https://clouddragon.huawei.com/cloudmodeling/myspace/diagram?diagramId=f46394eae0ec49d8a4693ebd93f0665c)；

![CBS场景的本体模型](https://cloudmodelingapi.tools.huawei.com/cloudmodelingdrawiosvr/d/1aa8934bdd27478cb45c4f5b06237c77?t=1792382890116)

本期 Q4 的重点是让 OMS/OAG 具备**安全交付、接口统一、自动索引、多实例扩展、配置治理、可恢复的数据同步与可量化的检索性能**。

### 1.2 最新目标与交付边界

| 目标 | 最新要求 | 主责 |
|---|---|---|
| OMS 安全 / DFx | 模型加密参数拆分，详细方案跟随《本体模型文件支持加密》；OMS 分域/定义接口及 Agent/OMS 双级缓存 | OMS/GDE |
| 公共 DFx | OMS/OAG 场景包分层与恢复指导书遵循 GDE 统一要求 | OMS/OAG/GDE |
| OAG 统一 | V2 query/entities 双模式、Skill V1 → V2，枚举不建索引、Property 全量返回枚举 | OAG/Skill |
| App 自动化 | **先修复手动创建索引偶现问题**，再自动触发建索引及图缓存刷新 | OMS/OAG |
| 全量增量 | 1000 万行首次全量、10 万行增量；DataSync 异步生产通知、Spark 合并小文件及前置去重 | Spark/DataSync/OAG |
| 租户资源 | **线程池、队列与并发配额按租户划分，线程池资源参数按租户 DCC 监听**；系统级参数不进入 DCC | OAG/配置底座 |
| 子图查询 | 依照附件：**2U4G 单实例 10 QPS、平均 ≤5 s、极端限流拒绝率 <20%**；3U4G 为建议压测规格 | OAG/性能测试 |
| 检索预研与安全 | 仅 OpenSearch 倒排检索及 ID-only 安全索引要共同评审 | OMS/OAG/安全 |

**边界**：保留 Q4-01～20 原编号；公共 GDE 和加密专项仅定义集成责任，不重复制定安全或运维底座规范。详细 Task API、DCC Watch 协议、数据库 LVQ 与索引删除时点属于待联调实现；不能把本文目标描述成已上线能力。

### 1.3 术语、责任边界与主链路

| 术语/责任 | 本文明确的边界 |
|---|---|
| OMS | 本体定义、EnumType、分域分组、模型 revision、App 安装状态与元数据权限的权威来源 |
| OAG | 定义索引和 Instance 值索引、V2 子图检索、内存图、异步任务生命周期、索引发布与租户资源隔离 |
| CBS/业务 Agent | 分域本体定义缓存；query 或提前抽取的 entities；对子图与业务知识进一步使用，不把 OAG 当业务推理引擎 |
| Spark | 计算侧生成图与语义索引数据、合并小文件、两类数据按完整业务键去重 |
| DataSync Producer/Consumer | 写 MinIO 不可变分片/Manifest → READY → 消费通知并调用 OAG Notice；不代替 OAG 的索引构建 |
| GaussVector / OpenSearch / NebulaGraph | 实例 Vector、词法倒排、图数据/内存图回源的不同存储依赖；故障与版本发布分别管理 |
| DCC | 租户线程池与配额等候选运行参数的动态配置来源，真实 SDK/命名空间需与平台底座核实 |
| `revision/generation` | 同一 ontology/tenant 下发布的一致模型版本；不同索引、图缓存不得跨 revision 混用 |
| 稳定业务键 | 实例值逻辑键 `(tenantId, ontologyId, objectTypeId, propertyId, normalized(value))`；若按租户/本体物理隔离，可在单表内使用后三项，**原值归一化规则必须冻结** |
| `U` 与 `U4G` | 早期成本估算中 `U` 的物理定义未给出；性能附件 `2U4G/3U4G` 为具体部署档位，需用部署单独确认 CPU/内存映射 |

```mermaid
flowchart LR
  Agent[CBS / Agent / Skill] -->|query 或 entities| OAG[OAG V2 检索]
  OMS[OMS 定义与 App] -->|模型 revision / EnumType| OAG
  OMS -->|分域定义 + revision| Agent
  OMS -->|App 安装事件| Job[OAG 索引任务 / 图缓存]
  Spark[Spark 清洗去重与合并] --> Producer[DataSync Producer]
  Producer --> MinIO[MinIO CSV + Manifest]
  MinIO --> Consumer[DataSync Consumer READY]
  Consumer -->|Notice| Job
  Job --> GV[GaussVector / OpenSearch]
  Job --> Graph[内存图 / NebulaGraph]
  GV --> OAG
  Graph --> OAG
```

**数据一致性原则**：Notice 受理不等于建库成功；任务状态与索引发布版本必须持久化，多实例请求使用相同的 active revision。敏感 ID/数据值在日志、缓存、接口中按 tenant/ontology 权限隔离。

### 1.4 最新需求范围与需求清单（2026-10-31）

根据本次最新输入，保留原先 20 条的序号与基本能力边界。**最新清单没有工作量列**，不将旧版 7.9 视为当前预算。

| 需求编号 | 模块与能力 | 本轮需求描述 | 详细设计 |
|---|---|---|---|
| Q4-01 | OMS / 本体加密 | 参数拆分；详细方案跟随《本体模型文件支持加密》 | §2.1、§6 |
| Q4-02 | DFx / OMS 分域 | 分域/本体定义接口规范，Agent 缓存+OMS 内部缓存避免实时全量查询 | §2.2 |
| Q4-03 | DFx / OMS 多实例 | 水平扩展及负载分担 | §2.3 |
| Q4-04 | DFx / OMS 恢复 | 公共故障恢复指导书，跟随 GDE 统一要求 | §2.5 |
| Q4-05 | DFx / OMS 配置 | 场景包参数分层，跟随 GDE 统一要求 | §2.4、§7 |
| Q4-06 | OAG / 统一接口 | 服务/软件场景统一；默认不建枚举检索索引，子图属性全量返回枚举 | §3.1 |
| Q4-07 | 接口统一 / Skill | V1 切换 V2，V1 标记 deprecated | §3.2 |
| Q4-08 | DFx / 自动索引 | **先修复手动建索引偶现问题**，再由 OMS App 安装触发 OAG 建索引并刷新图 | §3.3 |
| Q4-09 | DFx / 多实例 | OAG 多实例、内存图同步刷新及接口负载分担 | §3.4 |
| Q4-10 | DFx / 配置分层 | 组网参数场景包、系统参数配置中心、任务参数 API；租户线程池/DCC Watch | §3.5、§7 |
| Q4-11 | DFx / 恢复 | 公共故障恢复指导书，跟随 GDE 统一要求 | §3.5 |
| Q4-12 | 性能 / 数据导入 | **单表 1000 万行全量（100 万用户）、10 万行增量**；DataSync Producer/Consumer 异步通知（爱华）、Spark 目标 256M 小文件合并（振鲁）及图/语义去重、Embedding/向量库资源与入库规格 | §4.1、§4.7 |
| Q4-13 | 性能 / 子图查询 | **原始需求：单实例 10 QPS、3 s，并支持水平扩展**；10-26 测试附件：2U4G 10 QPS、平均 ≤5 s、拒绝 <20%——两种口径并列，验收优先级待冻结 | §5.1、§8 |
| Q4-14 | 性能 / 定义索引 | 数据库全量比对、差异 Embedding | §4.2 |
| Q4-15 | 性能 / LVQ | LVQ 建表前置、COPY 后免 rebuild 的目标及 DCC COPY 大小调优 | §4.5 |
| Q4-16 | 性能 / 删除 | Delete 语义索引删除接口联调 | §4.6 |
| Q4-17 | 性能 / 增量 | Incremental 在向量库比对，缺失/变化才向量化插入 | §4.3 |
| Q4-18 | 性能/准确率 / 预研 | 实例值只进 OpenSearch 不进向量库，OMS 配语义字段；关键词单路路由及覆盖范围评估 | §5.3 |
| Q4-19 | 安全 / 索引字段 | 向量/OpenSearch 去名称描述、ID 反查内存图/NebulaGraph，详情跟随加密专项 | §6.1 |
| Q4-20 | 安全 / 明文屏蔽 | 后台日志及前端子图明文脱敏，通过加密堆栈参数控制，详情跟随加密专项 | §6.2 |

**需求差异与优先级**：Q4-08 手动索引缺陷先于自动化；Q4-12 需完成 Spark→DataSync→MinIO→OAG 三项优化及 1000 万行验证；Q4-10 必须物理隔离租户线程池/队列；Q4-13 原始 **10 QPS/3s** 是不能删除的目标，附件 **2U4G/平均 5s** 是另一测试口径，**未评审前均保留，不能宣称 3s 已满足或已被正式取消**；Q4-18 的 Keyword-only 与 Q4-19 的 OpenSearch ID-only 存在安全与召回冲突。

### 1.5 需求到设计与验收追踪

| 设计专题 | 需求项 | 主要交付 | 验收用例组 |
|---|---|---|---|
| OMS 安全、分域及可用性 | Q4-01～05 | 模型加密、查询/缓存规范、OMS 集群、场景包参数与恢复手册 | OMS-Q4-01～05 |
| OAG V2 与 App 自动交付 | Q4-06～09 | 统一 V2、Skill 迁移、自动建索引和多实例图刷新 | OAG-Q4-06～09 |
| 配置及高可用 | Q4-10～11 | 分层参数、DCC 演进、多实例恢复手册 | DFx-Q4-10～11 |
| 索引与检索性能 | Q4-12～17 | FULL/INCREMENTAL/DELETE、数据库差异同步、LVQ 预研、压测与资源模型 | IDX-Q4-12～17 |
| 倒排-only 与安全 | Q4-18～20 | 属性检索模式预研、索引明文治理、日志/界面保护 | SEC-Q4-18～20 |

---

## 2. OMS 功能设计：本体加密、分域访问与高可用（Q4-01～05）

### 2.1 本体模型加密与参数拆分（Q4-01）

本项详细方案**跟随《本体模型文件支持加密》**，本文只要求 OMS 明确加密相关场景包/系统配置/请求参数边界，以及安装、升级、回滚、多实例加载时的参数传递、配置验证和集成测试。不得在此另行发明加密算法、密钥格式或 `onto_encrypt` 0/1 的含义。安全及模型文件兼容性验收由专项主导，OMS/OAG 承担接口和功能回归。

### 2.2 分域查询与定义接口、Agent/OMS 双级缓存（Q4-02）

**目标**：CBS 不在每轮 Agent 调用中实时拉取整本体；OMS 提供按域与按定义范围访问，Agent 按会话复用已验证定义。OMS 缓存加速仅对同一租户/ontology/revision 生效，不因跨会话内存缓存泄漏模型权限。

| 能力 | 既有/建议入口 | 请求与返回（需同 OMS 现行 DTO 对齐） | 缓存策略 |
|---|---|---|---|
| 分组列表 | `GET /api/v1/ontologies/{ontologyId}/list`（既有参考） | tenant 鉴权、本体 ID；返回组 ID/名称/可见性及 revision | Agent 每会话首次/失效后取；OMS 本地 LRU/TTL |
| 组成员与定义 | `POST /api/v1/ontologies/{ontologyId}/group/members`（既有参考） | Body 为 groupId(s) 等筛选参数；响应 ObjectType/Property/Relation 定义与 revision，**实际字段待 DTO 冻结** | Agent 只缓存当前分域使用的定义 |
| 本体定义批量查询 | 复用已有 OMS 定义查询接口（具体路径待 OMS 核对） | 按对象/属性 ID 列表 + revision 批量取；不逐属性 N+1 查询 | 同 revision 批量回源与 OMS 本地缓存 |

**缓存约束**：OMS Key 至少 `(tenantId, ontologyId, revision, groupId / definitionIds, authScope)`；Agent Key 含租户、session、revision 和分域选择，返回使用 ETag/版本号或显式 revision；OMS App 安装/模型 revision 切换后发布失效事件，Agent 订阅或下次调用检测版本，不以仅 TTL 保证强一致。命中率、回源数、过期数、首次/热缓存耗时、缓存内存及租户隔离可观测。失败时最多回退到**仍有效且已授权**的同 revision 定义，不能用旧模型冒充当前模型。

**新增场景与验收**（对应源 TODO，尚未有实测结果）：**10 个在线会话、10 路并发调用 OMS 分域/定义查询，3 秒内响应**。需要冻结：每个会话 1 次/多次请求、冷/热缓存、每次返回的分组及定义规模、网络和 JVM 环境、成功率统计口径。按 `10 个会话 × 每会话至少 1 个并发请求` 建议分别跑冷启动和预热后场景，记录端到端从 Agent 发起至 OMS 完整响应的延迟、P50/P95/最大值、OOM/GC 与回源次数；**默认按每请求 ≤3s 判定，不能以平均值掩盖单请求超时**，最终口径需业务测试签认。OMS 内部压测及 Agent 缓存复用测试分别报告，不把 OAG 子图的 5s 规格用在 OMS 接口上。

### 2.3 OMS 多实例水平扩展（Q4-03）

OMS API 由网关按健康 Pod 均衡，服务端缓存可各 Pod 自建但必须以**数据库模型 revision 作为事实源**。安装/升级成功后先发布模型 revision 变更事件，Pod 原子切换可见定义；未刷新或校验失败的 Pod 从就绪探针/路由池暂时摘除或回源，并保留旧有效版本只读。建议 1→2→3 Pod 回归：10 并发分域查询、单 Pod 故障、滚动升级、跨实例数据版本一致、CPU/堆缓存线性占用、认证 tenant 隔离和负载偏斜；会话状态不能保存在固定单 Pod 上。

**与加密依赖**：模型密钥生命周期、加密模型落盘/内存策略跟随专项；多实例只定义缓存重建、版本切换和安全访问的集成职责，不新增另一套安全协议。

### 2.4 OMS 场景包参数分层（Q4-05）

该项是 **GDE 公共需求**。OMS 提供场景包/系统参数与接口参数清单，适配 GDE 统一参数规范和配置校验、安装/升级/回滚机制，不单独设计一套 OMS 配置底座。

### 2.5 OMS 故障快速恢复（Q4-04）

**GDE 公共恢复指导书**为权威：OMS 补充模型 revision、分组缓存、多实例状态、加密依赖、App 安装与权限异常等专项章节，按公共模板输出症状、指标与命令、止损、恢复、校验和演练结果。RTO/RPO 以 GDE 统一标准为准，不自定新指标。

---

## 3. OAG 统一接口、自动交付与高可用（Q4-06～11）

### 3.1 服务/软件场景统一 V2 本体子图接口（Q4-06）

**现有规范与链接**：[GitHub《本体子图语义检索接口v2》](./本体子图语义检索接口v2.md)；历史设计参见 `ICT服务与软件/Agentic Operation Center/Docs/27/27.3.0/02.设计/02.设计文档/Agentic Operation Center 27.3.0 功能设计说明书(IR20260729001097_OAG子图检索能力增强)/1.子图检索接口设计v2.md`；[内部 Wiki 字段说明](https://wiki.huawei.com/wiki/WIKI2026101013239851?title=%E5%AD%97%E6%AE%B5%E8%AF%B4%E6%98%8E)。以 GitHub 已核验的正式 V2 参数表为接口设计依据；历史路径和 Wiki 属参考，不凭不可读取材料改写协议。

**统一 API**：`POST /v2/onto-retrieval/subgraph/semantic-search`，`Content-Type: application/json`。同一个入口根据 `query` / `entities` 参数组合运行，无独立软件 URL；Body 中传必填 `ontologyId`（1～256 字符），`query` 可选（1～1024），`entities` 可选（**JSON String，1～102400 字符**）；至少一个非空，两者都传则 **entities 优先**、服务端不再执行原始 query 的实体提取。

| Body 参数 | 接口默认 / 约束 | 设计说明 |
|---|---|---|
| `ontologyId` | 必填，1～256 字符 | 从 tenant 权限校验归属，不再拼入 V1 路径 |
| `query` / `entities` | 二选一非空，entities 优先 | entities 字符串解码后根为 `{"entities":{"extractedEntities":[...]}}` |
| `adaptiveRetrieval` | 默认 1 | =1 时 ObjectType+Property ≤300 节点默认返回全量；软件建议 **0** |
| `seedRetrievalMode` | `vector` / `keyword` / `hybrid`，服务端默认 `vector` | Skill 为延续旧调用可**显式传 hybrid** |
| `similarityThreshold` | 0.6，vector/hybrid 生效 | 关键词模式不由 dense 阈值直接过滤 |
| `topk` | 默认 3（小写 k） | CLI `--topK` 仅作兼容，向服务端发送 `topk` |
| `graphExpansionStrategy` | `minimal`（另有 khop/component） | `hopLimit=3`，khop 策略时生效 |
| `includeFunctions / includeActions` | 0 / 0 | Skill 可以为保持原行为显式传 includeFunctions=1 |

**软件配置组合**：entities 非空 + adaptiveRetrieval=0 + DCC/配置中心 `enableObjectLinking=false`、`enablePropertyLinking=false`、`enablePropertyValueLinking=true`、`includeAllProperties=true`，**开关不是请求 Body 参数**。`entities.extractedEntities[]` 至少 1 个对象，objectType 必填，properties 可省略（本期软件约定不传）；`propertyValues[].propertyValues[].value` 必填；`property` 可省略或空串，表示在该 ObjectType 全部启用的实例值语义属性中链接。种子仅为 ObjectType，实例 value 命中对象归并种子；枚举不用索引检索，Property 装配全量 OMS EnumType/values[]。

**请求示例**（entities 是 JSON 字符串，而非直接嵌套对象）：

```json
{
  "ontologyId": "dtmi.ontology.example.1",
  "query": "How many prepaid accounts are there?",
  "entities": "{\"entities\":{\"extractedEntities\":[{\"objectType\":\"Account\"}],\"propertyValues\":[{\"objectType\":\"Account\",\"propertyValues\":[{\"property\":\"paymentType\",\"value\":\"prepaid\"}]}]}}",
  "adaptiveRetrieval": 0,
  "seedRetrievalMode": "hybrid",
  "similarityThreshold": 0.7,
  "topk": 2,
  "graphExpansionStrategy": "minimal",
  "includeFunctions": 0,
  "includeActions": 0
}
```

**返回结构与可选扩展**：`resultCode / resultMessage / result`，后者包含 `seedNodes`（只有对象种子）、`nodes`、`edges`、`functions`、`actions`，可含 `propertyValuesLinks`（值链接诊断，包含 `valuesMapping[]`）；`result=null` 为失败。entities 响应示例2-1 采用 `nodes[].label/properties` 与 `edges[].edgeType/propertyMap`；**Property 节点顶层**可有 `propertyEnumValues`（仅枚举型、OMS 全量）及 `propertyInstanceValues`（仅支持实例链接且有命中），`properties.dataType=enum` 时带 `enumDataType`。`propertyEnumValues[].isDefault` 为 `"true"/"false"` 字符串；本次不继续依赖 `semanticExtensions`。query 示例1-2 还沿用 `nodes[].type`/`edges[].name`，**两套返回 DTO 尚未最终统一**，客户端应按实际类型适配。

**规范差异记录**：V2 query 示例1 省略了参数表必填的 `ontologyId`，以参数表为准；entities 响应示例包含历史 Enum 映射候选，与本期“不建/不查 t_oag_enum”实施原则不同——新方案只从 OMS 返回完整 Enum Property，不能以旧示例推断仍有 Enum 召回。OAG 只提供受控相关子图、不执行任意 nGQL、规则推理或业务决定；图方向及最小连通方式须保持原始关系语义。

### 3.2 Skill 和脚本从 V1 迁移到 V2（Q4-07）

**本次改造文件**：`ontology-platform-unified-skill/SKILL.md`、`ontology-platform-unified-skill/scripts/semantic_subgraph_search.py`。原脚本按 `/v1/onto-retrieval/{ontologyId}/subgraph/semantic-search` 拼接 URL、Body 使用 `topK`、强制 query，不支持 entities，并且 HTTP 失败可能被当成成功。迁移后的脚本改用 `/v2/onto-retrieval/subgraph/semantic-search`，`ontologyId` 入 Body、发送 `topk`，支持 query-only、entities-only 与混合输入，并进行本地参数校验。

**Skill 调用**：

```bash
python scripts/semantic_subgraph_search.py --query "<问题/业务主题>"
python scripts/semantic_subgraph_search.py --ontology-id "<本体ID>" --entities-file ./entities.json --adaptive-retrieval 0
python scripts/semantic_subgraph_search.py --query-json @request-v2.json
```

第一条需要环境变量 `ONTOLOGY_ID`；仍需 `SERVICE_NAMESPACE`、`TENANT_ID`。`--entities-file` 或 `--entities` 传入内部对象或 `{"entities":{...}}` 包装后自动转 HTTP JSON String。完整 Body 支持显式 0，不再通过 `or default` 覆盖。脚本正确识别 HTTP 非 2xx、`resultCode` 失败、`result=null`、非法 JSON 和网络超时，失败时输出结构化错误并返回非零退出；**保留原 `message_type=message_ontololgy_subgraph` 以避免上游包装契约突变**。

**V1 deprecation**：迁移各调用方后可按正式评审添加 `Deprecation` 公告，监控旧端点调用来源及流量；V1 不立即删除，需业务回归、灰度回退和退役批准。

### 3.3 App 安装自动创建索引、刷新内存图（Q4-08）

**P0 前置门禁：修复手动索引偶现失败。** 复现同 tenant/ontology/revision 的重复点击、异步任务排队、异常重试、图模型刷新失败、半成品向量表和两 Pod 并发构建；收集任务阶段、错误码、线程队列、数据库 DDL、缓存版本日志定位，修复后做批跑和断点恢复，原 activeRevision 未受影响才进入自动流程。

**设计事件**：OMS 安装/升级 App 完成模型落库→记录 `tenantId, appId, ontologyId, modelRevision, operation, requestId`→通过可靠投递/outbox 通知 OAG（推荐内部 API，具体路径待冻结）→OAG 以 `(tenantId,ontologyId,modelRevision,operation,requestId)` 任务级幂等；先创建持久 Task，再异步构建定义索引与图缓存影子版本→校验数据完整性及 schema→提交发布标记/activeRevision→所有 Pod 检测 revision 后加载，不同 revision 不混用。HTTP 202 只代表受理，不代表就绪；OMS 面向上层应提供安装成功与“检索就绪”两种可观察状态。

**状态转移建议**：`ACCEPTED → VALIDATING → BUILDING → VERIFYING → PUBLISHING → SUCCESS`，任何可恢复阶段可进入 `FAILED_RETRYABLE`，不可恢复变为 `FAILED_FINAL`，取消需有安全检查点；这是建议 Task 内部状态，不替代当前数据库的 status=0/1/2/3 状态编码。失败保留旧 active revision，修复后可按相同 requestId 重试，避免重复索引。发布或回滚前须确保缓存与索引同一 modelRevision，不能从未验证的 `PUBLISHING` 暴露结果。

### 3.4 OAG 多实例水平扩展、内存图一致性与负载分担（Q4-09）

**参考既有专项**：`ICT服务与软件/Agentic Operation Center/Docs/27/27.3.0/02.设计/02.设计文档/Agentic Operation Center 27.3.0 功能设计说明书（IR20260731000589 SR20260806887975&SR20260806887798 本体模型支持内存图管理和子图检索）.md`。本文定义 Q4 集成闭环，具体缓存 SDK/内部协议以该专项联调确认。

- **计算/流量**：OAG 2/3 Pod 经健康网关负载分担，各 Pod 查询本地只读、按 tenant/ontology/revision 隔离的内存图；索引构建 Task 使用数据库持久状态和抢占租约/心跳选主，不能多 Pod 重复执行同一 Task；Worker 接管按任务 Checkpoint 重放。
- **缓存版本**：OMS revision 为源，OAG 在本地影子图加载/校验后原子切换；发布记录只包含已验证 revision，热切换时旧查询绑定旧版本直到完成，避免 nodes/edges 与向量索引错版。Pod 漏通知应轮询/重连后对账，迟到通知不得回滚到旧版本。
- **负载与内存**：每 Pod 图对象数、100MB/本体的附件估算及实际存储占用单独计量；图缓存采用有界/租户隔离的预热和淘汰。构建任务、Embedding、查询可采用分离线程池，避免模型入库阻塞实时检索。
- **故障恢复/验收**：N=1/2/3 的成功 QPS、延迟与分布；杀死一个 Pod、换新 Pod、修正 DCC、重放 Notice、模型更新时全局查询可用和 revision 一致性，保留每 Pod CPU/内存/线程/网络和下游向量服务负载证据。下游瓶颈不能通过增加 OAG Pod 数自动消失（详见 §5.1）。

### 3.5 OAG 参数分层与公共故障恢复（Q4-10～11）

分层规则见 §7.1；**线程池资源按租户隔离，线程池参数按租户 DCC 监听**（详见 §7.3～§7.5），不能用全局 `@Value` 静态注入声称支持租户热更新。容器还须有全局资源上限。

故障快速恢复**跟随 GDE 公共需求**，OAG 专项增加：Embedding 服务 503、Instance Task 卡住、MinIO READY/NOTICE 丢失、租户队列饥饿/配置 Watch 错误、图缓存 revision 不一致等场景。提交证据包括监控/日志、恢复动作与演练结果；RTO/RPO 仍按 GDE 统一要求执行。

---

## 4. 实例索引构建、差异同步与性能（Q4-12、Q4-14～17）

### 4.1 Spark/DataSync 全量与增量数据入库、1000 万行验收（Q4-12）

**原始规格**：单表首次全量 **1000 万行 / 100 万用户**，增量 **10 万行**。输入按 tenant/ontology/modelRevision/snapshotVersion 定义同一版本快照，OAG 不直接等待 Spark/MinIO 文件生成完成。源需求的三项措施及责任不合并：

1. **DataSync 生产者—消费者异步（爱华）**：Producer 接收 Spark 已生成的独立语义索引 CSV（不重复生成），写入 MinIO **不可变文件**，完成 checksum/rowCount/Manifest 后发布 READY；Consumer 只有收到完整 READY 才调用 `index-data/notice`，OAG 返回任务 `ACCEPTED` 并持久化后 Consumer ACK。这样去掉**接口同步等待 CSV 上传 MinIO**，但 OAG 必须仍读取 CSV、做真实入库、异步更新任务状态；READY 丢失通过 outbox/重放重试，不允许仅凭“文件存在”判定快照完成。实际 Notice DTO 暂只有 files 列表，Manifest/READY/ACK 为 DataSync 协议演进建议，**不能当作现有必填字段**。
2. **Spark 合并小文件（振鲁）**：计算侧按租户、ontology、revision、快照和分区归属合并图数据/语义索引小文件，**目标单文件 256M（原 TODO 写法，按 MB/MiB 单位需压测冻结）**。不可跨 snapshot/version/tenant 混合，合并后重算文件 hash/rowCount；测试前后 OAG Notice 次数、MinIO 对象数、DataSync 请求 CPU 和排队时间。
3. **Spark 图/语义去重前移**：图按完整顶点/边复合键及事件版本去重；语义按 `(tenantId, ontologyId, objectTypeId, propertyId, normalized(value))` 去重。新的语义索引文件由 Spark 单独生成，DataSync 直接上传 MinIO；**后端仍保留唯一索引与幂等**，避免跨批、回放和乱序导致 COPY 主键冲突。

```mermaid
sequenceDiagram
  participant S as Spark
  participant P as DataSync Producer
  participant M as MinIO
  participant C as DataSync Consumer
  participant O as OAG Task
  participant V as Vector / OpenSearch
  S->>S: 图/语义去重 + 256M目标文件合并
  S->>P: 独立语义CSV分片/快照版本
  P->>M: 上传分片 + sha256 + Manifest
  M-->>P: 分片全部可读
  P->>C: READY(jobId/snapshotVersion/manifestUri)
  C->>O: POST notice(租户header, requestId, files)
  O-->>C: accepted taskId(s), 任务已落库
  C->>C: ACK READY（支持重放）
  O->>M: 流式读取CSV并校验hash/rowCount
  O->>V: 差异识别/Embedding/写入/Verify
  O-->>C: 由query查询最终SUCCESS/FAILED
```

#### 4.1.1 历史实测数据（源 TODO 完整保留并修复原表格合并表头）

原 TODO 提供的实验条件为 **OAG 3U4G、8/16 并发、不同服务器及文件数**；以下速率来自该表，**不是 1000 万全量的已达标数据**。

| 测试模型 | 服务器类型 | OAG规格 | 数据量 | 测试场景 | OAG接口同步（条/s） | Embedding读数据（条/s） | 向量入库（条/s） | 总耗时（s） |
|---|---|---|---|---|---:|---:|---:|---:|
| 单文件全量 | 920C 物理机 | 3U4G | 10万 | 8并发 | 345.01 | 526.73 | 814.71 | 289.85 |
| 单文件全量 | HV6 虚拟机 | 3U4G | 18万 | 8并发 | 340.74 | 463.32 | 706.09 | 528.26 |
| 多文件10并发全量 | 920C 物理机 | 3U4G | 200万 | 8并发 | 262.81 | 215.18 | 316.83 | 7610.10 |
| 多文件10并发增量 | 920C 物理机 | 3U4G | 20万 | 8并发 | 403.80 | 859.52 | 770.90 | 505.20 |
| 多文件10并发全量 | 920C 物理机 | 3U4G | 20万 | 16并发 | 387.32 | 1550.39 | 556.49 | 526.70 |
| 多文件10并发增量 | 920C 物理机 | 3U4G | 20万 | 16并发 | 451.32 | 1252.11 | 826.45 | 452.00 |

**证据级别与风险**：上表中“Embedding读数据速率”是原实验列名，**不能直接断言等于模型推理吞吐**；每个阶段统计窗口可能不同，不相加为总吞吐。20万数据、16并发的某些阶段反而变慢，应检查存储瓶颈、上下游并发与文件数。另据本次 TODO，**Embedding 模型约 120 条/s 向量**，这属于另外一个已提供的观察值，未标明模型副本数、文本长度或批次，请独立复核。

#### 4.1.2 100 万用户/1000 万行验证与资源模型

1. **固定数据和工作负载**：100 万用户、单表 1000 万 **去重前/后两种行数均记录**，ObjectType/Property 分布、纯数字 ID 占比、平均文本长度、每用户十条的示例关系需验证。分别压测首次 FULL（全新键）与 10 万增量（新增键比例 0/10/100%），不能把全部已存量的 INCREMENTAL 当成全量。
2. **串联全链路**：Spark 计算/合并→DataSync Producer→MinIO READY→Consumer Notice→OAG CSV 读取与验证→数据库差异→Embedding→COPY/LVQ→OpenSearch→任务 Publish；分别统计总耗时和各阶段 wall-time，包含失败重试与资源峰值。每种工作负载做 1/2/3 OAG Pod 和 1/2/3 Embedding 模型副本矩阵。
3. **容量初算，不是验收结论**：仅按历史 200 万全量/7610.10s 等比例外推，1000 万全量约 **38050.5s ≈10.57 小时**（等效端到端 262.81 条/s）；如 1000 万条全部要推理、且一个模型服务持续 120 条/s，则模型单副本理论下限约 **83333s ≈23.15 小时**，2 副本理想下限约 11.57h，尚未加上 IO/数据库与下游争用。**两个估算来自不同测试口径，不能同时视为可实现吞吐**；实际耗时至少受真正的 Embedding 在途能力和最慢流水段约束。
4. **多实例受限场景**：当 OAG 从 1 Pod 扩至 2 Pod，理论并发/吞吐可增加，但若 Embedding 固定 120 条/s、GaussVector COPY/IO 或 MinIO 带宽不扩，**不能承诺 2 倍吞吐**。先算 `min(OAG可调度行速率, embedding实例数×可用120条/s, 向量库可持续写速率, OpenSearch/网络瓶颈)`，再用实测确认扩展效率；模型副本横扩需检查实际负载均衡和 Istio 503 UC。
5. **资源预算**：OAG CPU/堆/线程/连接（3U4G历史与 2U4G查询档位不得混淆）、Embedding 模型容器 GPU/CPU 与实例数、GaussVector LVQ/COPY 内存及磁盘/IOPS、OpenSearch bulk/thread pool、MinIO 文件空间和暂存峰值分别报价，给出新增数据率变化的资源斜率。结果按 N 实例、N 模型副本和各 stage rows/s 发布，不以固定资源值代替容量测算。

**通过条件**：1000 万全量和 10 万增量均记录数据完整数/去重数、源 Manifest checksum、任务最终状态、重复 Embedding 率、向量/倒排计数一致性、无主键冲突、错误恢复。**最新原始需求只给了规模没有给全量入库总时长硬阈值；最终总耗时、资源预算、可扩倍数须以压测结论签审**，不自造“10 分钟”类指标。

### 4.2 定义索引“全量比对 + 增量 Embedding”（Q4-14）

TODO：下面的方案，保留SQL语句，按照本体实例增强数据分批增量Embedding独立临时表设计方案 刷新

验证结果：

GaussDB识别2张表增量差异的SQL语句：
```Sql
SELECT  
	test."value",  
	test.object_type_id,  
	test.property_id  
FROM test  
WHERE NOT EXISTS (  
	SELECT 1  
	FROM "t_oag_instance_dtmi.ontology.65313863.1"  
	WHERE "t_oag_instance_dtmi.ontology.65313863.1"."value" = test."value"  
	AND "t_oag_instance_dtmi.ontology.65313863.1".object_type_id = test.object_type_id  
	AND "t_oag_instance_dtmi.ontology.65313863.1".property_id = test.property_id  
);  
```

```
ontoretrievalvectordb2000=# SELECT  
ontoretrievalvectordb2000-# test."value",  
ontoretrievalvectordb2000-# test.object_type_id,  
ontoretrievalvectordb2000-# test.property_id  
ontoretrievalvectordb2000-# FROM test  
ontoretrievalvectordb2000-# WHERE NOT EXISTS (  
ontoretrievalvectordb2000(# SELECT 1  
ontoretrievalvectordb2000(# FROM "t_oag_instance_dtmi.ontology.65313863.1"  
ontoretrievalvectordb2000(# WHERE "t_oag_instance_dtmi.ontology.65313863.1"."value" = test."value"  
ontoretrievalvectordb2000(# AND "t_oag_instance_dtmi.ontology.65313863.1".object_type_id = test.object_type_id  
ontoretrievalvectordb2000(# AND "t_oag_instance_dtmi.ontology.65313863.1".property_id = test.property_id  
ontoretrievalvectordb2000(# );  
value | object_type_id | property_id  
--------------+---------------------------------------+-------------  
温控器A | oag_instance_dtmi.ontology.65313863.1 | P1001  
3号车间-东区 | oag_instance_dtmi.ontology.65313863.1 | P1002  
(2 rows)
```

### 4.3 Incremental 和 FULL_REPLACE 的数据库差异比对（Q4-17）

TODO：下面的方案，保留SQL语句，按照本体实例增强数据分批增量Embedding独立临时表设计方案 刷新

**核心实现目标**：以数据库内组合键比较替代全量删表/全量重复 Embedding。稳定键为 `(object_type_id, property_id, normalized(value))`，并加 `tenantId/ontologyId` 物理隔离；源值归一化语义必须固定。

**FULL_REPLACE**：
1. 由于是首次全量入库，按照当前已有的索引入库流程，每一条数据均需要做embedding，然后批量copy入库。

**INCREMENTAL（只有变更集）**：
1. 按照批次新建临时表，建表结构同原有的向量表结构。
TODO：补充临时表的表名命名，防止多并发表名冲突

```sql
create table if not exists "${tableName}"  
(  
    vector floatvector(${vectorDim}) not null,    value VARCHAR(4096),    synonyms text,    property_id VARCHAR(512) not null,    property_name VARCHAR(512),    object_type_id VARCHAR(256) not null,    object_type_name VARCHAR(512),    CONSTRAINT "uk_instance_${tableName}" PRIMARY KEY (object_type_id, property_id,value));  
set maintenance_work_mem='4GB';  
```

2. 将增量数据插入临时表，只写入value、property_id、object_type_id三个字段的值；
3. 在Gauss库内比对和识别增量数据，然后针对增量数据进行embedding并入库。
4. 

### 4.5 LVQ 预建（Q4-15）

LVQ索引:支持空表建索引
https://3ms.huawei.com/km/blogs/details/17820657?l=zh-cn

``` sql
CREATE Index tablename_idx_lvq on tablename using gsdiskann (vector L2/Cosine) with (
      enable_pq = true, 
      lvq_nclus = 128, 
      subgraph_count = 1, 
      quantization_type = 'lvq', 
      num_parallels = xx, 
      enable_vector_copy = false, 
      build_with_quantized_vector = true
    );
```
TODO: 去除原有代码逻辑中的重建索引的逻辑，可以参考：https://github.com/cfwl100/onology_dsl/blob/main/docs/notice%E6%8E%A5%E5%8F%A3%E5%88%B0%E5%90%91%E9%87%8F%E5%85%A5%E5%BA%93%E5%AE%8C%E6%95%B4%E6%B5%81%E7%A8%8B.md

### 4.6 Delete 接口及索引删除联调（Q4-16）

参见《ICT服务与软件/Agentic Operation Center/Docs/27/27.3.0/02.设计/02.设计文档/Agentic Operation Center 27.3.0 功能设计说明书（IR20260731000589 SR20260804861012&SR20260804861215&SR20260804861015&SR20260804861454 OAG语义检索）.md》

TODO: notice接口delete字段，代表删除对应的记录
**INSTANCE_VALUE CSV 字段：**

| CSV 字段 | UPSERT | DELETE | 说明 |
|---|---:|---:|---|
| `property_id` | 必选 | 必选 | 所属 Property.id；作为稳定归属键的一部分 |
| `property_name` | 必选 | 必选 | Property 的规范 `name`；由生产者提供，必须与 `property_id` 在当前 ontology generation 中一致 |
| `object_type_id` | 必选 | 必选 | 所属 ObjectType.id；作为稳定归属键的一部分 |
| `object_type_name` | 必选 | 必选 | ObjectType 的规范 `name`；由生产者提供，必须与 `object_type_id` 在当前 ontology generation 中一致 |
| `value` | 必选 | 必选 | 去重后的真实 Instance Value；与归属 ID 一起确定业务键 |
| `synonyms` | 可选 | 忽略 | 实例值同义词；CSV 中使用 `\n` 转义分隔 |
| `op` | 必选 | 必选 | `UPSERT / DELETE`；`FULL_REPLACE` 中只允许 `UPSERT` |


### 4.7 联调与容量测算（Q4-12）

压测分为：① 1000 万行首次 FULL；② 10 万行增量中分别注入 0%、10%、100% 新值（用于观测嵌入重用）；③ 批次乱序、重试、断连、分区缺失；④ 双库存储故障；⑤ 多实例故障接管与任务恢复。明确模型 ID、去重率、值平均长度、Embedding 模型和限流参数、数据源快照版本、COPY 方式、数据库副本和资源规格；输出全链路瓶颈与建议配置，而非仅给单线程 rows/s。

---

## 5. 查询性能与分级索引预研（Q4-13、Q4-18）

TODO：需要考虑OAG多实例时，可以水平扩展，并发数翻倍，同时依赖embedding模型的水平扩展能力。
embedding模型120条/s向量。

### 5.1 子图检索性能规格与横向扩展（Q4-13）

**权威性能输入**：《子图检索的查询性能规格(10-26).md》。该指标专用于软件场景，Pipeline **只包含实体链接 → 实体裁剪 → 子图构建**；不计 CBS 业务分词、索引数据入库或 Cypher 执行。**本轮正式规格从旧草案“3 s”调整为附件给出的“2U4G 单实例、10 QPS、平均耗时 ≤5 s、极端拒绝比例 <20%”**。附件另建议**实际压测按 3U4G 开展**；二者须分开标注并各自测量，不能拿 3U4G 的成绩证明 2U4G 指标。

| 约束类别 | 附件值 | 验收边界 |
|---|---|---|
| 本体模型 | ObjectType **≤150**，Property **≤3000**，Edge **≤400** | 当前 CBS 144/2896/370 在约束内，后续超限需重新评估 |
| 单实例配置 | **2U4G** | 静态内存图预算 **1 GB（10 × 100 MB）**；该规格最多承载 **10 个本体** |
| CPU 单核下限 | SHA-256 256B **≥280 万 ops/s、≥700 MB/s** | CPU 密集型基准；附件有 openssl 命令 |
| 输入对象 | `entities` 对象数 **<20** | 超出范围不可直接按此性能基线承诺 |
| `propertyValues` 数量分布 | **1–4：40%；4–8：50%；8–12：<10%** | 4/8 边界重合且占比未封闭为 100%，压测脚本需先冻结分桶含义，不自行修改附件 |
| 流量与样本 | 每秒发 **10 个请求，连续 1000 次**，CXO 黄金测试集 L1 | 记录成功、拒绝、业务异常和超时；发送约 100 秒 |
| 平均耗时 | **≤5 s** | 平均统计口径与未完成/拒绝请求处理须评审冻结；P95/P99 可观测但**不是附件硬阈值** |
| 吞吐 | **最大 10 QPS** | 这是附件列出的输入/吞吐规格，需同时报告成功 QPS |
| 流控拒绝 | 极端场景 **<20%** | 队列满的拒绝属正常但必须单独统计比例 |
| 内存/资源变化 | 后续新增 CPU 密集任务 | 应下调性能基线或增加资源，不默认仍保持 2U4G 指标 |
| 硬件 | ARM 鲲鹏 920C 物理机为标配，x86 Intel 2288 HV6/E9000 虚拟机为局点情况 | 记录架构、CPU 单核基准和虚拟化条件 |


| 参数 | 本次测试条件 | 说明 |
|---|---|---|
| `seedRetrievalMode` | `hybrid` | 向量+关键词 |
| `similarityThreshold` | **0.7** | 与 V2 接口缺省 0.6 不同 |
| `topK` / V2 `topk` | **≤3** | >3 不在附件测试范围 |
| `hopLimit` | **≤3** | khop 生效 |
| `adaptiveRetrieval` | **1** | 小本体 ≤300 节点可全量；具体计数边界需核实 |
| `includeFunctions` / `includeActions` | **0 / 0** | 不扩大关联对象 |
| `graphExpansionStrategy` | **minimal** | 路径低冗余策略 |
| `subgraph-retrieval-cache-switch` | **false** | **压测关闭问题缓存**，不能用缓存命中虚增指标 |

**执行规则**：重启后预热 **3 分钟**，前 **3 次**压测结果不计；**查询高峰不得并行进行实例值向量化入库**，需错峰。测试在 2U4G 基准和 3U4G 建议资源分别运行，采集成功请求平均时延、P50/P95/P99、拒绝率、错误率、CPU/内存/GC、OMS EnumType 读取、Instance 检索和图算法耗时、每租户活跃线程及排队情况。扩到 2/3 Pod 时分别固定总入口 QPS 和每 Pod 压力，评估共享向量库/图库饱和，而非默认线性扩展。

### 5.2 租户级查询准入与信号量流控

《新增Value参数统计_2026-10-31.md》扫描值：`semantic-search.max-pool-size=30`、`semantic-search.queue-capacity=50`、`semantic-search.timeout-seconds=300`。


### 5.3 OMS Property `retrieval` 索引模式扩展设计（Q4-18，预研）

**设计输入**：现有属性定义在 `retrieval` 下只有 `enabled`（样例 `accountId` 为 `false`）。新增**可选** `indexMode`，支持 **仅关键词、仅向量、混合**三种取值；未填写 `indexMode` 且启用检索时默认**混合索引**，以兼容既有开启检索的属性。保留 `retrieval.enabled=false` 的优先级，**禁用属性不能因为省略 indexMode 被自动启用**。

**OMS Property 最小改造示例**（保留原 `id/name/display/description/status/extensions/dataType/refSynonymTypeName/createdAt` 等属性字段不变）：完整检索子结构的建议 [JSON Schema](./schemas/oms-property-retrieval.schema.json) 已单独提交，**该 Schema 只校验 `retrieval` 字段，不替换 OMS 现有完整 Property Schema**。

```json
{
  "id": "dtmi.65313863.property-type.38396236-3130393330653430.1",
  "name": "accountId",
  "dataType": "long",
  "retrieval": {
    "enabled": true,
    "indexMode": "KEYWORD_ONLY"
  }
}
```

完整字段表：

| 字段 | 类型 | 默认 / 取值 | 规则 |
|---|---|---|---|
| `retrieval.enabled` | boolean | 沿用模型既有值，如 `false` | **false=不构建实例语义索引，也不参与值召回**；属性仍可在 OMS 建模/Binding/子图属性补全出现 |
| `retrieval.indexMode` | string（可省略） | `HYBRID`（当 enabled=true 且字段缺失时） | `KEYWORD_ONLY` / `VECTOR_ONLY` / `HYBRID`；建议仅 enabled=true 时生效 |
| `retrieval` 整体缺失 | 继承既有模型规范 | 不在本文另行改变 enabled 的缺省 | 防止新字段引入对旧模型的隐式索引启用 |

**四种有效运行状态**：

| enabled / indexMode | OpenSearch | GaussVector | Embedding | 查询通道 |
|---|---|---|---|---|
| `false` / 任意（建议不填） | 不建 | 不建 | 不调用 | 无 |
| `true` / 字段省略或 `HYBRID` | 建 | 建 | 调用 | Keyword + Vector，RRF 或既有融合 |
| `true` / `KEYWORD_ONLY` | **建** | 不建 | 不调用 | **仅 Keyword** |
| `true` / `VECTOR_ONLY` | 不建 | **建** | 调用 | **仅 Vector** |


**查询路由与融合**：进入 Instance Value Linking 时按 `objectType + propertyId` 确定其 indexMode，然后将请求全局 `seedRetrievalMode` 与 Property 支持通道做**交集**。全局 `hybrid` + KEYWORD_ONLY 只执行 Keyword，+VECTOR_ONLY 只执行 Vector；只有一个可用通道时不应以“缺少另一通道分数”进行惩罚；RRF 仅对实际执行的通道融合，`similarityThreshold` 仅约束 Vector。若全局请求为 `vector` 而属性只有 KEYWORD_ONLY，**不得偷偷改为 keyword**；应定义空候选/显式不兼容诊断（具体 API 行为待评审）。当 `property` 省略或 `""` 时，检索当前 ObjectType 下**所有 `retrieval.enabled=true` 的语义字段**，并按各属性模式分派查询，不无条件扫描所有非语义属性。

**是否所有实例都入 OpenSearch？** 否。只有 `HYBRID`/`KEYWORD_ONLY` 的有效属性值进入 OpenSearch；`VECTOR_ONLY` 只入向量库；`enabled=false` 不入二者。**EnumType/values[] 永远来自 OMS 本体定义，不由 `indexMode` 启动枚举索引。**

**与 Q4-19 安全方案的依赖**：如果最终要求 OpenSearch 严格 ID-only，基于 name/description/value 的 BM25/Keyword 检索能力将受限，须安全评审允许的受控词法字段或明确精确检索/召回降级，不得声称在严格 ID-only 下完整保留模糊召回。

**预研验收**：验证四状态的实际索引内容与 Embedding 调用次数；全文/向量单通道路由、hybrid 的 RRF 与 topK；revision 模式切换/删除、跨租户隔离、无 property 过滤时的对象内字段路由；使用纯数字 AccountId、英文/中文短文本、同义词测试 Recall@K/Precision@K、磁盘量、入库/查询耗时。正式 DTO 字段名和值取值、模式变化是全量重建还是增量、禁用后索引删除授权等由 OMS/OAG/安全联评后冻结。

---

## 6. 数据安全与明文治理（Q4-19～20）

### 6.1 向量与 OpenSearch 去名称描述、按 ID 回查（Q4-19）

**详细方案跟随《本体模型文件支持加密》**。OMS/OAG 负责字段适配和权限回归：向量/全文索引尽量只持久化稳定 ID、归属和必要检索元数据，名称/描述查询通过 OMS/内存图/NebulaGraph 按 ID 或经授权的 name→id 方案补齐，不能跨租户读取其他模型数据。哪些明文字段允许保留、加密格式及密钥轮换由专项冻结。

**功能冲突必须决策**：OpenSearch 若只存 ID，无法原样执行针对 name/description 的 BM25 与 fuzziness；Q4-18 的 lexical-only 在安全评审前不能同时承诺严格 ID-only 和完整模糊召回。需明确授权词法字段或接受能力降级，基于真实黄金集测试召回、ID 回查、索引迁移、旧客户端兼容和性能影响。固定哈希不等于模糊文本检索。

### 6.2 后台日志与前端子图明文脱敏（Q4-20）

**详细方案跟随《本体模型文件支持加密》**。原需求提出后台可打印子图明文、前端页面子图明文脱敏，开关由**加密堆栈参数**控制。何时允许后台明文、默认开关状态、授权角色与环境范围必须由加密/安全专项确认，**不意味着常规生产日志应默认打印完整子图**。

建议仅在获授权、时效受控且可审计的调试场景允许后台子图明文；平时日志记录 traceId、revision、节点/边数量、任务 ID、错误码。前端遮盖应在服务端鉴权后执行相应字段/可见性策略，不能只依赖 CSS；导出、响应、异常栈、APM 也应一致。加密堆栈开关属于安全/部署级配置，**不纳入普通租户线程池 DCC 配置**。OMS/OAG 的验收仅覆盖专项方案的接口联调、日志/页面/导出回归。

---

## 7. 参数分层、DCC 租户监听与资源池隔离（Q4-05、Q4-10）

### 7.1 参数统计口径与分级原则

**附件依据**：《新增Value参数统计_2026-10-31.md》统计最近 3 个月 Java 新增 `@Value`：**115 处注解、83 个唯一配置 Key**，**该统计只说明代码新增声明和默认值，不证明所有键已注册到 DCC、具备动态监听或已在本体服务运行时生效**。**统计一致性注意**：附件摘要写 83 个唯一 Key，但七类明细表实际逐行列出 **72 个不同 Key**（本轮 DCC 候选 38 个、系统级 34 个），有 **11 个 Key 未在附件分类明细中列出**；必须重新对照源码扫描结果补齐后才可宣称完成全部 83 项分类。同名 Key 的不同默认值按原表保留，不能未经检查选一个作为正式配置。

| 分级 | 配置来源与示例 | 本次约束 |
|---|---|---|
| 场景包/部署组网 | `onto_encrypt`、`oag.cache.type`、图数据库依赖 | 跟随 GDE 公共参数分级；不能由租户 Body 越权修改 |
| **租户级 DCC** | §7.2 的线程池、资源准入、检索/排序、功能开关、索引任务参数 | **按租户隔离资源/队列，按租户 Watch/推送更新，具备资源上限、审计和安全回退** |
| 系统级非 DCC | 附件第 5/6/7 类：MinIO、Nebula、OpenSearch、证书与数据库、租户初始化/namespace、Pod/日志/探针 | **不放置在 DCC**，由部署底座/系统密钥或环境管理；租户不能随意覆盖基础设施连接参数 |
| 请求/任务级 | V2 query/entities、topk、hopLimit、jobId、snapshotVersion、COPY 任务模式 | 原 API 参数不自动提升为 DCC；请求可覆盖项受安全/资源限额约束 |

**优先级（建议）**：实际执行以 `认证租户 → inputMode(query/entities) → DCC tenant/mode override → DCC 已登记基线 → 版本兼容预置` 解析，并受 Pod/集群硬上限约束。对于 Body 已定义的检索参数，先遵守接口规定的显式值与默认值优先级，DCC 仅对允许覆盖的资源/功能执行配置，不得悄然重写用户显式合法请求。DCC 读不到、键非法或 Watch 断线时不得把安全策略、队列上限解释成无限制。

### 7.2 需要纳入 DCC 的候选参数清单（按附件原 Key）

以下四类为本轮**DCC 注册与分类候选**，默认值严格采用附件扫描值，`8/20`、`1000/4000`、`1/6` 是**源码多个位置不同默认值**，需先统一实际含义。实际名字、租户/模式作用域、热更新安全性、值域与 DCC 注册方式在联调时冻结。

**A. 线程池/批处理/模型缓存（10 项，全部明确资源归属）**

| 参数 Key | 附件默认值 | 资源属性与 DCC 生效要求 |
|---|---|---|
| `embedding-thread-core-pool-size` | `8` | 模型内部租户执行池 core；按 tenant 建配额，不能只建立一个全局池 |
| `embedding-thread-max-pool-size` | `32` | 模型内部租户执行池 max，必须 `core ≤ max` 且受全局预算 |
| `embedding-model-cache-size` | `10` | 模型对象缓存容量，**不是线程数**；按租户划分缓存占用和可见性、全局有界 |
| `embedding-thread-pool-size` | `1` | Embedding 外层批任务并发；附件显示 5 处使用，不可假设它控制内层全部并发 |
| `batchInstance.threadPoolSize` | `8 / 20` | Instance 批次执行资源，租户独立队列/配额，默认冲突待收敛 |
| `batchInstance.maxBatchSize` | `1000 / 4000` | 批处理大小，按 tenant 配置，影响下一批次而非中途重切 |
| `batchInstance.retry` | `3` | 任务失败重试次数，租户级重试节流防止雪崩 |
| `parallelFlush.Size` | `8 / 20` | 向量库并行 Flush 额度；真实 Key 的大小写必须保持并核实实际读取 |
| `parseFile.threadPoolSize` | `20` | CSV 解析资源；按租户限制文件并行处理数和排队 |
| `notice.threadPoolSize` | `20` | Notice/任务消费资源；防止大租户挤占小租户的通知 |

**B. 查询准入、排序/检索与 RRF（16 项）**

| 参数 Key | 附件默认值 | 建议作用域 |
|---|---|---|
| `semantic-search.max-pool-size` | `30` | 租户级查询并发许可（旧 Q4 25，仅历史草案） |
| `semantic-search.queue-capacity` | `50` | 租户级等待队列长度 |
| `semantic-search.timeout-seconds` | `300` | 租户级许可等待超时；300 s 风险需复评 |
| `rrf.k` | `10` | 租户+query/entities 模式的融合平滑参数 |
| `rrf.channel-weights.ontology-object-vector` | `0.5` | 对象 vector 通道权重，核实与 dense 是否为别名 |
| `rrf.channel-weights.ontology-object-lexical` | `0.5` | 对象关键词权重 |
| `rrf.channel-weights.ontology-object-dense` | `0.5` | 对象 dense 权重，注意同义 Key 重复 |
| `rrf.channel-weights.instance-vector` | `0.5` | 实例 vector 通道权重，核实与 dense 是否为别名 |
| `rrf.channel-weights.instance-lexical` | `0.5` | 实例关键词权重 |
| `rrf.channel-weights.instance-dense` | `0.5` | 实例 dense 权重，检查双重加权 |
| `ontology-object-similarity-threshold` | `-1` | 租户/模式覆盖；`-1` 哨兵含义待定义 |
| `instance-similarity-threshold` | `-1` | 同上；不能以 -1 作为实际余弦阈值 |
| `instance-topk` | `-1` | 实例候选 TopK，实际最大值需约束 |
| `rrf-topk` | `-1` | RRF 输出 TopK，不能无限放大 |
| `adjacency-cache-max-size` | `1000` | 租户级图邻接缓存额度，亦受总堆内存约束 |
| `rule-config-path` | 无 | **文件系统路径属于特殊风险项**；建议系统级受控白名单路径或仅 DCC 发布可信 Rule 版本 ID，不允许租户任意指定本地路径，最终归属待安全评审 |

**C. 检索开关 / 子图过滤（7 项）**

| 参数 Key | 附件默认值 | 作用 |
|---|---|---|
| `subgraph.undirected-filter` | `false` | 附件源码默认 false；既有软件 V2 预置 true，需按版本+模式冻结 |
| `enable-object-linking` | `false` | 软件 entities 关闭已对齐对象的二次链接 |
| `enable-property-linking` | `false` | 软件 entities 关闭已对齐属性的二次链接；query 不得被误关闭 |
| `enable-property-value-linking` | `true` | 当前软件 V2 仅 Instance Value Linking，不再构建 Enum 索引 |
| `include-all-properties` | `true` | Property 属性补全，枚举全量另遵循 Schema |
| `include-keys` | `false` | Key 属性返回控制，不能绕过必要模型完整性规则 |
| `subgraph-retrieval-cache-switch` | `true` | 查询缓存开关；**性能压测必须覆盖为 false** |

**D. 索引任务与任务保留（5 项）**

| 参数 Key | 附件默认值 | 作用 |
|---|---|---|
| `index-build.max-retry` | `3` | 租户索引任务失败重试；结合全局重试洪峰控制 |
| `index-task.max-concurrent-tasks` | `10` | 租户后台任务并发许可，另有全局上限 |
| `index-task.queue-length` | `200` | 租户后台排队上限与公平性 |
| `index-task.queue-timeout-hours` | `1 / 6` | 不同源码默认冲突；按任务类别核实实际 timeout |
| `index-task.file-ttl-hours` | `168` | 文件有效期，不能短于可恢复任务处理窗口 |

**系统级排除**：附件第 5/6/7 类标注无需进入 DCC：MinIO scheme/证书/实例名/bucket、GaussVector/OpenSearch 实例名、Nebula IP/port/space、Elasticsearch URI/证书、JDBC 连接、`support_new_tenants`/tenantId 初始化、namespace/镜像模板、`POD_NAME/NODE_NAME/HOST_IP/LOG_LEVEL_CONFIGMAP_PATH` 和探针端口。`server.ssl.trust-store-password` 等敏感信息须由密钥机制管理，**不复制真实密码到 DCC**。上述配置虽涉及环境/租户身份，也不因字段含 tenant 就自动成为租户 DCC 开关。

**本轮参数差异收口**：10 + 16 + 7 + 5 = **38 个已列出的 DCC 候选**（其中 `rule-config-path` 尚需安全评审），另有 **34 个系统级明细 Key 明确不进入 DCC**。附件摘要与明细差 **11 个未列出 Key**，先追溯扫描源码再归类，不能默认这些缺失项属于 DCC。配置注册清单还须核对同 Key 不同默认值、权限和实际生效点。

### 7.3 线程池资源按租户划分：实现架构

**目标不只是“不同租户读取不同参数”，而是线程池/队列/并发资源真正隔离。**

```mermaid
flowchart TD
    A[鉴权 tenantId] --> B[TenantResourceRegistry]
    D[DCC tenant/mode 配置] --> W[Listener / Watch Manager]
    W --> B
    B --> E[Tenant-A ExecutorBundle]
    B --> F[Tenant-B ExecutorBundle]
    E --> E1[Embedding / Batch / Parse / Flush / Notice]
    F --> F1[Embedding / Batch / Parse / Flush / Notice]
    E --> G[Pod 级 CPU/线程/内存/连接全局配额]
    F --> G
    G --> H[Embedding / Storage 共享后端]
```

- 入口从认证上下文获取 `tenantId`，不能信任任意 Body 伪造；每个 TenantExecutorBundle 按租户持有独立的提交配额、执行队列、Worker 与缓存预算，或采用能证明等效隔离的有界虚拟队列调度器。
- **索引入库相关接口，增加租户id字段，用于控制不同租户的线程池资源，包括notice、query等接口增加tenantID**。

TODO：在接口的请求头中增加 `x-gde-tenant-id`, 客户端调用时 headers.add("x-gde-tenant-id", tenantId); 比如如下的notice接口，增加header参数：
##### 调用方法

POST

##### URI

```text
/v1/onto-retrieval/{ontologyId}/index-data/notice
```

对应 Spring 接口：

```java
@PostMapping("/v1/onto-retrieval/{ontologyId}/index-data/notice")
```

##### 请求参数

**IndexFileImportRequest 参数列表**

| 参数名称            | 类型                  | 是否必选 | 默认值 | OpenAPI 约束                                 | 说明                                                                 |
| :-------------- | :------------------ | :--- | :-- | :----------------------------------------- | :----------------------------------------------------------------- |
| `requestId`     | String              | 是    | -   | `minLength: 1`，`maxLength: 256`            | 调用方幂等键；文件直接导入时用于创建任务，关联任务时用于通知幂等                                   |
| `triggerTaskId` | String              | 否    | -   | `maxLength: 256`                           | OAC 交付文件时关联手动构建产生的原任务；直接文件导入不传                                     |
| `dataType`      | String              | 是    | -   | `enum: [METADATA_ENUM, INSTANCE_VALUE]`    | 当前文件批次的数据类型                                                        |
| `importMode`    | String              | 是    | -   | `enum: [FULL_REPLACE, INCREMENTAL, CLEAR]` | 全量替换、增量导入或全量清理索引；`CLEAR` 仅允许 `dataType=INSTANCE_VALUE`             |
| `files`         | Array[MinioCsvFile] | 条件必选 | -   | `minItems: 1`                           

TODO: 同样的，接口还包括：/{ontologyId}/index-tasks/query，/{ontologyId}/index-tasks/retry，/{ontologyId}/index-tasks/cancel，


### 7.4 DCC 按租户监听、热变更及线程池安全迁移

**推荐控制流程（设计建议，不宣称 DCC 现有 SDK 已支持）**：

1. **配置登记**：将 §7.2 的候选 Key 逐项定义 `tenantId + inputMode/operationType + configKey + version + value + range + dynamic/restartRequired`；记录来源、默认值和审计，支持既有租户预置迁移。`@Value` 只是在 Bean 初始化时读取一次，**不具备自动 DCC 动态监听能力**。
2. **订阅与初始化**：OAG 每 Pod 通过 DCC 官方 Listener/Watch SDK（或等价机制）订阅对应租户/键范围；首次加载和重连后获取**完整配置快照**并按版本检查。
3. **校验后生效**：DCC参数校验规则，线程 `core ≤ max`、批大小/队列/超时合理区间等需要做整套校验；
4. **线程池等资源平滑调整**：监听到DCC回调后，自动重建线程池、连接池等资源，采用单例模式管理线程池或连接池资源。
5. **可观测性**：审计日志借助DCC的审计能力，同时OAG配置回调记录 tenantId、key、configVersion、来源、结果/原因和生效时间。

**示意代码**：
可以参考本体加密内存图的DCC注册和监听逻辑

### 7.5 DCC 参数兼容、冲突和验收

| 决策项 | 附件/旧草案情况 | 本轮规则 |
|---|---|---|
| 搜索并发 | 附件 `max-pool-size=30`，旧 Q4 为 25 | **记录版本差异**，以实际租户有效值冻结；不是性能附件证明了 30 最优 |
| 批次线程数 | `batchInstance.threadPoolSize=8/20`、`parallelFlush.Size=8/20` | 查源码有效注入点、作用阶段和具体模式后再统一 DCC 默认 |
| 批大小 | `batchInstance.maxBatchSize=1000/4000`，需求另有 COPY 批大小 | 区分逻辑 Batch、COPY 分片与 Spark 合并文件大小，不能复用同一 Key |
| 任务队列超时 | `index-task.queue-timeout-hours=1/6` | 按任务类型/版本决定，确保不少于消息重放窗口 |
| 无向图 | 统计显示 `undirected-filter=false`，软件 V2 设计 true | 明确租户 + query/entities + 发布版本的生效矩阵并回归，不静默修改 |
| 缓存开关 | 统计 `subgraph-retrieval-cache-switch=true` | **性能压测强制 false**，并保存 DCC 快照与请求参数 |
| RRF 权重 | `vector` 与 `dense` 两组同值、合计不能假设已归一 | 先核查是否同一通道别名，防止重复融合权重 |
| 配置差异与多实例 | 静态 @Value + DCC 事件 | 完整回放、Watch 重连、Pod 重启和配置版本对账 |
| 容量安全 | 每租户线程数可独立调节 | 一次修改需验证所有活跃租户和 Pod 全局预算，不能因租户数增长导致 OOM/线程耗尽 |

**租户隔离测试矩阵**：T1=租户 A 满载 embedding、租户 B 仍可查询/写入；T2=更新 A 池 max/queue、B 无变化；T3=A 缩小 pool、旧请求自然完成且不丢任务；T4=Pod A/B Watch 事件乱序、断线重连后同版本；T5=异常值、过量配额、DCC 不可达时保留旧快照；T6=新租户首次创建/空闲回收；T7=多 Pod 受总配额/后端资源限制且不会跨租户泄漏。所有测试记录实际线程数、拒绝、Task 完成率和内存曲线。

---

## 8. 验收标准、发布门禁与技术决策

### 8.1 最新 20 项需求验收矩阵

| 用例组 | 对应需求 | 最低验收断言/验证依据 |
|---|---|---|
| OMS-Q4-01 | Q4-01 | OMS 加密参数分层/透传与模型文件加密专项一致；加密算法/密钥与安全测试跟随专项 |
| OMS-Q4-02 | Q4-02 | Agent 与 OMS 缓存减少实时全量取定义；同 tenant/revision/权限范围可见数据一致，缓存失效可重取 |
| OMS-Q4-03 | Q4-03 | 2/3 实例负载均衡、OMS revision 与读写权限一致，不跨 Pod 泄漏 |
| OMS-Q4-04 | Q4-04 | 按 GDE 公共恢复指导书交付 OMS 专项场景、诊断指标及演练记录 |
| OMS-Q4-05 | Q4-05 | 参照 GDE 公共参数分级完成 OMS 场景包/系统/接口参数映射和安装回归 |
| OAG-Q4-06 | Q4-06 | V2 query/entities 检索同入口；不建/不查 t_oag_enum；Property 完整枚举、真实 Instance 映射，移除旧 semanticExtensions |
| OAG-Q4-07 | Q4-07 | 根目录 Skill/脚本迁移 V2，保留历史输出消息包装；7 项离线回归覆盖两种输入、topk/0 值、HTTP/业务失败；V1 deprecated 并盘点历史副本 |
| OAG-Q4-08 | Q4-08 | **手动建索引偶现问题先闭环**；随后 OMS App 自动建索引、图/索引同 revision，失败保留旧 active |
| OAG-Q4-09 | Q4-09 | 多 Pod 图缓存与索引 revision 一致、跨实例负载分担，滚动升级与任务接管可恢复 |
| DFx-Q4-10 | Q4-10 | **租户线程池/队列真实隔离且按租户 DCC Watch 生效**；合法变更、缩容 drain、跨 Pod 对账和全局资源限制 |
| DFx-Q4-11 | Q4-11 | OAG 专项故障纳入 GDE 公共 Runbook，有演练、证据和恢复结果 |
| IDX-Q4-12 | Q4-12 | **1000 万行 FULL / 10 万行增量**；DataSync Producer/Consumer 异步通知与 MinIO READ；Spark 小文件合并、图/语义去重；COPY 无主键冲突、失败可恢复 |
| IDX-Q4-13 | Q4-13 | 附件的 2U4G/10 QPS/平均 ≤5 s/拒绝 <20% 及全部固定条件可复现；**3U4G 建议压测单独出结果** |
| IDX-Q4-14 | Q4-14 | 定义索引未变更的向量复用；模型/输入变化才触发增量 Embedding，元数据/词法索引仍正确更新 |
| IDX-Q4-15 | Q4-15 | LVQ 先建/后建同环境 A/B；预建可用性与 COPY 总耗时、Recall 验证，COPY 批大小可按租户 DCC 调整/回退 |
| IDX-Q4-16 | Q4-16 | Delete/CLEAR 与 DataSync 联调，双库成功对账、幂等、重试及冲突处理 |
| IDX-Q4-17 | Q4-17 | FULL 与 incremental 的数据库差异对比准确；无新键不调用 Embedding、不误删已有键；分批并发安全 |
| SEC-Q4-18 | Q4-18 | OMS retrieval.enabled + 可选 indexMode（HYBRID/KEYWORD_ONLY/VECTOR_ONLY），disabled 不建；混合/单路建库查询、模式迁移、无 property 路由与旧数据兼容 |
| SEC-Q4-19 | Q4-19 | name/description 索引最小化、ID→定义回查与权限正确，严格 ID-only/BM25 矛盾完成加密专项安全评审 |
| SEC-Q4-20 | Q4-20 | 加密堆栈参数控制后台日志明文和前端脱敏；专项认证与生产日志/导出/异常回归无泄露 |

### 8.2 子图查询性能规格专用验收（附件 10-26）

| 测试编号 | 条件/数据集 | 验证与交付结果 |
|---|---|---|
| PERF-Q4-01 | **2U4G** 单实例；≤150 ObjectType、≤3000 Property、≤400 Edge，静态图 1 GB、≤10 本体 | 固定环境镜像、CPU 单核 SHA-256 ≥280 万 ops/s/700 MB/s、JVM、实例数与本体 revision |
| PERF-Q4-02 | CXO L1 黄金集，entities 对象数 <20，propertyValues 分桶 40% / 50% / <10% | 冻结输入用例、随机种子及 **4/8 边界重叠的解释方式**；未冻结不得声称完全复现附件 |
| PERF-Q4-03 | hybrid、0.7、topK≤3、hopLimit≤3、adaptive=1、minimal、Functions/Actions=0 | 快照并记录 V2 `topk` 实际绑定、无向开关与 DCC 租户配置；问题缓存 **false** |
| PERF-Q4-04 | 重启后预热 ≥3 min，前 3 次结果剔除，查询高峰无实例向量化入库 | 记录预热时点与错峰窗口，不允许缓存命中/后台任务影响对照 |
| PERF-Q4-05 | **10 请求/秒，连续 1000 请求**，2U4G 基准 | **平均成功耗时 ≤5 s**（均值统计口径需签审）、拒绝总比例 <20%；同时报告成功 QPS、P50/P95/P99、失败/超时 |
| PERF-Q4-06 | **3U4G 建议压测**，同用例/参数并与 2U4G 对照 | 单独报告耗时与吞吐，不能作为 2U4G 达标替代证据 |
| PERF-Q4-07 | 2/3 Pod 水平扩展 + 两个租户并行 | 在总入口 QPS 固定/每 Pod QPS 固定两种情形下验证扩展效率、租户池隔离和全局后端瓶颈 |
| PERF-Q4-08 | CPU 单核达标与不达标、ARM/x86 混合、图数/Property 数/枚举值规模梯度 | 测试超出附件约束后的性能降级；正式规格只针对符合约束的环境 |

**拒绝率和时延不得混算**：拒绝率建议按 `flowRejected / submitted`；平均耗时建议按成功完成响应统计，并同时给出失败/排队独立分位值，最终以压测评审冻结的测量口径为准。附件规定的是**平均 ≤5 秒**，没有给出 P95/P99 硬门槛；这些分位统计应采集，但不能用旧草案“3 s”偷偷替代正式验收指标。**3U4G 的结果必须独立标识。**

### 8.3 DataSync/Spark 与租户资源专项测试

| 编号 | 场景 | 准入断言 |
|---|---|---|
| ING-Q4-01 | DataSync Producer 上传完成→Consumer 通知 OAG；重复 READY、Notice 重放、网络短断 | OAG 不等上游 MinIO 上传，仍按 Manifest 读取；Task 只创建一次有效任务，无丢消息 |
| ING-Q4-02 | Spark 小文件多/少对照，保持相同输入行数和 revision | DataSync 请求数与 MinIO 文件数下降，CPU/线程等待和索引总耗时可量化 |
| ING-Q4-03 | Spark 图与语义索引数据跨分区重复，COPY 压测 | 图主键/语义组合键去重正确，COPY 无主键冲突；OAG 保留幂等校验 |
| ING-Q4-04 | FULL 1000 万行的部分分区滞后，增量 10 万行乱序和重试 | FULL 不因单分片到达误删，增量只有真正新增键调用 Embedding，版本旧消息不覆盖新值 |
| DCC-Q4-01 | 租户 A 池满、租户 B 保持轻载 | 租户间队列/Worker/配额隔离，A 满不会拖垮 B |
| DCC-Q4-02 | 线程池 core/max、Batch/Flush/Parse 和查询队列配置变更 | 各 Tenant Watch 并稳定生效；在线缩容不丢已执行/排队任务 |
| DCC-Q4-03 | DCC Listener 断线、重连、版本跳跃、非法值/超出总预算 | 老配置继续可用且告警；非法值拒绝生效；多 Pod configVersion 一致 |
| DCC-Q4-04 | 大量闲置租户、2/3 Pod 同时创建资源池 | 懒创建/回收，系统总线程数与连接数不超限；隔离和副本级预算正确 |
| DCC-Q4-05 | `25/30`、`8/20`、`1000/4000`、`1/6`、`undirected-filter` 差异 | 所有冲突 Key 的生效版本与模式有回归证据，不能任意取较大/较小值 |

### 8.4 发布顺序与依赖关系

| 阶段 | 实施重点 | 准入门禁 |
|---|---|---|
| A—接口与配置基线 | 20 项责任冻结、加密专项/GDE 公共依赖、V2 DTO、DCC 38 项候选审查 | 参数默认冲突、系统级排除和租户监听接口明确 |
| B—基础稳定性 | **手动索引偶现问题修复**、Task/Manifest、图/索引同 revision | 手动构建可恢复、旧 active 不污染；才可进入自动化 |
| C—DataSync/Spark 流水线 | Producer/Consumer 异步、Spark 合并小文件/图与语义去重、差异 Embedding | 1000 万/10 万、重试/乱序/故障联调通过 |
| D—OAG 多实例/DCC | 自动索引、租户池和 Watch、V2 Skill、公共恢复手册 | 多 Pod/多租户隔离回归，DCC 断线有安全回退 |
| E—检索规格与安全预研 | 2U4G 指标、3U4G 对照、LVQ A/B、Keyword-only 与 ID-only 评审 | 性能报告、资源评估、加密专项决策、未决项留档 |

**仅表示建议技术依赖顺序**；正式版本、需求优先级、工作量和每项资源预算需项目管理确认。分层配置公共需求和故障 Runbook 不在本文件重复独立建设。Q4-18 为预研，不宜在安全/搜索方案未冻结前承诺全部局点上线。

### 8.5 统一可观测性与验收证据

检索与建库日志按安全策略脱敏记录：`traceId、tenantId（授权或脱敏）、ontologyId/revision、queryMode、jobId、partitionId、sourceVersion、configVersion、indexVersion、graphCacheVersion、submitted/accepted/rejected、activeThreads、queuedTasks、embeddingInFlight、rowCount/duplicateCount/rowDiff、copyDuration、indexBuildDuration、pipelineLatency、responseBytes、errorCategory`。按 Tenant / Pod / 输入模式分别展示 DCC Watch 状态、查询拒绝率、平均/P95/P99、模型实例数和图缓存预算；敏感名字/枚举实例原值只在授权路径可见。

测试报告必须包含：2U4G/3U4G 两套环境清单、CPU 单核 openssl 检测结果、模型版本与内存图数量、10 QPS/1000 次发送记录、3 分钟预热、缓存关闭、后台 Embedding 错峰、拒绝和超时分母、Spark/MinIO 文件数变化、Embedding 复用比例，以及各租户线程资源配置版本。无硬件/样本同一性时不得直接比较资源或性能。

### 8.6 待决策事项与评审责任

| 编号 | 必须冻结的议题 | 建议牵头 |
|---|---|---|
| D-01 | 最新 20 条需求的最终 owner、优先级与工作量；旧版 7.9 不沿用 | 项目管理/OMS/OAG |
| D-02 | OMS 加密、索引 ID-only 与后台明文/前台脱敏参数，统一跟随《本体模型文件支持加密》 | OMS/安全 |
| D-03 | GDE 公共场景包分层与故障恢复规范、OMS 分域接口/缓存 revision | GDE/OMS/CBS |
| D-04 | 手动建索引偶现根因、修复验收后 OMS 自动通知/发布流程 | OMS/OAG |
| D-05 | DataSync READY/NOTICE/ACK、Spark 文件合并与图/语义去重稳定 Key、快照水位 | Spark/DataSync/OAG |
| D-06 | **DCC 已列 38 项候选注册**、34 项系统级排除；核对附件摘要 83 与明细 72 差的 **11 个未列出 Key**，再定最终注册清单；包括默认冲突、Rule 路径与租户 Watch API | OAG/配置底座 |
| D-07 | Pod 与集群层面租户线程/队列/Embedding/连接池的总资源预算和副本间分配 | OAG/架构/资源管理 |
| D-08 | 2U4G 与 3U4G 的测试职责、平均延迟的统计分母、propertyValues 分桶边界 | OAG/测试/CBS |
| D-09 | V2 `topk`/附件 `topK`、`undirected-filter=false/true` 以及 25/30 并发默认 | OAG/Skill/配置底座 |
| D-10 | LVQ 提前建索引的数据库版本支持、COPY Batch 值域和回退 | OAG/GaussVector |
| D-11 | OMS `retrieval.indexMode` 值域、默认、迁移/旧数据兼容；Keyword/Vector 单路入库与 ID-only 的 BM25 安全冲突 | OMS/OAG/安全 |
| D-12 | 10 QPS 压测是否需要集群级租户配额服务，DCC Watch 失效时如何保护查询资源 | OAG/平台底座 |

**设计收口**：本轮方案将 Q4 最新 20 项需求聚焦为“公共加密/GDE 依赖 → 手动索引稳定性 → 异步索引全量/增量 → 租户级 DCC 资源隔离 → OAG V2 统一查询 → 精确的性能与安全验收”。所有原始配置键与新附件的规模、约束、测试条件均分别标明；**没有把代码扫描的默认值当成运行配置，也没有把 3U4G 建议压测当成 2U4G 已验收。**
