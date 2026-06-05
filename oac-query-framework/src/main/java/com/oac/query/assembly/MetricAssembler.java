package com.oac.query.assembly;

import com.oac.query.runtime.FragmentResult;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 将聚合行收集到 OntologyQueryResult 的指标区域。
 */
public class MetricAssembler {
    public List<Map<String, Object>> assemble(List<FragmentResult> fragmentResults) {
        List<Map<String, Object>> metrics = new ArrayList<Map<String, Object>>();
        for (FragmentResult fragmentResult : fragmentResults) {
            for (Map<String, Object> row : fragmentResult.getRows()) {
                metrics.add(new LinkedHashMap<String, Object>(row));
            }
        }
        return metrics;
    }
}
