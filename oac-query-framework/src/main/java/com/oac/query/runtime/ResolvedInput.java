package com.oac.query.runtime;

import com.oac.query.plan.physical.FragmentDependency.InputOperator;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 从上游查询分片解析出来、供下游查询分片使用的动态输入值。
 */
public class ResolvedInput {
    private final String downstreamNodeId;
    private final String downstreamInputField;
    private final InputOperator operator;
    private final List<Object> values;

    public ResolvedInput(String downstreamNodeId, String downstreamInputField, InputOperator operator, List<Object> values) {
        this.downstreamNodeId = downstreamNodeId;
        this.downstreamInputField = downstreamInputField;
        this.operator = operator;
        this.values = values == null ? new ArrayList<Object>() : new ArrayList<Object>(values);
    }

    public String getDownstreamNodeId() {
        return downstreamNodeId;
    }

    public String getDownstreamInputField() {
        return downstreamInputField;
    }

    public InputOperator getOperator() {
        return operator;
    }

    public List<Object> getValues() {
        return Collections.unmodifiableList(values);
    }

    public boolean isEmpty() {
        return values.isEmpty();
    }
}
