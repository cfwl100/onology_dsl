package com.onology.oac.queryframework.core;

import com.onology.oac.queryframework.domain.MetadataModels;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.PlanModels;
import com.onology.oac.queryframework.domain.PlanModels.SplitDecision;
import com.onology.oac.queryframework.domain.PlanModels.SplitStrategy;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Builds a datasource-level physical plan from OQL and BindingGraph. */
public class PhysicalPlanBuilder {
    private final SplitStrategySelector splitStrategySelector;

    public PhysicalPlanBuilder(SplitStrategySelector splitStrategySelector) {
        this.splitStrategySelector = splitStrategySelector;
    }

    public PlanModels.PhysicalPlan build(OqlModels.OqlQuery query, PlanModels.BindingGraph graph) {
        SplitDecision decision = splitStrategySelector.select(query.operation(), graph, query);
        Map<String, List<PlanModels.PropertyBindingNode>> props = graph.propertyNodes().stream()
                .collect(Collectors.groupingBy(p -> p.binding().datasourceId(), LinkedHashMap::new, Collectors.toList()));
        Map<String, List<PlanModels.RelationshipBindingNode>> rels = graph.relationshipNodes().stream()
                .collect(Collectors.groupingBy(r -> r.binding().datasourceId(), LinkedHashMap::new, Collectors.toList()));

        List<PlanModels.PhysicalPlanNode> nodes = new ArrayList<>();
        int index = 1;
        for (String sourceId : graph.datasourceIds()) {
            MetadataModels.DatasourceType sourceType = graph.capabilities().containsKey(sourceId)
                    ? graph.capabilities().get(sourceId).datasourceType()
                    : null;
            nodes.add(new PlanModels.PhysicalSourceQueryNode(
                    "P" + index++, List.of(), sourceId, sourceType,
                    props.getOrDefault(sourceId, List.of()),
                    rels.getOrDefault(sourceId, List.of()),
                    query.conditions(), query.returns(), query.aggregateFilter(), query.orders(), query.maxResults()));
        }

        String root = nodes.isEmpty() ? null : nodes.get(nodes.size() - 1).nodeId();
        if (decision.strategy() == SplitStrategy.CROSS_SOURCE_MEMORY_MERGE
                || decision.strategy() == SplitStrategy.CROSS_SOURCE_FRAGMENT_QUERY) {
            root = appendMerge(nodes, index++);
        } else if (decision.strategy() == SplitStrategy.ASSOCIATION_MULTI_STAGE_ASSEMBLE) {
            root = appendAssociation(nodes, index++);
        } else if (decision.strategy() == SplitStrategy.AGGREGATE_MEMORY) {
            root = appendAggregate(nodes, index++, query.aggregateFilter());
        }
        return new PlanModels.PhysicalPlan(query.operation(), decision, nodes, root);
    }

    private String appendMerge(List<PlanModels.PhysicalPlanNode> nodes, int index) {
        String nodeId = "P" + index;
        nodes.add(new PlanModels.PhysicalMergeJoinNode(nodeId,
                nodes.stream().map(PlanModels.PhysicalPlanNode::nodeId).toList(), List.of("rid")));
        return nodeId;
    }

    private String appendAssociation(List<PlanModels.PhysicalPlanNode> nodes, int index) {
        String nodeId = "P" + index;
        nodes.add(new PlanModels.PhysicalAssociationAssembleNode(nodeId,
                nodes.stream().map(PlanModels.PhysicalPlanNode::nodeId).toList()));
        return nodeId;
    }

    private String appendAggregate(List<PlanModels.PhysicalPlanNode> nodes, int index, OqlModels.OqlAggregateFilter filter) {
        String nodeId = "P" + index;
        nodes.add(new PlanModels.PhysicalMemoryAggregateNode(nodeId,
                nodes.stream().map(PlanModels.PhysicalPlanNode::nodeId).toList(), filter));
        return nodeId;
    }
}
