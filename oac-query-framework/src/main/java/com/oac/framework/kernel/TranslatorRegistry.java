package com.oac.framework.kernel;

import com.oac.query.binding.DatasourceType;

public interface TranslatorRegistry {
    void register(QueryTranslator translator);
    QueryTranslator find(DatasourceType datasourceType);
}
