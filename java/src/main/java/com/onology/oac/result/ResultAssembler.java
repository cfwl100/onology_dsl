package com.onology.oac.result;

import com.onology.oac.compiler.LogicalPlan;
import com.onology.oac.compiler.PhysicalPlan;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class ResultAssembler {
    public Map<String, Object> assemble(LogicalPlan logical, PhysicalPlan physical, Map<String, Object> raw) {
        List<Object> records = new ArrayList<>();
        for (Object value : raw.values()) {
            records.add(value);
        }

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("degraded", physical.degraded());
        metadata.put("hints", physical.hints());
        metadata.put("logicalNotes", logical.notes());

        return Map.of(
                "operation", logical.operation(),
                "objectType", logical.objectType(),
                "records", records,
                "metadata", metadata
        );
    }
}
