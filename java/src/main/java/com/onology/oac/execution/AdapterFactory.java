package com.onology.oac.execution;

import org.springframework.stereotype.Component;

@Component
public class AdapterFactory {
    public SourceAdapter create(String source) {
        return new MockSqlAdapter(source);
    }
}
