package com.oac.framework.kernel;

import java.util.List;

public class DynamicInput {
    private final String field;
    private final InputOperator operator;
    private final List<Object> values;

    public DynamicInput(String field, InputOperator operator, List<Object> values) {
        this.field = field;
        this.operator = operator;
        this.values = values;
    }

    public String field() {
        return field;
    }

    public InputOperator operator() {
        return operator;
    }

    public List<Object> values() {
        return values;
    }

    public enum InputOperator {
        EQ,
        IN
    }
}
