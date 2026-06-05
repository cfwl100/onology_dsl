package com.oac.query.runtime;

import com.oac.query.plan.physical.FragmentDependency;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.spi.DatasourceExecutor;
import com.oac.query.spi.PhysicalQuery;
import com.oac.query.spi.QueryExtensionRegistry;
import com.oac.query.spi.QueryTranslator;
import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.List;

/**
 * 通过翻译器/执行器 SPI 组合执行物理源查询分片。
 *
 * 当前调度器按顺序执行，但已经遵守 FragmentDependency 语义，
 * 方便后续替换为拓扑排序或并发执行器。
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
                // 同时保存到运行时上下文和查询分片上：
                // 前者用于观测，后者供支持动态输入的翻译器绑定参数。
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
