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
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 将语义层 LogicalPlan 下沉为可执行的数据源查询分片。
 *
 * v1 仍然把条件和返回字段细节保留在 OQL 模型上，因此这里还会传入 OqlQuery；
 * 但 LogicalPlan 是必填参数，用来明确架构链路，并为后续优化器和解释输出提供稳定锚点。
 *
 * <h2>策略实现说明</h2>
 * <ul>
 *   <li>{@link SplitStrategy#SINGLE_SOURCE_SINGLE_TABLE}: 单数据源单表，直接下推</li>
 *   <li>{@link SplitStrategy#SINGLE_SOURCE_MULTI_TABLE_JOIN}: 单数据源多表，数据库 Join 下推</li>
 *   <li>{@link SplitStrategy#CROSS_SOURCE_MEMORY_MERGE}: 跨源无依赖，各源并行查询后内存合并</li>
 *   <li>{@link SplitStrategy#DAG_DEPENDENT_QUERY}: 跨源但前后有依赖，A 输出作为 B 输入</li>
 *   <li>{@link SplitStrategy#ASSOCIATION_GRAPH_PUSHDOWN}: 关联查询，图数据库原生边下推</li>
 *   <li>{@link SplitStrategy#ASSOCIATION_RELATIONAL_JOIN}: 关联查询，SQL 关系表 Join</li>
 *   <li>{@link SplitStrategy#ASSOCIATION_MULTI_STAGE_ASSEMBLE}: 跨源关联或依赖型关联，多阶段装配</li>
 *   <li>{@link SplitStrategy#AGGREGATE_PUSHDOWN}: 聚合可下推到数据库</li>
 *   <li>{@link SplitStrategy#AGGREGATE_PARTIAL_PUSHDOWN_MERGE}: 多源各自局部聚合后内存合并</li>
 *   <li>{@link SplitStrategy#AGGREGATE_MEMORY}: 聚合无法下推，纯 OAC 内存计算</li>
 *   <li>{@link SplitStrategy#DAG_DEPENDENT_AGGREGATE}: 聚合依赖前序 DAG 查询结果</li>
 * </ul>
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

        SplitStrategy strategy = decision.getStrategy();
        switch (strategy) {
            case SINGLE_SOURCE_SINGLE_TABLE:
                buildSingleSourceSingleTable(plan, query, graph);
                break;
            case SINGLE_SOURCE_MULTI_TABLE_JOIN:
                buildSingleSourceMultiTableJoin(plan, query, graph);
                break;
            case CROSS_SOURCE_MEMORY_MERGE:
                buildCrossSourceMemoryMerge(plan, query, graph);
                break;
            case DAG_DEPENDENT_QUERY:
                buildDagDependentQuery(plan, query, graph);
                break;
            case ASSOCIATION_GRAPH_PUSHDOWN:
                buildAssociationGraphPushdown(plan, query, graph);
                break;
            case ASSOCIATION_RELATIONAL_JOIN:
                buildAssociationRelationalJoin(plan, query, graph);
                break;
            case ASSOCIATION_MULTI_STAGE_ASSEMBLE:
                buildAssociationMultiStageAssemble(plan, query, graph);
                break;
            case AGGREGATE_PUSHDOWN:
                buildAggregatePushdown(plan, query, graph);
                break;
            case AGGREGATE_PARTIAL_PUSHDOWN_MERGE:
                buildAggregatePartialPushdownMerge(plan, query, graph);
                break;
            case AGGREGATE_MEMORY:
                buildAggregateMemory(plan, query, graph);
                break;
            case DAG_DEPENDENT_AGGREGATE:
                buildDagDependentAggregate(plan, query, graph);
                break;
            default:
                throw new IllegalStateException("Unsupported strategy: " + strategy);
        }

        return plan;
    }

    /**
     * SINGLE_SOURCE_SINGLE_TABLE: 单数据源单表查询。
     * 生成一个源节点，直接下推到数据库执行。
     */
    private void buildSingleSourceSingleTable(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        if (datasourceIds.isEmpty()) {
            return;
        }
        String datasourceId = datasourceIds.iterator().next();
        PhysicalSourceQueryNode sourceNode = createSourceNode("F1", datasourceId, query, graph);
        plan.addNode(sourceNode);
    }

    /**
     * SINGLE_SOURCE_MULTI_TABLE_JOIN: 单数据源多表 Join 查询。
     * 生成一个源节点（含多表绑定），由数据库执行 Join。
     * 根据设计文档 7.4.2，Join Key 由 dim_cell.cell_id = sdr_cell_kpi.cell_id 推导。
     */
    private void buildSingleSourceMultiTableJoin(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        if (datasourceIds.isEmpty()) {
            return;
        }
        String datasourceId = datasourceIds.iterator().next();
        PhysicalSourceQueryNode sourceNode = createSourceNode("F1", datasourceId, query, graph);
        sourceNode.setPushdownJoin(true);
        plan.addNode(sourceNode);
        String joinKey = determineMergeJoinKey(query, graph);
        plan.addNode(new PhysicalMergeJoinNode("M1", joinKey));
    }

    /**
     * CROSS_SOURCE_MEMORY_MERGE: 跨源无依赖并行查询。
     * 每个数据源生成独立源节点，执行后由 MergeJoinNode 内存合并。
     * 根据设计文档 7.4.3，合并策略为 FIRST_NON_NULL，Join Key 为 cellId。
     */
    private void buildCrossSourceMemoryMerge(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        int index = 1;
        for (String datasourceId : datasourceIds) {
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + index++, datasourceId, query, graph);
            plan.addNode(sourceNode);
        }
        if (plan.getSourceNodes().size() > 1) {
            String joinKey = determineMergeJoinKey(query, graph);
            plan.addNode(new PhysicalMergeJoinNode("M1", joinKey));
        }
    }

    /**
     * DAG_DEPENDENT_QUERY: 跨源有依赖的 DAG 查询。
     * 前一个源节点的输出作为后续源节点的输入条件。
     * 根据设计文档 7.4.10，FragmentDependency 指定 A.rows[*].cellId -> B.cell_id IN (...)。
     * 执行时由 DagInputResolver 提取上游输出字段，注入到下游动态输入条件。
     */
    private void buildDagDependentQuery(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        List<String> datasourceIdList = new ArrayList<String>(datasourceIds);
        for (int i = 0; i < datasourceIdList.size(); i++) {
            String datasourceId = datasourceIdList.get(i);
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + (i + 1), datasourceId, query, graph);
            if (i > 0) {
                sourceNode.setUpstreamNodeId("F" + i);
            }
            plan.addNode(sourceNode);
        }
        if (plan.getSourceNodes().size() >= 2) {
            buildFragmentDependencies(plan, query, graph);
        }
    }

    /**
     * ASSOCIATION_GRAPH_PUSHDOWN: 关联查询，图数据库原生边下推。
     * 关系由图数据库原生边表示，直接下推到图数据库执行。
     */
    private void buildAssociationGraphPushdown(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        int index = 1;
        for (String datasourceId : datasourceIds) {
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + index++, datasourceId, query, graph);
            sourceNode.setNativeAssociation(true);
            plan.addNode(sourceNode);
        }
        plan.addNode(new PhysicalAssociationAssembleNode("R1"));
    }

    /**
     * ASSOCIATION_RELATIONAL_JOIN: 关联查询，SQL 关系表 Join。
     * 关系表示为外键关联，由数据库执行 Join。
     */
    private void buildAssociationRelationalJoin(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        if (datasourceIds.isEmpty()) {
            return;
        }
        String datasourceId = datasourceIds.iterator().next();
        PhysicalSourceQueryNode sourceNode = createSourceNode("F1", datasourceId, query, graph);
        sourceNode.setPushdownJoin(true);
        plan.addNode(sourceNode);
        plan.addNode(new PhysicalAssociationAssembleNode("R1"));
    }

    /**
     * ASSOCIATION_MULTI_STAGE_ASSEMBLE: 跨源关联或依赖型关联，多阶段装配。
     * 多个数据源分别查询，然后由 AssociationAssembleNode 组装结果。
     * 根据设计文档 7.4.6，当关系跨越多个数据源时（如 MySQL -> API），
     * 第一阶段结果作为第二阶段的动态输入（path.gridId = 上游 gridId）。
     */
    private void buildAssociationMultiStageAssemble(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        int index = 1;
        for (String datasourceId : datasourceIds) {
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + index, datasourceId, query, graph);
            if (index > 1) {
                sourceNode.setUpstreamNodeId("F" + (index - 1));
                sourceNode.setPath("path." + determineMergeJoinKey(query, graph));
            }
            plan.addNode(sourceNode);
            index++;
        }
        plan.addNode(new PhysicalAssociationAssembleNode("R1"));
        if (graph.isDependencyRequired() && plan.getSourceNodes().size() >= 2) {
            buildFragmentDependencies(plan, query, graph);
        }
    }

    /**
     * AGGREGATE_PUSHDOWN: 聚合查询可下推到数据库。
     * GROUP BY 和 HAVING 都在数据库执行，OAC 只做结果装配。
     */
    private void buildAggregatePushdown(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        if (datasourceIds.isEmpty()) {
            return;
        }
        String datasourceId = datasourceIds.iterator().next();
        PhysicalSourceQueryNode sourceNode = createSourceNode("F1", datasourceId, query, graph);
        sourceNode.setPushdownAggregation(true);
        sourceNode.setPushdownHaving(true);
        plan.addNode(sourceNode);
    }

    /**
     * AGGREGATE_PARTIAL_PUSHDOWN_MERGE: 多源局部聚合后内存合并。
     * 各数据源先执行局部聚合（使用 SUM/COUNT 代替 AVG），然后由 MemoryAggregateNode 合并最终结果。
     * 用于跨源聚合场景，如跨 MySQL 和 ES 的 AVG 计算。
     * 根据设计文档 7.4.8，各数据源执行局部聚合后，最终 AVG = totalSum / totalCount。
     */
    private void buildAggregatePartialPushdownMerge(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        int index = 1;
        for (String datasourceId : datasourceIds) {
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + index++, datasourceId, query, graph);
            sourceNode.setPushdownAggregation(true);
            sourceNode.setPartialAggregate(true);
            plan.addNode(sourceNode);
        }
        plan.addNode(new PhysicalMemoryAggregateNode("A1"));
    }

    /**
     * AGGREGATE_MEMORY: 聚合无法下推，纯 OAC 内存计算。
     * 各数据源只做明细查询，所有聚合在 OAC 内存中完成。
     */
    private void buildAggregateMemory(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        int index = 1;
        for (String datasourceId : datasourceIds) {
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + index++, datasourceId, query, graph);
            plan.addNode(sourceNode);
        }
        plan.addNode(new PhysicalMemoryAggregateNode("A1"));
    }

    /**
     * DAG_DEPENDENT_AGGREGATE: 聚合依赖前序 DAG 查询结果。
     * 根据设计文档 7.4.11，先执行上游图查询获取 cellId 列表，
     * 再由下游 SQL 执行聚合查询 WHERE cell_id IN (...),
     * 聚合下推到数据库（HAVING AVG(prb_usage) > ?）。
     */
    private void buildDagDependentAggregate(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        Set<String> datasourceIds = graph.datasourceIds();
        List<String> datasourceIdList = new ArrayList<String>(datasourceIds);
        for (int i = 0; i < datasourceIdList.size(); i++) {
            String datasourceId = datasourceIdList.get(i);
            PhysicalSourceQueryNode sourceNode = createSourceNode("F" + (i + 1), datasourceId, query, graph);
            if (i > 0) {
                sourceNode.setUpstreamNodeId("F" + i);
                sourceNode.setPushdownAggregation(true);
                sourceNode.setPushdownHaving(true);
            }
            plan.addNode(sourceNode);
        }
        if (plan.getSourceNodes().size() >= 2) {
            buildFragmentDependencies(plan, query, graph);
        }
    }

    /**
     * 构建 FragmentDependency 依赖关系。
     * 假设第一个源节点为上游，后续源节点依赖其输出。
     */
    private void buildFragmentDependencies(PhysicalPlan plan, OqlQuery query, BindingGraph graph) {
        List<PhysicalSourceQueryNode> sourceNodes = plan.getSourceNodes();
        if (sourceNodes.size() < 2) {
            return;
        }
        PhysicalSourceQueryNode upstream = sourceNodes.get(0);
        Map<String, BindingGraph.RelationshipBinding> relationshipBindings = graph.getRelationshipBindings();
        String outputField = determineUpstreamOutputField(query, graph);
        String inputField = determineDownstreamInputField(query, graph);
        for (int i = 1; i < sourceNodes.size(); i++) {
            PhysicalSourceQueryNode downstream = sourceNodes.get(i);
            plan.addDependency(new FragmentDependency(
                    upstream.getId(),
                    outputField,
                    downstream.getId(),
                    inputField,
                    InputOperator.IN,
                    true,
                    1000
            ));
        }
    }

    private String determineUpstreamOutputField(OqlQuery query, BindingGraph graph) {
        List<ObjectDecl> objects = query.getObjects();
        if (!objects.isEmpty()) {
            ObjectDecl firstObject = objects.get(0);
            BindingGraph.ObjectBinding objectBinding = graph.objectBinding(firstObject.getAlias());
            if (objectBinding != null) {
                for (BindingGraph.FieldBinding field : objectBinding.getFieldBindings().values()) {
                    if ("cellId".equalsIgnoreCase(field.getLogicalField()) || "id".equalsIgnoreCase(field.getLogicalField())) {
                        return field.getLogicalField();
                    }
                }
            }
        }
        return "cellId";
    }

    private String determineDownstreamInputField(OqlQuery query, BindingGraph graph) {
        return "cell_id";
    }

    private String determineMergeJoinKey(OqlQuery query, BindingGraph graph) {
        List<ObjectDecl> objects = query.getObjects();
        if (!objects.isEmpty()) {
            ObjectDecl firstObject = objects.get(0);
            BindingGraph.ObjectBinding objectBinding = graph.objectBinding(firstObject.getAlias());
            if (objectBinding != null) {
                for (BindingGraph.FieldBinding field : objectBinding.getFieldBindings().values()) {
                    String logicalField = field.getLogicalField();
                    if ("cellId".equalsIgnoreCase(logicalField) || "id".equalsIgnoreCase(logicalField)) {
                        return logicalField;
                    }
                }
            }
        }
        return "rid";
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
