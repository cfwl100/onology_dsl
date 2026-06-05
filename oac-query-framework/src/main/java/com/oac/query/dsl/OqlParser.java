package com.oac.query.dsl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.oac.query.dsl.OqlQuery.AggregateFilter;
import com.oac.query.dsl.OqlQuery.AggregateFilterGroup;
import com.oac.query.dsl.OqlQuery.Condition;
import com.oac.query.dsl.OqlQuery.ConditionGroup;
import com.oac.query.dsl.OqlQuery.Expr;
import com.oac.query.dsl.OqlQuery.FieldExpr;
import com.oac.query.dsl.OqlQuery.FunctionExpr;
import com.oac.query.dsl.OqlQuery.MaxResults;
import com.oac.query.dsl.OqlQuery.MetricPredicateFilter;
import com.oac.query.dsl.OqlQuery.ObjectDecl;
import com.oac.query.dsl.OqlQuery.OperationType;
import com.oac.query.dsl.OqlQuery.OrderDecl;
import com.oac.query.dsl.OqlQuery.PredicateCondition;
import com.oac.query.dsl.OqlQuery.RelationshipDecl;
import com.oac.query.dsl.OqlQuery.Relation;
import com.oac.query.dsl.OqlQuery.ReturnDecl;
import com.oac.query.dsl.OqlQuery.ReturnKind;
import com.oac.query.dsl.OqlQuery.ValueExpr;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 将规范化 OQL JSON 解析为框架内部模型。
 *
 * 这里刻意使用显式解析，而不是依赖 Jackson 多态注解，因为 Expr、Condition、
 * AggregateFilter 都通过 kind 字段区分类型，同时校验器还需要保留未知顶层字段，
 * 用于严格 OQL 校验。
 */
public class OqlParser {
    private final ObjectMapper mapper;

    public OqlParser() {
        this(new ObjectMapper());
    }

    public OqlParser(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    public OqlQuery parse(String json) {
        try {
            return parse(mapper.readTree(json));
        } catch (IOException e) {
            throw new IllegalArgumentException("Invalid OQL JSON", e);
        }
    }

    public OqlQuery parse(JsonNode root) {
        if (root == null || !root.isObject()) {
            throw new IllegalArgumentException("OQL root must be a JSON object");
        }
        OqlQuery query = new OqlQuery();
        query.setTopLevelFields(fieldNames(root));
        query.setVersion(text(root, "version"));
        query.setSchemaRef(text(root, "schemaRef"));
        if (root.has("strict")) {
            query.setStrict(root.get("strict").asBoolean(true));
        }
        query.setOperation(enumValue(OperationType.class, text(root, "operation")));
        query.setObjects(parseObjects(root.get("objects")));
        query.setRelationships(parseRelationships(root.get("relationships")));
        query.setConditions(parseCondition(root.get("conditions")));
        query.setReturns(parseReturns(root.get("returns")));
        query.setAggregateFilter(parseAggregateFilter(root.get("aggregateFilter")));
        query.setOrders(parseOrders(root.get("orders")));
        query.setMaxResults(parseMaxResults(root.get("maxResults")));
        query.setMutation(map(root.get("mutation")));
        query.setOptions(map(root.get("options")));
        query.setExtensions(map(root.get("extensions")));
        query.setSourceQuery(parseSourceQueries(root.get("sourceQuery")));
        return query;
    }

    private List<ObjectDecl> parseObjects(JsonNode node) {
        List<ObjectDecl> objects = new ArrayList<ObjectDecl>();
        if (node == null || !node.isArray()) {
            return objects;
        }
        for (JsonNode item : node) {
            ObjectDecl object = new ObjectDecl();
            object.setObjectType(text(item, "objectType"));
            object.setAlias(text(item, "alias"));
            object.setFromSource(text(item, "fromSource"));
            objects.add(object);
        }
        return objects;
    }

    private List<RelationshipDecl> parseRelationships(JsonNode node) {
        List<RelationshipDecl> relationships = new ArrayList<RelationshipDecl>();
        if (node == null || !node.isArray()) {
            return relationships;
        }
        for (JsonNode item : node) {
            RelationshipDecl relationship = new RelationshipDecl();
            relationship.setRelationshipType(text(item, "relationshipType"));
            relationship.setAlias(text(item, "alias"));
            relationship.setFrom(text(item, "from"));
            relationship.setTo(text(item, "to"));
            relationship.setDirection(text(item, "direction"));
            relationship.setMode(text(item, "mode"));
            relationships.add(relationship);
        }
        return relationships;
    }

    private Condition parseCondition(JsonNode node) {
        if (node == null || node.isNull() || !node.isObject() || node.size() == 0) {
            return null;
        }
        String kind = text(node, "kind");
        if ("GROUP".equals(kind)) {
            ConditionGroup group = new ConditionGroup();
            group.setRelation(enumValue(Relation.class, text(node, "relation")));
            List<Condition> children = new ArrayList<Condition>();
            JsonNode childrenNode = node.get("children");
            if (childrenNode != null && childrenNode.isArray()) {
                for (JsonNode child : childrenNode) {
                    children.add(parseCondition(child));
                }
            }
            group.setChildren(children);
            return group;
        }
        PredicateCondition predicate = new PredicateCondition();
        predicate.setRef(text(node, "ref"));
        predicate.setField(text(node, "field"));
        predicate.setLeft(parseExpr(node.get("left")));
        predicate.setOperator(text(node, "operator"));
        predicate.setValues(values(node.get("values")));
        if (node.has("subquery")) {
            predicate.setSubquery(parse(node.get("subquery")));
        }
        return predicate;
    }

    private Expr parseExpr(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        if (!node.isObject()) {
            return new ValueExpr(jsonValue(node));
        }
        String kind = text(node, "kind");
        if ("FIELD".equals(kind)) {
            return new FieldExpr(text(node, "ref"), text(node, "field"));
        }
        if ("FUNCTION".equals(kind)) {
            FunctionExpr function = new FunctionExpr();
            function.setNamespace(text(node, "namespace"));
            function.setName(text(node, "name"));
            List<Expr> args = new ArrayList<Expr>();
            JsonNode argsNode = node.get("args");
            if (argsNode != null && argsNode.isArray()) {
                for (JsonNode arg : argsNode) {
                    args.add(parseExpr(arg));
                }
            }
            function.setArgs(args);
            return function;
        }
        return new ValueExpr(jsonValue(node.get("value")));
    }

    private List<ReturnDecl> parseReturns(JsonNode node) {
        List<ReturnDecl> returns = new ArrayList<ReturnDecl>();
        if (node == null || !node.isArray()) {
            return returns;
        }
        for (JsonNode item : node) {
            ReturnDecl ret = new ReturnDecl();
            ret.setKind(enumValue(ReturnKind.class, text(item, "kind")));
            ret.setRef(text(item, "ref"));
            ret.setFields(strings(item.get("fields")));
            ret.setExpr(parseExpr(item.get("expr")));
            ret.setAlias(text(item, "alias"));
            ret.setField(text(item, "field"));
            ret.setFunction(text(item, "function"));
            returns.add(ret);
        }
        return returns;
    }

    private AggregateFilter parseAggregateFilter(JsonNode node) {
        if (node == null || node.isNull() || !node.isObject() || node.size() == 0) {
            return null;
        }
        String kind = text(node, "kind");
        if ("GROUP".equals(kind)) {
            AggregateFilterGroup group = new AggregateFilterGroup();
            group.setRelation(enumValue(Relation.class, text(node, "relation")));
            List<AggregateFilter> children = new ArrayList<AggregateFilter>();
            JsonNode childrenNode = node.get("children");
            if (childrenNode != null && childrenNode.isArray()) {
                for (JsonNode child : childrenNode) {
                    children.add(parseAggregateFilter(child));
                }
            }
            group.setChildren(children);
            return group;
        }
        MetricPredicateFilter filter = new MetricPredicateFilter();
        filter.setMetricAlias(text(node, "metricAlias"));
        filter.setOperator(text(node, "operator"));
        filter.setValues(values(node.get("values")));
        return filter;
    }

    private List<OrderDecl> parseOrders(JsonNode node) {
        List<OrderDecl> orders = new ArrayList<OrderDecl>();
        if (node == null || !node.isArray()) {
            return orders;
        }
        for (JsonNode item : node) {
            OrderDecl order = new OrderDecl();
            order.setRef(text(item, "ref"));
            order.setField(text(item, "field"));
            order.setDirection(text(item, "direction"));
            orders.add(order);
        }
        return orders;
    }

    private MaxResults parseMaxResults(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }
        MaxResults maxResults = new MaxResults();
        if (node.has("limit")) {
            maxResults.setLimit(node.get("limit").asInt());
        }
        if (node.has("offset")) {
            maxResults.setOffset(node.get("offset").asInt());
        }
        return maxResults;
    }

    private List<OqlQuery> parseSourceQueries(JsonNode node) {
        List<OqlQuery> queries = new ArrayList<OqlQuery>();
        if (node == null || !node.isArray()) {
            return queries;
        }
        for (JsonNode item : node) {
            queries.add(parse(item));
        }
        return queries;
    }

    private String text(JsonNode node, String field) {
        JsonNode value = node == null ? null : node.get(field);
        return value == null || value.isNull() ? null : value.asText();
    }

    private <T extends Enum<T>> T enumValue(Class<T> enumType, String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }
        try {
            return Enum.valueOf(enumType, value);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private List<String> strings(JsonNode node) {
        List<String> values = new ArrayList<String>();
        if (node == null || !node.isArray()) {
            return values;
        }
        for (JsonNode item : node) {
            values.add(item.asText());
        }
        return values;
    }

    private List<Object> values(JsonNode node) {
        List<Object> values = new ArrayList<Object>();
        if (node == null || !node.isArray()) {
            return values;
        }
        for (JsonNode item : node) {
            values.add(jsonValue(item));
        }
        return values;
    }

    private Object jsonValue(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        if (node.isTextual()) {
            return node.asText();
        }
        if (node.isInt() || node.isLong()) {
            return node.asLong();
        }
        if (node.isFloat() || node.isDouble() || node.isBigDecimal()) {
            return node.asDouble();
        }
        if (node.isBoolean()) {
            return node.asBoolean();
        }
        return mapper.convertValue(node, Object.class);
    }

    private Map<String, Object> map(JsonNode node) {
        if (node == null || node.isNull() || !node.isObject() || node.size() == 0) {
            return new LinkedHashMap<String, Object>();
        }
        return mapper.convertValue(node, new TypeReference<Map<String, Object>>() {
        });
    }

    private Set<String> fieldNames(JsonNode node) {
        Set<String> names = new LinkedHashSet<String>();
        Iterator<String> iterator = node.fieldNames();
        while (iterator.hasNext()) {
            names.add(iterator.next());
        }
        return names;
    }

    public String toJson(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Cannot serialize OQL value", e);
        }
    }
}
