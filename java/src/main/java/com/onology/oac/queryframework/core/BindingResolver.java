package com.onology.oac.queryframework.core;

import com.onology.oac.queryframework.domain.MetadataModels.BindingMetadataProvider;
import com.onology.oac.queryframework.domain.MetadataModels.DatasourceCapability;
import com.onology.oac.queryframework.domain.MetadataModels.DatasourceCapabilityProvider;
import com.onology.oac.queryframework.domain.MetadataModels.OntologyMetadataProvider;
import com.onology.oac.queryframework.domain.MetadataModels.PropertyBinding;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.OqlModels.ReturnKind;
import com.onology.oac.queryframework.domain.PlanModels;
import com.onology.oac.queryframework.domain.ResultModels.OacError;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Resolves OQL aliases and ontology fields to physical datasource bindings. */
public class BindingResolver {
    private final OntologyMetadataProvider ontologyMetadataProvider;
    private final BindingMetadataProvider bindingMetadataProvider;
    private final DatasourceCapabilityProvider capabilityProvider;

    public BindingResolver(OntologyMetadataProvider ontologyMetadataProvider,
                           BindingMetadataProvider bindingMetadataProvider,
                           DatasourceCapabilityProvider capabilityProvider) {
        this.ontologyMetadataProvider = ontologyMetadataProvider;
        this.bindingMetadataProvider = bindingMetadataProvider;
        this.capabilityProvider = capabilityProvider;
    }

    public BindingResult resolve(OqlModels.OqlQuery query) {
        List<OacError> errors = new ArrayList<>();
        List<PlanModels.ObjectBindingNode> objects = new ArrayList<>();
        List<PlanModels.PropertyBindingNode> properties = new ArrayList<>();
        List<PlanModels.RelationshipBindingNode> relationships = new ArrayList<>();
        List<PlanModels.PhysicalBindingNode> physicalNodes = new ArrayList<>();
        List<PlanModels.BindingEdge> edges = new ArrayList<>();
        Map<String, DatasourceCapability> capabilities = new LinkedHashMap<>();
        Map<String, String> aliasToObjectType = new LinkedHashMap<>();

        if (query.objects() != null) {
            for (OqlModels.OqlObject object : query.objects()) {
                ontologyMetadataProvider.findObjectType(query.schemaRef(), object.objectType()).ifPresentOrElse(found -> {
                    objects.add(new PlanModels.ObjectBindingNode(object.alias(), object.objectType()));
                    aliasToObjectType.put(object.alias(), object.objectType());
                }, () -> errors.add(OacError.of("UNKNOWN_OBJECT_TYPE", "objectType not found: " + object.objectType(), "objects")));
            }
        }

        Set<FieldRef> fieldRefs = collectFieldRefs(query);
        for (FieldRef fieldRef : fieldRefs) {
            String objectType = aliasToObjectType.get(fieldRef.ref());
            if (objectType == null) {
                continue;
            }
            if (ontologyMetadataProvider.findProperty(query.schemaRef(), objectType, fieldRef.field()).isEmpty()) {
                errors.add(OacError.of("UNKNOWN_FIELD", "field not found: " + fieldRef.field(), fieldRef.path()));
                continue;
            }
            List<PropertyBinding> bindings = bindingMetadataProvider.findPropertyBindings(query.schemaRef(), objectType, fieldRef.field());
            if (bindings.isEmpty()) {
                errors.add(OacError.of("PROPERTY_BINDING_NOT_FOUND", "property binding not found: " + objectType + "." + fieldRef.field(), fieldRef.path()));
                continue;
            }
            for (PropertyBinding binding : bindings) {
                properties.add(new PlanModels.PropertyBindingNode(fieldRef.ref(), objectType, fieldRef.field(), binding));
                physicalNodes.add(PlanModels.PhysicalBindingNode.from(binding));
                edges.add(new PlanModels.BindingEdge(fieldRef.ref() + "." + fieldRef.field(), binding.datasourceId() + "." + binding.fieldName(), "BINDS_TO"));
                capabilityProvider.findCapability(binding.datasourceId()).ifPresent(capability -> capabilities.put(binding.datasourceId(), capability));
            }
        }

        if (query.relationships() != null) {
            for (OqlModels.OqlRelationship relationship : query.relationships()) {
                if (ontologyMetadataProvider.findRelationshipType(query.schemaRef(), relationship.relationshipType()).isEmpty()) {
                    errors.add(OacError.of("UNKNOWN_RELATIONSHIP_TYPE", "relationshipType not found: " + relationship.relationshipType(), "relationships"));
                    continue;
                }
                bindingMetadataProvider.findRelationshipBinding(query.schemaRef(), relationship.relationshipType()).ifPresentOrElse(binding -> {
                    relationships.add(new PlanModels.RelationshipBindingNode(relationship.alias(), binding));
                    capabilityProvider.findCapability(binding.datasourceId()).ifPresent(capability -> capabilities.put(binding.datasourceId(), capability));
                }, () -> errors.add(OacError.of("RELATIONSHIP_BINDING_NOT_FOUND", "relationship binding not found: " + relationship.relationshipType(), "relationships")));
            }
        }

        return new BindingResult(new PlanModels.BindingGraph(objects, properties, relationships, physicalNodes, edges, capabilities), errors);
    }

    private Set<FieldRef> collectFieldRefs(OqlModels.OqlQuery query) {
        Set<FieldRef> refs = new LinkedHashSet<>();
        if (query.returns() != null) {
            for (int i = 0; i < query.returns().size(); i++) {
                OqlModels.OqlReturnItem item = query.returns().get(i);
                if (item.kind() == ReturnKind.FIELDS && item.fields() != null) {
                    for (String field : item.fields()) {
                        refs.add(new FieldRef(item.ref(), field, "returns[" + i + "].fields"));
                    }
                }
                if ((item.kind() == ReturnKind.GROUP_BY || item.kind() == ReturnKind.METRIC) && item.ref() != null && item.field() != null && !"*".equals(item.field())) {
                    refs.add(new FieldRef(item.ref(), item.field(), "returns[" + i + "].field"));
                }
                collectExpressionRefs(item.expr(), "returns[" + i + "].expr", refs);
            }
        }
        collectConditionRefs(query.conditions(), "conditions", refs);
        if (query.orders() != null) {
            for (int i = 0; i < query.orders().size(); i++) {
                OqlModels.OqlOrder order = query.orders().get(i);
                if (order.ref() != null && order.field() != null) {
                    refs.add(new FieldRef(order.ref(), order.field(), "orders[" + i + "].field"));
                }
            }
        }
        return refs;
    }

    private void collectConditionRefs(OqlModels.OqlCondition condition, String path, Set<FieldRef> refs) {
        if (condition == null) {
            return;
        }
        if (condition.ref() != null && condition.field() != null) {
            refs.add(new FieldRef(condition.ref(), condition.field(), path + ".field"));
        }
        collectExpressionRefs(condition.left(), path + ".left", refs);
        if (condition.children() != null) {
            for (int i = 0; i < condition.children().size(); i++) {
                collectConditionRefs(condition.children().get(i), path + ".children[" + i + "]", refs);
            }
        }
    }

    private void collectExpressionRefs(OqlModels.OqlExpression expr, String path, Set<FieldRef> refs) {
        if (expr == null) {
            return;
        }
        if (expr.kind() == OqlModels.ExpressionKind.FIELD && expr.ref() != null && expr.field() != null) {
            refs.add(new FieldRef(expr.ref(), expr.field(), path + ".field"));
        }
        if (expr.args() != null) {
            for (int i = 0; i < expr.args().size(); i++) {
                collectExpressionRefs(expr.args().get(i), path + ".args[" + i + "]", refs);
            }
        }
    }

    public record BindingResult(PlanModels.BindingGraph bindingGraph, List<OacError> errors) {
        public boolean isSuccess() {
            return errors == null || errors.isEmpty();
        }
    }

    private record FieldRef(String ref, String field, String path) {
    }
}
