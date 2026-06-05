package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 运行时用于查找翻译器和执行器的轻量 SPI 注册表。
 *
 * 生产部署可以用插件化注册替换模拟默认实现，而无需改动 QueryFrameworkService。
 */
public class QueryExtensionRegistry {
    private final Map<DatasourceType, QueryTranslator<? extends PhysicalQuery>> translators = new LinkedHashMap<DatasourceType, QueryTranslator<? extends PhysicalQuery>>();
    private final Map<DatasourceType, DatasourceExecutor<? extends PhysicalQuery>> executors = new LinkedHashMap<DatasourceType, DatasourceExecutor<? extends PhysicalQuery>>();

    public static QueryExtensionRegistry mockDefaults() {
        QueryExtensionRegistry registry = new QueryExtensionRegistry();
        for (DatasourceType type : DatasourceType.values()) {
            if (type == DatasourceType.SQL) {
                registry.registerTranslator(new SqlQueryTranslator());
            } else {
                registry.registerTranslator(new MockQueryTranslator(type));
            }
            registry.registerExecutor(new MockDatasourceExecutor(type));
        }
        return registry;
    }

    public void registerTranslator(QueryTranslator<? extends PhysicalQuery> translator) {
        translators.put(translator.supportType(), translator);
    }

    public void registerExecutor(DatasourceExecutor<? extends PhysicalQuery> executor) {
        executors.put(executor.supportType(), executor);
    }

    @SuppressWarnings("unchecked")
    public QueryTranslator<PhysicalQuery> translator(DatasourceType type) {
        return (QueryTranslator<PhysicalQuery>) translators.get(type);
    }

    @SuppressWarnings("unchecked")
    public DatasourceExecutor<PhysicalQuery> executor(DatasourceType type) {
        return (DatasourceExecutor<PhysicalQuery>) executors.get(type);
    }
}
