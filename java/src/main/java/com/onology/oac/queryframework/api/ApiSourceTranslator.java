package com.onology.oac.queryframework.api;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.ApiPhysicalQuery;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.Map;

/** Builds a simple GET API request from source binding metadata. */
public class ApiSourceTranslator implements QueryTranslator<ApiPhysicalQuery> {
    @Override
    public DatasourceType supportType() {
        return DatasourceType.API;
    }

    @Override
    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.datasourceType() == DatasourceType.API;
    }

    @Override
    public ApiPhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        String path = fragment.properties().isEmpty() ? "/" : fragment.properties().get(0).binding().apiPath();
        return new ApiPhysicalQuery(fragment.datasourceId(), fragment.datasourceType(), "GET", path,
                Map.of(), Map.of(), null);
    }
}
