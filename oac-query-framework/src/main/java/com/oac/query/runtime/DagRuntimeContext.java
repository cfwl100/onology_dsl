package com.oac.query.runtime;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * DAG 执行期间保存查询分片结果和动态输入的运行时暂存区。
 */
public class DagRuntimeContext {
    private final Map<String, FragmentResult> results = new LinkedHashMap<String, FragmentResult>();
    private final Map<String, ResolvedInput> inputs = new LinkedHashMap<String, ResolvedInput>();

    public void putResult(String fragmentId, FragmentResult result) {
        results.put(fragmentId, result);
    }

    public FragmentResult result(String fragmentId) {
        return results.get(fragmentId);
    }

    public void putInput(ResolvedInput input) {
        inputs.put(key(input.getDownstreamNodeId(), input.getDownstreamInputField()), input);
    }

    public ResolvedInput input(String downstreamNodeId, String inputField) {
        return inputs.get(key(downstreamNodeId, inputField));
    }

    private String key(String nodeId, String inputField) {
        return nodeId + "." + inputField;
    }
}
