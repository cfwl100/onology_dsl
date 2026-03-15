package com.onology.oac.operation;

import com.onology.oac.model.OacResponse;
import com.onology.oac.model.OqlRequest;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class ValidateHandler implements OacModeHandler {
    protected final OacPipeline pipeline;

    public ValidateHandler(OacPipeline pipeline) {
        this.pipeline = pipeline;
    }

    @Override
    public OacResponse handle(OqlRequest request) {
        OacPipeline.CompiledPlan compiled = pipeline.compile(request);
        return OacResponse.ok("validate", Map.of("message", "validation passed"), Map.of(
                "logical", compiled.logical(),
                "physical", compiled.physical()
        ));
    }
}
