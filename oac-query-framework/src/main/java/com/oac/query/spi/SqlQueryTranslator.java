package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.AggregateFilter;
import com.oac.query.dsl.OqlQuery.AggregateFilterGroup;
import com.oac.query.dsl.OqlQuery.Condition;
import com.oac.query.dsl.OqlQuery.ConditionGroup;
import com.oac.query.dsl.OqlQuery.Expr;
import com.oac.query.dsl.OqlQuery.FieldExpr;
import com.oac.query.dsl.OqlQuery.FunctionExpr;
import com.oac.query.dsl.OqlQuery.MetricPredicateFilter;
import com.oac.query.dsl.OqlQuery.OperationType;
import com.oac.query.dsl.OqlQuery.OrderDecl;
import com.oac.query.dsl.OqlQuery.PredicateCondition;
import com.oac.query.dsl.OqlQuery.ReturnDecl;
import com.oac.query.dsl.OqlQuery.ReturnKind;
import com.oac.query.dsl.OqlQuery.ValueExpr;
import com.oac.query.plan.physical.PhysicalFieldBinding;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.spi.PhysicalQueries.SqlPhysicalQuery;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * SQL 数据源翻译器。
 *
 * 该类只使用 BindingGraph 下沉到 PhysicalSourceQueryNode 的可信表名和列名；
 * OQL 中的用户值全部转换为命名参数，避免直接拼接到 SQL 文本中。
 */
public class SqlQueryTranslator implements QueryTranslator<PhysicalQuery> {
    public DatasourceType supportType() {
        return DatasourceType.SQL;
    }

    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.getDatasourceType() == DatasourceType.SQL;
    }

    public PhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        SqlBuildContext sql = new SqlBuildContext(fragment);
        String payload;
        if (fragment.getOperation() == OperationType.AGGREGATE) {
            payload = buildAggregateSql(fragment, sql);
        } else {
            payload = buildQuerySql(fragment, sql);
        }

        Map<String, Object> queryParameters = new LinkedHashMap<String, Object>();
        queryParameters.put("namedParameters", sql.getParameters());
        queryParameters.put("dynamicInputs", fragment.getDynamicInputs());
        queryParameters.put("projections", fragment.getProjections());
        return new SqlPhysicalQuery(fragment.getId(), fragment.getDatasourceId(), payload, queryParameters);
    }

    private String buildQuerySql(PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        StringBuilder builder = new StringBuilder();
        builder.append("SELECT ");
        builder.append(join(selectItems(fragment, sql), ", "));
        builder.append(" FROM ");
        builder.append(fromClause(sql));
        appendWhere(builder, fragment, sql);
        appendOrder(builder, fragment, sql);
        appendLimit(builder, fragment, sql);
        return builder.toString();
    }

    private String buildAggregateSql(PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        List<String> selectItems = new ArrayList<String>();
        List<String> groupByItems = new ArrayList<String>();
        for (ReturnDecl ret : fragment.getReturns()) {
            if (ret.getKind() == ReturnKind.GROUP_BY) {
                String expression = groupByExpression(ret, fragment, sql);
                groupByItems.add(expression);
                selectItems.add(expression + " AS " + quoteIdentifier(aliasOrField(ret)));
            } else if (ret.getKind() == ReturnKind.METRIC) {
                selectItems.add(metricExpression(ret, fragment, sql) + " AS " + quoteIdentifier(ret.getAlias()));
            }
        }
        if (selectItems.isEmpty()) {
            selectItems.add("COUNT(*) AS " + quoteIdentifier("count"));
        }

        StringBuilder builder = new StringBuilder();
        builder.append("SELECT ");
        builder.append(join(selectItems, ", "));
        builder.append(" FROM ");
        builder.append(fromClause(sql));
        appendWhere(builder, fragment, sql);
        if (!groupByItems.isEmpty()) {
            builder.append(" GROUP BY ").append(join(groupByItems, ", "));
        }
        appendHaving(builder, fragment.getAggregateFilter(), sql);
        appendOrder(builder, fragment, sql);
        appendLimit(builder, fragment, sql);
        return builder.toString();
    }

    private List<String> selectItems(PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        List<String> items = new ArrayList<String>();
        if (fragment.getReturns().isEmpty()) {
            for (String projection : fragment.getProjections()) {
                items.add(columnExpression(fragment, null, projection, sql) + " AS " + quoteIdentifier(projection));
            }
            return items;
        }
        for (ReturnDecl ret : fragment.getReturns()) {
            if (ret.getKind() == ReturnKind.FIELDS) {
                for (String field : ret.getFields()) {
                    if (fragment.findFieldBinding(ret.getRef(), field) != null || fragment.getFieldBindings().isEmpty()) {
                        items.add(columnExpression(fragment, ret.getRef(), field, sql) + " AS " + quoteIdentifier(field));
                    }
                }
            } else if (ret.getKind() == ReturnKind.EXPR) {
                items.add(expression(ret.getExpr(), fragment, sql) + " AS " + quoteIdentifier(aliasOrField(ret)));
            }
        }
        if (items.isEmpty()) {
            for (String projection : fragment.getProjections()) {
                items.add(columnExpression(fragment, null, projection, sql) + " AS " + quoteIdentifier(projection));
            }
        }
        return items;
    }

    private void appendWhere(StringBuilder builder, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        List<String> predicates = new ArrayList<String>();
        String conditionSql = condition(fragment.getCondition(), fragment, sql);
        if (conditionSql != null && !conditionSql.trim().isEmpty()) {
            predicates.add(conditionSql);
        }
        predicates.addAll(dynamicInputPredicates(fragment, sql));
        if (!predicates.isEmpty()) {
            builder.append(" WHERE ").append(join(predicates, " AND "));
        }
    }

    private String condition(Condition condition, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (condition == null) {
            return null;
        }
        if (condition instanceof ConditionGroup) {
            ConditionGroup group = (ConditionGroup) condition;
            List<String> children = new ArrayList<String>();
            for (Condition child : group.getChildren()) {
                String childSql = condition(child, fragment, sql);
                if (childSql != null && !childSql.trim().isEmpty()) {
                    children.add(childSql);
                }
            }
            if (children.isEmpty()) {
                return null;
            }
            if (group.getRelation() == OqlQuery.Relation.NOT) {
                return "NOT (" + children.get(0) + ")";
            }
            String relation = group.getRelation() == null ? "AND" : group.getRelation().name();
            return "(" + join(children, " " + relation + " ") + ")";
        }

        PredicateCondition predicate = (PredicateCondition) condition;
        if (predicate.getSubquery() != null) {
            throw new IllegalArgumentException("SQL subquery translation is not implemented in v1");
        }
        String left = predicate.getLeft() == null
                ? columnExpression(fragment, predicate.getRef(), predicate.getField(), sql)
                : expression(predicate.getLeft(), fragment, sql);
        return predicateSql(left, predicate.getOperator(), predicate.getValues(), sql);
    }

    private List<String> dynamicInputPredicates(PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (fragment.getDynamicInputs().isEmpty()) {
            return Collections.emptyList();
        }
        List<String> predicates = new ArrayList<String>();
        for (Map.Entry<String, List<Object>> entry : fragment.getDynamicInputs().entrySet()) {
            List<Object> values = entry.getValue();
            if (values == null || values.isEmpty()) {
                continue;
            }
            String left = columnExpression(fragment, null, entry.getKey(), sql);
            predicates.add(left + " IN (" + sql.parameters(values, "d") + ")");
        }
        return predicates;
    }

    private void appendHaving(StringBuilder builder, AggregateFilter filter, SqlBuildContext sql) {
        String having = aggregateFilter(filter, sql);
        if (having != null && !having.trim().isEmpty()) {
            builder.append(" HAVING ").append(having);
        }
    }

    private String aggregateFilter(AggregateFilter filter, SqlBuildContext sql) {
        if (filter == null) {
            return null;
        }
        if (filter instanceof AggregateFilterGroup) {
            AggregateFilterGroup group = (AggregateFilterGroup) filter;
            List<String> children = new ArrayList<String>();
            for (AggregateFilter child : group.getChildren()) {
                String childSql = aggregateFilter(child, sql);
                if (childSql != null && !childSql.trim().isEmpty()) {
                    children.add(childSql);
                }
            }
            if (children.isEmpty()) {
                return null;
            }
            if (group.getRelation() == OqlQuery.Relation.NOT) {
                return "NOT (" + children.get(0) + ")";
            }
            String relation = group.getRelation() == null ? "AND" : group.getRelation().name();
            return "(" + join(children, " " + relation + " ") + ")";
        }
        MetricPredicateFilter predicate = (MetricPredicateFilter) filter;
        return predicateSql(quoteIdentifier(predicate.getMetricAlias()), predicate.getOperator(), predicate.getValues(), sql);
    }

    private void appendOrder(StringBuilder builder, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (fragment.getOrders().isEmpty()) {
            return;
        }
        List<String> orderItems = new ArrayList<String>();
        for (OrderDecl order : fragment.getOrders()) {
            String direction = "DESC".equalsIgnoreCase(order.getDirection()) ? "DESC" : "ASC";
            String expression = orderExpression(order, fragment, sql);
            if (expression != null) {
                orderItems.add(expression + " " + direction);
            }
        }
        if (!orderItems.isEmpty()) {
            builder.append(" ORDER BY ").append(join(orderItems, ", "));
        }
    }

    private void appendLimit(StringBuilder builder, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (fragment.getMaxResults() == null) {
            return;
        }
        builder.append(" LIMIT ").append(sql.parameter("limit", fragment.getMaxResults().getLimit()));
        if (fragment.getMaxResults().getOffset() > 0) {
            builder.append(" OFFSET ").append(sql.parameter("offset", fragment.getMaxResults().getOffset()));
        }
    }

    private String orderExpression(OrderDecl order, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (order.getRef() == null || fragment.findFieldBinding(order.getRef(), order.getField()) != null || fragment.getFieldBindings().isEmpty()) {
            return columnExpression(fragment, order.getRef(), order.getField(), sql);
        }
        return quoteIdentifier(order.getField());
    }

    private String groupByExpression(ReturnDecl ret, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (ret.getExpr() != null) {
            return expression(ret.getExpr(), fragment, sql);
        }
        return columnExpression(fragment, ret.getRef(), ret.getField(), sql);
    }

    private String metricExpression(ReturnDecl ret, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        String function = ret.getFunction() == null ? "COUNT" : ret.getFunction().trim().toUpperCase(Locale.ROOT);
        if ("COUNT".equals(function) && "*".equals(ret.getField())) {
            return "COUNT(*)";
        }
        return function + "(" + columnExpression(fragment, ret.getRef(), ret.getField(), sql) + ")";
    }

    private String expression(Expr expr, PhysicalSourceQueryNode fragment, SqlBuildContext sql) {
        if (expr instanceof FieldExpr) {
            FieldExpr field = (FieldExpr) expr;
            return columnExpression(fragment, field.getRef(), field.getField(), sql);
        }
        if (expr instanceof ValueExpr) {
            return sql.parameter("p", ((ValueExpr) expr).getValue());
        }
        if (expr instanceof FunctionExpr) {
            FunctionExpr function = (FunctionExpr) expr;
            List<String> args = new ArrayList<String>();
            for (Expr arg : function.getArgs()) {
                args.add(expression(arg, fragment, sql));
            }
            return functionName(function) + "(" + join(args, ", ") + ")";
        }
        throw new IllegalArgumentException("Unsupported SQL expression type");
    }

    private String predicateSql(String left, String operator, List<Object> values, SqlBuildContext sql) {
        String op = operator == null ? "" : operator.trim().toUpperCase(Locale.ROOT);
        if ("EQ".equals(op)) {
            return left + " = " + sql.parameter("p", first(values));
        }
        if ("NE".equals(op)) {
            return left + " <> " + sql.parameter("p", first(values));
        }
        if ("GT".equals(op)) {
            return left + " > " + sql.parameter("p", first(values));
        }
        if ("GTE".equals(op)) {
            return left + " >= " + sql.parameter("p", first(values));
        }
        if ("LT".equals(op)) {
            return left + " < " + sql.parameter("p", first(values));
        }
        if ("LTE".equals(op)) {
            return left + " <= " + sql.parameter("p", first(values));
        }
        if ("IN".equals(op)) {
            return left + " IN (" + sql.parameters(values, "p") + ")";
        }
        if ("NOT_IN".equals(op)) {
            return left + " NOT IN (" + sql.parameters(values, "p") + ")";
        }
        if ("BETWEEN".equals(op)) {
            return left + " BETWEEN " + sql.parameter("p", values.get(0)) + " AND " + sql.parameter("p", values.get(1));
        }
        if ("LIKE".equals(op)) {
            return left + " LIKE " + sql.parameter("p", first(values));
        }
        if ("CONTAINS".equals(op)) {
            return left + " LIKE " + sql.parameter("p", "%" + first(values) + "%");
        }
        if ("STARTS_WITH".equals(op)) {
            return left + " LIKE " + sql.parameter("p", first(values) + "%");
        }
        if ("ENDS_WITH".equals(op)) {
            return left + " LIKE " + sql.parameter("p", "%" + first(values));
        }
        if ("IS_NULL".equals(op) || "NOT_EXISTS".equals(op)) {
            return left + " IS NULL";
        }
        if ("IS_NOT_NULL".equals(op) || "EXISTS".equals(op)) {
            return left + " IS NOT NULL";
        }
        if ("IS_EMPTY".equals(op)) {
            return "(" + left + " IS NULL OR " + left + " = '')";
        }
        if ("IS_NOT_EMPTY".equals(op)) {
            return "(" + left + " IS NOT NULL AND " + left + " <> '')";
        }
        throw new IllegalArgumentException("Unsupported SQL operator: " + operator);
    }

    private Object first(List<Object> values) {
        if (values == null || values.isEmpty()) {
            throw new IllegalArgumentException("SQL predicate value is required");
        }
        return values.get(0);
    }

    private String columnExpression(PhysicalSourceQueryNode fragment, String ref, String field, SqlBuildContext sql) {
        PhysicalFieldBinding binding = fragment.findFieldBinding(ref, field);
        if (binding != null) {
            return sql.tableAlias(binding.getPhysicalContainer()) + "." + quoteIdentifier(binding.getPhysicalField());
        }
        String tableAlias = sql.defaultTableAlias();
        return tableAlias + "." + quoteIdentifier(field);
    }

    private String fromClause(SqlBuildContext sql) {
        List<String> tables = new ArrayList<String>();
        for (Map.Entry<String, String> entry : sql.getTableAliases().entrySet()) {
            tables.add(quoteIdentifier(entry.getKey()) + " " + entry.getValue());
        }
        return join(tables, ", ");
    }

    private String functionName(FunctionExpr function) {
        String namespace = function.getNamespace();
        String name = function.getName() == null ? "" : function.getName().trim().toUpperCase(Locale.ROOT);
        if (namespace == null || namespace.trim().isEmpty() || "core".equalsIgnoreCase(namespace)) {
            return name;
        }
        return namespace.trim() + "." + name;
    }

    private String aliasOrField(ReturnDecl ret) {
        if (ret.getAlias() != null && !ret.getAlias().trim().isEmpty()) {
            return ret.getAlias();
        }
        if (ret.getField() != null && !ret.getField().trim().isEmpty()) {
            return ret.getField();
        }
        return "expr";
    }

    private static String quoteIdentifier(String identifier) {
        if (identifier == null || identifier.trim().isEmpty()) {
            throw new IllegalArgumentException("SQL identifier must not be empty");
        }
        return "`" + identifier.replace("`", "``") + "`";
    }

    private String join(List<String> values, String delimiter) {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) {
                builder.append(delimiter);
            }
            builder.append(values.get(i));
        }
        return builder.toString();
    }

    private static class SqlBuildContext {
        private final PhysicalSourceQueryNode fragment;
        private final Map<String, String> tableAliases = new LinkedHashMap<String, String>();
        private final Map<String, Object> parameters = new LinkedHashMap<String, Object>();
        private int parameterIndex;

        SqlBuildContext(PhysicalSourceQueryNode fragment) {
            this.fragment = fragment;
            Set<String> containers = new LinkedHashSet<String>();
            for (PhysicalFieldBinding binding : fragment.getFieldBindings()) {
                containers.add(binding.getPhysicalContainer());
            }
            if (containers.isEmpty()) {
                containers.add(fragment.getObjectType() == null ? fragment.getObjectAlias() : fragment.getObjectType());
            }
            int index = 0;
            for (String container : containers) {
                tableAliases.put(container, "t" + index++);
            }
        }

        Map<String, String> getTableAliases() {
            return tableAliases;
        }

        Map<String, Object> getParameters() {
            return parameters;
        }

        String tableAlias(String container) {
            String alias = tableAliases.get(container);
            if (alias != null) {
                return alias;
            }
            alias = "t" + tableAliases.size();
            tableAliases.put(container, alias);
            return alias;
        }

        String defaultTableAlias() {
            return tableAliases.values().iterator().next();
        }

        String parameter(String prefix, Object value) {
            String name = prefix + (++parameterIndex);
            parameters.put(name, value);
            return ":" + name;
        }

        String parameters(List<Object> values, String prefix) {
            if (values == null || values.isEmpty()) {
                throw new IllegalArgumentException("SQL IN predicate values must not be empty");
            }
            List<String> names = new ArrayList<String>();
            for (Object value : values) {
                names.add(parameter(prefix, value));
            }
            return joinStatic(names, ", ");
        }

        private static String joinStatic(List<String> values, String delimiter) {
            StringBuilder builder = new StringBuilder();
            for (int i = 0; i < values.size(); i++) {
                if (i > 0) {
                    builder.append(delimiter);
                }
                builder.append(values.get(i));
            }
            return builder.toString();
        }
    }
}
