package com.oac.framework.kernel;

import com.oac.query.binding.DatasourceType;

public interface ExecutorRegistry {
    void register(DatasourceExecutor executor);
    DatasourceExecutor find(DatasourceType datasourceType);
}
