package com.onology.oac.queryframework.dag;

/**
 * Describes a runtime dependency between two physical query fragments.
 *
 * <p>Typical case: upstream fragment A returns vertex ids from GQL, then downstream fragment B
 * consumes those ids as SQL WHERE field IN (...).
 */
public record FragmentDependency(
        String upstreamNodeId,
        String upstreamOutputField,
        String downstreamNodeId,
        String downstreamInputField,
        InputOperator operator,
        boolean required,
        int maxInputSize
) {
    public enum InputOperator {
        EQ,
        IN
    }

    public FragmentDependency {
        if (maxInputSize <= 0) {
            maxInputSize = 1000;
        }
        if (operator == null) {
            operator = InputOperator.IN;
        }
    }
}
