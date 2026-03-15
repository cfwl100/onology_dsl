package com.onology.oac.operation;

import com.onology.oac.model.OacResponse;
import com.onology.oac.model.OqlRequest;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class ExplainHandler extends ValidateHandler {
    public ExplainHandler(OacPipeline pipeline) {
        super(pipeline);
    }

    @Override
    public OacResponse handle(OqlRequest request) {
        OacPipeline.CompiledPlan compiled = pipeline.compile(request);
        return OacResponse.ok("explain", Map.of(
                "logicalPlan", compiled.logical(),
                "physicalPlan", compiled.physical()
        ), Map.of("degraded", compiled.physical().degraded()));
    }
}
