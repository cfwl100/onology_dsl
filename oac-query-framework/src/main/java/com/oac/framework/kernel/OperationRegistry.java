package com.oac.framework.kernel;

public interface OperationRegistry {
    void register(OperationPlugin plugin);
    OperationPlugin find(OperationType type);
}
