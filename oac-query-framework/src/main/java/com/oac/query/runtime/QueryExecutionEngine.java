package com.oac.query.runtime;

import com.oac.query.plan.physical.FragmentDependency;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.spi.DatasourceExecutor;
import com.oac.query.spi.PhysicalQuery;
import com.oac.query.spi.QueryExtensionRegistry;
import com.oac.query.spi.QueryTranslator;
import com.oac.query.strategy.SplitStrategy;
import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.List;

/**
 * 通过翻译器/执行器 SPI 组合执行物理源查询分片。
 *
 * 当前调度器按顺序执行，但已经遵守 FragmentDependency 语义，
 * 方便后续替换为拓扑排序或并发执行器。
 *
 * <h2>策略相关执行说明</h2>
 * <ul>
 *   <li>{@link SplitStrategy#SINGLE_SOURCE_SINGLE_TABLE}: 直接执行单个源节点</li>
 *   <li>{@link SplitStrategy#SINGLE_SOURCE_MULTI_TABLE_JOIN}: 执行带 Join 下推提示的源节点</li>
 *   <li>{@link SplitStrategy#CROSS_SOURCE_MEMORY_MERGE}: 并行执行所有源节点，结果由 MergeJoinNode 合并</li>
 *   <li>{@link SplitStrategy#DAG_DEPENDENT_QUERY}: 按依赖顺序执行，动态注入上游输出到下游条件</li>
 *   <li>{@link SplitStrategy#ASSOCIATION_GRAPH_PUSHDOWN}: 执行带原生关联提示的源节点</li>
 *   <li>{@link SplitStrategy#ASSOCIATION_RELATIONAL_JOIN}: 执行带关系型 Join 提示的源节点</li>
 *   <li>{@link SplitStrategy#ASSOCIATION_MULTI_STAGE_ASSEMBLE}: 执行所有源节点，由 AssociationAssembleNode 组装</li>
 *   <li>{@link SplitStrategy#AGGREGATE_PUSHDOWN}: 执行带聚合下推提示的源节点</li>
 *   <li>{@link SplitStrategy#AGGREGATE_PARTIAL_PUSHDOWN_MERGE}: 执行所有源节点（带局部聚合），结果由 MemoryAggregateNode 合并</li>
 *   <li>{@link SplitStrategy#AGGREGATE_MEMORY}: 执行源节点（明细查询），结果由 MemoryAggregateNode 计算聚合</li>
 *   <li>{@link SplitStrategy#DAG_DEPENDENT_AGGREGATE}: 按依赖顺序执行源节点，最后由 MemoryAggregateNode 聚合</li>
 * </ul>
 */
public class QueryExecutionEngine {
    private final QueryExtensionRegistry registry;
    private final DagInputResolver inputResolver;

    public QueryExecutionEngine(QueryExtensionRegistry registry) {
        this(registry, new DagInputResolver());
    }

    public QueryExecutionEngine(QueryExtensionRegistry registry, DagInputResolver inputResolver) {
        this.registry = registry;
        this.inputResolver = inputResolver;
    }

    public List<FragmentResult> execute(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        SplitStrategy strategy = plan.getStrategy();
        switch (strategy) {
            case SINGLE_SOURCE_SINGLE_TABLE:
                return executeSingleSourceSingleTable(plan, plannerContext, executionContext);
            case SINGLE_SOURCE_MULTI_TABLE_JOIN:
                return executeSingleSourceMultiTableJoin(plan, plannerContext, executionContext);
            case CROSS_SOURCE_MEMORY_MERGE:
                return executeCrossSourceMemoryMerge(plan, plannerContext, executionContext);
            case DAG_DEPENDENT_QUERY:
                return executeDagDependentQuery(plan, plannerContext, executionContext);
            case ASSOCIATION_GRAPH_PUSHDOWN:
                return executeAssociationGraphPushdown(plan, plannerContext, executionContext);
            case ASSOCIATION_RELATIONAL_JOIN:
                return executeAssociationRelationalJoin(plan, plannerContext, executionContext);
            case ASSOCIATION_MULTI_STAGE_ASSEMBLE:
                return executeAssociationMultiStageAssemble(plan, plannerContext, executionContext);
            case AGGREGATE_PUSHDOWN:
                return executeAggregatePushdown(plan, plannerContext, executionContext);
            case AGGREGATE_PARTIAL_PUSHDOWN_MERGE:
                return executeAggregatePartialPushdownMerge(plan, plannerContext, executionContext);
            case AGGREGATE_MEMORY:
                return executeAggregateMemory(plan, plannerContext, executionContext);
            case DAG_DEPENDENT_AGGREGATE:
                return executeDagDependentAggregate(plan, plannerContext, executionContext);
            default:
                throw new IllegalStateException("Unsupported strategy: " + strategy);
        }
    }

    /**
     * SINGLE_SOURCE_SINGLE_TABLE: 单数据源单表直接下推。
     */
    private List<FragmentResult> executeSingleSourceSingleTable(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
            results.add(result);
        }
        return results;
    }

    /**
     * SINGLE_SOURCE_MULTI_TABLE_JOIN: 单数据源多表 Join 下推。
     * 源节点已设置 pushdownJoin 提示，翻译器据此生成带 Join 的 SQL。
     */
    private List<FragmentResult> executeSingleSourceMultiTableJoin(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (sourceNode.isPushdownJoin()) {
                FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
                results.add(result);
            }
        }
        return results;
    }

    /**
     * CROSS_SOURCE_MEMORY_MERGE: 跨源无依赖并行查询。
     * 所有源节点独立执行，结果由后续 MergeJoinNode 合并。
     * v1 顺序执行，v2 可改为并发。
     */
    private List<FragmentResult> executeCrossSourceMemoryMerge(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        DagRuntimeContext dagContext = new DagRuntimeContext();
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
            dagContext.putResult(sourceNode.getId(), result);
            results.add(result);
        }
        return results;
    }

    /**
     * DAG_DEPENDENT_QUERY: 跨源有依赖的 DAG 查询。
     * 按拓扑顺序执行，后续节点依赖前序节点的输出。
     */
    private List<FragmentResult> executeDagDependentQuery(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        DagRuntimeContext dagContext = new DagRuntimeContext();
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (shouldSkipForDependencies(plan, sourceNode, dagContext)) {
                FragmentResult skipped = FragmentResult.empty(sourceNode.getId());
                dagContext.putResult(sourceNode.getId(), skipped);
                results.add(skipped);
                continue;
            }
            applyDynamicInputs(plan, sourceNode, dagContext);
            FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
            dagContext.putResult(sourceNode.getId(), result);
            results.add(result);
        }
        return results;
    }

    /**
     * ASSOCIATION_GRAPH_PUSHDOWN: 关联查询图数据库原生边下推。
     * 源节点已设置 nativeAssociation 提示，由图数据库执行关系遍历。
     */
    private List<FragmentResult> executeAssociationGraphPushdown(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (sourceNode.isNativeAssociation()) {
                FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
                results.add(result);
            }
        }
        return results;
    }

    /**
     * ASSOCIATION_RELATIONAL_JOIN: 关联查询关系型 Join。
     * 源节点设置 pushdownJoin 提示，翻译器生成 SQL Join。
     */
    private List<FragmentResult> executeAssociationRelationalJoin(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (sourceNode.isPushdownJoin()) {
                FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
                results.add(result);
            }
        }
        return results;
    }

    /**
     * ASSOCIATION_MULTI_STAGE_ASSEMBLE: 跨源关联多阶段装配。
     * 所有源节点执行后，由 AssociationAssembleNode 组装结果。
     */
    private List<FragmentResult> executeAssociationMultiStageAssemble(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        DagRuntimeContext dagContext = new DagRuntimeContext();
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (shouldSkipForDependencies(plan, sourceNode, dagContext)) {
                FragmentResult skipped = FragmentResult.empty(sourceNode.getId());
                dagContext.putResult(sourceNode.getId(), skipped);
                results.add(skipped);
                continue;
            }
            applyDynamicInputs(plan, sourceNode, dagContext);
            FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
            dagContext.putResult(sourceNode.getId(), result);
            results.add(result);
        }
        return results;
    }

    /**
     * AGGREGATE_PUSHDOWN: 聚合完全下推到数据库。
     * 源节点设置 pushdownAggregation 和 pushdownHaving 提示。
     */
    private List<FragmentResult> executeAggregatePushdown(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (sourceNode.isPushdownAggregation() && sourceNode.isPushdownHaving()) {
                FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
                results.add(result);
            }
        }
        return results;
    }

    /**
     * AGGREGATE_PARTIAL_PUSHDOWN_MERGE: 多源局部聚合后内存合并。
     * 各源节点执行局部聚合（pushdownAggregation=true, pushdownHaving=false），
     * 结果由 MemoryAggregateNode 合并最终聚合值（如 AVG）。
     */
    private List<FragmentResult> executeAggregatePartialPushdownMerge(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        DagRuntimeContext dagContext = new DagRuntimeContext();
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (sourceNode.isPushdownAggregation()) {
                FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
                dagContext.putResult(sourceNode.getId(), result);
                results.add(result);
            }
        }
        return results;
    }

    /**
     * AGGREGATE_MEMORY: 聚合无法下推，纯 OAC 内存计算。
     * 源节点只做明细查询，MemoryAggregateNode 计算最终聚合结果。
     */
    private List<FragmentResult> executeAggregateMemory(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        DagRuntimeContext dagContext = new DagRuntimeContext();
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
            dagContext.putResult(sourceNode.getId(), result);
            results.add(result);
        }
        return results;
    }

    /**
     * DAG_DEPENDENT_AGGREGATE: 聚合依赖前序 DAG 查询结果。
     * 先执行依赖的源查询，将其结果作为聚合源的条件输入，
     * 最后由 MemoryAggregateNode 计算聚合。
     */
    private List<FragmentResult> executeDagDependentAggregate(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        DagRuntimeContext dagContext = new DagRuntimeContext();
        List<FragmentResult> results = new ArrayList<FragmentResult>();
        for (PhysicalSourceQueryNode sourceNode : plan.getSourceNodes()) {
            if (shouldSkipForDependencies(plan, sourceNode, dagContext)) {
                FragmentResult skipped = FragmentResult.empty(sourceNode.getId());
                dagContext.putResult(sourceNode.getId(), skipped);
                results.add(skipped);
                continue;
            }
            applyDynamicInputs(plan, sourceNode, dagContext);
            FragmentResult result = executeSource(sourceNode, plannerContext, executionContext);
            dagContext.putResult(sourceNode.getId(), result);
            results.add(result);
        }
        return results;
    }

    private boolean shouldSkipForDependencies(PhysicalPlan plan, PhysicalSourceQueryNode sourceNode, DagRuntimeContext dagContext) {
        for (FragmentDependency dependency : plan.getDependencies()) {
            if (!dependency.getDownstreamNodeId().equals(sourceNode.getId())) {
                continue;
            }
            FragmentResult upstreamResult = dagContext.result(dependency.getUpstreamNodeId());
            if (dependency.isRequired() && (upstreamResult == null || upstreamResult.isEmpty())) {
                return true;
            }
        }
        return false;
    }

    private void applyDynamicInputs(PhysicalPlan plan, PhysicalSourceQueryNode sourceNode, DagRuntimeContext dagContext) {
        for (FragmentDependency dependency : plan.getDependencies()) {
            if (!dependency.getDownstreamNodeId().equals(sourceNode.getId())) {
                continue;
            }
            FragmentResult upstreamResult = dagContext.result(dependency.getUpstreamNodeId());
            ResolvedInput input = inputResolver.resolve(dependency, upstreamResult);
            if (!input.isEmpty()) {
                dagContext.putInput(input);
                sourceNode.putDynamicInput(input.getDownstreamInputField(), input.getValues());
            }
        }
    }

    private FragmentResult executeSource(PhysicalSourceQueryNode sourceNode, PlannerContext plannerContext, ExecutionContext executionContext) {
        QueryTranslator<PhysicalQuery> translator = registry.translator(sourceNode.getDatasourceType());
        DatasourceExecutor<PhysicalQuery> executor = registry.executor(sourceNode.getDatasourceType());
        if (translator == null) {
            return FragmentResult.failed(sourceNode.getId(), OqlError.of("TRANSLATOR_NOT_FOUND", "No translator registered", "translator")
                    .fragmentId(sourceNode.getId())
                    .datasourceId(sourceNode.getDatasourceId()));
        }
        if (executor == null) {
            return FragmentResult.failed(sourceNode.getId(), OqlError.of("EXECUTOR_NOT_FOUND", "No executor registered", "executor")
                    .fragmentId(sourceNode.getId())
                    .datasourceId(sourceNode.getDatasourceId()));
        }
        if (!translator.canTranslate(sourceNode, plannerContext)) {
            return FragmentResult.failed(sourceNode.getId(), OqlError.of("TRANSLATOR_REJECTED", "Translator cannot translate fragment", "translator")
                    .fragmentId(sourceNode.getId())
                    .datasourceId(sourceNode.getDatasourceId())
                    .translatorName(translator.getClass().getSimpleName()));
        }
        try {
            PhysicalQuery query = translator.translate(sourceNode, plannerContext);
            return executor.execute(query, executionContext);
        } catch (RuntimeException e) {
            return FragmentResult.failed(sourceNode.getId(), OqlError.of("FRAGMENT_EXECUTION_ERROR", e.getMessage(), "executor")
                    .fragmentId(sourceNode.getId())
                    .datasourceId(sourceNode.getDatasourceId())
                    .executorName(executor.getClass().getSimpleName()));
        }
    }
}
