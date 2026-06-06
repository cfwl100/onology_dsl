package com.oac.framework.kernel;

public interface ExecutionContext {
    long timeoutMs();
    String traceId();
}
