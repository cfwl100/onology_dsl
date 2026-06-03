package com.onology.oac.queryframework;

import com.onology.oac.queryframework.core.SplitStrategySelector;
import com.onology.oac.queryframework.domain.MetadataModels;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.PlanModels;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SplitStrategySelectorTest {
    @Test
    void shouldSelectSingleTablePushdown() {
        var graph = new PlanModels.BindingGraph(
                List.of(new PlanModels.ObjectBindingNode("c", "Cell")),
                List.of(new PlanModels.PropertyBindingNode("c", "Cell", "cellId", binding("cell_id", "dim_cell"))),
                List.of(),
                List.of(PlanModels.PhysicalBindingNode.from(binding("cell_id", "dim_cell"))),
                List.of(),
                Map.of("mysql_1", capability("mysql_1")));

        var decision = new SplitStrategySelector().select(OqlModels.OperationType.QUERY, graph, query(OqlModels.OperationType.QUERY));

        assertEquals(PlanModels.SplitStrategy.SINGLE_SOURCE_SINGLE_TABLE, decision.strategy());
    }

    @Test
    void shouldSelectCrossSourceMerge() {
        var mysqlBinding = binding("cell_id", "dim_cell");
        var apiBinding = new MetadataModels.PropertyBinding("schema", "Cell", "status", "api_1",
                MetadataModels.DatasourceType.API, null, null, null, "status", null, null, null, null,
                "/status", null, false, false, false);
        var graph = new PlanModels.BindingGraph(
                List.of(new PlanModels.ObjectBindingNode("c", "Cell")),
                List.of(new PlanModels.PropertyBindingNode("c", "Cell", "cellId", mysqlBinding),
                        new PlanModels.PropertyBindingNode("c", "Cell", "status", apiBinding)),
                List.of(),
                List.of(PlanModels.PhysicalBindingNode.from(mysqlBinding), PlanModels.PhysicalBindingNode.from(apiBinding)),
                List.of(),
                Map.of("mysql_1", capability("mysql_1"), "api_1", apiCapability("api_1")));

        var decision = new SplitStrategySelector().select(OqlModels.OperationType.QUERY, graph, query(OqlModels.OperationType.QUERY));

        assertEquals(PlanModels.SplitStrategy.CROSS_SOURCE_MEMORY_MERGE, decision.strategy());
    }

    private OqlModels.OqlQuery query(OqlModels.OperationType operationType) {
        return new OqlModels.OqlQuery("1.0", "schema", true, operationType,
                List.of(new OqlModels.OqlObject("Cell", "c", null)), List.of(), null, List.of(), null,
                List.of(), null, List.of(), Map.of(), Map.of());
    }

    private MetadataModels.PropertyBinding binding(String field, String table) {
        return new MetadataModels.PropertyBinding("schema", "Cell", field, "mysql_1", MetadataModels.DatasourceType.MYSQL,
                "db", "public", table, field, null, null, null, null, null, null, false, false, false);
    }

    private MetadataModels.DatasourceCapability capability(String sourceId) {
        return new MetadataModels.DatasourceCapability(sourceId, MetadataModels.DatasourceType.MYSQL,
                true, true, true, true, true, true, true, true, true, false, true, false);
    }

    private MetadataModels.DatasourceCapability apiCapability(String sourceId) {
        return new MetadataModels.DatasourceCapability(sourceId, MetadataModels.DatasourceType.API,
                true, true, false, false, false, false, true, false, false, false, false, false);
    }
}
