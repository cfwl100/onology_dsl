package com.oac.framework.kernel;

import com.oac.query.spi.PhysicalQuery;

public interface DatasourceExecutor {
    DatasourceKind datasourceKind();
    FragmentResult execute(PhysicalQuery query, ExecutionContext context);
}
