package com.oac.query.runtime;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 单次请求的执行上下文，携带 trace、租户和用户信息。
 */
public class ExecutionContext {
    private final String traceId;
    private final String tenantId;
    private final String userId;
    private final Map<String, Object> attributes;

    public ExecutionContext(String traceId, String tenantId, String userId, Map<String, Object> attributes) {
        this.traceId = traceId;
        this.tenantId = tenantId;
        this.userId = userId;
        this.attributes = attributes == null ? new LinkedHashMap<String, Object>() : new LinkedHashMap<String, Object>(attributes);
    }

    public static ExecutionContext defaults() {
        return new ExecutionContext("exec-trace", "tenant-default", "user-default", new LinkedHashMap<String, Object>());
    }

    public String getTraceId() {
        return traceId;
    }

    public String getTenantId() {
        return tenantId;
    }

    public String getUserId() {
        return userId;
    }

    public Map<String, Object> getAttributes() {
        return Collections.unmodifiableMap(attributes);
    }
}
