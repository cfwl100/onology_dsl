# 本体实例增强数据分批增量 Embedding 独立临时表设计方案

> 版本：V1.0  
> 日期：2026-11-01  
> 模块：OAG / 本体实例向量索引构建  
> 文档性质：功能与详细设计说明书  
> 适用环境：PostgreSQL、Java 17/21、Spring Boot/JDBC、Embedding 服务（如 BGE-M3）

---

## 1. 背景与设计目标

本体实例增强数据以多线程、分批、不定时的方式推送，每批默认 4,000 条（可配置）。正式表 A 已保存 (value, object_type_id, property_id) 及对应 vector。期望只为本批在 A 中不存在的组合键生成 Embedding 并写入 A，以免全量删表、全量重新计算向量。

本方案明确约束：

1. **每个业务批次独占一张 PostgreSQL TEMP 临时表 B**，各批次之间不共享临时表，也不创建差异任务表 C。
2. **每批数据独立处理**：不需要等待其他批次，即使批次之间相隔数分钟或数小时。
3. **只增不删**：仅处理 B 有而 A 无的数据；不识别、删除或覆盖 A 中已有数据及 vector。
4. **数据库内精确比对**：value、object_type_id、property_id 三字段共同判定业务唯一性。
5. **临时表只在差异识别阶段存活**：事务提交自动 DROP，结果至多 4,000 条回到 Java 内存；Embedding 期间不持有临时表和查询事务。
6. **幂等插入**：通过 A 的联合唯一约束和 ON CONFLICT DO NOTHING 防止重复入库；跨批次并发 Embedding 的重复调用属于单独的协调问题。

集合关系：

- 本批新增候选 Δ = DISTINCT(B) − A（以组合键为准）。
- A_new = A_old ∪ INSERTABLE(Δ)。
- A 中已有的相同业务键完全保留，包含现有 vector；绝不执行 DELETE A。

### 1.1 适用边界

本方案假定 A 中已存在的 vector 可以复用，不考虑模型版本升级、旧 vector 为 NULL 的补齐或相同组合键的其他属性更新。若业务存在租户、本体范围，A 的真实联合唯一键和比对条件必须包含其隔离字段，不能在共享租户数据上省略范围。

## 2. 总体架构

~~~mermaid
flowchart TD
    IN[Java 多线程接收批次<br/>默认每批 4000 条] --> BT[批次独立数据库事务]
    BT --> B[CREATE TEMP TABLE B<br/>唯一表名 / ON COMMIT DROP]
    B --> COPY[本批 JDBC Batch 插入]
    COPY --> DIFF[SELECT DISTINCT B<br/>NOT EXISTS A]
    DIFF --> MEM[将新增 Δ 返回 Java 内存]
    MEM --> END[提交差异事务<br/>自动 DROP B / 释放连接]
    END --> E[独立 Embedding 阶段<br/>批量调用模型 / 全局并发限流]
    E --> W[短事务 JDBC 批量 INSERT A<br/>ON CONFLICT DO NOTHING]
    W --> DONE[本批完成]
    E --> ERR[失败后从原批次重试]
    ERR --> BT
~~~

数据库职责：本批存储、去重、差异过滤与最终唯一键校验。  
Java 职责：批次调度、临时表命名、Embedding 并发及失败重试。  
A 表职责：权威存量及 Vector 数据；无删除操作。

## 3. 独立临时表命名规范

### 3.1 推荐名称

命名模板：

~~~text
tmp_oag_emb_b_<batch_uuid32>
~~~

示例：

~~~text
tmp_oag_emb_b_a81f62c0d93e4b728f614c039ae725bd
~~~

字段语义：

| 字段 | 说明 |
|---|---|
| tmp | 临时关系标识 |
| oag | 本体检索 / 索引服务标识 |
| emb | Embedding 构建场景 |
| b | 批次中间表 B |
| batch_uuid32 | 服务端为每个批次新生成的 UUID v4，删除四个连字符，保留 32 位小写十六进制 |

该格式全长 **46 个 ASCII 字节**（前缀 14 + 32），在 PostgreSQL 常见的 63 字节标识符上限之内；不采用仅毫秒时间戳、线程 ID 或递增序号作为唯一性依据。

### 3.2 防冲突规则

- **业务层唯一**：每个批次生成新的 UUID，不同重试尝试也生成新 UUID；不要把相同请求传入的 batchId 原样拼成 SQL 表名。
- **数据库层隔离**：PostgreSQL 临时表属于当前会话的专属临时 schema，不同会话中即使表名相同也互不冲突。这是第二重隔离，而不是必须依赖名称唯一才安全。
- **同一会话防误复用**：使用 CREATE TEMP TABLE（不用 IF NOT EXISTS），若异常重名应立即失败，不隐式复用旧表。
- **严格生命周期**：在显式事务内 CREATE TEMP TABLE ... ON COMMIT DROP；成功 COMMIT 后自动删除，异常 ROLLBACK 后不留下该事务新创建的表。
- **安全标识符**：名称必须由服务端生成，只允许正则 ^tmp_oag_emb_b_[0-9a-f]{32}$；SQL 标识符不可用 JDBC ? 绑定，因此必须在完成校验后构造，并用双引号引用。外部传入的 value 仍使用预编译参数。
- **schema 明确**：CREATE TEMP TABLE 不显式指定 schema；后续访问统一使用 pg_temp."<table_name>"；访问 A 表统一加正式 schema（如 public.a）避免同名遮蔽。
- **连接绑定**：创建、插入临时表和差异查询必须位于同一物理 JDBC Connection / 一个数据库事务中；不允许比对前切换连接、自动提交或在事务内调用远程 Embedding。

Java 参考：

~~~java
private static final Pattern TEMP_PATTERN =
        Pattern.compile("^tmp_oag_emb_b_[0-9a-f]{32}$");

static String newTempTableName() {
    String name = "tmp_oag_emb_b_"
            + UUID.randomUUID().toString().replace("-", "");
    if (!TEMP_PATTERN.matcher(name).matches()
            || name.getBytes(StandardCharsets.US_ASCII).length > 63) {
        throw new IllegalStateException("Invalid temp table name");
    }
    return name;
}

static String safeTempRef(String name) {
    if (!TEMP_PATTERN.matcher(name).matches()) {
        throw new IllegalArgumentException("Invalid temp table identifier");
    }
    return "pg_temp.\"" + name + "\"";
}
~~~

**说明**：单纯避免 PostgreSQL 表名冲突时，固定名称也能通过会话隔离工作；但本方案依据业务要求采用独立 UUID 名称，便于日志定位、审计及故障排查。

## 4. 数据模型、索引与比对语义

A 为已存在正式表，以下仅是类型示例：

~~~sql
CREATE TABLE public.a (
    "value" TEXT NOT NULL,
    object_type_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    vector VECTOR(1024),
    PRIMARY KEY ("value", object_type_id, property_id)
);
~~~

正式表必须存在对应的 **非延迟** 联合唯一约束或唯一索引。若已有主键，不应再重复建索引；线上存量建索引需先排重，必要时采用 CREATE UNIQUE INDEX CONCURRENTLY 并在事务外执行。

本批临时表只需要三列，无 vector：

~~~sql
BEGIN;
CREATE TEMP TABLE "tmp_oag_emb_b_a81f62c0d93e4b728f614c039ae725bd" (
    "value" TEXT NOT NULL,
    object_type_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL
) ON COMMIT DROP;
~~~

B 表不建索引，批内通过 SELECT DISTINCT 去重；4,000 条规模通常以扫描 B、利用 A 的联合索引进行 Anti Join 为优先验证方案。实际值的 SQL 类型应与 A 完全一致，不能随意将业务 ID 转换为 BIGINT。如果 value 是超长文本，还需评估 A 表 B-tree 完整键的索引项大小限制。

严格保证三个字段 NOT NULL，否则普通等值比较的 NULL 语义会影响差异识别和唯一约束。

## 5. 单批处理 SQL 与事务边界

### 5.1 阶段 I：数据库差异识别（短事务）

1. 接收至多 configured batch-size 条数据，校验对象字段、长度、非空及租户/本体范围。
2. 使用 TransactionTemplate 开启**独立事务**，获取当前事务绑定的 JDBC Connection。
3. 创建本批唯一名称的 TEMP 表 B（ON COMMIT DROP）。
4. 通过 JDBC batchUpdate / PreparedStatement 批量写入本批记录（可分为每次 500 条执行）。
5. 对 B 去重并通过 NOT EXISTS 查询 A 表不存在的新增组合键。
6. 完整读取结果到 Java List，再提交事务，B 自动 DROP，连接归还池中。

在同一个事务中的 SQL 示意：

~~~sql
-- 在当前已开启的事务中执行，表名来自服务端安全生成器
CREATE TEMP TABLE "tmp_oag_emb_b_a81f62c0d93e4b728f614c039ae725bd" (
    "value" TEXT NOT NULL,
    object_type_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL
) ON COMMIT DROP;

-- Java 调用预编译 JDBC Batch，示例仅展示语义
INSERT INTO pg_temp."tmp_oag_emb_b_a81f62c0d93e4b728f614c039ae725bd"
    ("value", object_type_id, property_id)
VALUES (?, ?, ?);

SELECT b."value", b.object_type_id, b.property_id
FROM (
    SELECT DISTINCT "value", object_type_id, property_id
    FROM pg_temp."tmp_oag_emb_b_a81f62c0d93e4b728f614c039ae725bd"
) b
WHERE NOT EXISTS (
    SELECT 1
    FROM public.a a
    WHERE a."value" = b."value"
      AND a.object_type_id = b.object_type_id
      AND a.property_id = b.property_id
);
-- Java 读完 ResultSet 后 COMMIT；自动 DROP 临时表
~~~

禁止在 SQL 差异查询中执行 DELETE A；禁止将 Embedding 模型调用纳入本事务。

### 5.2 阶段 II：Java Embedding（无数据库事务）

仅处理第 I 阶段返回的新增列表。根据模型服务支持范围，将单批新增数据进一步切分为 embedding-request-size（如 32）的小批次。每个模型请求需要：

- 输入文本到输出向量的顺序一一对应；
- 校验结果数量、维度和非有限浮点数；
- 全局控制真实在途 HTTP 请求数（建议 Semaphore），而非仅限制外层 Future 的创建数量；
- 配置超时、有限次数退避重试、失败报警；
- value 以原始值（或明确规定的文本生成逻辑）计算，不能私自改变联合键语义。

### 5.3 阶段 III：新增数据批量写入 A（短事务）

~~~sql
INSERT INTO public.a (
    "value", object_type_id, property_id, vector
)
VALUES (?, ?, ?, ?)
ON CONFLICT ("value", object_type_id, property_id)
DO NOTHING;
~~~

使用 JDBC Batch 且只在向量生成和校验成功后插入。pgvector 的 VECTOR(1024) 可由 pgvector-java 的 PGvector(float[]) 绑定（在数据库连接上正确注册类型）；如实际数据库类型是 DOUBLE PRECISION[]，则改用 JDBC SQL Array。

每次写入可以使用 100～500 条的批量提交大小，通过压测调整。已插入的存量行及其 Vector 均不修改。

### 5.4 事务时序

| 阶段 | 是否持有数据库事务 | 是否持有临时表 | 失败处理 |
|---|---|---|---|
| 创建 B + 导入 + SELECT 差异 | 是，短事务 | 是 | 回滚该批次差异阶段 |
| Java Embedding | 否 | 否 | 本批按原始数据重试 |
| Batch INSERT A | 是，独立短事务 | 否 | 回滚写入子批并重试 |
| 处理完成 | 否 | 否 | 记录统计并结束 |

## 6. Java 核心实现框架

示例采用 Spring JdbcTemplate + TransactionTemplate。服务入口不得包裹覆盖 Embedding 的长事务；TransactionTemplate 必须使用与 JdbcTemplate **相同 DataSource 对应的事务管理器**。

~~~java
@Service
public class IncrementalEmbeddingService {
    private final JdbcTemplate jdbc;
    private final TransactionTemplate diffTx;
    private final EmbeddingClient embeddingClient;
    private final IncrementalConfig config;

    public IncrementalEmbeddingService(
            JdbcTemplate jdbc,
            PlatformTransactionManager txManager,
            EmbeddingClient embeddingClient,
            IncrementalConfig config) {
        this.jdbc = jdbc;
        this.diffTx = new TransactionTemplate(txManager);
        this.diffTx.setPropagationBehavior(
                TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        this.embeddingClient = embeddingClient;
        this.config = config;
    }

    public record Row(String value, long objectTypeId, long propertyId) {}

    public List<Row> findIncremental(List<Row> input) {
        if (input == null || input.size() > config.batchSize()) {
            throw new IllegalArgumentException("Invalid input batch size");
        }
        if (input.isEmpty()) {
            return List.of();
        }
        // 其他校验：所有联合键非空、值长度、业务作用域
        return diffTx.execute(tx -> {
            String tempName = newTempTableName();
            String ref = safeTempRef(tempName);
            jdbc.execute("CREATE TEMP TABLE \"" + tempName + "\" ("
                    + "\"value\" TEXT NOT NULL, "
                    + "object_type_id BIGINT NOT NULL, "
                    + "property_id BIGINT NOT NULL"
                    + ") ON COMMIT DROP");

            jdbc.batchUpdate(
                    "INSERT INTO " + ref
                            + " (\"value\", object_type_id, property_id)"
                            + " VALUES (?, ?, ?)",
                    input, 500,
                    (ps, row) -> {
                        ps.setString(1, row.value());
                        ps.setLong(2, row.objectTypeId());
                        ps.setLong(3, row.propertyId());
                    });

            return jdbc.query(
                    "SELECT b.\"value\", b.object_type_id, b.property_id "
                    + "FROM (SELECT DISTINCT \"value\", object_type_id, property_id "
                    + "FROM " + ref + ") b "
                    + "WHERE NOT EXISTS (SELECT 1 FROM public.a a "
                    + "WHERE a.\"value\" = b.\"value\" "
                    + "AND a.object_type_id = b.object_type_id "
                    + "AND a.property_id = b.property_id)",
                    (rs, i) -> new Row(
                            rs.getString("value"),
                            rs.getLong("object_type_id"),
                            rs.getLong("property_id")));
        });
        // 返回前事务提交，ON COMMIT DROP；绝不能把 ResultSet 延迟消费
    }

    public void processBatch(List<Row> input) {
        List<Row> delta = findIncremental(input);
        for (int i = 0; i < delta.size(); i += config.embeddingRequestSize()) {
            List<Row> subset = delta.subList(
                    i, Math.min(delta.size(), i + config.embeddingRequestSize()));
            // HTTP 调用受全局 Semaphore 控制；无数据库事务
            List<float[]> vectors = embeddingClient.embed(
                    subset.stream().map(Row::value).toList());
            validateVectors(subset, vectors, config.vectorDimension());
            // 每次独立短事务：使用 pgvector-java 批量插入 A，
            // INSERT ... ON CONFLICT DO NOTHING；失败则向上抛出
            writeBatchToA(subset, vectors);
        }
    }

    // newTempTableName / safeTempRef / validateVectors / writeBatchToA
    // 按上文约定实现；动态表名只由经过校验的本地生成器产生。
}
~~~

特别注意：如果调用方已有外层事务，REQUIRES_NEW 虽能隔离差异事务，但外层事务仍可能占用连接。推荐将 processBatch 入口保持为**非事务**方法，在内部将 diff 和 write 分为独立、短生命周期事务。不要使线程池任务共享 Connection。

## 7. 并发安全与一致性

### 7.1 两层防重

| 层级 | 保障方式 | 可以保证 | 不可保证 |
|---|---|---|---|
| 临时表 B | UUID 名称 + PostgreSQL 会话隔离 | 不同批次不覆盖临时数据 | 跨批次值不重复 |
| 正式表 A | 组合唯一键 + ON CONFLICT DO NOTHING | 同一组合键最多一条数据、不覆盖已有 vector | 并发模型请求绝不重复 |

典型竞态：批次 X、Y 同时发现 A 中不存在同一组合键，都执行 Embedding，最后只有一个 INSERT 成功。这不会破坏 A 的数据正确性，但会浪费一次模型调用。

### 7.2 可选跨批次 Embedding 去重

基础版本优先实现数据库级正确性；若压测发现跨批次重复 Embedding 明显，可增加按完整联合键计算的 SingleFlight/分布式锁：

1. 在模型调用**前**对该组合键申请锁；支持多 JVM 部署时，使用有可靠续租与 fencing 设计的分布式协调机制。
2. 取得锁后再次 SELECT A；如果已经存在，直接跳过 Embedding。
3. 如果仍不存在，计算向量并 INSERT A，事务成功后释放锁。
4. 超时、进程崩溃时需要有锁失效策略；仅靠无续租的短 TTL 锁无法绝对避免重复计算。

**重要权衡**：跨实例互斥需要额外连接或协调成本，并且单纯数据库级 ON CONFLICT 无法让外部模型调用具备 exactly-once 语义。当前没有 C 表，也不持久化待处理任务，因此不能承诺所有故障情况下严格零次重复 Embedding。

## 8. 失败处理与恢复

- **创建/装载/比对失败**：回滚差异识别事务；本事务新建临时表自动消失；重新处理原始批次。
- **Embedding 失败**：临时表早已删除，应依赖上游的原始批次重放机制（消息队列/持久化来源）重试，不能依赖 Java 进程内的 List 在崩溃后恢复。
- **A 部分子批已提交，后续失败**：重放原始批次后重新与 A 比对，已入库记录被自动过滤，只计算未入库部分。
- **写 A 冲突**：DO NOTHING，视为该组合键已由其他任务持久化；可计入 conflict_skipped 指标。
- **数据校验失败**：整个业务批次进入异常处理，不将零向量作为正常 Embedding 的静默替代，除非明确业务定义。
- **批次确认语义**：如果接口在 Embedding 完成前确认成功，必须有可靠队列持久保存原批次及可追踪的 job/batch ID；同步返回模式则必须明确超时和重试约定。

## 9. 配置建议

以下是初始压测参数，非最终性能规格：

~~~yaml
ontology:
  incremental-embedding:
    enabled: true
    batch-size: 4000                  # 单业务批最大记录数
    max-concurrent-batches: 8         # 同时执行的业务批次上限
    temp-table-prefix: tmp_oag_emb_b_ # 固定代码生成，禁止外部覆盖成任意SQL
    jdbc-load-sub-batch-size: 500     # 单次 JDBC 批量导入分段
    embedding-request-size: 32        # 单次模型调用的文本条数
    embedding-max-concurrency: 4      # 全局真实在途 HTTP 请求数
    embedding-max-retries: 3
    vector-dimension: 1024
    jdbc-write-batch-size: 200
~~~

Java 配置校验：batch-size > 0；embedding-request-size > 0；并发上限 > 0；确保模型输出维度与 A 表字段维度一致。Embedding 嵌套线程池需以实际发送的 HTTP 并发为准，不能仅以 CompletableFuture 的创建数判断。

## 10. 性能考虑与容量约束

### 10.1 理论效果

假定批次 4,000 条、其中 3,800 条已在 A、200 条新增：

| 指标 | 全量重新 Embedding | 本方案 |
|---|---:|---:|
| 数据库比对输入 | 无 | 4,000 条 |
| 需生成 Vector 的数据 | 4,000 条 | 200 条 |
| 模型文本输入减少比例 | 0% | 95% |
| 32 条/请求时理论请求数 | 125 | 7 |
| 修改 A 中存量记录 | 取决于全量重建方式 | 0 |

以上不含模型重试、批内文本重复、跨批次竞态及缓存优化，不能视为实测性能承诺。

### 10.2 PostgreSQL 成本与风险

- 每批 CREATE/DROP TEMP TABLE 仍是 DDL，会修改 PostgreSQL 系统目录。高频率、长时间大量批次可能造成 pg_class、pg_attribute 等目录膨胀及 Autovacuum 压力，**唯一表名不能消除这种开销**。
- 建议监控每秒建表数、创建耗时、系统目录大小、数据库连接池等待、对 A 的索引查询耗时、WAL 量、后台清理滞后及 DB CPU/IO。
- 在单批约 4,000 条下原则上不为 B 建索引；若 A 中联合键索引缺失，先修复 A 索引而非为临时表反复建索引。
- 实测时使用 EXPLAIN (ANALYZE, BUFFERS) 检查反连接计划，但避免对线上超高负载频繁执行重型诊断。
- 若批次频率长期达到较高水平，建议把**每批物理建表**作为架构可调整点，评估复用会话临时表或共享暂存表；本版严格遵循每批独立建表要求。

## 11. 可观测性与验收

### 11.1 建议指标

- batch_id、temp_table_name、batch_input_rows、batch_distinct_rows、batch_existing_rows、batch_delta_rows
- temp_create_ms、temp_load_ms、diff_query_ms、temp_lifecycle_ms
- embedding_request_count、embedding_input_rows、embedding_latency_ms、embedding_retry_count、embedding_error_count
- a_inserted_rows、a_conflict_skipped_rows、a_write_ms、batch_end_to_end_ms
- active_batch_count、active_embedding_http_requests、datasource_active_connections、datasource_wait_ms

日志中的表名只能来自服务端生成器，输入 value 可能包含业务敏感信息，不建议完整记录原始值。

### 11.2 关键验收用例

| 用例 | 验证点 |
|---|---|
| 4000 条本批、全部已存在 | delta=0，不调用 Embedding |
| 4000 条本批、部分新增 | 仅对新增去重组合键向量化 |
| 批内重复组合键 | DISTINCT 后最多处理一次 |
| 两批并发、不同临时表名 | 表名不重复，会话隔离，数据互不污染 |
| 两批并发、存在相同新增键 | A 不重复入库；记录可能存在重复模型调用的已知限制 |
| 一批隔数小时到达 | 不依赖全量结束信号，独立处理 |
| 临时表事务回滚 | 无残留表、可重放本批 |
| 模型异常、部分已入库 | 重放后只处理仍缺失的数据 |
| 同名普通正式表存在 | B 用 pg_temp 访问，A 用 public.a 访问 |
| 批次超出配置上限 | 明确拒绝或由上游切批，不能静默截断 |
| 没有模型输出/错误维度 | 不写入错误 Vector，返回失败并支持重试 |

## 12. 最终技术选型结论

采用 **批次独立 UUID 临时表 + ON COMMIT DROP + NOT EXISTS + Java 内存增量数据 + 分批 Embedding + A 表唯一键幂等插入**。每批默认 4,000 条，可配置；批次互不共享表、不等待后续批次，也不使用额外持久化差异表 C。

该方案可以保证**存量复用、不全量删表、不全量重新 Embedding、批次独立隔离和 A 表不重复入库**。对“跨批次并发模型调用绝不重复”和“进程崩溃后自动恢复未入库增量”不做超出架构能力的保证，分别通过可选分布式去重和可靠原始批次重放实现增强。

### 参考

- [PostgreSQL CREATE TABLE / TEMPORARY / ON COMMIT](https://www.postgresql.org/docs/current/sql-createtable.html)
- [PostgreSQL INSERT / ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
- [PostgreSQL 标识符语法](https://www.postgresql.org/docs/current/sql-syntax-lexical.html)
- [Amazon RDS for PostgreSQL: High object counts / Temporary tables](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.HighObjectCount.html)
- [pgvector-java](https://github.com/pgvector/pgvector-java)
