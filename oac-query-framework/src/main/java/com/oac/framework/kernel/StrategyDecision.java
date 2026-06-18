package com.oac.framework.kernel;

import java.util.Map;

public final class StrategyDecision {
    private final String strategyCode;
    private final int priority;
    private final String reason;
    private final Map<String, Object> attributes;

    public StrategyDecision(String strategyCode, int priority, String reason, Map<String, Object> attributes) {
        this.strategyCode = strategyCode;
        this.priority = priority;
        this.reason = reason;
        this.attributes = attributes;
    }

    public String strategyCode() {
        return strategyCode;
    }

    public int priority() {
        return priority;
    }

    public String reason() {
        return reason;
    }

    public Map<String, Object> attributes() {
        return attributes;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private String strategyCode = "";
        private int priority = 0;
        private String reason = "";
        private Map<String, Object> attributes = Map.of();

        public Builder strategyCode(String strategyCode) {
            this.strategyCode = strategyCode;
            return this;
        }

        public Builder priority(int priority) {
            this.priority = priority;
            return this;
        }

        public Builder reason(String reason) {
            this.reason = reason;
            return this;
        }

        public Builder attributes(Map<String, Object> attributes) {
            this.attributes = attributes;
            return this;
        }

        public StrategyDecision build() {
            return new StrategyDecision(strategyCode, priority, reason, attributes);
        }
    }
}
