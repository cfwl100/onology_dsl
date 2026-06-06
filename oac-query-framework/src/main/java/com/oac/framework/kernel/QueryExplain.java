package com.oac.framework.kernel;

import com.oac.query.plan.logical.LogicalPlan;
import com.oac.query.plan.physical.PhysicalPlan;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public final class QueryExplain {
    private final LogicalPlan logicalPlan;
    private final PhysicalPlan physicalPlan;
    private final String strategy;
    private final List<String> decisions;

    public QueryExplain(Builder builder) {
        this.logicalPlan = builder.logicalPlan;
        this.physicalPlan = builder.physicalPlan;
        this.strategy = builder.strategy;
        this.decisions = Collections.unmodifiableList(new ArrayList<>(builder.decisions));
    }

    public LogicalPlan logicalPlan() {
        return logicalPlan;
    }

    public PhysicalPlan physicalPlan() {
        return physicalPlan;
    }

    public String strategy() {
        return strategy;
    }

    public List<String> decisions() {
        return decisions;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private LogicalPlan logicalPlan;
        private PhysicalPlan physicalPlan;
        private String strategy = "";
        private List<String> decisions = new ArrayList<>();

        public Builder logicalPlan(LogicalPlan logicalPlan) {
            this.logicalPlan = logicalPlan;
            return this;
        }

        public Builder physicalPlan(PhysicalPlan physicalPlan) {
            this.physicalPlan = physicalPlan;
            return this;
        }

        public Builder strategy(String strategy) {
            this.strategy = strategy == null ? "" : strategy;
            return this;
        }

        public Builder addDecision(String decision) {
            if (decision != null) {
                this.decisions.add(decision);
            }
            return this;
        }

        public Builder decisions(List<String> decisions) {
            this.decisions = decisions == null ? new ArrayList<>() : decisions;
            return this;
        }

        public QueryExplain build() {
            return new QueryExplain(this);
        }
    }
}
