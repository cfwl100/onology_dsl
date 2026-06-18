package com.oac.framework.kernel;

public interface OntologyMetadataProvider {
    ObjectSchema getSchema(String schemaRef);
    boolean hasObjectType(String objectType);
    boolean hasRelationshipType(String relationshipType);
}
