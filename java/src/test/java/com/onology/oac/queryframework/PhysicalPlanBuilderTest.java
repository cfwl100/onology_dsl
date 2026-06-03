package com.onology.oac.queryframework;

import com.onology.oac.queryframework.core.PhysicalPlanBuilder;
import com.onology.oac.queryframework.core.SplitStrategySelector;
import com.onology.oac.queryframework.domain.MetadataModels;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.PlanModels;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PhysicalPlanBuilderTest {
    @Test
    void shouldAppendMergeNodeForCrossSourceQuery() {
        var mysqlBinding = binding("cellId", "cell_id", "mysql_1", MetadataModels.DatasourceType.MYSQL);
        var apiBinding = binding("status", "status", "api_1", MetadataModels.DatasourceType.API);
        var graph = new PlanModels.BindingGraph(
                List.of(new PlanModels.ObjectBindingNode("c", "Cell")),
                List.of(new PlanModels.PropertyBindingNode("c", "Cell", "cellId", mysqlBinding),
                        new PlanModels.PropertyBindingNode("c", "Cell", "status", apiBinding)),
                List.of(),
                List.of(PlanModels.PhysicalBindingNode.from(mysqlBinding), PlanModels.PhysicalBindingNode.from(apiBinding)),
                List.of(),
                Map.of("mysql_1", mysqlCapability(), "api_1", apiCapability()));

        var plan = new PhysicalPlanBuilder(new SplitStrategySelector()).build(query(), graph);

        assertEquals(PlanModels.SplitStrategy.CROSS_SOURCE_MEMORY_MERGE, plan.splitDecision().strategy());
        assertTrue(plan.nodes().stream().anyMatch(item -> item instanceof PlanModels.PhysicalMergeJoinNode));
    }

    private OqlModels.OqlQuery query() {
        return new OqlModels.OqlQuery("1.0", "schema", true, OqlModels.OperationType.QUERY,
                List.of(new OqlModels.OqlObject("Cell", "c", null)), List.of(), null, List.of(), null,
                List.of(), null, List.of(), Map.of(), Map.of());
    }

    private MetadataModels.PropertyBinding binding(String property, String field, String source, MetadataModels.DatasourceType type) {
        return new MetadataModels.PropertyBinding("schema", "Cell", property, source, type,
                "db", "public", "dim_cell", field, null, null, null, null, null, null, false, false, false);
    }

    private MetadataModels.DatasourceCapability mysqlCapability() {
        return new MetadataModels.DatasourceCapability("mysql_1", MetadataModels.DatasourceType.MYSQL,
                true, true, true, true, true, true, true, true, true, false, true, false);
    }

    private MetadataModels.DatasourceCapability apiCapability() {
        return new MetadataModels.DatasourceCapability("api_1", MetadataModels.DatasourceType.API,
                true, true, false, false, false, false, true, false, false, false, false, false);
    }
}
