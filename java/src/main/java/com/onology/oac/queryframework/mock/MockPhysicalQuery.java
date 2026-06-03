package com.onology.oac.queryframework.mock;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PhysicalQuery;

import java.util.List;
import java.util.Map;

/** Physical query used by tests and framework demos. */
public record MockPhysicalQuery(
        String datasourceId,
        DatasourceType datasourceType,
        String fragmentId,
        List<String> projectedFields,
        Map<String, Object> attributes
) implements PhysicalQuery {
}
