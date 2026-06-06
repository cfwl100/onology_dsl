package com.oac.framework.kernel;

import java.util.Map;

public class DagRuntimeContext {
    private final Map<String, FragmentResult> fragmentResults;
    private final Map<String, DynamicInput> dynamicInputs;

    public DagRuntimeContext(Map<String, FragmentResult> fragmentResults, Map<String, DynamicInput> dynamicInputs) {
        this.fragmentResults = fragmentResults;
        this.dynamicInputs = dynamicInputs;
    }

    public FragmentResult result(String fragmentId) {
        return fragmentResults.get(fragmentId);
    }

    public DynamicInput input(String fragmentId, String field) {
        return dynamicInputs.get(fragmentId + ":" + field);
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private Map<String, FragmentResult> fragmentResults = Map.of();
        private Map<String, DynamicInput> dynamicInputs = Map.of();

        public Builder fragmentResults(Map<String, FragmentResult> fragmentResults) {
            this.fragmentResults = fragmentResults;
            return this;
        }

        public Builder dynamicInputs(Map<String, DynamicInput> dynamicInputs) {
            this.dynamicInputs = dynamicInputs;
            return this;
        }

        public DagRuntimeContext build() {
            return new DagRuntimeContext(fragmentResults, dynamicInputs);
        }
    }
}
