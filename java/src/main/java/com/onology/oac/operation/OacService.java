package com.onology.oac.operation;

import com.onology.oac.model.OacResponse;
import com.onology.oac.model.OqlRequest;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class OacService {
    private final Map<String, OacModeHandler> handlers;

    public OacService(ValidateHandler validateHandler, ExplainHandler explainHandler, ExecuteHandler executeHandler) {
        this.handlers = Map.of(
                "validate", validateHandler,
                "explain", explainHandler,
                "execute", executeHandler
        );
    }

    public OacResponse process(String mode, OqlRequest request) {
        OacModeHandler handler = handlers.get(mode);
        if (handler == null) {
            throw new IllegalArgumentException("unsupported mode: " + mode);
        }
        return handler.handle(request);
    }
}
