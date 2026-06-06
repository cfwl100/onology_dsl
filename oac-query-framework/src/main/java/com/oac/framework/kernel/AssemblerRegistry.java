package com.oac.framework.kernel;

import com.oac.query.binding.BindingGraph;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.validation.ValidationResult;

public interface AssemblerRegistry {
    void register(ResultAssembler assembler);
    ResultAssembler find(OqlQuery query, BindingGraph graph, PhysicalPlan plan);
}
