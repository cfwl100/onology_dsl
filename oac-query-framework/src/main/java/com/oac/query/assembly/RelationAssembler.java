package com.oac.query.assembly;

import com.oac.query.runtime.FragmentResult;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 将关系形态的查询分片行转换为本体关系结果行。
 */
public class RelationAssembler {
    public List<Map<String, Object>> assemble(List<FragmentResult> fragmentResults) {
        List<Map<String, Object>> relationships = new ArrayList<Map<String, Object>>();
        for (FragmentResult fragmentResult : fragmentResults) {
            for (Map<String, Object> row : fragmentResult.getRows()) {
                if (row.containsKey("sourceRid") && row.containsKey("targetRid")) {
                    Map<String, Object> relation = new LinkedHashMap<String, Object>();
                    relation.put("sourceRid", row.get("sourceRid"));
                    relation.put("targetRid", row.get("targetRid"));
                    relation.put("relationshipType", row.get("relationshipType"));
                    relation.put("fragmentId", fragmentResult.getFragmentId());
                    relationships.add(relation);
                }
            }
        }
        return relationships;
    }
}
