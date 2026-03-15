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

/**
 * OntologyBinder 负责把 OQL 中的对象/字段绑定到本体映射元数据。
 *
 * <p>输出 LogicalPlan（逻辑计划）供后续 translator 按 source 切分。
 */
@Component
public class OntologyBinder {
    private final SchemaRegistry registry;

    public OntologyBinder(SchemaRegistry registry) {
        this.registry = registry;
    }

    public LogicalPlan bind(OqlRequest request) {
        // 当前示例以首对象为主查询对象，后续可扩展为多对象 JOIN/关联路径。
        var target = request.getObjects().get(0);
        Map<String, ObjectSchema> snapshot = registry.getSnapshot(request.getSchemaRef());
        ObjectSchema schema = snapshot.get(target.objectType());
        if (schema == null) {
            throw new IllegalArgumentException("objectType not found: " + target.objectType());
        }

        // returns 为空时，按 identityField 最小投影。
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
