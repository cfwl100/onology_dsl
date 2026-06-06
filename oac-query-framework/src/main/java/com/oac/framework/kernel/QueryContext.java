package com.oac.framework.kernel;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class QueryContext {
    private final String queryId;
    private final String traceId;
    private final long timeoutMs;
    private final int maxResults;
    private final Map<String, Object> properties;

    private QueryContext(Builder builder) {
        this.queryId = builder.queryId;
        this.traceId = builder.traceId;
        this.timeoutMs = builder.timeoutMs;
        this.maxResults = builder.maxResults;
        this.properties = Collections.unmodifiableMap(builder.properties);
    }

    public String queryId() {
        return queryId;
    }

    public String traceId() {
        return traceId;
    }

    public long timeoutMs() {
        return timeoutMs;
    }

    public int maxResults() {
        return maxResults;
    }

    public Map<String, Object> properties() {
        return properties;
    }

    public Object property(String key) {
        return properties.get(key);
    }

    public static QueryContext defaults() {
        return builder().build();
    }

    public static Builder builder() {
        return new Builder();
    }

    public Builder toBuilder() {
        return new Builder()
                .queryId(queryId)
                .traceId(traceId)
                .timeoutMs(timeoutMs)
                .maxResults(maxResults)
                .properties(properties);
    }

    public static final class Builder {
        private String queryId = "";
        private String traceId = "";
        private long timeoutMs = 30000;
        private int maxResults = 1000;
        private Map<String, Object> properties = new HashMap<>();

        public Builder queryId(String queryId) {
            this.queryId = queryId == null ? "" : queryId;
            return this;
        }

        public Builder traceId(String traceId) {
            this.traceId = traceId == null ? "" : traceId;
            return this;
        }

        public Builder timeoutMs(long timeoutMs) {
            this.timeoutMs = timeoutMs;
            return this;
        }

        public Builder maxResults(int maxResults) {
            this.maxResults = maxResults;
            return this;
        }

        public Builder properties(Map<String, Object> properties) {
            this.properties = properties == null ? Collections.emptyMap() : properties;
            return this;
        }

        public Builder putProperty(String key, Object value) {
            Objects.requireNonNull(key, "property key must not be null");
            this.properties.put(key, value);
            return this;
        }

        public QueryContext build() {
            return new QueryContext(this);
        }
    }
}
