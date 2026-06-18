package com.oac.framework.kernel;

import com.oac.query.binding.BindingGraph;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.validation.ValidationResult;

public interface ResultAssembler {
    boolean supports(OqlQuery query, BindingGraph graph);
    ValidationResult assemble(FragmentResult result, QueryContext context);
}
