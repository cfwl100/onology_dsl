package com.oac.query.runtime;

import com.oac.query.assembly.OntologyQueryResult;
import com.oac.query.assembly.QueryResultAssembler;
import com.oac.query.binding.BindingResolver;
import com.oac.query.binding.BindingResult;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.logical.LogicalPlan;
import com.oac.query.plan.logical.LogicalPlanBuilder;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.plan.physical.PhysicalPlanBuilder;
import com.oac.query.spi.QueryExtensionRegistry;
import com.oac.query.validation.OqlValidator;
import com.oac.query.validation.ValidationResult;

import java.util.List;

/**
 * OAC 查询流水线的门面入口。
 *
 * 这里刻意保留每个阶段的显式调用：校验、绑定、逻辑规划、物理规划、查询分片执行和结果装配。
 */
public class QueryFrameworkService {
    private final OqlValidator validator;
    private final BindingResolver bindingResolver;
    private final LogicalPlanBuilder logicalPlanBuilder;
    private final PhysicalPlanBuilder physicalPlanBuilder;
    private final QueryExecutionEngine executionEngine;
    private final QueryResultAssembler resultAssembler;

    public QueryFrameworkService() {
        this(new OqlValidator(), new BindingResolver(), new LogicalPlanBuilder(), new PhysicalPlanBuilder(),
                new QueryExecutionEngine(QueryExtensionRegistry.mockDefaults()), new QueryResultAssembler());
    }

    public QueryFrameworkService(OqlValidator validator, BindingResolver bindingResolver, LogicalPlanBuilder logicalPlanBuilder,
                                 PhysicalPlanBuilder physicalPlanBuilder, QueryExecutionEngine executionEngine,
                                 QueryResultAssembler resultAssembler) {
        this.validator = validator;
        this.bindingResolver = bindingResolver;
        this.logicalPlanBuilder = logicalPlanBuilder;
        this.physicalPlanBuilder = physicalPlanBuilder;
        this.executionEngine = executionEngine;
        this.resultAssembler = resultAssembler;
    }

    public OntologyQueryResult run(OqlQuery query, PlannerContext plannerContext, ExecutionContext executionContext) {
        ValidationResult validationResult = validator.validate(query);
        if (!validationResult.isSuccess()) {
            return OntologyQueryResult.failure(validationResult.getErrors(), executionContext.getTraceId());
        }
        BindingResult bindingResult = bindingResolver.resolve(query);
        if (!bindingResult.isSuccess()) {
            return OntologyQueryResult.failure(bindingResult.getErrors(), executionContext.getTraceId());
        }
        LogicalPlan logicalPlan = logicalPlanBuilder.build(query);
        PhysicalPlan physicalPlan = physicalPlanBuilder.build(logicalPlan, query, bindingResult.getGraph());
        List<FragmentResult> fragmentResults = executionEngine.execute(physicalPlan, plannerContext, executionContext);
        return resultAssembler.assemble(query, fragmentResults, executionContext.getTraceId());
    }
}
