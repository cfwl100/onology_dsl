package com.onology.oac.queryframework;

import com.onology.oac.queryframework.dag.DagInputResolver;
import com.onology.oac.queryframework.dag.FragmentDependency;
import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class DagInputResolverTest {
    @Test
    void shouldResolveUpstreamRowsAsDownstreamInValues() {
        FragmentDependency dependency = new FragmentDependency("A", "cellId", "B", "cell_id",
                FragmentDependency.InputOperator.IN, true, 100);
        FragmentResult upstream = new FragmentResult("A", "graph_1",
                List.of(Map.of("cellId", "c1"), Map.of("cellId", "c2"), Map.of("cellId", "c1")), Map.of());

        DagInputResolver.ResolvedInput input = new DagInputResolver().resolve(dependency, upstream);

        assertEquals("cell_id", input.field());
        assertEquals(FragmentDependency.InputOperator.IN, input.operator());
        assertEquals(List.of("c1", "c2"), input.values());
    }
}
