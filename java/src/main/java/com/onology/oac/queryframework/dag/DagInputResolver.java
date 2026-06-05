package com.onology.oac.queryframework.dag;

import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Extracts downstream input values from upstream fragment results. */
public class DagInputResolver {
    public ResolvedInput resolve(FragmentDependency dependency, FragmentResult upstreamResult) {
        Set<Object> values = new LinkedHashSet<>();
        for (Map<String, Object> row : upstreamResult.rows()) {
            if (row.containsKey(dependency.upstreamOutputField())) {
                Object value = row.get(dependency.upstreamOutputField());
                if (value != null) {
                    values.add(value);
                }
            }
            if (values.size() >= dependency.maxInputSize()) {
                break;
            }
        }
        return new ResolvedInput(dependency.downstreamInputField(), dependency.operator(), new ArrayList<>(values));
    }

    public record ResolvedInput(String field, FragmentDependency.InputOperator operator, List<Object> values) {
        public boolean isEmpty() {
            return values == null || values.isEmpty();
        }
    }
}
