package com.oac.framework.error;

public class OacException extends RuntimeException {
    private final ErrorCode errorCode;

    public OacException(ErrorCode errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public OacException(ErrorCode errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public ErrorCode errorCode() {
        return errorCode;
    }
}
