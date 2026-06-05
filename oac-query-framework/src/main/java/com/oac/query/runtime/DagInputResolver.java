package com.oac.query.runtime;

import com.oac.query.plan.physical.FragmentDependency;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * 从上游查询分片输出中提取字段值，并转换为下游动态输入条件。
 */
public class DagInputResolver {
    public ResolvedInput resolve(FragmentDependency dependency, FragmentResult upstreamResult) {
        Set<Object> values = new LinkedHashSet<Object>();
        if (upstreamResult != null) {
            for (Map<String, Object> row : upstreamResult.getRows()) {
                Object value = row.get(dependency.getUpstreamOutputField());
                if (value != null) {
                    values.add(value);
                }
                if (values.size() >= dependency.getMaxInputSize()) {
                    break;
                }
            }
        }
        return new ResolvedInput(dependency.getDownstreamNodeId(), dependency.getDownstreamInputField(),
                dependency.getOperator(), new ArrayList<Object>(values));
    }
}
