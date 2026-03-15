package com.onology.oac.operation;

import com.onology.oac.model.OacResponse;
import com.onology.oac.model.OqlRequest;

public interface OacModeHandler {
    OacResponse handle(OqlRequest request);
}
