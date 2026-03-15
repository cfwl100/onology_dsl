package com.onology.oac.execution;

import com.onology.oac.compiler.PhysicalNode;

import java.util.List;
import java.util.Map;

public class MockSqlAdapter implements SourceAdapter {
    private final String source;

    public MockSqlAdapter(String source) {
        this.source = source;
    }

    @Override
    public List<Map<String, Object>> execute(PhysicalNode node) {
        return List.of(Map.of(
                "source", source,
                "nodeId", node.nodeId(),
                "statement", node.statement()
        ));
    }
}
