package com.onology.oac.queryframework.service;

import com.onology.oac.queryframework.assembler.ObjectAssembler;
import com.onology.oac.queryframework.core.BindingResolver;
import com.onology.oac.queryframework.core.OqlValidator;
import com.onology.oac.queryframework.core.PhysicalPlanBuilder;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.ResultModels.OacError;
import com.onology.oac.queryframework.domain.ResultModels.OntologyQueryResult;
import com.onology.oac.queryframework.executor.QueryExecutionEngine;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.ExecutionContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;

import java.util.List;

/** Facade that wires validation, binding, planning, execution and assembly. */
public class QueryFrameworkService {
    private final OqlValidator validator;
    private final BindingResolver bindingResolver;
    private final PhysicalPlanBuilder physicalPlanBuilder;
    private final QueryExecutionEngine executionEngine;
    private final ObjectAssembler objectAssembler;

    public QueryFrameworkService(OqlValidator validator,
                                 BindingResolver bindingResolver,
                                 PhysicalPlanBuilder physicalPlanBuilder,
                                 QueryExecutionEngine executionEngine,
                                 ObjectAssembler objectAssembler) {
        this.validator = validator;
        this.bindingResolver = bindingResolver;
        this.physicalPlanBuilder = physicalPlanBuilder;
        this.executionEngine = executionEngine;
        this.objectAssembler = objectAssembler;
    }

    public OntologyQueryResult run(OqlModels.OqlQuery query,
                                   PlannerContext plannerContext,
                                   ExecutionContext executionContext) {
        OqlValidator.ValidationResult validation = validator.validate(query);
        if (!validation.isSuccess()) {
            return OntologyQueryResult.failed(validation.errors());
        }
        BindingResolver.BindingResult binding = bindingResolver.resolve(query);
        if (!binding.isSuccess()) {
            return OntologyQueryResult.failed(binding.errors());
        }
        var physicalPlan = physicalPlanBuilder.build(query, binding.bindingGraph());
        QueryExecutionEngine.ExecutionResult execution = executionEngine.execute(physicalPlan, plannerContext, executionContext);
        if (!execution.isSuccess()) {
            return OntologyQueryResult.failed(execution.errors());
        }
        return OntologyQueryResult.success(objectAssembler.assemble(execution.fragmentResults()), List.of(), List.of(), null);
    }
}
