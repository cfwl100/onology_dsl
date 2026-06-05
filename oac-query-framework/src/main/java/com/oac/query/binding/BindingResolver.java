package com.oac.query.binding;

import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.AggregateFilter;
import com.oac.query.dsl.OqlQuery.AggregateFilterGroup;
import com.oac.query.dsl.OqlQuery.Condition;
import com.oac.query.dsl.OqlQuery.ConditionGroup;
import com.oac.query.dsl.OqlQuery.Expr;
import com.oac.query.dsl.OqlQuery.FieldExpr;
import com.oac.query.dsl.OqlQuery.FunctionExpr;
import com.oac.query.dsl.OqlQuery.MetricPredicateFilter;
import com.oac.query.dsl.OqlQuery.ObjectDecl;
import com.oac.query.dsl.OqlQuery.PredicateCondition;
import com.oac.query.dsl.OqlQuery.RelationshipDecl;
import com.oac.query.dsl.OqlQuery.ReturnDecl;
import com.oac.query.dsl.OqlQuery.ReturnKind;
import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.List;

/**
 * 将本体别名和逻辑字段解析为可信的物理绑定。
 *
 * 翻译器只能消费 BindingGraph 中的标识符，不能直接使用用户传入的表名、索引名或字段名。
 */
public class BindingResolver {
    private final MockOntologyMetadata metadata;

    public BindingResolver() {
        this(MockOntologyMetadata.defaults());
    }

    public BindingResolver(MockOntologyMetadata metadata) {
        this.metadata = metadata;
    }

    public BindingResult resolve(OqlQuery query) {
        List<OqlError> errors = new ArrayList<OqlError>();
        BindingGraph graph = new BindingGraph();
        for (ObjectDecl object : query.getObjects()) {
            try {
                graph.addObjectBinding(object.getAlias(), metadata.objectBinding(object.getObjectType()));
                if (object.getFromSource() != null && !object.getFromSource().trim().isEmpty()) {
                    graph.setDependencyRequired(true);
                }
            } catch (IllegalArgumentException e) {
                errors.add(OqlError.of("OQL_BINDING_ERROR", e.getMessage(), "objects").alias(object.getAlias()).objectType(object.getObjectType()));
            }
        }
        for (RelationshipDecl relationship : query.getRelationships()) {
            try {
                graph.addRelationshipBinding(relationship.getAlias(), metadata.relationshipBinding(relationship.getRelationshipType()));
            } catch (IllegalArgumentException e) {
                errors.add(OqlError.of("OQL_BINDING_ERROR", e.getMessage(), "relationships").alias(relationship.getAlias()));
            }
        }
        validateReferencedFields(query, graph, errors);
        return errors.isEmpty() ? BindingResult.success(graph) : BindingResult.failure(errors);
    }

    private void validateReferencedFields(OqlQuery query, BindingGraph graph, List<OqlError> errors) {
        validateConditionFields(query.getConditions(), graph, errors);
        validateReturns(query, graph, errors);
        validateAggregateFilter(query.getAggregateFilter(), errors);
    }

    private void validateConditionFields(Condition condition, BindingGraph graph, List<OqlError> errors) {
        if (condition == null) {
            return;
        }
        if (condition instanceof ConditionGroup) {
            for (Condition child : ((ConditionGroup) condition).getChildren()) {
                validateConditionFields(child, graph, errors);
            }
            return;
        }
        PredicateCondition predicate = (PredicateCondition) condition;
        if (predicate.getLeft() != null) {
            validateExpr(predicate.getLeft(), graph, errors, "conditions.left");
        } else {
            ensureField(graph, predicate.getRef(), predicate.getField(), "conditions.field", errors);
        }
    }

    private void validateReturns(OqlQuery query, BindingGraph graph, List<OqlError> errors) {
        for (ReturnDecl ret : query.getReturns()) {
            if (ret.getKind() == ReturnKind.FIELDS) {
                for (String field : ret.getFields()) {
                    ensureField(graph, ret.getRef(), field, "returns.fields", errors);
                }
            } else if (ret.getKind() == ReturnKind.GROUP_BY) {
                if (ret.getExpr() != null) {
                    validateExpr(ret.getExpr(), graph, errors, "returns.expr");
                } else {
                    ensureField(graph, ret.getRef(), ret.getField(), "returns.field", errors);
                }
            } else if (ret.getKind() == ReturnKind.METRIC && !"*".equals(ret.getField())) {
                ensureField(graph, ret.getRef(), ret.getField(), "returns.field", errors);
            } else if (ret.getExpr() != null) {
                validateExpr(ret.getExpr(), graph, errors, "returns.expr");
            }
        }
    }

    private void validateAggregateFilter(AggregateFilter filter, List<OqlError> errors) {
        if (filter == null || filter instanceof MetricPredicateFilter) {
            return;
        }
        for (AggregateFilter child : ((AggregateFilterGroup) filter).getChildren()) {
            validateAggregateFilter(child, errors);
        }
    }

    private void validateExpr(Expr expr, BindingGraph graph, List<OqlError> errors, String path) {
        if (expr instanceof FieldExpr) {
            FieldExpr field = (FieldExpr) expr;
            ensureField(graph, field.getRef(), field.getField(), path, errors);
        } else if (expr instanceof FunctionExpr) {
            for (Expr arg : ((FunctionExpr) expr).getArgs()) {
                validateExpr(arg, graph, errors, path + ".args");
            }
        }
    }

    private void ensureField(BindingGraph graph, String alias, String field, String path, List<OqlError> errors) {
        BindingGraph.ObjectBinding object = graph.objectBinding(alias);
        if (object == null) {
            return;
        }
        if (field == null || "*".equals(field)) {
            return;
        }
        if (object.field(field) == null) {
            errors.add(OqlError.of("OQL_BINDING_ERROR", "field is not bound in ontology metadata", path)
                    .alias(alias)
                    .objectType(object.getObjectType())
                    .field(field));
        }
    }
}
