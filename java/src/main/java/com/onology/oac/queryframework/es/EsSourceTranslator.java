package com.onology.oac.queryframework.es;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.EsPhysicalQuery;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.LinkedHashMap;
import java.util.Map;

/** Builds a basic Elasticsearch DSL body from fragment properties. */
public class EsSourceTranslator implements QueryTranslator<EsPhysicalQuery> {
    @Override
    public DatasourceType supportType() {
        return DatasourceType.ELASTICSEARCH;
    }

    @Override
    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.datasourceType() == DatasourceType.ELASTICSEARCH;
    }

    @Override
    public EsPhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        Map<String, Object> dsl = new LinkedHashMap<>();
        dsl.put("fields", fragment.properties().stream().map(p -> p.propertyName()).toList());
        return new EsPhysicalQuery(fragment.datasourceId(), fragment.datasourceType(), "index", dsl);
    }
}
