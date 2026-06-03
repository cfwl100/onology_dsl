package com.onology.oac.queryframework.spi;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;

import java.util.Map;

/**
 * Extension SPI for translators and executors.
 */
public final class QueryFrameworkSpi {
    private QueryFrameworkSpi() {
    }

    public interface PhysicalQuery {
        String datasourceId();

        DatasourceType datasourceType();
    }

    public record SqlPhysicalQuery(String datasourceId, DatasourceType datasourceType, String sql,
                                   java.util.List<Object> parameters, String dialect) implements PhysicalQuery {
    }

    public record GqlPhysicalQuery(String datasourceId, DatasourceType datasourceType, String gql,
                                   Map<String, Object> parameters, String graphSpace) implements PhysicalQuery {
    }

    public record ApiPhysicalQuery(String datasourceId, DatasourceType datasourceType, String method, String url,
                                   Map<String, String> headers, Map<String, Object> queryParams,
                                   Object body) implements PhysicalQuery {
    }

    public record DacPhysicalQuery(String datasourceId, DatasourceType datasourceType, String requestType,
                                   Map<String, Object> body) implements PhysicalQuery {
    }

    public record EsPhysicalQuery(String datasourceId, DatasourceType datasourceType, String index,
                                  Map<String, Object> dsl) implements PhysicalQuery {
    }

    public record PlannerContext(String schemaRef, Map<String, Object> attributes) {
    }

    public record ExecutionContext(String tenantId, int timeoutMillis, Map<String, Object> attributes) {
    }

    public interface QueryTranslator<T extends PhysicalQuery> {
        DatasourceType supportType();

        boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context);

        T translate(PhysicalSourceQueryNode fragment, PlannerContext context);
    }

    public interface DatasourceExecutor<T extends PhysicalQuery> {
        DatasourceType supportType();

        FragmentResult execute(T query, ExecutionContext context);
    }
}
