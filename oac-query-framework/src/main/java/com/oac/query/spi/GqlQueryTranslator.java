package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;
import com.oac.query.plan.physical.PhysicalFieldBinding;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.spi.PhysicalQueries.GqlPhysicalQuery;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * GQL translator for graph datasource fragments.
 */
public class GqlQueryTranslator implements QueryTranslator<PhysicalQuery> {
    public DatasourceType supportType() {
        return DatasourceType.GQL;
    }

    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.getDatasourceType() == DatasourceType.GQL;
    }

    public PhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        String label = fragment.getObjectType() == null ? fragment.getObjectAlias() : fragment.getObjectType();
        StringBuilder builder = new StringBuilder();
        builder.append("MATCH (v:").append(label).append(")");