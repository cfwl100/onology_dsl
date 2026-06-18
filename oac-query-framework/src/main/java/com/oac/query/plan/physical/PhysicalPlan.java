package com.oac.query.plan.physical;

import com.oac.query.plan.logical.LogicalPlan;
import com.oac.query.strategy.SplitDecision;
import com.oac.query.strategy.SplitStrategy;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 由 LogicalPlan 和 BindingGraph 派生出的、面向数据源执行的 DAG。
 */
public class PhysicalPlan {
    private final LogicalPlan logicalPlan;
    private final SplitDecision decision;
    private final List<PhysicalPlanNode> nodes = new ArrayList<PhysicalPlanNode>();
    private final List<PhysicalSourceQueryNode> sourceNodes = new ArrayList<PhysicalSourceQueryNode>();
    private final List<FragmentDependency> dependencies = new ArrayList<FragmentDependency>();

    public PhysicalPlan(LogicalPlan logicalPlan, SplitDecision decision) {
        this.logicalPlan = logicalPlan;
        this.decision = decision;
    }

    public LogicalPlan getLogicalPlan() {
        return logicalPlan;
    }

    public SplitDecision getDecision() {
        return decision;
    }

    public SplitStrategy getStrategy() {
        return decision.getStrategy();
    }

    public void addNode(PhysicalPlanNode node) {
        nodes.add(node);
        if (node instanceof PhysicalSourceQueryNode) {
            sourceNodes.add((PhysicalSourceQueryNode) node);
        }
    }

    public void addDependency(FragmentDependency dependency) {
        dependencies.add(dependency);
    }

    public List<PhysicalPlanNode> getNodes() {
        return Collections.unmodifiableList(nodes);
    }

    public List<PhysicalSourceQueryNode> getSourceNodes() {
        return Collections.unmodifiableList(sourceNodes);
    }

    public List<FragmentDependency> getDependencies() {
        return Collections.unmodifiableList(dependencies);
    }

    public PhysicalSourceQueryNode sourceNode(String id) {
        for (PhysicalSourceQueryNode sourceNode : sourceNodes) {
            if (sourceNode.getId().equals(id)) {
                return sourceNode;
            }
        }
        return null;
    }

    public interface PhysicalPlanNode {
        String getId();

        String getNodeType();
    }

    public static class PhysicalMergeJoinNode implements PhysicalPlanNode {
        private final String id;
        private final String joinKey;

        public PhysicalMergeJoinNode(String id) {
            this(id, "rid");
        }

        public PhysicalMergeJoinNode(String id, String joinKey) {
            this.id = id;
            this.joinKey = joinKey;
        }

        public String getId() {
            return id;
        }

        public String getJoinKey() {
            return joinKey;
        }

        public String getNodeType() {
            return "PhysicalMergeJoinNode";
        }
    }

    public static class PhysicalAssociationAssembleNode implements PhysicalPlanNode {
        private final String id;

        public PhysicalAssociationAssembleNode(String id) {
            this.id = id;
        }

        public String getId() {
            return id;
        }

        public String getNodeType() {
            return "PhysicalAssociationAssembleNode";
        }
    }

    public static class PhysicalMemoryAggregateNode implements PhysicalPlanNode {
        private final String id;

        public PhysicalMemoryAggregateNode(String id) {
            this.id = id;
        }

        public String getId() {
            return id;
        }

        public String getNodeType() {
            return "PhysicalMemoryAggregateNode";
        }
    }
}
