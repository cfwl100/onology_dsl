package com.onology.oac.queryframework.assembler;

import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import com.onology.oac.queryframework.domain.ResultModels.OntologyObjectInstance;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Merges cross-source fragment rows by rid with FIRST_NON_NULL semantics. */
public class ObjectAssembler {
    public List<OntologyObjectInstance> assemble(Map<String, FragmentResult> fragments) {
        Map<String, OntologyObjectInstance> objects = new LinkedHashMap<>();
        for (FragmentResult fragment : fragments.values()) {
            for (Map<String, Object> row : fragment.rows()) {
                String objectType = String.valueOf(row.getOrDefault("objectType", "Object"));
                String rid = String.valueOf(row.getOrDefault("rid", objectType + ":" + row.hashCode()));
                Map<String, Object> properties = new LinkedHashMap<>(row);
                properties.remove("objectType");
                properties.remove("rid");
                objects.merge(rid, new OntologyObjectInstance(objectType, rid, properties), this::merge);
            }
        }
        return new ArrayList<>(objects.values());
    }

    private OntologyObjectInstance merge(OntologyObjectInstance left, OntologyObjectInstance right) {
        Map<String, Object> properties = new LinkedHashMap<>(left.properties());
        right.properties().forEach(properties::putIfAbsent);
        return new OntologyObjectInstance(left.objectType(), left.rid(), properties);
    }
}
