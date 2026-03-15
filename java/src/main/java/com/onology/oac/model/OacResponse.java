package com.onology.oac.model;

import java.util.Map;
import java.util.UUID;

public record OacResponse(
        String requestId,
        String traceId,
        String mode,
        boolean success,
        Object data,
        Map<String, Object> metadata,
        Map<String, Object> error
) {
    public static OacResponse ok(String mode, Object data, Map<String, Object> metadata) {
        return new OacResponse(UUID.randomUUID().toString(), UUID.randomUUID().toString(), mode, true, data, metadata, null);
    }
}
