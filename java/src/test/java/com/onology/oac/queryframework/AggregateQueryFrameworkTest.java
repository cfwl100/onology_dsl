package com.onology.oac.queryframework;

import com.onology.oac.queryframework.aggregator.AvgAccumulator;
import com.onology.oac.queryframework.core.SplitStrategySelector;
import com.onology.oac.queryframework.domain.MetadataModels;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.PlanModels;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AggregateQueryFrameworkTest {
    @Test
    void shouldPushdownAggregateWhenSourceSupportsGroupByAndHaving() {
        var binding = new MetadataModels.PropertyBinding("schema", "Cell", "prbUsage", "mysql_1",
                MetadataModels.DatasourceType.MYSQL, "db", "public", "kpi", "prb_usage",
                null, null, null, null, null, null, false, false, false);
        var graph = new PlanModels.BindingGraph(
                List.of(new PlanModels.ObjectBindingNode("c", "Cell")),
                List.of(new PlanModels.PropertyBindingNode("c", "Cell", "prbUsage", binding)),
                List.of(),
                List.of(PlanModels.PhysicalBindingNode.from(binding)),
                List.of(),
                Map.of("mysql_1", capability()));

        var query = new OqlModels.OqlQuery("1.0", "schema", true, OqlModels.OperationType.AGGREGATE,
                List.of(new OqlModels.OqlObject("Cell", "c", null)), List.of(), null,
                List.of(new OqlModels.OqlReturnItem(OqlModels.ReturnKind.METRIC, "c", null, null,
                        "prbUsage", OqlModels.AggregateFunction.AVG, "avgPrb")),
                null, List.of(), null, List.of(), Map.of(), Map.of());

        var decision = new SplitStrategySelector().select(OqlModels.OperationType.AGGREGATE, graph, query);

        assertEquals(PlanModels.SplitStrategy.AGGREGATE_PUSHDOWN, decision.strategy());
    }

    @Test
    void avgAccumulatorUsesSumAndCount() {
        AvgAccumulator acc = new AvgAccumulator();
        acc.add(10);
        acc.add(20);
        acc.merge(new BigDecimal("30"), 1);
        assertEquals(new BigDecimal("20"), acc.result().stripTrailingZeros());
    }

    private MetadataModels.DatasourceCapability capability() {
        return new MetadataModels.DatasourceCapability("mysql_1", MetadataModels.DatasourceType.MYSQL,
                true, true, true, true, true, true, true, true, true, false, true, false);
    }
}
