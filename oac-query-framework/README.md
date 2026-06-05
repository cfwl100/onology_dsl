# OAC Query Framework

Java 8 compatible Maven library for the OAC ontology query transformation framework.

The first version implements the read-query loop:

```text
OQL -> OqlValidator -> BindingResolver -> LogicalPlan -> PhysicalPlan
    -> DAG Execution -> QueryTranslator SPI -> DatasourceExecutor SPI
    -> ResultAssembler -> OntologyQueryResult
```

## Public Entry Points

- `OqlParser.parse(String json): OqlQuery`
- `OqlValidator.validate(OqlQuery query): ValidationResult`
- `QueryFrameworkService.run(OqlQuery query, PlannerContext plannerContext, ExecutionContext executionContext): OntologyQueryResult`

## Scope

- Supported: `QUERY`, `AGGREGATE`, `ASSOCIATION_QUERY`
- Recognized but not implemented: `CREATE`, `UPDATE`, `DELETE`, `UPSERT`, `BATCH`
- Metadata and datasource adapters are in-memory mock implementations intended to keep the SPI stable.

## Build

```bash
mvn test
```
当前工程端到端主线可以理解为：

```text
OQL JSON
  -> OqlParser
  -> OqlQuery
  -> QueryFrameworkService.run
  -> OqlValidator
  -> BindingResolver / BindingGraph
  -> LogicalPlanBuilder
  -> PhysicalPlanBuilder / PhysicalPlan
  -> QueryExecutionEngine
  -> Translator SPI
  -> Executor SPI
  -> FragmentResult
  -> QueryResultAssembler
  -> OntologyQueryResult
```

**1. OQL 解析**
如果输入是 JSON 字符串，先由 [OqlParser.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\dsl\OqlParser.java:53>) 解析成 `OqlQuery`。  
它会显式解析 `objects`、`relationships`、`conditions`、`returns`、`aggregateFilter` 等结构，递归处理表达式、条件树和聚合过滤树。

**2. 主入口编排**
真正的框架入口是 [QueryFrameworkService.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\runtime\QueryFrameworkService.java:47>) 的 `run` 方法。它按阶段执行：

```java
validate -> bind -> logicalPlan -> physicalPlan -> execute -> assemble
```

现在逻辑计划已经被真实使用：

```java
LogicalPlan logicalPlan = logicalPlanBuilder.build(query);
PhysicalPlan physicalPlan = physicalPlanBuilder.build(logicalPlan, query, bindingResult.getGraph());
```

**3. OQL 校验**
[OqlValidator.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\validation\OqlValidator.java:56>) 负责 DSL 规则校验。  
它会判断：

- `QUERY` 不能带 `relationships`、`aggregateFilter`、`mutation`
- `AGGREGATE` 只能返回 `GROUP_BY` / `METRIC`
- `ASSOCIATION_QUERY` 必须声明关系
- 函数必须注册，且只能出现在允许位置
- 写操作当前 v1 会被明确拦截

校验失败时不会进入后续绑定和执行，直接返回失败的 `OntologyQueryResult`。

**4. 本体绑定**
[BindingResolver.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\binding\BindingResolver.java:38>) 把 OQL 中的对象、字段、关系 alias 解析到物理数据源绑定。  
当前使用 `MockOntologyMetadata` 提供内存元数据，例如：

```text
Order.amount -> mysql-sales.orders.amount
Cell.prbUsage -> dac-kpi.cell_kpi.prb_usage
Cell.alarmCount -> es-alarm.alarm_index.alarm_count
```

绑定后的 `BindingGraph` 会告诉物理规划阶段：是否单源、是否跨源、是否支持 join、是否支持聚合下推等。

**5. 逻辑计划**
`LogicalPlanBuilder` 生成与数据源无关的语义计划，例如：

```text
LogicalScanNode
LogicalFilterNode
LogicalProjectNode
LogicalAggregateNode
LogicalAssociationNode
LogicalLimitNode
```

这一步表达“查什么”，不关心怎么查数据库。

**6. 物理计划**
[PhysicalPlanBuilder.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\plan\physical\PhysicalPlanBuilder.java:38>) 接收 `LogicalPlan + OqlQuery + BindingGraph`，生成面向数据源执行的 `PhysicalPlan`。

它会：

- 按数据源生成 `PhysicalSourceQueryNode`
- 根据策略补充 merge / aggregate / association 物理节点
- 对 DAG 场景添加 `FragmentDependency`

DAG 依赖边目前在 [PhysicalPlanBuilder.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\plan\physical\PhysicalPlanBuilder.java:75>) 生成，语义是：

```text
A.cellId -> B.cell_id IN (...)
```

**7. 执行阶段**
[QueryExecutionEngine.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\runtime\QueryExecutionEngine.java:34>) 顺序执行物理 source 节点。

执行 B 之前，会先检查依赖：

- 如果 A 无结果且依赖 `required=true`，跳过 B
- 如果 A 有结果，则 [applyDynamicInputs](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\runtime\QueryExecutionEngine.java:65>) 调用 `DagInputResolver`
- `DagInputResolver` 从 A 的结果中提取字段、去重、过滤 `null`
- 然后注入到 B 的 `dynamicInputs`

之后 [executeSource](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\runtime\QueryExecutionEngine.java:81>) 会：

```text
PhysicalSourceQueryNode
  -> QueryTranslator
  -> PhysicalQuery
  -> DatasourceExecutor
  -> FragmentResult
```

当前 translator/executor 是 mock 实现，但 SPI 边界已经留好。

**8. DAG A->B 示例**
你刚加的测试覆盖了这个场景：

```text
A 返回:
cellId = cell-001
cellId = cell-001
cellId = null
cellId = cell-002

注入给 B:
cell_id IN ["cell-001", "cell-002"]
```

对应测试在 [RuntimeAssemblyTest.java](<D:\code\oac\oac-query-framework\src\test\java\com\oac\query\RuntimeAssemblyTest.java:73>)。

**9. 结果装配**
最后 [QueryResultAssembler.java](<D:\code\oac\oac-query-framework\src\main\java\com\oac\query\assembly\QueryResultAssembler.java:28>) 根据 operation 类型装配结果：

- `QUERY`：走 `ObjectAssembler`
- `ASSOCIATION_QUERY`：装配 objects + relationships
- `AGGREGATE`：装配 metrics

最终统一返回 `OntologyQueryResult`。

当前工程本质上已经跑通了一个“可插拔数据源的 OQL 查询转换执行框架骨架”：校验、绑定、规划、DAG 动态入参、SPI 执行、结果装配都在，只是元数据和数据源执行还是 mock。