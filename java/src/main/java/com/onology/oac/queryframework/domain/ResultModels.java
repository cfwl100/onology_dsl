package com.onology.oac.queryframework.domain;

import java.util.List;
import java.util.Map;

/**
 * Standard fragment and ontology query result models.
 */
public final class ResultModels {
    private ResultModels() {
    }

    public record OntologyQueryResult(
            boolean success,
            List<OntologyObjectInstance> objects,
            List<OntologyRelationshipInstance> relationships,
            List<Map<String, Object>> aggregations,
            PageInfo pageInfo,
            List<OacError> errors
    ) {
        public static OntologyQueryResult failed(List<OacError> errors) {
            return new OntologyQueryResult(false, List.of(), List.of(), List.of(), null, errors);
        }

        public static OntologyQueryResult success(
                List<OntologyObjectInstance> objects,
                List<OntologyRelationshipInstance> relationships,
                List<Map<String, Object>> aggregations,
                PageInfo pageInfo) {
            return new OntologyQueryResult(true, objects, relationships, aggregations, pageInfo, List.of());
        }
    }

    public record OntologyObjectInstance(String objectType, String rid, Map<String, Object> properties) {
    }

    public record OntologyRelationshipInstance(
            String relationshipType,
            String rid,
            String sourceRid,
            String targetRid,
            Map<String, Object> properties
    ) {
    }

    public record FragmentResult(
            String fragmentId,
            String datasourceId,
            List<Map<String, Object>> rows,
            Map<String, String> propertyMappings
    ) {
    }

    public record PageInfo(Integer limit, Integer offset, Integer total) {
    }

    public record OacError(String code, String message, String path, Map<String, Object> details) {
        public static OacError of(String code, String message, String path) {
            return new OacError(code, message, path, Map.of());
        }
    }
}
