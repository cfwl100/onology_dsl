package com.oac.framework.error;

public enum ErrorCode {
    VALIDATION_ERROR(1000, "Query validation failed"),
    PLANNING_ERROR(2000, "Query planning failed"),
    TRANSLATION_ERROR(3000, "Query translation failed"),
    EXECUTION_ERROR(4000, "Query execution failed"),
    ASSEMBLY_ERROR(5000, "Result assembly failed"),
    INTERNAL_ERROR(9999, "Internal framework error");

    private final int code;
    private final String description;

    ErrorCode(int code, String description) {
        this.code = code;
        this.description = description;
    }

    public int code() {
        return code;
    }

    public String description() {
        return description;
    }
}
