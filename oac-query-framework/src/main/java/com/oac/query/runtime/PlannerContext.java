package com.oac.query.runtime;

import com.oac.query.validation.FunctionRegistry;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 绑定、规划和翻译器共享的不可变规划上下文。
 */
public class PlannerContext {
    private final String traceId;
    private final FunctionRegistry functionRegistry;
    private final Map<String, Object> attributes;

    public PlannerContext(String traceId, FunctionRegistry functionRegistry, Map<String, Object> attributes) {
        this.traceId = traceId;
        this.functionRegistry = functionRegistry == null ? FunctionRegistry.withCoreFunctions() : functionRegistry;
        this.attributes = attributes == null ? new LinkedHashMap<String, Object>() : new LinkedHashMap<String, Object>(attributes);
    }

    public static PlannerContext defaults() {
        return new PlannerContext("planner-trace", FunctionRegistry.withCoreFunctions(), new LinkedHashMap<String, Object>());
    }

    public String getTraceId() {
        return traceId;
    }

    public FunctionRegistry getFunctionRegistry() {
        return functionRegistry;
    }

    public Map<String, Object> getAttributes() {
        return Collections.unmodifiableMap(attributes);
    }
}
