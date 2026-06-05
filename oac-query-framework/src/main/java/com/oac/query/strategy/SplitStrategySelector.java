package com.oac.query.strategy;

import com.oac.query.binding.BindingGraph;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.OperationType;

/**
 * 根据操作类型和绑定能力选择粗粒度物理执行策略。
 */
public class SplitStrategySelector {
    public SplitDecision select(OperationType operation, BindingGraph graph, OqlQuery query) {
        if (operation == OperationType.ASSOCIATION_QUERY) {
            return selectAssociation(graph);
        }
        if (operation == OperationType.AGGREGATE) {
            return selectAggregate(graph);
        }
        return selectQuery(graph);
    }

    private SplitDecision selectQuery(BindingGraph graph) {
        if (graph.isSingleDatasource()) {
            if (graph.isSingleTable()) {
                return new SplitDecision(SplitStrategy.SINGLE_SOURCE_SINGLE_TABLE, "single datasource and single table");
            }
            if (graph.canPushdownJoin()) {
                return new SplitDecision(SplitStrategy.SINGLE_SOURCE_MULTI_TABLE_JOIN, "single datasource can push down join");
            }
            return new SplitDecision(SplitStrategy.CROSS_SOURCE_MEMORY_MERGE, "single datasource cannot push down join, use memory merge");
        }
        if (graph.isDependencyRequired()) {
            return new SplitDecision(SplitStrategy.DAG_DEPENDENT_QUERY, "cross datasource query has upstream/downstream dependency");
        }
        return new SplitDecision(SplitStrategy.CROSS_SOURCE_MEMORY_MERGE, "cross datasource without dependency");
    }

    private SplitDecision selectAssociation(BindingGraph graph) {
        if (graph.hasNativeAssociation()) {
            return new SplitDecision(SplitStrategy.ASSOCIATION_GRAPH_PUSHDOWN, "relationship can be pushed down to graph datasource");
        }
        if (graph.isSingleDatasource() && graph.canPushdownJoin()) {
            return new SplitDecision(SplitStrategy.ASSOCIATION_RELATIONAL_JOIN, "relationship can be represented as relational join");
        }
        return new SplitDecision(SplitStrategy.ASSOCIATION_MULTI_STAGE_ASSEMBLE, "relationship requires multi-stage assembly");
    }

    private SplitDecision selectAggregate(BindingGraph graph) {
        if (graph.isDependencyRequired()) {
            return new SplitDecision(SplitStrategy.DAG_DEPENDENT_AGGREGATE, "aggregate input depends on previous fragment");
        }
        if (graph.isSingleDatasource() && graph.canPushdownAggregation() && graph.canPushdownHaving()) {
            return new SplitDecision(SplitStrategy.AGGREGATE_PUSHDOWN, "datasource supports group by and having");
        }
        if (graph.isCrossDatasource() && graph.canPushdownAggregation()) {
            return new SplitDecision(SplitStrategy.AGGREGATE_PARTIAL_PUSHDOWN_MERGE, "partial aggregate can be pushed down and merged");
        }
        return new SplitDecision(SplitStrategy.AGGREGATE_MEMORY, "aggregate must run in OAC memory");
    }
}
