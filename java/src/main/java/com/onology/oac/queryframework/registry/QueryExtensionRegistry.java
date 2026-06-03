package com.onology.oac.queryframework.registry;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.DatasourceExecutor;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PhysicalQuery;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Registry for query translators and datasource executors. */
public class QueryExtensionRegistry {
    private final Map<DatasourceType, QueryTranslator<? extends PhysicalQuery>> translators = new LinkedHashMap<>();
    private final Map<DatasourceType, DatasourceExecutor<? extends PhysicalQuery>> executors = new LinkedHashMap<>();

    public QueryExtensionRegistry(List<QueryTranslator<? extends PhysicalQuery>> translators,
                                  List<DatasourceExecutor<? extends PhysicalQuery>> executors) {
        if (translators != null) {
            translators.forEach(item -> this.translators.put(item.supportType(), item));
        }
        if (executors != null) {
            executors.forEach(item -> this.executors.put(item.supportType(), item));
        }
    }

    public Optional<QueryTranslator<? extends PhysicalQuery>> translator(DatasourceType type) {
        return Optional.ofNullable(translators.get(type));
    }

    public Optional<DatasourceExecutor<? extends PhysicalQuery>> executor(DatasourceType type) {
        return Optional.ofNullable(executors.get(type));
    }
}
