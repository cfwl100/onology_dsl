package com.onology.oac.queryframework.core;

import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.OqlModels.AggregateFilterKind;
import com.onology.oac.queryframework.domain.OqlModels.ConditionKind;
import com.onology.oac.queryframework.domain.OqlModels.ExpressionKind;
import com.onology.oac.queryframework.domain.OqlModels.OperationType;
import com.onology.oac.queryframework.domain.OqlModels.ReturnKind;
import com.onology.oac.queryframework.domain.ResultModels.OacError;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Composable OQL validator for query operations.
 */
public class OqlValidator {
    public ValidationResult validate(OqlModels.OqlQuery query) {
        List<OacError> errors = new ArrayList<>();
        if (query == null) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "query must not be null", "$"));
            return new ValidationResult(errors);
        }
        validateTopLevel(query, errors);
        validateAliasClosure(query, errors);
        validateReturns(query, errors);
        validateCondition(query.conditions(), "conditions", errors);
        validateAggregateFilter(query, errors);
        return new ValidationResult(errors);
    }

    private void validateTopLevel(OqlModels.OqlQuery query, List<OacError> errors) {
        if (query.operation() == null) {
            errors.add(OacError.of("UNKNOWN_OPERATION", "operation must not be null", "operation"));
            return;
        }
        if (query.schemaRef() == null || query.schemaRef().isBlank()) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "schemaRef must not be blank", "schemaRef"));
        }
        if ((query.operation() == OperationType.QUERY || query.operation() == OperationType.AGGREGATE)
                && (query.objects() == null || query.objects().isEmpty())) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", query.operation() + " requires objects", "objects"));
        }
        if ((query.operation() == OperationType.QUERY || query.operation() == OperationType.AGGREGATE
                || query.operation() == OperationType.ASSOCIATION_QUERY)
                && (query.returns() == null || query.returns().isEmpty())) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", query.operation() + " requires returns", "returns"));
        }
        if (query.operation() == OperationType.QUERY && query.relationships() != null && !query.relationships().isEmpty()) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "QUERY must not contain relationships", "relationships"));
        }
        if (query.operation() == OperationType.QUERY && query.aggregateFilter() != null) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "QUERY must not contain aggregateFilter", "aggregateFilter"));
        }
        if (query.operation() == OperationType.AGGREGATE && query.relationships() != null && !query.relationships().isEmpty()) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "AGGREGATE must not contain relationships", "relationships"));
        }
        if (query.operation() == OperationType.ASSOCIATION_QUERY
                && (query.relationships() == null || query.relationships().isEmpty())) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "ASSOCIATION_QUERY requires relationships", "relationships"));
        }
        if (query.operation() == OperationType.ASSOCIATION_QUERY && query.aggregateFilter() != null) {
            errors.add(OacError.of("OQL_VALIDATION_ERROR", "ASSOCIATION_QUERY must not contain aggregateFilter", "aggregateFilter"));
        }
    }

    private void validateAliasClosure(OqlModels.OqlQuery query, List<OacError> errors) {
        Set<String> aliases = new HashSet<>();
        if (query.objects() != null) {
            for (int i = 0; i < query.objects().size(); i++) {
                OqlModels.OqlObject object = query.objects().get(i);
                if (object.alias() == null || object.alias().isBlank()) {
                    errors.add(OacError.of("UNKNOWN_ALIAS", "object alias must not be blank", "objects[" + i + "].alias"));
                } else if (!aliases.add(object.alias())) {
                    errors.add(OacError.of("UNKNOWN_ALIAS", "duplicate alias: " + object.alias(), "objects[" + i + "].alias"));
                }
            }
        }
        if (query.relationships() != null) {
            for (int i = 0; i < query.relationships().size(); i++) {
                OqlModels.OqlRelationship relationship = query.relationships().get(i);
                if (relationship.alias() != null && aliases.contains(relationship.alias())) {
                    errors.add(OacError.of("UNKNOWN_ALIAS", "relationship alias conflicts with object alias: "
                            + relationship.alias(), "relationships[" + i + "].alias"));
                }
                if (!aliases.contains(relationship.from())) {
                    errors.add(OacError.of("UNKNOWN_ALIAS", "relationships.from references unknown alias: "
                            + relationship.from(), "relationships[" + i + "].from"));
                }
                if (!aliases.contains(relationship.to())) {
                    errors.add(OacError.of("UNKNOWN_ALIAS", "relationships.to references unknown alias: "
                            + relationship.to(), "relationships[" + i + "].to"));
                }
            }
        }
        validateConditionAliases(query.conditions(), aliases, "conditions", errors);
        if (query.returns() != null) {
            for (int i = 0; i < query.returns().size(); i++) {
                OqlModels.OqlReturnItem item = query.returns().get(i);
                if ((item.kind() == ReturnKind.FIELDS || item.kind() == ReturnKind.METRIC || item.kind() == ReturnKind.GROUP_BY)
                        && item.ref() != null && !aliases.contains(item.ref())) {
                    errors.add(OacError.of("UNKNOWN_ALIAS", "returns.ref references unknown alias: " + item.ref(),
                            "returns[" + i + "].ref"));
                }
            }
        }
    }

    private void validateReturns(OqlModels.OqlQuery query, List<OacError> errors) {
        if (query.returns() == null) {
            return;
        }
        boolean hasMetric = false;
        for (int i = 0; i < query.returns().size(); i++) {
            OqlModels.OqlReturnItem item = query.returns().get(i);
            if (item.kind() == null) {
                errors.add(OacError.of("INVALID_RETURN_KIND", "returns.kind must not be null", "returns[" + i + "].kind"));
                continue;
            }
            if (query.operation() == OperationType.AGGREGATE) {
                if (item.kind() != ReturnKind.GROUP_BY && item.kind() != ReturnKind.METRIC) {
                    errors.add(OacError.of("INVALID_RETURN_KIND", "AGGREGATE only allows GROUP_BY and METRIC",
                            "returns[" + i + "].kind"));
                }
                if (item.kind() == ReturnKind.METRIC) {
                    hasMetric = true;
                    if (item.function() == null) {
                        errors.add(OacError.of("INVALID_RETURN_KIND", "METRIC requires function", "returns[" + i + "].function"));
                    }
                    if (item.function() != OqlModels.AggregateFunction.COUNT && Objects.equals(item.field(), "*")) {
                        errors.add(OacError.of("INVALID_RETURN_KIND", "only COUNT allows field=*", "returns[" + i + "].field"));
                    }
                }
                if ((item.kind() == ReturnKind.METRIC || item.kind() == ReturnKind.GROUP_BY)
                        && (item.alias() == null || item.alias().isBlank())) {
                    errors.add(OacError.of("INVALID_RETURN_KIND", item.kind() + " requires alias", "returns[" + i + "].alias"));
                }
            } else if (item.kind() != ReturnKind.FIELDS && item.kind() != ReturnKind.EXPR) {
                errors.add(OacError.of("INVALID_RETURN_KIND", query.operation() + " only allows FIELDS and EXPR",
                        "returns[" + i + "].kind"));
            }
            if (item.kind() == ReturnKind.FIELDS && (item.fields() == null || item.fields().isEmpty())) {
                errors.add(OacError.of("INVALID_RETURN_KIND", "FIELDS requires explicit fields", "returns[" + i + "].fields"));
            }
            if ((item.kind() == ReturnKind.EXPR || item.kind() == ReturnKind.GROUP_BY) && item.expr() != null) {
                validateExpression(item.expr(), "returns[" + i + "].expr", errors);
            }
        }
        if (query.operation() == OperationType.AGGREGATE && !hasMetric) {
            errors.add(OacError.of("INVALID_RETURN_KIND", "AGGREGATE requires at least one METRIC", "returns"));
        }
    }

    private void validateCondition(OqlModels.OqlCondition condition, String path, List<OacError> errors) {
        if (condition == null) {
            return;
        }
        if (condition.kind() == ConditionKind.GROUP) {
            if (condition.children() == null || condition.children().isEmpty()) {
                errors.add(OacError.of("INVALID_CONDITION", "GROUP.children must not be empty", path + ".children"));
            } else {
                if (condition.relation() == OqlModels.GroupRelation.NOT && condition.children().size() != 1) {
                    errors.add(OacError.of("INVALID_CONDITION", "NOT group requires exactly one child", path + ".children"));
                }
                for (int i = 0; i < condition.children().size(); i++) {
                    validateCondition(condition.children().get(i), path + ".children[" + i + "]", errors);
                }
            }
        } else if (condition.kind() == ConditionKind.PREDICATE) {
            validateOperatorValues(condition.operator(), condition.values(), path, errors, "INVALID_CONDITION");
            if (condition.left() != null) {
                validateExpression(condition.left(), path + ".left", errors);
            }
        }
    }

    private void validateAggregateFilter(OqlModels.OqlQuery query, List<OacError> errors) {
        if (query.aggregateFilter() == null) {
            return;
        }
        if (query.operation() != OperationType.AGGREGATE) {
            errors.add(OacError.of("INVALID_AGGREGATE_FILTER", "aggregateFilter only allowed for AGGREGATE", "aggregateFilter"));
            return;
        }
        Set<String> metricAliases = new HashSet<>();
        if (query.returns() != null) {
            query.returns().stream()
                    .filter(r -> r.kind() == ReturnKind.METRIC)
                    .map(OqlModels.OqlReturnItem::alias)
                    .filter(Objects::nonNull)
                    .forEach(metricAliases::add);
        }
        validateAggregateFilterNode(query.aggregateFilter(), "aggregateFilter", metricAliases, errors);
    }

    private void validateAggregateFilterNode(OqlModels.OqlAggregateFilter filter, String path, Set<String> metricAliases,
                                             List<OacError> errors) {
        if (filter.kind() == AggregateFilterKind.METRIC_PREDICATE) {
            if (!metricAliases.contains(filter.metricAlias())) {
                errors.add(OacError.of("INVALID_AGGREGATE_FILTER", "metricAlias not found: " + filter.metricAlias(),
                        path + ".metricAlias"));
            }
            validateOperatorValues(filter.operator(), filter.values(), path, errors, "INVALID_AGGREGATE_FILTER");
        } else if (filter.kind() == AggregateFilterKind.GROUP) {
            if (filter.children() == null || filter.children().isEmpty()) {
                errors.add(OacError.of("INVALID_AGGREGATE_FILTER", "GROUP.children must not be empty", path + ".children"));
            } else {
                if (filter.relation() == OqlModels.GroupRelation.NOT && filter.children().size() != 1) {
                    errors.add(OacError.of("INVALID_AGGREGATE_FILTER", "NOT group requires exactly one child", path + ".children"));
                }
                for (int i = 0; i < filter.children().size(); i++) {
                    validateAggregateFilterNode(filter.children().get(i), path + ".children[" + i + "]", metricAliases, errors);
                }
            }
        }
    }

    private void validateConditionAliases(OqlModels.OqlCondition condition, Set<String> aliases, String path,
                                          List<OacError> errors) {
        if (condition == null) {
            return;
        }
        if (condition.ref() != null && !aliases.contains(condition.ref())) {
            errors.add(OacError.of("UNKNOWN_ALIAS", "condition ref references unknown alias: " + condition.ref(), path + ".ref"));
        }
        if (condition.left() != null) {
            validateExpressionAlias(condition.left(), aliases, path + ".left", errors);
        }
        if (condition.children() != null) {
            for (int i = 0; i < condition.children().size(); i++) {
                validateConditionAliases(condition.children().get(i), aliases, path + ".children[" + i + "]", errors);
            }
        }
    }

    private void validateExpressionAlias(OqlModels.OqlExpression expression, Set<String> aliases, String path,
                                         List<OacError> errors) {
        if (expression.kind() == ExpressionKind.FIELD && expression.ref() != null && !aliases.contains(expression.ref())) {
            errors.add(OacError.of("UNKNOWN_ALIAS", "FIELD.ref references unknown alias: " + expression.ref(), path + ".ref"));
        }
        if (expression.args() != null) {
            for (int i = 0; i < expression.args().size(); i++) {
                validateExpressionAlias(expression.args().get(i), aliases, path + ".args[" + i + "]", errors);
            }
        }
    }

    private void validateExpression(OqlModels.OqlExpression expression, String path, List<OacError> errors) {
        if (expression == null || expression.kind() == null) {
            errors.add(OacError.of("FUNCTION_NOT_SUPPORTED", "expression.kind must not be null", path));
            return;
        }
        if (expression.kind() == ExpressionKind.FUNCTION) {
            if (expression.name() == null || expression.name().isBlank()) {
                errors.add(OacError.of("UNREGISTERED_FUNCTION", "function name must not be blank", path + ".name"));
            }
            if (expression.name() != null && Set.of("COUNT", "SUM", "AVG", "MIN", "MAX").contains(expression.name())) {
                errors.add(OacError.of("FUNCTION_NOT_SUPPORTED", "aggregate function must use returns.kind=METRIC", path));
            }
        }
        if (expression.args() != null) {
            for (int i = 0; i < expression.args().size(); i++) {
                validateExpression(expression.args().get(i), path + ".args[" + i + "]", errors);
            }
        }
    }

    private void validateOperatorValues(OqlModels.Operator operator, List<Object> values, String path, List<OacError> errors,
                                        String code) {
        if (operator == null) {
            errors.add(OacError.of(code, "operator must not be null", path + ".operator"));
            return;
        }
        if (operator == OqlModels.Operator.BETWEEN && (values == null || values.size() != 2)) {
            errors.add(OacError.of(code, "BETWEEN requires exactly two values", path + ".values"));
        }
        if (Set.of(OqlModels.Operator.IS_NULL, OqlModels.Operator.IS_NOT_NULL, OqlModels.Operator.IS_EMPTY,
                OqlModels.Operator.IS_NOT_EMPTY, OqlModels.Operator.EXISTS, OqlModels.Operator.NOT_EXISTS).contains(operator)
                && values != null && !values.isEmpty()) {
            errors.add(OacError.of(code, operator + " must not contain values", path + ".values"));
        }
    }

    public record ValidationResult(List<OacError> errors) {
        public boolean isSuccess() {
            return errors == null || errors.isEmpty();
        }
    }
}
