package com.oac.query.plan.logical;

import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.ObjectDecl;
import com.oac.query.dsl.OqlQuery.OperationType;
import com.oac.query.plan.logical.LogicalPlan.SimpleLogicalNode;

/**
 * 将已通过校验的 OQL 转换为与数据源无关的逻辑计划。
 *
 * 构建器为每个语义步骤保留一个节点，使物理规划器无需反复检查 OQL 字段组合，
 * 就能判断查询形态。
 */
public class LogicalPlanBuilder {
    public LogicalPlan build(OqlQuery query) {
        LogicalPlan plan = new LogicalPlan(query.getOperation());
        int index = 1;
        for (ObjectDecl object : query.getObjects()) {
            plan.addNode(new SimpleLogicalNode("L" + index++, "LogicalScanNode", object.getAlias() + ":" + object.getObjectType()));
        }
        if (query.getConditions() != null) {
            plan.addNode(new SimpleLogicalNode("L" + index++, "LogicalFilterNode", "conditions"));
        }
        if (query.getOperation() == OperationType.ASSOCIATION_QUERY) {
            plan.addNode(new SimpleLogicalNode("L" + index++, "LogicalAssociationNode", "relationships"));
        }
        if (query.getOperation() == OperationType.AGGREGATE) {
            plan.addNode(new SimpleLogicalNode("L" + index++, "LogicalAggregateNode", "returns metrics"));
        } else {
            plan.addNode(new SimpleLogicalNode("L" + index++, "LogicalProjectNode", "returns fields"));
        }
        if (!query.getOrders().isEmpty()) {
            plan.addNode(new SimpleLogicalNode("L" + index++, "LogicalOrderNode", "orders"));
        }
        if (query.getMaxResults() != null) {
            plan.addNode(new SimpleLogicalNode("L" + index, "LogicalLimitNode", "maxResults"));
        }
        return plan;
    }
}
