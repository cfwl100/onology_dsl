package com.onology.oac.compiler;

import com.onology.oac.model.Condition;
import com.onology.oac.model.OrderBy;

import java.util.List;

public record LogicalPlan(
        String operation,
        String objectAlias,
        String objectType,
        List<BoundField> boundFields,
        List<Condition> filters,
        List<OrderBy> orders,
        int limit,
        List<String> notes
) {}
