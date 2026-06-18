package com.oac.framework.kernel;

import com.oac.query.binding.DatasourceType;
import com.oac.query.spi.PhysicalQuery;

public interface QueryTranslator {
    DatasourceType supportType();
    PhysicalQuery translate(PhysicalSourceNode sourceNode, TranslationContext context);
}
