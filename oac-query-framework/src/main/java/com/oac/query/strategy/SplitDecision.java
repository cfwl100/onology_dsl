package com.oac.query.strategy;

/** 策略选择结果，以及用于解释/调试输出的选择原因。 */
public class SplitDecision {
    private final SplitStrategy strategy;
    private final String reason;

    public SplitDecision(SplitStrategy strategy, String reason) {
        this.strategy = strategy;
        this.reason = reason;
    }

    public SplitStrategy getStrategy() {
        return strategy;
    }

    public String getReason() {
        return reason;
    }
}
