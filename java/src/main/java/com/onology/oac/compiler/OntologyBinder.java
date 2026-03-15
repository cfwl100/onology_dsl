package com.onology.oac.compiler;

import com.onology.oac.metadata.FieldMapping;
import com.onology.oac.metadata.ObjectSchema;
import com.onology.oac.metadata.SchemaRegistry;
import com.onology.oac.model.OqlRequest;
import com.onology.oac.model.ReturnField;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class OntologyBinder {
    private final SchemaRegistry registry;

    public OntologyBinder(SchemaRegistry registry) {
        this.registry = registry;
    }

    public LogicalPlan bind(OqlRequest request) {
        var target = request.getObjects().get(0);
        Map<String, ObjectSchema> snapshot = registry.getSnapshot(request.getSchemaRef());
        ObjectSchema schema = snapshot.get(target.objectType());
        if (schema == null) {
            throw new IllegalArgumentException("objectType not found: " + target.objectType());
        }

        List<String> requested = request.getReturns().isEmpty()
                ? List.of(schema.identityField())
                : request.getReturns().stream().map(ReturnField::field).toList();

        List<BoundField> boundFields = new ArrayList<>();
        for (String f : requested) {
            FieldMapping mapping = schema.fields().get(f);
            if (mapping == null) {
                throw new IllegalArgumentException("field not found: " + f);
            }
            boundFields.add(new BoundField(f, mapping.source(), mapping.table(), mapping.column()));
        }

        List<String> notes = new ArrayList<>();
        long sourceCount = boundFields.stream().map(BoundField::source).distinct().count();
        if (sourceCount > 1) {
            notes.add("single-object multi-source field assembly required");
        }

        return new LogicalPlan(
                request.getOperation().name(),
                target.alias(),
                target.objectType(),
                boundFields,
                request.getConditions(),
                request.getOrders(),
                request.getMaxResults(),
                notes
        );
    }
}
