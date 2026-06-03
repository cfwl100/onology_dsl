package com.onology.oac.queryframework.domain;

import java.util.List;
import java.util.Map;

/**
 * Canonical OQL query models used by the extensible OAC query framework.
 *
 * <p>The classes intentionally model the semantic OQL layer only. They must not contain SQL,
 * GQL, API or other physical-source concepts.
 */
public final class OqlModels {
    private OqlModels() {
    }

    public enum OperationType {
        QUERY,
        AGGREGATE,
        ASSOCIATION_QUERY,
        CREATE,
        UPDATE,
        DELETE,
        UPSERT,
        BATCH
    }

    public enum ConditionKind {
        PREDICATE,
        GROUP
    }

    public enum ReturnKind {
        FIELDS,
        EXPR,
        GROUP_BY,
        METRIC
    }

    public enum ExpressionKind {
        FIELD,
        VALUE,
        FUNCTION
    }

    public enum AggregateFunction {
        COUNT,
        SUM,
        AVG,
        MIN,
        MAX
    }

    public enum Operator {
        EQ,
        NE,
        GT,
        GTE,
        LT,
        LTE,
        IN,
        NOT_IN,
        BETWEEN,
        LIKE,
        CONTAINS,
        STARTS_WITH,
        ENDS_WITH,
        IS_NULL,
        IS_NOT_NULL,
        IS_EMPTY,
        IS_NOT_EMPTY,
        EXISTS,
        NOT_EXISTS
    }

    public enum SortDirection {
        ASC,
        DESC
    }

    public enum RelationshipDirection {
        OUTBOUND,
        INBOUND,
        BOTH
    }

    public enum RelationshipMode {
        ONE,
        LIST
    }

    public enum AggregateFilterKind {
        METRIC_PREDICATE,
        GROUP
    }

    public enum GroupRelation {
        AND,
        OR,
        NOT
    }

    public record OqlQuery(
            String version,
            String schemaRef,
            Boolean strict,
            OperationType operation,
            List<OqlObject> objects,
            List<OqlRelationship> relationships,
            OqlCondition conditions,
            List<OqlReturnItem> returns,
            OqlAggregateFilter aggregateFilter,
            List<OqlOrder> orders,
            OqlMaxResults maxResults,
            List<OqlQuery> sourceQuery,
            Map<String, Object> options,
            Map<String, Object> extensions
    ) {
        public boolean strictMode() {
            return strict == null || strict;
        }
    }

    public record OqlObject(String objectType, String alias, String fromSource) {
    }

    public record OqlRelationship(
            String relationshipType,
            String alias,
            String from,
            String to,
            RelationshipDirection direction,
            RelationshipMode mode
    ) {
    }

    public record OqlCondition(
            ConditionKind kind,
            GroupRelation relation,
            List<OqlCondition> children,
            String ref,
            String field,
            OqlExpression left,
            Operator operator,
            List<Object> values,
            OqlQuery subquery
    ) {
    }

    public record OqlReturnItem(
            ReturnKind kind,
            String ref,
            List<String> fields,
            OqlExpression expr,
            String field,
            AggregateFunction function,
            String alias
    ) {
    }

    public record OqlExpression(
            ExpressionKind kind,
            String ref,
            String field,
            Object value,
            String namespace,
            String name,
            List<OqlExpression> args
    ) {
    }

    public record OqlAggregateFilter(
            AggregateFilterKind kind,
            String metricAlias,
            Operator operator,
            List<Object> values,
            GroupRelation relation,
            List<OqlAggregateFilter> children
    ) {
    }

    public record OqlOrder(String ref, String field, SortDirection direction) {
    }

    public record OqlMaxResults(Integer limit, Integer offset) {
        public int normalizedLimit(int defaultLimit, int maxLimit) {
            int candidate = limit == null ? defaultLimit : limit;
            return Math.min(candidate, maxLimit);
        }

        public int normalizedOffset() {
            return offset == null ? 0 : offset;
        }
    }
}
