package com.oac.framework.kernel;

import com.oac.query.assembly.OntologyQueryResult;
import com.oac.query.binding.BindingResolver;
import com.oac.query.dsl.OqlParser;
import com.oac.query.plan.physical.PhysicalPlanBuilder;
import com.oac.query.validation.OqlError;

public final class QueryKernel {
    private final OqlParser parser;
    private final BindingResolver bindingResolver;
    private final OperationRegistry operationRegistry;
    private final SplitStrategyEngine strategyEngine;
    private final PhysicalPlanBuilder physicalPlanBuilder;
    private final TranslatorRegistry translatorRegistry;
    private final ExecutorRegistry executorRegistry;
    private final AssemblerRegistry assemblerRegistry;
    private final OntologyMetadataProvider metadataProvider;

    private QueryKernel(Builder builder) {
        this.parser = builder.parser;
        this.bindingResolver = builder.bindingResolver;
        this.operationRegistry = builder.operationRegistry;
        this.strategyEngine = builder.strategyEngine;
        this.physicalPlanBuilder = builder.physicalPlanBuilder;
        this.translatorRegistry = builder.translatorRegistry;
        this.executorRegistry = builder.executorRegistry;
        this.assemblerRegistry = builder.assemblerRegistry;
        this.metadataProvider = builder.metadataProvider;
    }

    public OntologyQueryResult execute(String oqlJson, QueryContext context) {
        return OntologyQueryResult.failure(
                java.util.Collections.singletonList(new OqlError("NOT_IMPLEMENTED", "QueryKernel.execute not yet implemented", "")),
                context.traceId()
        );
    }

    public QueryExplain explain(String oqlJson, QueryContext context) {
        return QueryExplain.builder().build();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private OqlParser parser;
        private BindingResolver bindingResolver;
        private OperationRegistry operationRegistry;
        private SplitStrategyEngine strategyEngine;
        private PhysicalPlanBuilder physicalPlanBuilder;
        private TranslatorRegistry translatorRegistry;
        private ExecutorRegistry executorRegistry;
        private AssemblerRegistry assemblerRegistry;
        private OntologyMetadataProvider metadataProvider;

        public Builder parser(OqlParser parser) {
            this.parser = parser;
            return this;
        }

        public Builder bindingResolver(BindingResolver bindingResolver) {
            this.bindingResolver = bindingResolver;
            return this;
        }

        public Builder operationRegistry(OperationRegistry operationRegistry) {
            this.operationRegistry = operationRegistry;
            return this;
        }

        public Builder strategyEngine(SplitStrategyEngine strategyEngine) {
            this.strategyEngine = strategyEngine;
            return this;
        }

        public Builder physicalPlanBuilder(PhysicalPlanBuilder physicalPlanBuilder) {
            this.physicalPlanBuilder = physicalPlanBuilder;
            return this;
        }

        public Builder translatorRegistry(TranslatorRegistry translatorRegistry) {
            this.translatorRegistry = translatorRegistry;
            return this;
        }

        public Builder executorRegistry(ExecutorRegistry executorRegistry) {
            this.executorRegistry = executorRegistry;
            return this;
        }

        public Builder assemblerRegistry(AssemblerRegistry assemblerRegistry) {
            this.assemblerRegistry = assemblerRegistry;
            return this;
        }

        public Builder metadataProvider(OntologyMetadataProvider metadataProvider) {
            this.metadataProvider = metadataProvider;
            return this;
        }

        public QueryKernel build() {
            return new QueryKernel(this);
        }
    }
}
