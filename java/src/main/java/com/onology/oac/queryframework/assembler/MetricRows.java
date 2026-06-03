package com.onology.oac.queryframework.assembler;

import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Collects aggregate or metric rows from fragment results. */
public class MetricRows {
    public List<Map<String, Object>> collect(Map<String, FragmentResult> fragments) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (FragmentResult fragment : fragments.values()) {
            rows.addAll(fragment.rows());
        }
        return rows;
    }
}
