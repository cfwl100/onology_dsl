package com.oac.query.validation;

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
import com.oac.query.dsl.OqlQuery.OperationType;
import com.oac.query.dsl.OqlQuery.PredicateCondition;
import com.oac.query.dsl.OqlQuery.RelationshipDecl;
import com.oac.query.dsl.OqlQuery.ReturnDecl;
import com.oac.query.dsl.OqlQuery.ReturnKind;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * OQL v2.0 查询文档的结构与语义校验器。
 *
 * 该类在绑定和执行前拦截 DSL 层面的非法请求，使错误以 OqlError 返回，
 * 避免无效请求继续流入数据源翻译器。
 */
public class OqlValidator {
    private static final Set<String> ALLOWED_TOP_LEVEL = new HashSet<String>(Arrays.asList(
            "version", "schemaRef", "strict", "operation", "objects", "relationships", "conditions",
            "returns", "aggregateFilter", "orders", "maxResults", "sourceQuery", "mutation", "options", "extensions"
    ));
    private static final Set<String> ALL_OPERATORS = new HashSet<String>(Arrays.asList(
            "EQ", "NE", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN", "BETWEEN", "LIKE", "CONTAINS",
            "STARTS_WITH", "ENDS_WITH", "IS_NULL", "IS_NOT_NULL", "IS_EMPTY", "IS_NOT_EMPTY",
            "EXISTS", "NOT_EXISTS"
    ));
    private static final Set<String> AGGREGATE_FILTER_OPERATORS = new HashSet<String>(Arrays.asList(
            "EQ", "NE", "GT", "GTE", "LT", "LTE", "BETWEEN", "IN", "NOT_IN", "IS_NULL", "IS_NOT_NULL"
    ));
    private static final Set<String> AGGREGATE_FUNCTIONS = new HashSet<String>(Arrays.asList("COUNT", "SUM", "AVG", "MIN", "MAX"));

    private final FunctionRegistry functionRegistry;

    public OqlValidator() {
        this(FunctionRegistry.withCoreFunctions());
    }

    public OqlValidator(FunctionRegistry functionRegistry) {
        this.functionRegistry = functionRegistry;
    }

    public ValidationResult validate(OqlQuery query) {
        ValidationResult result = ValidationResult.ok();
        if (query == null) {
            result.add("OQL_VALIDATION_ERROR", "query must not be null", "$");
            return result;
        }
        validateTopLevel(query, result);
        Set<String> objectAliases = validateObjects(query, result);
        Set<String> aliases = new LinkedHashSet<String>(objectAliases);
        aliases.addAll(relationshipAliases(query));
        if (query.getOperation() == null) {
            result.add("OQL_VALIDATION_ERROR", "operation must be a legal enum", "operation");
            return result;
        }
        switch (query.getOperation()) {
            case QUERY:
                validateQuery(query, aliases, result);
                break;
            case AGGREGATE:
                validateAggregate(query, aliases, result);
                break;
            case ASSOCIATION_QUERY:
                validateAssociationQuery(query, objectAliases, aliases, result);
                break;
            default:
                // v1 只实现查询闭环。写操作虽然已进入 DSL 枚举，
                // 但会在这里被明确拦截。
                result.add("UNSUPPORTED_OPERATION", "write and batch operations are not implemented in this query framework v1", "operation");
        }
        validateCondition(query.getConditions(), aliases, "conditions", result);
        return result;
    }

    private void validateTopLevel(OqlQuery query, ValidationResult result) {
        if (!OqlQuery.CURRENT_VERSION.equals(query.getVersion())) {
            result.add("OQL_VALIDATION_ERROR", "version must be " + OqlQuery.CURRENT_VERSION, "version");
        }
        if (blank(query.getSchemaRef())) {
            result.add("OQL_VALIDATION_ERROR", "schemaRef must not be empty", "schemaRef");
        }
        for (String field : query.getTopLevelFields()) {
            if (!ALLOWED_TOP_LEVEL.contains(field)) {
                String code = "having".equals(field) ? "OQL_HAVING_NOT_ALLOWED" : "OQL_UNKNOWN_FIELD";
                result.add(code, "top-level field is not allowed: " + field, field);
            }
        }
        if (query.hasTopLevelField("linkQuery")) {
            result.add("OQL_LINK_QUERY_NOT_ALLOWED", "linkQuery is not supported; use ASSOCIATION_QUERY relationships", "linkQuery");
        }
        if (query.getMaxResults() != null) {
            if (query.getMaxResults().getLimit() <= 0) {
                result.add("OQL_VALIDATION_ERROR", "maxResults.limit must be greater than 0", "maxResults.limit");
            }
            if (query.getMaxResults().getOffset() < 0) {
                result.add("OQL_VALIDATION_ERROR", "maxResults.offset must be greater than or equal to 0", "maxResults.offset");
            }
        }
    }

    private Set<String> validateObjects(OqlQuery query, ValidationResult result) {
        Set<String> aliases = new LinkedHashSet<String>();
        List<ObjectDecl> objects = query.getObjects();
        for (int i = 0; i < objects.size(); i++) {
            ObjectDecl object = objects.get(i);
            if (blank(object.getObjectType())) {
                result.add("OQL_VALIDATION_ERROR", "objects.objectType must not be empty", "objects[" + i + "].objectType");
            }
            if (blank(object.getAlias())) {
                result.add("OQL_VALIDATION_ERROR", "objects.alias must not be empty", "objects[" + i + "].alias");
            } else if (!aliases.add(object.getAlias())) {
                result.add("OQL_VALIDATION_ERROR", "object alias must be unique: " + object.getAlias(), "objects[" + i + "].alias");
            }
        }
        return aliases;
    }

    private void validateQuery(OqlQuery query, Set<String> aliases, ValidationResult result) {
        requireObjectsAndReturns(query, result);
        if (!query.getRelationships().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "QUERY must not contain relationships", "relationships");
        }
        if (query.getAggregateFilter() != null) {
            result.add("OQL_VALIDATION_ERROR", "QUERY must not contain aggregateFilter", "aggregateFilter");
        }
        if (!query.getMutation().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "QUERY must not contain mutation", "mutation");
        }
        validateReturnsForQuery(query.getReturns(), aliases, "returns", result);
    }

    private void validateAggregate(OqlQuery query, Set<String> aliases, ValidationResult result) {
        requireObjectsAndReturns(query, result);
        if (!query.getRelationships().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "AGGREGATE must not contain relationships", "relationships");
        }
        if (!query.getMutation().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "AGGREGATE must not contain mutation", "mutation");
        }
        Set<String> metricAliases = new LinkedHashSet<String>();
        boolean hasMetric = false;
        for (int i = 0; i < query.getReturns().size(); i++) {
            ReturnDecl ret = query.getReturns().get(i);
            if (ret.getKind() != ReturnKind.GROUP_BY && ret.getKind() != ReturnKind.METRIC) {
                result.add("OQL_VALIDATION_ERROR", "AGGREGATE returns only allow GROUP_BY and METRIC", "returns[" + i + "].kind");
                continue;
            }
            if (ret.getKind() == ReturnKind.METRIC) {
                hasMetric = true;
                validateMetricReturn(ret, i, aliases, result);
                if (!blank(ret.getAlias())) {
                    metricAliases.add(ret.getAlias());
                }
            } else {
                validateGroupByReturn(ret, i, aliases, result);
            }
        }
        if (!hasMetric) {
            result.add("OQL_VALIDATION_ERROR", "AGGREGATE returns must contain at least one METRIC", "returns");
        }
        validateAggregateFilter(query.getAggregateFilter(), metricAliases, "aggregateFilter", result);
    }

    private void validateAssociationQuery(OqlQuery query, Set<String> objectAliases, Set<String> aliases, ValidationResult result) {
        requireObjectsAndReturns(query, result);
        if (query.getRelationships().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "ASSOCIATION_QUERY must contain relationships", "relationships");
        }
        if (!query.getMutation().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "ASSOCIATION_QUERY must not contain mutation", "mutation");
        }
        for (int i = 0; i < query.getRelationships().size(); i++) {
            RelationshipDecl relationship = query.getRelationships().get(i);
            if (!objectAliases.contains(relationship.getFrom())) {
                result.add("OQL_VALIDATION_ERROR", "relationships.from must reference declared object alias", "relationships[" + i + "].from");
            }
            if (!objectAliases.contains(relationship.getTo())) {
                result.add("OQL_VALIDATION_ERROR", "relationships.to must reference declared object alias", "relationships[" + i + "].to");
            }
            if (objectAliases.contains(relationship.getAlias())) {
                result.add("OQL_VALIDATION_ERROR", "relationship alias must not conflict with object alias", "relationships[" + i + "].alias");
            }
        }
        validateReturnsForQuery(query.getReturns(), aliases, "returns", result);
    }

    private void validateReturnsForQuery(List<ReturnDecl> returns, Set<String> aliases, String path, ValidationResult result) {
        for (int i = 0; i < returns.size(); i++) {
            ReturnDecl ret = returns.get(i);
            if (ret.getKind() != ReturnKind.FIELDS && ret.getKind() != ReturnKind.EXPR) {
                result.add("OQL_VALIDATION_ERROR", "QUERY and ASSOCIATION_QUERY only allow FIELDS and EXPR returns", path + "[" + i + "].kind");
                continue;
            }
            if (ret.getKind() == ReturnKind.FIELDS) {
                if (!aliases.contains(ret.getRef())) {
                    result.add("OQL_VALIDATION_ERROR", "returns.ref must reference known alias: " + ret.getRef(), path + "[" + i + "].ref");
                }
                if (ret.getFields().isEmpty()) {
                    result.add("OQL_VALIDATION_ERROR", "FIELDS.fields must explicitly list fields", path + "[" + i + "].fields");
                }
                if (ret.getFields().contains("*")) {
                    result.add("OQL_VALIDATION_ERROR", "FIELDS.fields must not contain *", path + "[" + i + "].fields");
                }
            } else {
                if (blank(ret.getAlias())) {
                    result.add("OQL_VALIDATION_ERROR", "EXPR return must declare alias", path + "[" + i + "].alias");
                }
                validateExpr(ret.getExpr(), aliases, FunctionRegistry.RETURNS_EXPR, path + "[" + i + "].expr", result);
            }
        }
    }

    private void validateGroupByReturn(ReturnDecl ret, int i, Set<String> aliases, ValidationResult result) {
        if (blank(ret.getAlias())) {
            result.add("OQL_VALIDATION_ERROR", "GROUP_BY must declare alias", "returns[" + i + "].alias");
        }
        if (ret.getExpr() != null) {
            validateExpr(ret.getExpr(), aliases, FunctionRegistry.RETURNS_GROUP_BY_EXPR, "returns[" + i + "].expr", result);
        } else {
            if (!aliases.contains(ret.getRef())) {
                result.add("OQL_VALIDATION_ERROR", "GROUP_BY ref must reference known alias", "returns[" + i + "].ref");
            }
            if (blank(ret.getField())) {
                result.add("OQL_VALIDATION_ERROR", "GROUP_BY must use ref+field or expr", "returns[" + i + "].field");
            }
        }
    }

    private void validateMetricReturn(ReturnDecl ret, int i, Set<String> aliases, ValidationResult result) {
        if (blank(ret.getAlias())) {
            result.add("OQL_VALIDATION_ERROR", "METRIC must declare alias", "returns[" + i + "].alias");
        }
        String function = upper(ret.getFunction());
        if (!AGGREGATE_FUNCTIONS.contains(function)) {
            result.add("OQL_VALIDATION_ERROR", "METRIC.function must be COUNT/SUM/AVG/MIN/MAX", "returns[" + i + "].function");
        }
        if (!aliases.contains(ret.getRef())) {
            result.add("OQL_VALIDATION_ERROR", "METRIC ref must reference known alias", "returns[" + i + "].ref");
        }
        if (blank(ret.getField())) {
            result.add("OQL_VALIDATION_ERROR", "METRIC.field must not be empty", "returns[" + i + "].field");
        }
        if ("*".equals(ret.getField()) && !"COUNT".equals(function)) {
            result.add("OQL_VALIDATION_ERROR", "Only COUNT allows field = *", "returns[" + i + "].field");
        }
    }

    private void validateCondition(Condition condition, Set<String> aliases, String path, ValidationResult result) {
        if (condition == null) {
            return;
        }
        if (condition instanceof ConditionGroup) {
            ConditionGroup group = (ConditionGroup) condition;
            if (group.getChildren().isEmpty()) {
                result.add("OQL_VALIDATION_ERROR", "GROUP.children must not be empty", path + ".children");
            }
            if (group.getRelation() == OqlQuery.Relation.NOT && group.getChildren().size() != 1) {
                result.add("OQL_VALIDATION_ERROR", "GROUP.relation NOT must contain exactly one child", path + ".children");
            }
            for (int i = 0; i < group.getChildren().size(); i++) {
                validateCondition(group.getChildren().get(i), aliases, path + ".children[" + i + "]", result);
            }
            return;
        }
        PredicateCondition predicate = (PredicateCondition) condition;
        if (!ALL_OPERATORS.contains(upper(predicate.getOperator()))) {
            result.add("OQL_VALIDATION_ERROR", "conditions.operator is not supported: " + predicate.getOperator(), path + ".operator");
        }
        if (predicate.getLeft() == null) {
            if (!aliases.contains(predicate.getRef())) {
                result.add("OQL_VALIDATION_ERROR", "conditions.ref must reference known alias: " + predicate.getRef(), path + ".ref");
            }
            if (blank(predicate.getField())) {
                result.add("OQL_VALIDATION_ERROR", "PREDICATE must use ref+field or left", path + ".field");
            }
        } else {
            validateExpr(predicate.getLeft(), aliases, FunctionRegistry.CONDITIONS_LEFT, path + ".left", result);
        }
        validateValuesForOperator(predicate.getOperator(), predicate.getValues(), path + ".values", result);
    }

    private void validateAggregateFilter(AggregateFilter filter, Set<String> metricAliases, String path, ValidationResult result) {
        if (filter == null) {
            return;
        }
        if (filter instanceof AggregateFilterGroup) {
            AggregateFilterGroup group = (AggregateFilterGroup) filter;
            if (group.getChildren().isEmpty()) {
                result.add("OQL_VALIDATION_ERROR", "aggregateFilter GROUP.children must not be empty", path + ".children");
            }
            if (group.getRelation() == OqlQuery.Relation.NOT && group.getChildren().size() != 1) {
                result.add("OQL_VALIDATION_ERROR", "aggregateFilter NOT must contain exactly one child", path + ".children");
            }
            for (int i = 0; i < group.getChildren().size(); i++) {
                validateAggregateFilter(group.getChildren().get(i), metricAliases, path + ".children[" + i + "]", result);
            }
            return;
        }
        MetricPredicateFilter predicate = (MetricPredicateFilter) filter;
        if (!metricAliases.contains(predicate.getMetricAlias())) {
            result.add("OQL_VALIDATION_ERROR", "aggregateFilter.metricAlias must reference METRIC alias", path + ".metricAlias");
        }
        if (!AGGREGATE_FILTER_OPERATORS.contains(upper(predicate.getOperator()))) {
            result.add("OQL_VALIDATION_ERROR", "aggregateFilter.operator is not supported", path + ".operator");
        }
        validateValuesForOperator(predicate.getOperator(), predicate.getValues(), path + ".values", result);
    }

    private void validateExpr(Expr expr, Set<String> aliases, String location, String path, ValidationResult result) {
        if (expr == null) {
            result.add("OQL_VALIDATION_ERROR", "expression must not be empty", path);
            return;
        }
        if (expr instanceof FieldExpr) {
            FieldExpr field = (FieldExpr) expr;
            if (!aliases.contains(field.getRef())) {
                result.add("OQL_VALIDATION_ERROR", "FIELD.ref must reference known alias: " + field.getRef(), path + ".ref");
            }
            if (blank(field.getField())) {
                result.add("OQL_VALIDATION_ERROR", "FIELD.field must not be empty", path + ".field");
            }
            return;
        }
        if (expr instanceof FunctionExpr) {
            validateFunction((FunctionExpr) expr, aliases, location, path, result);
        }
    }

    private void validateFunction(FunctionExpr function, Set<String> aliases, String location, String path, ValidationResult result) {
        String name = upper(function.getName());
        if (AGGREGATE_FUNCTIONS.contains(name)) {
            result.add("OQL_VALIDATION_ERROR", "aggregate functions must be expressed with returns.kind = METRIC", path + ".name");
        }
        FunctionDescriptor descriptor = functionRegistry.resolve(function.getNamespace(), name);
        if (descriptor == null) {
            result.add(OqlError.of("UNREGISTERED_FUNCTION", "Function is not registered in OAC function registry.", path)
                    .detail("namespace", function.getNamespace())
                    .detail("name", function.getName()));
        } else {
            if (!descriptor.allows(location)) {
                result.add("OQL_VALIDATION_ERROR", "FUNCTION is not allowed in " + location, path);
            }
            int argSize = function.getArgs().size();
            if (argSize < descriptor.getMinArgs() || argSize > descriptor.getMaxArgs()) {
                result.add("OQL_VALIDATION_ERROR", "FUNCTION args count does not match registry declaration", path + ".args");
            }
        }
        for (int i = 0; i < function.getArgs().size(); i++) {
            validateExpr(function.getArgs().get(i), aliases, location, path + ".args[" + i + "]", result);
        }
    }

    private void validateValuesForOperator(String operator, List<Object> values, String path, ValidationResult result) {
        String op = upper(operator);
        int size = values == null ? 0 : values.size();
        if ("BETWEEN".equals(op) && size != 2) {
            result.add("OQL_VALIDATION_ERROR", "BETWEEN must contain exactly two values", path);
        } else if (Arrays.asList("IS_NULL", "IS_NOT_NULL", "IS_EMPTY", "IS_NOT_EMPTY", "EXISTS", "NOT_EXISTS").contains(op) && size != 0) {
            result.add("OQL_VALIDATION_ERROR", op + " must not contain values", path);
        } else if (Arrays.asList("EQ", "NE", "GT", "GTE", "LT", "LTE", "LIKE", "CONTAINS", "STARTS_WITH", "ENDS_WITH").contains(op) && size != 1) {
            result.add("OQL_VALIDATION_ERROR", op + " must contain exactly one value", path);
        } else if (Arrays.asList("IN", "NOT_IN").contains(op) && size == 0) {
            result.add("OQL_VALIDATION_ERROR", op + " must contain at least one value", path);
        }
    }

    private void requireObjectsAndReturns(OqlQuery query, ValidationResult result) {
        if (query.getObjects().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "objects must not be empty", "objects");
        }
        if (query.getReturns().isEmpty()) {
            result.add("OQL_VALIDATION_ERROR", "returns must not be empty", "returns");
        }
    }

    private Set<String> relationshipAliases(OqlQuery query) {
        Set<String> aliases = new LinkedHashSet<String>();
        for (RelationshipDecl relationship : query.getRelationships()) {
            if (!blank(relationship.getAlias())) {
                aliases.add(relationship.getAlias());
            }
        }
        return aliases;
    }

    private boolean blank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String upper(String value) {
        return value == null ? "" : value.trim().toUpperCase();
    }
}
