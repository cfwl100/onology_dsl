package com.oac.framework.kernel;

public interface FunctionRegistry {
    boolean isRegistered(String namespace, String name);
    Object invoke(String namespace, String name, Object[] args);
}
