package com.onology.oac.queryframework.domain;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceCapability;
import com.onology.oac.queryframework.domain.MetadataModels.PropertyBinding;
import com.onology.oac.queryframework.domain.MetadataModels.RelationshipBinding;
import com.onology.oac.queryframework.domain.OqlModels.OperationType;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Binding graph and query plan models.
 */
public final class PlanModels {
    private PlanModels() {
    }

    public record BindingGraph(
            List<ObjectBindingNode> objectNodes,
            List<PropertyBindingNode> propertyNodes,
            List<RelationshipBindingNode> relationshipNodes,
            List<PhysicalBindingNode> physicalNodes,
            List<BindingEdge> edges,
            Map<String, DatasourceCapability> capabilities
    ) {
        public boolean isSingleDatasource() {
            return datasourceIds().size() <= 1;
        }

        public boolean isCrossDatasource() {
            return datasourceIds().size() > 1;
        }

        public boolean isSingleDatabase() {
            return distinctPhysicalValues(PhysicalBindingNode::databaseName).size() <= 1;
        }

        public boolean isSingleSchema() {
            return distinctPhysicalValues(PhysicalBindingNode::schemaName).size() <= 1;
        }

        public boolean isSingleTable() {
            return distinctPhysicalValues(PhysicalBindingNode::tableName).size() <= 1;
        }

        public boolean requiresJoin() {
            return !isSingleTable() || !relationshipNodes.isEmpty();
        }

        public boolean requiresMemoryMerge() {
            return isCrossDatasource() || !canPushdownJoin();
        }

        public boolean canPushdownFilter() {
            return capabilities.values().stream().allMatch(DatasourceCapability::supportPredicatePushdown);
        }

        public boolean canPushdownOrder() {
            return capabilities.values().stream().allMatch(DatasourceCapability::supportOrderBy);
        }

        public boolean canPushdownAggregation() {
            return isSingleDatasource()
                    && capabilities.values().stream().allMatch(c -> c.supportAggregation() && c.supportGroupBy());
        }

        public boolean canPushdownHaving() {
            return isSingleDatasource() && capabilities.values().stream().allMatch(DatasourceCapability::supportHaving);
        }

        public boolean canPushdownJoin() {
            return isSingleDatasource() && capabilities.values().stream().allMatch(DatasourceCapability::supportJoin);
        }

        public Set<String> datasourceIds() {
            Set<String> ids = new LinkedHashSet<>();
            for (PhysicalBindingNode physicalNode : physicalNodes) {
                if (physicalNode.datasourceId() != null) {
                    ids.add(physicalNode.datasourceId());
                }
            }
            for (RelationshipBindingNode relationNode : relationshipNodes) {
                if (relationNode.binding().datasourceId() != null) {
                    ids.add(relationNode.binding().datasourceId());
                }
            }
            return ids;
        }

        private Set<String> distinctPhysicalValues(PhysicalValueExtractor extractor) {
            Set<String> values = new LinkedHashSet<>();
            for (PhysicalBindingNode node : physicalNodes) {
                String value = extractor.extract(node);
                if (value != null && !value.isBlank()) {
                    values.add(value);
                }
            }
            return values;
        }
    }

    @FunctionalInterface
    private interface PhysicalValueExtractor {
        String extract(PhysicalBindingNode node);
    }

    public record ObjectBindingNode(String alias, String objectType) {
    }

    public record PropertyBindingNode(String alias, String objectType, String propertyName, PropertyBinding binding) {
    }

    public record RelationshipBindingNode(String alias, RelationshipBinding binding) {
    }

    public record PhysicalBindingNode(
            String datasourceId,
            MetadataModels.DatasourceType datasourceType,
            String databaseName,
            String schemaName,
            String tableName,
            String fieldName
    ) {
        public static PhysicalBindingNode from(PropertyBinding binding) {
            return new PhysicalBindingNode(binding.datasourceId(), binding.datasourceType(), binding.databaseName(),
                    binding.schemaName(), binding.tableName(), binding.fieldName());
        }
    }

    public record BindingEdge(String fromNodeId, String toNodeId, String edgeType) {
    }

    public interface LogicalPlanNode {
        String nodeId();

        List<String> children();
    }

    public record LogicalPlan(OperationType operationType, List<LogicalPlanNode> nodes, String rootNodeId) {
    }

    public record LogicalScanNode(String nodeId, List<String> children, String objectAlias, String objectType)
            implements LogicalPlanNode {
    }

    public record LogicalProjectNode(String nodeId, List<String> children, List<String> projectedAliases)
            implements LogicalPlanNode {
    }

    public record LogicalFilterNode(String nodeId, List<String> children, OqlModels.OqlCondition condition)
            implements LogicalPlanNode {
    }

    public record LogicalAssociationNode(String nodeId, List<String> children, List<OqlModels.OqlRelationship> relationships)
            implements LogicalPlanNode {
    }

    public record LogicalAggregateNode(
            String nodeId,
            List<String> children,
            List<OqlModels.OqlReturnItem> aggregateReturns,
            OqlModels.OqlAggregateFilter aggregateFilter
    ) implements LogicalPlanNode {
    }

    public record LogicalOrderNode(String nodeId, List<String> children, List<OqlModels.OqlOrder> orders)
            implements LogicalPlanNode {
    }

    public record LogicalLimitNode(String nodeId, List<String> children, OqlModels.OqlMaxResults maxResults)
            implements LogicalPlanNode {
    }

    public enum SplitStrategy {
        SINGLE_SOURCE_SINGLE_TABLE,
        SINGLE_SOURCE_MULTI_TABLE_JOIN,
        SINGLE_SOURCE_MULTI_SCHEMA_JOIN,
        SINGLE_SOURCE_MULTI_DATABASE_JOIN,
        SINGLE_SOURCE_GRAPH_TRAVERSAL,
        CROSS_SOURCE_FRAGMENT_QUERY,
        CROSS_SOURCE_MEMORY_MERGE,
        ASSOCIATION_GRAPH_PUSHDOWN,
        ASSOCIATION_RELATIONAL_JOIN,
        ASSOCIATION_PROPERTY_REFERENCE,
        ASSOCIATION_MULTI_STAGE_ASSEMBLE,
        AGGREGATE_PUSHDOWN,
        AGGREGATE_PARTIAL_PUSHDOWN_MERGE,
        AGGREGATE_MEMORY
    }

    public record SplitDecision(SplitStrategy strategy, List<String> reasons) {
        public static SplitDecision of(SplitStrategy strategy, String reason) {
            return new SplitDecision(strategy, List.of(reason));
        }
    }

    public interface PhysicalPlanNode {
        String nodeId();

        List<String> children();
    }

    public record PhysicalPlan(OperationType operationType, SplitDecision splitDecision, List<PhysicalPlanNode> nodes,
                               String rootNodeId) {
        public List<PhysicalSourceQueryNode> sourceNodes() {
            List<PhysicalSourceQueryNode> result = new ArrayList<>();
            for (PhysicalPlanNode node : nodes) {
                if (node instanceof PhysicalSourceQueryNode sourceQueryNode) {
                    result.add(sourceQueryNode);
                }
            }
            return result;
        }
    }

    public record PhysicalSourceQueryNode(
            String nodeId,
            List<String> children,
            String datasourceId,
            MetadataModels.DatasourceType datasourceType,
            List<PropertyBindingNode> properties,
            List<RelationshipBindingNode> relationships,
            OqlModels.OqlCondition condition,
            List<OqlModels.OqlReturnItem> returns,
            OqlModels.OqlAggregateFilter aggregateFilter,
            List<OqlModels.OqlOrder> orders,
            OqlModels.OqlMaxResults maxResults
    ) implements PhysicalPlanNode {
    }

    public record PhysicalMergeJoinNode(String nodeId, List<String> children, List<String> joinKeys)
            implements PhysicalPlanNode {
    }

    public record PhysicalAssociationAssembleNode(String nodeId, List<String> children)
            implements PhysicalPlanNode {
    }

    public record PhysicalMemoryAggregateNode(String nodeId, List<String> children, OqlModels.OqlAggregateFilter filter)
            implements PhysicalPlanNode {
    }
}
