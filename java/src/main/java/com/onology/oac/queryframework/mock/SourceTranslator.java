package com.onology.oac.queryframework.mock;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.Map;

/** Minimal translator for framework tests. */
public class SourceTranslator implements QueryTranslator<MockPhysicalQuery> {
    private final DatasourceType type;

    public SourceTranslator(DatasourceType type) {
        this.type = type;
    }

    @Override
    public DatasourceType supportType() {
        return type;
    }

    @Override
    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.datasourceType() == type;
    }

    @Override
    public MockPhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return new MockPhysicalQuery(fragment.datasourceId(), fragment.datasourceType(), fragment.nodeId(),
                fragment.properties().stream().map(item -> item.propertyName()).distinct().toList(), Map.of());
    }
}
