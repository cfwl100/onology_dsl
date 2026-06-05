package com.oac.query.plan.physical;

import java.util.Objects;

/**
 * 两个物理查询分片之间的运行时依赖边。
 *
 * Java 8 不支持 record，因此这里用 final 字段和值语义模拟设计文档中的 record 结构。
 */
public final class FragmentDependency {
    private final String upstreamNodeId;
    private final String upstreamOutputField;
    private final String downstreamNodeId;
    private final String downstreamInputField;
    private final InputOperator operator;
    private final boolean required;
    private final int maxInputSize;

    public enum InputOperator {
        EQ,
        IN
    }

    public FragmentDependency(String upstreamNodeId, String upstreamOutputField, String downstreamNodeId,
                              String downstreamInputField, InputOperator operator, boolean required, int maxInputSize) {
        this.upstreamNodeId = upstreamNodeId;
        this.upstreamOutputField = upstreamOutputField;
        this.downstreamNodeId = downstreamNodeId;
        this.downstreamInputField = downstreamInputField;
        this.operator = operator;
        this.required = required;
        this.maxInputSize = maxInputSize;
    }

    public String getUpstreamNodeId() {
        return upstreamNodeId;
    }

    public String getUpstreamOutputField() {
        return upstreamOutputField;
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

    public boolean isRequired() {
        return required;
    }

    public int getMaxInputSize() {
        return maxInputSize;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof FragmentDependency)) {
            return false;
        }
        FragmentDependency that = (FragmentDependency) o;
        return required == that.required
                && maxInputSize == that.maxInputSize
                && Objects.equals(upstreamNodeId, that.upstreamNodeId)
                && Objects.equals(upstreamOutputField, that.upstreamOutputField)
                && Objects.equals(downstreamNodeId, that.downstreamNodeId)
                && Objects.equals(downstreamInputField, that.downstreamInputField)
                && operator == that.operator;
    }

    @Override
    public int hashCode() {
        return Objects.hash(upstreamNodeId, upstreamOutputField, downstreamNodeId, downstreamInputField, operator, required, maxInputSize);
    }

    @Override
    public String toString() {
        return "FragmentDependency{"
                + "upstreamNodeId='" + upstreamNodeId + '\''
                + ", upstreamOutputField='" + upstreamOutputField + '\''
                + ", downstreamNodeId='" + downstreamNodeId + '\''
                + ", downstreamInputField='" + downstreamInputField + '\''
                + ", operator=" + operator
                + ", required=" + required
                + ", maxInputSize=" + maxInputSize
                + '}';
    }
}
