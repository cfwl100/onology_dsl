package com.onology.oac.queryframework.assembler;

import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import com.onology.oac.queryframework.domain.ResultModels.OntologyRelationshipInstance;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Converts rows containing relationship metadata into ontology relationship instances. */
public class RelationRows {
    public List<OntologyRelationshipInstance> build(Map<String, FragmentResult> fragments) {
        List<OntologyRelationshipInstance> result = new ArrayList<>();
        for (FragmentResult fragment : fragments.values()) {
            for (Map<String, Object> row : fragment.rows()) {
                Object type = row.get("relationshipType");
                if (type == null) {
                    continue;
                }
                String relationType = String.valueOf(type);
                String rid = String.valueOf(row.getOrDefault("relationshipRid", relationType + ":" + row.hashCode()));
                String sourceRid = String.valueOf(row.getOrDefault("sourceRid", ""));
                String targetRid = String.valueOf(row.getOrDefault("targetRid", ""));
                result.add(new OntologyRelationshipInstance(relationType, rid, sourceRid, targetRid, row));
            }
        }
        return result;
    }
}
