package com.onology.oac.queryframework.gql;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.GqlPhysicalQuery;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.Map;
import java.util.StringJoiner;

/** Builds a simple graph query text from one source fragment. */
public class GqlSourceTranslator implements QueryTranslator<GqlPhysicalQuery> {
    @Override
    public DatasourceType supportType() {
        return DatasourceType.NEBULA_GRAPH;
    }

    @Override
    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.datasourceType() == DatasourceType.NEBULA_GRAPH
                || fragment.datasourceType() == DatasourceType.INFINITY_GRAPH;
    }

    @Override
    public GqlPhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        String graphSpace = fragment.properties().isEmpty() ? null : fragment.properties().get(0).binding().graphSpace();
        String tag = fragment.properties().isEmpty() ? "Vertex" : fragment.properties().get(0).binding().vertexLabel();
        StringJoiner fields = new StringJoiner(", ");
        fragment.properties().forEach(item -> fields.add(item.propertyName()));
        String queryText = "MATCH (v:" + tag + ") RETURN " + (fields.length() == 0 ? "v" : fields);
        return new GqlPhysicalQuery(fragment.datasourceId(), fragment.datasourceType(), queryText, Map.of(), graphSpace);
    }
}
