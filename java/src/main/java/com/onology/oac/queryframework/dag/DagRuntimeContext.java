package com.onology.oac.queryframework.dag;

import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/** Runtime state shared by dependent DAG fragments. */
public class DagRuntimeContext {
    private final Map<String, FragmentResult> fragmentResults = new LinkedHashMap<>();
    private final Map<String, DagInputResolver.ResolvedInput> resolvedInputs = new LinkedHashMap<>();

    public void putResult(String nodeId, FragmentResult result) {
        fragmentResults.put(nodeId, result);
    }

    public Optional<FragmentResult> result(String nodeId) {
        return Optional.ofNullable(fragmentResults.get(nodeId));
    }

    public void putInput(String downstreamNodeId, DagInputResolver.ResolvedInput input) {
        resolvedInputs.put(downstreamNodeId + ":" + input.field(), input);
    }

    public Optional<DagInputResolver.ResolvedInput> input(String downstreamNodeId, String field) {
        return Optional.ofNullable(resolvedInputs.get(downstreamNodeId + ":" + field));
    }
}
