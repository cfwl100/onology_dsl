package com.onology.oac.operation;

import com.onology.oac.model.OacResponse;
import com.onology.oac.model.OqlRequest;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class ExecuteHandler extends ValidateHandler {
    public ExecuteHandler(OacPipeline pipeline) {
        super(pipeline);
    }

    @Override
    public OacResponse handle(OqlRequest request) {
        OacPipeline.CompiledPlan compiled = pipeline.compile(request);
        Map<String, Object> raw = pipeline.orchestrator().run(compiled.physical());
        Map<String, Object> assembled = pipeline.assembler().assemble(compiled.logical(), compiled.physical(), raw);
        Object metadataObj = assembled.get("metadata");
        Map<String, Object> metadata = metadataObj instanceof Map<?, ?> m
                ? m.entrySet().stream().collect(java.util.stream.Collectors.toMap(
                        e -> String.valueOf(e.getKey()),
                        Map.Entry::getValue
                ))
                : Map.of();
        return OacResponse.ok("execute", assembled, metadata);
    }
}
