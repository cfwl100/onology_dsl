package com.oac.query.plan.logical;

import com.oac.query.dsl.OqlQuery.OperationType;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 由规范化 OQL 生成的语义查询计划。
 *
 * LogicalPlan 刻意保持与数据源无关：它只描述扫描、过滤、投影、关联和聚合
 * 等查询意图；PhysicalPlan 再决定这些意图如何拆分到具体数据源。
 */
public class LogicalPlan {
    private final OperationType operation;
    private final List<LogicalPlanNode> nodes = new ArrayList<LogicalPlanNode>();

    public LogicalPlan(OperationType operation) {
        this.operation = operation;
    }

    public OperationType getOperation() {
        return operation;
    }

    public void addNode(LogicalPlanNode node) {
        nodes.add(node);
    }

    public List<LogicalPlanNode> getNodes() {
        return Collections.unmodifiableList(nodes);
    }

    public boolean hasNodeType(String type) {
        for (LogicalPlanNode node : nodes) {
            if (node.getType().equals(type)) {
                return true;
            }
        }
        return false;
    }

    public interface LogicalPlanNode {
        String getId();

        String getType();

        String getDescription();
    }

    public static class SimpleLogicalNode implements LogicalPlanNode {
        private final String id;
        private final String type;
        private final String description;

        public SimpleLogicalNode(String id, String type, String description) {
            this.id = id;
            this.type = type;
            this.description = description;
        }

        public String getId() {
            return id;
        }

        public String getType() {
            return type;
        }

        public String getDescription() {
            return description;
        }
    }
}
