package com.oac.framework.kernel;

import com.oac.query.binding.BindingGraph;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.logical.LogicalPlan;
import com.oac.query.validation.ValidationResult;

public interface OperationPlugin {
    OperationType operationType();
    ValidationResult validate(OqlQuery query, QueryContext context);
    LogicalPlan buildLogicalPlan(OqlQuery query, BindingGraph graph, QueryContext context);
    ResultAssembler resultAssembler();
}
