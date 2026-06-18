package com.oac.framework.kernel;

import com.oac.query.binding.BindingGraph;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.logical.LogicalPlan;

public interface SplitStrategyEngine {
    StrategyDecision select(OqlQuery query, BindingGraph graph, LogicalPlan logicalPlan, QueryContext context);
}
