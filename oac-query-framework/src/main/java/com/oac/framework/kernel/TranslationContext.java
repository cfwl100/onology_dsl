package com.oac.framework.kernel;

public class TranslationContext {
    private final QueryContext queryContext;
    private final DagRuntimeContext dagRuntimeContext;
    private final FunctionRegistry functionRegistry;

    public TranslationContext(QueryContext queryContext, DagRuntimeContext dagRuntimeContext, FunctionRegistry functionRegistry) {
        this.queryContext = queryContext;
        this.dagRuntimeContext = dagRuntimeContext;
        this.functionRegistry = functionRegistry;
    }

    public QueryContext queryContext() {
        return queryContext;
    }

    public DagRuntimeContext dagRuntimeContext() {
        return dagRuntimeContext;
    }

    public FunctionRegistry functionRegistry() {
        return functionRegistry;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private QueryContext queryContext;
        private DagRuntimeContext dagRuntimeContext;
        private FunctionRegistry functionRegistry;

        public Builder queryContext(QueryContext queryContext) {
            this.queryContext = queryContext;
            return this;
        }

        public Builder dagRuntimeContext(DagRuntimeContext dagRuntimeContext) {
            this.dagRuntimeContext = dagRuntimeContext;
            return this;
        }

        public Builder functionRegistry(FunctionRegistry functionRegistry) {
            this.functionRegistry = functionRegistry;
            return this;
        }

        public TranslationContext build() {
            return new TranslationContext(queryContext, dagRuntimeContext, functionRegistry);
        }
    }
}
