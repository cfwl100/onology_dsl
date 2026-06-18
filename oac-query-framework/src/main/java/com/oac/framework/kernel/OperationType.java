package com.oac.framework.kernel;

public final class OperationType {
    public static final OperationType QUERY = new OperationType("QUERY");
    public static final OperationType AGGREGATE = new OperationType("AGGREGATE");
    public static final OperationType ASSOCIATION_QUERY = new OperationType("ASSOCIATION_QUERY");
    public static final OperationType EXPLAIN = new OperationType("EXPLAIN");

    private final String code;

    public OperationType(String code) {
        if (code == null || code.trim().isEmpty()) {
            throw new IllegalArgumentException("operation code must not be blank");
        }
        this.code = code;
    }

    public String code() {
        return code;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        OperationType that = (OperationType) o;
        return code.equals(that.code);
    }

    @Override
    public int hashCode() {
        return code.hashCode();
    }

    @Override
    public String toString() {
        return "OperationType{" + code + "}";
    }
}
