package com.onology.oac.queryframework.core;

import com.onology.oac.queryframework.domain.MetadataModels;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.OqlModels.OperationType;
import com.onology.oac.queryframework.domain.PlanModels;
import com.onology.oac.queryframework.domain.PlanModels.SplitDecision;
import com.onology.oac.queryframework.domain.PlanModels.SplitStrategy;

/**
 * Selects whether a query should be pushed down, split into fragments, assembled in OAC,
 * or aggregated in OAC according to BindingGraph and datasource capabilities.
 */
public class SplitStrategySelector {
    public SplitDecision select(OperationType operation, PlanModels.BindingGraph graph, OqlModels.OqlQuery query) {
        return switch (operation) {
            case QUERY -> selectQuery(graph);
            case ASSOCIATION_QUERY -> selectAssociation(graph);
            case AGGREGATE -> selectAggregate(graph, query);
            default -> SplitDecision.of(SplitStrategy.CROSS_SOURCE_FRAGMENT_QUERY,
                    "operation is reserved for future mutation support");
        };
    }

    private SplitDecision selectQuery(PlanModels.BindingGraph graph) {
        if (graph.isSingleDatasource() && graph.isSingleTable()) {
            return SplitDecision.of(SplitStrategy.SINGLE_SOURCE_SINGLE_TABLE,
                    "single datasource and single physical table");
        }
        if (graph.isSingleDatasource() && graph.canPushdownJoin() && graph.isSingleSchema()) {
            return SplitDecision.of(SplitStrategy.SINGLE_SOURCE_MULTI_TABLE_JOIN,
                    "single datasource supports join pushdown");
        }
        if (graph.isCrossDatasource()) {
            return SplitDecision.of(SplitStrategy.CROSS_SOURCE_MEMORY_MERGE,
                    "cross datasource query requires OAC result merge");
        }
        return SplitDecision.of(SplitStrategy.CROSS_SOURCE_FRAGMENT_QUERY,
                "datasource capability is insufficient for a single pushdown query");
    }

    private SplitDecision selectAssociation(PlanModels.BindingGraph graph) {
        boolean allGraphEdges = !graph.relationshipNodes().isEmpty()
                && graph.relationshipNodes().stream()
                .allMatch(r -> r.binding().storageType() == MetadataModels.RelationshipStorageType.GRAPH_EDGE);
        if (allGraphEdges && graph.isSingleDatasource()
                && graph.capabilities().values().stream()
                .allMatch(MetadataModels.DatasourceCapability::supportGraphTraversal)) {
            return SplitDecision.of(SplitStrategy.ASSOCIATION_GRAPH_PUSHDOWN,
                    "all relationships are graph edges in one graph datasource");
        }

        boolean allRelational = !graph.relationshipNodes().isEmpty()
                && graph.relationshipNodes().stream()
                .allMatch(r -> r.binding().storageType() == MetadataModels.RelationshipStorageType.RELATIONAL_JOIN_TABLE);
        if (allRelational && graph.isSingleDatasource() && graph.canPushdownJoin()) {
            return SplitDecision.of(SplitStrategy.ASSOCIATION_RELATIONAL_JOIN,
                    "relationship table can be joined by the datasource");
        }
        return SplitDecision.of(SplitStrategy.ASSOCIATION_MULTI_STAGE_ASSEMBLE,
                "association requires staged query and OAC assembly");
    }

    private SplitDecision selectAggregate(PlanModels.BindingGraph graph, OqlModels.OqlQuery query) {
        if (graph.canPushdownAggregation() && (query.aggregateFilter() == null || graph.canPushdownHaving())) {
            return SplitDecision.of(SplitStrategy.AGGREGATE_PUSHDOWN,
                    "aggregation can be pushed down to the datasource");
        }
        if (graph.isCrossDatasource()) {
            return SplitDecision.of(SplitStrategy.AGGREGATE_PARTIAL_PUSHDOWN_MERGE,
                    "cross datasource aggregate requires partial aggregate merge");
        }
        return SplitDecision.of(SplitStrategy.AGGREGATE_MEMORY,
                "aggregate must run inside OAC");
    }
}
