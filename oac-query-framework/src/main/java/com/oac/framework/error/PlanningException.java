package com.oac.framework.error;

public class PlanningException extends OacException {
    public PlanningException(String message) {
        super(ErrorCode.PLANNING_ERROR, message);
    }

    public PlanningException(String message, Throwable cause) {
        super(ErrorCode.PLANNING_ERROR, message, cause);
    }
}
