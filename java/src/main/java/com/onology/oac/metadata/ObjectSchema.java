package com.onology.oac.metadata;

import java.util.Map;

public record ObjectSchema(String objectType, String primarySource, String identityField, Map<String, FieldMapping> fields) {}
