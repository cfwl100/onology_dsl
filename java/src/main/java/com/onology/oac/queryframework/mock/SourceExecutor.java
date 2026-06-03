package com.onology.oac.queryframework.mock;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.DatasourceExecutor;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.ExecutionContext;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Minimal executor for framework tests. */
public class SourceExecutor implements DatasourceExecutor<MockPhysicalQuery> {
    private final DatasourceType type;

    public SourceExecutor(DatasourceType type) {
        this.type = type;
    }

    @Override
    public DatasourceType supportType() {
        return type;
    }

    @Override
    public FragmentResult execute(MockPhysicalQuery query, ExecutionContext context) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("objectType", "MockObject");
        row.put("rid", "MockObject:1");
        for (String field : query.projectedFields()) {
            row.put(field, query.datasourceId() + ":" + field);
        }
        return new FragmentResult(query.fragmentId(), query.datasourceId(), List.of(row), Map.of());
    }
}
