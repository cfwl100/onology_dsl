package com.onology.oac.queryframework.example;

import com.onology.oac.queryframework.domain.MetadataModels;

import java.util.List;
import java.util.Optional;

/** Example in-memory metadata providers for QueryFrameworkService integration tests. */
public class ExampleMetadata implements MetadataModels.OntologyMetadataProvider, MetadataModels.BindingMetadataProvider,
        MetadataModels.DatasourceCapabilityProvider {
    @Override
    public Optional<MetadataModels.OntologyObjectType> findObjectType(String schemaRef, String objectType) {
        return Optional.of(new MetadataModels.OntologyObjectType(schemaRef, objectType, List.of("id")));
    }

    @Override
    public Optional<MetadataModels.OntologyProperty> findProperty(String schemaRef, String objectType, String propertyName) {
        return Optional.of(new MetadataModels.OntologyProperty(schemaRef, objectType, propertyName, "string"));
    }

    @Override
    public Optional<MetadataModels.OntologyRelationshipType> findRelationshipType(String schemaRef, String relationshipType) {
        return Optional.of(new MetadataModels.OntologyRelationshipType(schemaRef, relationshipType, "Cell", "Grid"));
    }

    @Override
    public List<MetadataModels.PropertyBinding> findPropertyBindings(String schemaRef, String objectType, String propertyName) {
        return List.of(new MetadataModels.PropertyBinding(schemaRef, objectType, propertyName, "mysql_1",
                MetadataModels.DatasourceType.MYSQL, "db", "public", "dim_cell", propertyName,
                null, null, null, null, null, null, "id".equals(propertyName), false, false));
    }

    @Override
    public Optional<MetadataModels.RelationshipBinding> findRelationshipBinding(String schemaRef, String relationshipType) {
        return Optional.of(new MetadataModels.RelationshipBinding(schemaRef, relationshipType, "Cell", "Grid",
                MetadataModels.RelationshipStorageType.RELATIONAL_JOIN_TABLE, "mysql_1", MetadataModels.DatasourceType.MYSQL,
                "cell_grid", "cell_id", "grid_id", "id", "id", null, null, null));
    }

    @Override
    public Optional<MetadataModels.DatasourceCapability> findCapability(String datasourceId) {
        return Optional.of(new MetadataModels.DatasourceCapability(datasourceId, MetadataModels.DatasourceType.MYSQL,
                true, true, true, true, true, true, true, true, true, false, true, false));
    }
}
