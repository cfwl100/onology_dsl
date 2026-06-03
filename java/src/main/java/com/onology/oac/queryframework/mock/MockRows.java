package com.onology.oac.queryframework.mock;

import java.util.LinkedHashMap;
import java.util.Map;

/** Small helper for deterministic framework demo rows. */
public final class MockRows {
    private MockRows() {
    }

    public static Map<String, Object> objectRow(String objectType, String rid, String field, Object value) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("objectType", objectType);
        row.put("rid", rid);
        row.put(field, value);
        return row;
    }
}
