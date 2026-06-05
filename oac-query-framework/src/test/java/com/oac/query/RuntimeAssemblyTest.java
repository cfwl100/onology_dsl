package com.oac.query;

import com.oac.query.assembly.AvgAccumulator;
import com.oac.query.assembly.ObjectAssembler;
import com.oac.query.binding.DatasourceType;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.logical.LogicalPlan;
import com.oac.query.plan.physical.FragmentDependency;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.runtime.DagInputResolver;
import com.oac.query.runtime.ExecutionContext;
import com.oac.query.runtime.FragmentResult;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.runtime.QueryExecutionEngine;
import com.oac.query.runtime.ResolvedInput;
import com.oac.query.spi.DatasourceExecutor;
import com.oac.query.spi.MockQueryTranslator;
import com.oac.query.spi.PhysicalQuery;
import com.oac.query.spi.QueryExtensionRegistry;
import com.oac.query.strategy.SplitDecision;
import com.oac.query.strategy.SplitStrategy;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 覆盖 DAG 输入解析和结果装配行为。
 */
class RuntimeAssemblyTest {
    @Test
    void dagInputResolverDeduplicatesFiltersNullsAndLimits() {
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        rows.add(row("cellId", "c1"));
        rows.add(row("cellId", "c1"));
        rows.add(row("cellId", null));
        rows.add(row("cellId", "c2"));
        rows.add(row("cellId", "c3"));
        FragmentResult upstream = new FragmentResult("A", true, rows);
        FragmentDependency dependency = new FragmentDependency("A", "cellId", "B", "cell_id", FragmentDependency.InputOperator.IN, true, 2);

        ResolvedInput input = new DagInputResolver().resolve(dependency, upstream);

        assertEquals(Arrays.asList("c1", "c2"), input.getValues());
    }

    @Test
    void requiredEmptyUpstreamSkipsDownstream() {
        QueryExtensionRegistry registry = new QueryExtensionRegistry();
        registry.registerTranslator(new MockQueryTranslator(DatasourceType.SQL));
        CountingExecutor executor = new CountingExecutor();
        registry.registerExecutor(executor);
        QueryExecutionEngine engine = new QueryExecutionEngine(registry);
        PhysicalPlan plan = new PhysicalPlan(new LogicalPlan(OqlQuery.OperationType.QUERY),
                new SplitDecision(SplitStrategy.DAG_DEPENDENT_QUERY, "test"));
        plan.addNode(new PhysicalSourceQueryNode("A", "sql-a", DatasourceType.SQL, "a", "A", Collections.singletonList("cellId"), null));
        plan.addNode(new PhysicalSourceQueryNode("B", "sql-b", DatasourceType.SQL, "b", "B", Collections.singletonList("value"), null));
        plan.addDependency(new FragmentDependency("A", "cellId", "B", "cell_id", FragmentDependency.InputOperator.IN, true, 10));

        List<FragmentResult> results = engine.execute(plan, PlannerContext.defaults(), ExecutionContext.defaults());

        assertEquals(2, results.size());
        assertEquals(1, executor.calls);
        assertTrue(results.get(1).isEmpty());
    }

    @Test
    void upstreamOutputIsInjectedAsDownstreamQueryParameter() {
        QueryExtensionRegistry registry = new QueryExtensionRegistry();
        registry.registerTranslator(new MockQueryTranslator(DatasourceType.SQL));
        RecordingDependencyExecutor executor = new RecordingDependencyExecutor();
        registry.registerExecutor(executor);
        QueryExecutionEngine engine = new QueryExecutionEngine(registry);
        PhysicalPlan plan = new PhysicalPlan(new LogicalPlan(OqlQuery.OperationType.QUERY),
                new SplitDecision(SplitStrategy.DAG_DEPENDENT_QUERY, "A 输出作为 B 入参"));
        plan.addNode(new PhysicalSourceQueryNode("A", "sql-a", DatasourceType.SQL, "a", "A", Collections.singletonList("cellId"), null));
        plan.addNode(new PhysicalSourceQueryNode("B", "sql-b", DatasourceType.SQL, "b", "B", Collections.singletonList("value"), null));
        plan.addDependency(new FragmentDependency("A", "cellId", "B", "cell_id", FragmentDependency.InputOperator.IN, true, 10));

        List<FragmentResult> results = engine.execute(plan, PlannerContext.defaults(), ExecutionContext.defaults());

        assertEquals(2, results.size());
        assertEquals(Arrays.asList("A", "B"), executor.executedFragmentIds);
        PhysicalQuery downstreamQuery = executor.executedQueries.get("B");
        assertNotNull(downstreamQuery);
        @SuppressWarnings("unchecked")
        Map<String, List<Object>> dynamicInputs = (Map<String, List<Object>>) downstreamQuery.parameters().get("dynamicInputs");
        assertEquals(Arrays.<Object>asList("cell-001", "cell-002"), dynamicInputs.get("cell_id"));
    }

    @Test
    void objectAssemblerUsesFirstNonNullConflictPolicy() {
        FragmentResult left = new FragmentResult("A", true, Collections.singletonList(row("rid", "r1", "name", "cell-a", "value", null)));
        FragmentResult right = new FragmentResult("B", true, Collections.singletonList(row("rid", "r1", "name", "ignored", "value", 42)));

        List<Map<String, Object>> objects = new ObjectAssembler().assemble(Arrays.asList(left, right));

        assertEquals(1, objects.size());
        assertEquals("cell-a", objects.get(0).get("name"));
        assertEquals(42, objects.get(0).get("value"));
    }

    @Test
    void avgAccumulatorUsesSumAndCount() {
        AvgAccumulator accumulator = new AvgAccumulator();
        accumulator.add(100, 4);
        accumulator.add(50, 1);

        assertEquals(30D, accumulator.average(), 0.001D);
    }

    private Map<String, Object> row(Object... keyValues) {
        Map<String, Object> row = new LinkedHashMap<String, Object>();
        for (int i = 0; i < keyValues.length; i += 2) {
            row.put(String.valueOf(keyValues[i]), keyValues[i + 1]);
        }
        return row;
    }

    private static class CountingExecutor implements DatasourceExecutor<PhysicalQuery> {
        private int calls;

        public DatasourceType supportType() {
            return DatasourceType.SQL;
        }

        public FragmentResult execute(PhysicalQuery query, ExecutionContext context) {
            calls++;
            return FragmentResult.empty(query.getFragmentId());
        }
    }

    private static class RecordingDependencyExecutor implements DatasourceExecutor<PhysicalQuery> {
        private final List<String> executedFragmentIds = new ArrayList<String>();
        private final Map<String, PhysicalQuery> executedQueries = new LinkedHashMap<String, PhysicalQuery>();

        public DatasourceType supportType() {
            return DatasourceType.SQL;
        }

        public FragmentResult execute(PhysicalQuery query, ExecutionContext context) {
            executedFragmentIds.add(query.getFragmentId());
            executedQueries.put(query.getFragmentId(), query);
            if ("A".equals(query.getFragmentId())) {
                List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
                rows.add(row("cellId", "cell-001"));
                rows.add(row("cellId", "cell-001"));
                rows.add(row("cellId", null));
                rows.add(row("cellId", "cell-002"));
                return new FragmentResult("A", true, rows);
            }
            return FragmentResult.empty(query.getFragmentId());
        }

        private Map<String, Object> row(Object... keyValues) {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            for (int i = 0; i < keyValues.length; i += 2) {
                row.put(String.valueOf(keyValues[i]), keyValues[i + 1]);
            }
            return row;
        }
    }
}
