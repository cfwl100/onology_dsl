package com.onology.oac.queryframework.domain;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Ontology metadata, physical binding and datasource capability models.
 */
public final class MetadataModels {
    private MetadataModels() {
    }

    public enum DatasourceType {
        MYSQL,
        GAUSSDB,
        POSTGRESQL,
        INFINITY_GRAPH,
        NEBULA_GRAPH,
        ELASTICSEARCH,
        DAC,
        API
    }

    public enum RelationshipStorageType {
        GRAPH_EDGE,
        RELATIONAL_JOIN_TABLE,
        PROPERTY_REFERENCE,
        API_REFERENCE,
        DAC_DIMENSION,
        ES_REFERENCE
    }

    public record OntologyObjectType(String schemaRef, String objectType, List<String> primaryKeys) {
    }

    public record OntologyProperty(String schemaRef, String objectType, String propertyName, String dataType) {
    }

    public record OntologyRelationshipType(
            String schemaRef,
            String relationshipType,
            String sourceObjectType,
            String targetObjectType
    ) {
    }

    public record PropertyBinding(
            String schemaRef,
            String objectType,
            String propertyName,
            String datasourceId,
            DatasourceType datasourceType,
            String databaseName,
            String schemaName,
            String tableName,
            String fieldName,
            String graphSpace,
            String vertexLabel,
            String edgeLabel,
            String indexName,
            String apiPath,
            String dacMetric,
            boolean primaryKey,
            boolean joinKey,
            boolean timeField
    ) {
        public PhysicalLocation location() {
            return new PhysicalLocation(datasourceId, datasourceType, databaseName, schemaName, tableName, fieldName,
                    graphSpace, vertexLabel, edgeLabel, indexName, apiPath, dacMetric);
        }
    }

    public record RelationshipBinding(
            String schemaRef,
            String relationshipType,
            String sourceObjectType,
            String targetObjectType,
            RelationshipStorageType storageType,
            String datasourceId,
            DatasourceType datasourceType,
            String relationTable,
            String sourceJoinField,
            String targetJoinField,
            String sourceProperty,
            String targetProperty,
            String graphSpace,
            String edgeLabel,
            String apiPath
    ) {
    }

    public record PhysicalLocation(
            String datasourceId,
            DatasourceType datasourceType,
            String databaseName,
            String schemaName,
            String tableName,
            String fieldName,
            String graphSpace,
            String vertexLabel,
            String edgeLabel,
            String indexName,
            String apiPath,
            String dacMetric
    ) {
    }

    public record DatasourceDefinition(String datasourceId, DatasourceType datasourceType, Map<String, Object> config) {
    }

    public record DatasourceCapability(
            String datasourceId,
            DatasourceType datasourceType,
            boolean supportProjection,
            boolean supportPredicatePushdown,
            boolean supportJoin,
            boolean supportGroupBy,
            boolean supportHaving,
            boolean supportOrderBy,
            boolean supportLimit,
            boolean supportCrossDatabase,
            boolean supportCrossSchema,
            boolean supportCrossSpace,
            boolean supportAggregation,
            boolean supportGraphTraversal
    ) {
        public boolean isSqlLike() {
            return datasourceType == DatasourceType.MYSQL
                    || datasourceType == DatasourceType.GAUSSDB
                    || datasourceType == DatasourceType.POSTGRESQL;
        }
    }

    public interface OntologyMetadataProvider {
        Optional<OntologyObjectType> findObjectType(String schemaRef, String objectType);

        Optional<OntologyProperty> findProperty(String schemaRef, String objectType, String propertyName);

        Optional<OntologyRelationshipType> findRelationshipType(String schemaRef, String relationshipType);
    }

    public interface BindingMetadataProvider {
        List<PropertyBinding> findPropertyBindings(String schemaRef, String objectType, String propertyName);

        Optional<RelationshipBinding> findRelationshipBinding(String schemaRef, String relationshipType);
    }

    public interface DatasourceCapabilityProvider {
        Optional<DatasourceCapability> findCapability(String datasourceId);
    }
}
