package com.onology.oac.queryframework.example;

import com.onology.oac.queryframework.assembler.ObjectAssembler;
import com.onology.oac.queryframework.core.BindingResolver;
import com.onology.oac.queryframework.core.OqlValidator;
import com.onology.oac.queryframework.core.PhysicalPlanBuilder;
import com.onology.oac.queryframework.core.SplitStrategySelector;
import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.executor.QueryExecutionEngine;
import com.onology.oac.queryframework.mock.SourceExecutor;
import com.onology.oac.queryframework.mock.SourceTranslator;
import com.onology.oac.queryframework.registry.QueryExtensionRegistry;
import com.onology.oac.queryframework.service.QueryFrameworkService;

import java.util.List;

/** Factory showing how to wire the query framework with example metadata and mock execution. */
public final class QueryFrameworkExample {
    private QueryFrameworkExample() {
    }

    public static QueryFrameworkService createMockService() {
        ExampleMetadata metadata = new ExampleMetadata();
        QueryExtensionRegistry registry = new QueryExtensionRegistry(
                List.of(new SourceTranslator(DatasourceType.MYSQL)),
                List.of(new SourceExecutor(DatasourceType.MYSQL)));
        return new QueryFrameworkService(
                new OqlValidator(),
                new BindingResolver(metadata, metadata, metadata),
                new PhysicalPlanBuilder(new SplitStrategySelector()),
                new QueryExecutionEngine(registry),
                new ObjectAssembler());
    }
}
