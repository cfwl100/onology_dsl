package com.onology.oac.queryframework.executor;

import com.onology.oac.queryframework.domain.PlanModels;
import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import com.onology.oac.queryframework.domain.ResultModels.OacError;
import com.onology.oac.queryframework.registry.QueryExtensionRegistry;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.ExecutionContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PhysicalQuery;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Executes translated physical source fragments through registered extensions. */
public class QueryExecutionEngine {
    private final QueryExtensionRegistry registry;

    public QueryExecutionEngine(QueryExtensionRegistry registry) {
        this.registry = registry;
    }

    public ExecutionResult execute(PlanModels.PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
        Map<String, FragmentResult> results = new LinkedHashMap<>();
        Map<String, OacError> errors = new LinkedHashMap<>();
        for (PlanModels.PhysicalSourceQueryNode sourceNode : plan.sourceNodes()) {
            registry.translator(sourceNode.datasourceType()).ifPresentOrElse(translator -> runFragment(
                    sourceNode, translator, plannerContext, executionContext, results, errors),
                    () -> errors.put(sourceNode.nodeId(), OacError.of("TRANSLATE_FAILED",
                            "translator not found for datasource type: " + sourceNode.datasourceType(), sourceNode.nodeId())));
        }
        return new ExecutionResult(results, errors.values().stream().toList());
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private void runFragment(PlanModels.PhysicalSourceQueryNode sourceNode,
                             QueryTranslator translator,
                             PlannerContext plannerContext,
                             ExecutionContext executionContext,
                             Map<String, FragmentResult> results,
                             Map<String, OacError> errors) {
        try {
            PhysicalQuery query = (PhysicalQuery) translator.translate(sourceNode, plannerContext);
            registry.executor(query.datasourceType()).ifPresentOrElse(executor ->
                    results.put(sourceNode.nodeId(), executor.execute(query, executionContext)),
                    () -> errors.put(sourceNode.nodeId(), OacError.of("EXECUTE_FAILED",
                            "executor not found for datasource type: " + query.datasourceType(), sourceNode.nodeId())));
        } catch (RuntimeException ex) {
            errors.put(sourceNode.nodeId(), OacError.of("EXECUTE_FAILED", ex.getMessage(), sourceNode.nodeId()));
        }
    }

    public record ExecutionResult(Map<String, FragmentResult> fragmentResults, List<OacError> errors) {
        public boolean isSuccess() {
            return errors == null || errors.isEmpty();
        }
    }
}
