package com.oac.query.plan.physical;

import com.oac.query.binding.BindingGraph;
import com.oac.query.binding.BindingGraph.FieldBinding;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.ObjectDecl;
import com.oac.query.plan.logical.LogicalPlan;
import com.oac.query.plan.physical.FragmentDependency.InputOperator;
import com.oac.query.plan.physical.PhysicalPlan.PhysicalAssociationAssembleNode;
import com.oac.query.plan.physical.PhysicalPlan.PhysicalMemoryAggregateNode;
import com.oac.query.plan.physical.PhysicalPlan.PhysicalMergeJoinNode;
import com.oac.query.strategy.SplitDecision;
import com.oac.query.strategy.SplitStrategy;
import com.oac.query.strategy.SplitStrategySelector;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 将语义层 LogicalPlan 下沉为可执行的数据源查询分片。
 *
 * v1 仍然把条件和返回字段细节保留在 OQL 模型上，因此这里还会传入 OqlQuery；
 * 但 LogicalPlan 是必填参数，用来明确架构链路，并为后续优化器和解释输出提供稳定锚点。
 */
public class PhysicalPlanBuilder {
    private final SplitStrategySelector strategySelector;

    public PhysicalPlanBuilder() {
        this(new SplitStrategySelector());
    }

    public PhysicalPlanBuilder(SplitStrategySelector strategySelector) {
        this.strategySelector = strategySelector;
    }

    public PhysicalPlan build(LogicalPlan logicalPlan, OqlQuery query, BindingGraph graph) {
        if (logicalPlan == null) {
            throw new IllegalArgumentException("logicalPlan must not be null");
        }
        if (logicalPlan.getOperation() != query.getOperation()) {
            throw new IllegalArgumentException("logicalPlan operation must match OQL operation");
        }
        SplitDecision decision = strategySelector.select(logicalPlan.getOperation(), graph, query);
        PhysicalPlan plan = new PhysicalPlan(logicalPlan, decision);
        int index = 1;
        Set<String> datasourceIds = graph.datasourceIds();
        for (String datasourceId : datasourceIds) {
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + index++, datasourceId, query, graph);
            plan.addNode(sourceNode);
        }
        // 非源节点由策略和逻辑形态共同决定：
        // 策略说明工作放在哪里执行，逻辑计划说明有哪些语义算子。
        if (decision.getStrategy() == SplitStrategy.CROSS_SOURCE_MEMORY_MERGE
                || decision.getStrategy() == SplitStrategy.SINGLE_SOURCE_MULTI_TABLE_JOIN) {
            plan.addNode(new PhysicalMergeJoinNode("M1"));
        }
        if (logicalPlan.hasNodeType("LogicalAggregateNode")
                && (decision.getStrategy() == SplitStrategy.AGGREGATE_MEMORY
                || decision.getStrategy() == SplitStrategy.AGGREGATE_PARTIAL_PUSHDOWN_MERGE)) {
            plan.addNode(new PhysicalMemoryAggregateNode("A1"));
        }
        if (logicalPlan.hasNodeType("LogicalAssociationNode")
                && (decision.getStrategy() == SplitStrategy.ASSOCIATION_MULTI_STAGE_ASSEMBLE
                || decision.getStrategy() == SplitStrategy.ASSOCIATION_RELATIONAL_JOIN
                || decision.getStrategy() == SplitStrategy.ASSOCIATION_GRAPH_PUSHDOWN)) {
            plan.addNode(new PhysicalAssociationAssembleNode("R1"));
        }
        if ((decision.getStrategy() == SplitStrategy.DAG_DEPENDENT_QUERY
                || decision.getStrategy() == SplitStrategy.DAG_DEPENDENT_AGGREGATE)
                && plan.getSourceNodes().size() >= 2) {
            PhysicalSourceQueryNode upstream = plan.getSourceNodes().get(0);
            PhysicalSourceQueryNode downstream = plan.getSourceNodes().get(1);
            plan.addDependency(new FragmentDependency(upstream.getId(), "cellId", downstream.getId(), "cell_id", InputOperator.IN, true, 1000));
        }
        return plan;
    }

    private PhysicalSourceQueryNode createSourceNode(String id, String datasourceId, OqlQuery query, BindingGraph graph) {
        List<FieldBinding> fieldBindings = graph.fieldBindingsForDatasource(datasourceId);
        FieldBinding first = fieldBindings.isEmpty() ? null : fieldBindings.get(0);
        String objectAlias = query.getObjects().isEmpty() ? "o" : query.getObjects().get(0).getAlias();
        String objectType = query.getObjects().isEmpty() ? "Unknown" : query.getObjects().get(0).getObjectType();
        for (ObjectDecl object : query.getObjects()) {
            BindingGraph.ObjectBinding objectBinding = graph.objectBinding(object.getAlias());
            if (objectBinding != null) {
                for (FieldBinding binding : objectBinding.getFieldBindings().values()) {
                    if (datasourceId.equals(binding.getDatasourceId())) {
                        objectAlias = object.getAlias();
                        objectType = object.getObjectType();
                        break;
                    }
                }
            }
        }
        List<PhysicalFieldBinding> sourceFieldBindings = sourceFieldBindingsFor(datasourceId, graph);
        List<String> projections = projectionsFor(datasourceId, graph, query);
        return new PhysicalSourceQueryNode(id, datasourceId, first == null ? graph.primaryType() : first.getDatasourceType(),
                objectAlias, objectType, projections, query.getConditions(), sourceFieldBindings,
                query.getOperation(), query.getReturns(), query.getAggregateFilter(), query.getOrders(), query.getMaxResults());
    }

    private List<PhysicalFieldBinding> sourceFieldBindingsFor(String datasourceId, BindingGraph graph) {
        List<PhysicalFieldBinding> bindings = new ArrayList<PhysicalFieldBinding>();
        for (Map.Entry<String, BindingGraph.ObjectBinding> objectEntry : graph.getObjectBindings().entrySet()) {
            String objectAlias = objectEntry.getKey();
            for (FieldBinding binding : objectEntry.getValue().getFieldBindings().values()) {
                if (datasourceId.equals(binding.getDatasourceId())) {
                    bindings.add(new PhysicalFieldBinding(objectAlias, binding));
                }
            }
        }
        return bindings;
    }

    private List<String> projectionsFor(String datasourceId, BindingGraph graph, OqlQuery query) {
        Set<String> available = new LinkedHashSet<String>();
        for (FieldBinding binding : graph.fieldBindingsForDatasource(datasourceId)) {
            available.add(binding.getLogicalField());
        }
        List<String> requested = OqlQuery.fieldReturns(query.getReturns());
        Set<String> projections = new LinkedHashSet<String>();
        if (requested.isEmpty()) {
            projections.addAll(available);
        } else {
            for (String field : requested) {
                if (available.contains(field)) {
                    projections.add(field);
                }
            }
        }
        if (projections.isEmpty()) {
            projections.add("rid");
        }
        return new ArrayList<String>(projections);
    }
}
