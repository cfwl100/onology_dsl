package com.oac.query.assembly;

import com.oac.query.runtime.FragmentResult;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 按 rid 合并多个查询分片返回的对象行。
 */
public class ObjectAssembler {
    public List<Map<String, Object>> assemble(List<FragmentResult> fragmentResults) {
        Map<Object, Map<String, Object>> byRid = new LinkedHashMap<Object, Map<String, Object>>();
        int synthetic = 1;
        for (FragmentResult fragmentResult : fragmentResults) {
            for (Map<String, Object> row : fragmentResult.getRows()) {
                Object rid = row.containsKey("rid") ? row.get("rid") : "synthetic-" + synthetic++;
                Map<String, Object> target = byRid.get(rid);
                if (target == null) {
                    target = new LinkedHashMap<String, Object>();
                    target.put("rid", rid);
                    byRid.put(rid, target);
                }
                mergeFirstNonNull(target, row);
            }
        }
        return new ArrayList<Map<String, Object>>(byRid.values());
    }

    private void mergeFirstNonNull(Map<String, Object> target, Map<String, Object> row) {
        // FIRST_NON_NULL 是设计方案中 v1 版本采用的默认冲突处理策略。
        for (Map.Entry<String, Object> entry : row.entrySet()) {
            Object existing = target.get(entry.getKey());
            if (existing == null && entry.getValue() != null) {
                target.put(entry.getKey(), entry.getValue());
            }
        }
    }
}
