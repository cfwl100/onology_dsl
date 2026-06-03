package com.onology.oac.queryframework.dac;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.DacPhysicalQuery;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.LinkedHashMap;
import java.util.Map;

/** Builds a DAC request body from metric and dimension bindings. */
public class DacSourceTranslator implements QueryTranslator<DacPhysicalQuery> {
    @Override
    public DatasourceType supportType() {
        return DatasourceType.DAC;
    }

    @Override
    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.datasourceType() == DatasourceType.DAC;
    }

    @Override
    public DacPhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("schemaRef", context.schemaRef());
        body.put("metrics", fragment.properties().stream().map(item -> item.binding().dacMetric()).toList());
        body.put("operation", "QUERY");
        return new DacPhysicalQuery(fragment.datasourceId(), fragment.datasourceType(), "QUERY", body);
    }
}
