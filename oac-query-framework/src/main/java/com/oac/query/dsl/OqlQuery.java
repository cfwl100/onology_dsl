package com.oac.query.dsl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 规范化 OQL 文档的内存模型。
 *
 * 该模型尽量贴近 DSL 规范中的概念：对象、关系、条件、返回、聚合过滤和执行选项。
 */
public class OqlQuery {
    public static final String CURRENT_VERSION = "2.0";

    private String version;
    private String schemaRef;
    private boolean strict = true;
    private OperationType operation;
    private List<ObjectDecl> objects = new ArrayList<ObjectDecl>();
    private List<RelationshipDecl> relationships = new ArrayList<RelationshipDecl>();
    private Condition conditions;
    private List<ReturnDecl> returns = new ArrayList<ReturnDecl>();
    private AggregateFilter aggregateFilter;
    private List<OrderDecl> orders = new ArrayList<OrderDecl>();
    private MaxResults maxResults;
    private List<OqlQuery> sourceQuery = new ArrayList<OqlQuery>();
    private Map<String, Object> mutation = new LinkedHashMap<String, Object>();
    private Map<String, Object> options = new LinkedHashMap<String, Object>();
    private Map<String, Object> extensions = new LinkedHashMap<String, Object>();
    private Set<String> topLevelFields = new LinkedHashSet<String>();

    /** 顶层 OQL 操作类型的取值范围。 */
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

    /** OQL 返回数组中允许出现的返回项类型。 */
    public enum ReturnKind {
        FIELDS,
        EXPR,
        GROUP_BY,
        METRIC
    }

    /** 表达式节点的类型标识。 */
    public enum ExprKind {
        FIELD,
        VALUE,
        FUNCTION
    }

    /** 聚合前过滤条件节点的类型标识。 */
    public enum ConditionKind {
        PREDICATE,
        GROUP
    }

    /** 聚合后过滤条件节点的类型标识。 */
    public enum AggregateFilterKind {
        METRIC_PREDICATE,
        GROUP
    }

    /** 条件组和聚合过滤组使用的布尔关系。 */
    public enum Relation {
        AND,
        OR,
        NOT
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public String getSchemaRef() {
        return schemaRef;
    }

    public void setSchemaRef(String schemaRef) {
        this.schemaRef = schemaRef;
    }

    public boolean isStrict() {
        return strict;
    }

    public void setStrict(boolean strict) {
        this.strict = strict;
    }

    public OperationType getOperation() {
        return operation;
    }

    public void setOperation(OperationType operation) {
        this.operation = operation;
    }

    public List<ObjectDecl> getObjects() {
        return objects;
    }

    public void setObjects(List<ObjectDecl> objects) {
        this.objects = objects == null ? new ArrayList<ObjectDecl>() : objects;
    }

    public List<RelationshipDecl> getRelationships() {
        return relationships;
    }

    public void setRelationships(List<RelationshipDecl> relationships) {
        this.relationships = relationships == null ? new ArrayList<RelationshipDecl>() : relationships;
    }

    public Condition getConditions() {
        return conditions;
    }

    public void setConditions(Condition conditions) {
        this.conditions = conditions;
    }

    public List<ReturnDecl> getReturns() {
        return returns;
    }

    public void setReturns(List<ReturnDecl> returns) {
        this.returns = returns == null ? new ArrayList<ReturnDecl>() : returns;
    }

    public AggregateFilter getAggregateFilter() {
        return aggregateFilter;
    }

    public void setAggregateFilter(AggregateFilter aggregateFilter) {
        this.aggregateFilter = aggregateFilter;
    }

    public List<OrderDecl> getOrders() {
        return orders;
    }

    public void setOrders(List<OrderDecl> orders) {
        this.orders = orders == null ? new ArrayList<OrderDecl>() : orders;
    }

    public MaxResults getMaxResults() {
        return maxResults;
    }

    public void setMaxResults(MaxResults maxResults) {
        this.maxResults = maxResults;
    }

    public List<OqlQuery> getSourceQuery() {
        return sourceQuery;
    }

    public void setSourceQuery(List<OqlQuery> sourceQuery) {
        this.sourceQuery = sourceQuery == null ? new ArrayList<OqlQuery>() : sourceQuery;
    }

    public Map<String, Object> getMutation() {
        return mutation;
    }

    public void setMutation(Map<String, Object> mutation) {
        this.mutation = mutation == null ? new LinkedHashMap<String, Object>() : mutation;
    }

    public Map<String, Object> getOptions() {
        return options;
    }

    public void setOptions(Map<String, Object> options) {
        this.options = options == null ? new LinkedHashMap<String, Object>() : options;
    }

    public Map<String, Object> getExtensions() {
        return extensions;
    }

    public void setExtensions(Map<String, Object> extensions) {
        this.extensions = extensions == null ? new LinkedHashMap<String, Object>() : extensions;
    }

    public Set<String> getTopLevelFields() {
        return topLevelFields;
    }

    public void setTopLevelFields(Set<String> topLevelFields) {
        this.topLevelFields = topLevelFields == null ? new LinkedHashSet<String>() : topLevelFields;
    }

    public boolean hasTopLevelField(String field) {
        return topLevelFields.contains(field);
    }

    /** 声明一个参与查询的本体对象别名。 */
    public static class ObjectDecl {
        private String objectType;
        private String alias;
        private String fromSource;

        public String getObjectType() {
            return objectType;
        }

        public void setObjectType(String objectType) {
            this.objectType = objectType;
        }

        public String getAlias() {
            return alias;
        }

        public void setAlias(String alias) {
            this.alias = alias;
        }

        public String getFromSource() {
            return fromSource;
        }

        public void setFromSource(String fromSource) {
            this.fromSource = fromSource;
        }
    }

    /** 声明 ASSOCIATION_QUERY 中的一段显式关系或路径跳。 */
    public static class RelationshipDecl {
        private String relationshipType;
        private String alias;
        private String from;
        private String to;
        private String direction;
        private String mode;

        public String getRelationshipType() {
            return relationshipType;
        }

        public void setRelationshipType(String relationshipType) {
            this.relationshipType = relationshipType;
        }

        public String getAlias() {
            return alias;
        }

        public void setAlias(String alias) {
            this.alias = alias;
        }

        public String getFrom() {
            return from;
        }

        public void setFrom(String from) {
            this.from = from;
        }

        public String getTo() {
            return to;
        }

        public void setTo(String to) {
            this.to = to;
        }

        public String getDirection() {
            return direction;
        }

        public void setDirection(String direction) {
            this.direction = direction;
        }

        public String getMode() {
            return mode;
        }

        public void setMode(String mode) {
            this.mode = mode;
        }
    }

    /** 描述一个返回项：字段、表达式、分组维度或聚合指标。 */
    public static class ReturnDecl {
        private ReturnKind kind;
        private String ref;
        private List<String> fields = new ArrayList<String>();
        private Expr expr;
        private String alias;
        private String field;
        private String function;

        public ReturnKind getKind() {
            return kind;
        }

        public void setKind(ReturnKind kind) {
            this.kind = kind;
        }

        public String getRef() {
            return ref;
        }

        public void setRef(String ref) {
            this.ref = ref;
        }

        public List<String> getFields() {
            return fields;
        }

        public void setFields(List<String> fields) {
            this.fields = fields == null ? new ArrayList<String>() : fields;
        }

        public Expr getExpr() {
            return expr;
        }

        public void setExpr(Expr expr) {
            this.expr = expr;
        }

        public String getAlias() {
            return alias;
        }

        public void setAlias(String alias) {
            this.alias = alias;
        }

        public String getField() {
            return field;
        }

        public void setField(String field) {
            this.field = field;
        }

        public String getFunction() {
            return function;
        }

        public void setFunction(String function) {
            this.function = function;
        }
    }

    /** 基于对象字段或返回别名的排序定义。 */
    public static class OrderDecl {
        private String ref;
        private String field;
        private String direction;

        public String getRef() {
            return ref;
        }

        public void setRef(String ref) {
            this.ref = ref;
        }

        public String getField() {
            return field;
        }

        public void setField(String field) {
            this.field = field;
        }

        public String getDirection() {
            return direction;
        }

        public void setDirection(String direction) {
            this.direction = direction;
        }
    }

    /** 用于结果规模保护的 limit/offset 定义。 */
    public static class MaxResults {
        private int limit = 1000;
        private int offset = 0;

        public int getLimit() {
            return limit;
        }

        public void setLimit(int limit) {
            this.limit = limit;
        }

        public int getOffset() {
            return offset;
        }

        public void setOffset(int offset) {
            this.offset = offset;
        }
    }

    /** OQL 表达式变体的标记接口。 */
    public interface Expr {
        ExprKind getKind();
    }

    /** 指向已声明 alias 和本体字段的表达式。 */
    public static class FieldExpr implements Expr {
        private String ref;
        private String field;

        public FieldExpr() {
        }

        public FieldExpr(String ref, String field) {
            this.ref = ref;
            this.field = field;
        }

        public ExprKind getKind() {
            return ExprKind.FIELD;
        }

        public String getRef() {
            return ref;
        }

        public void setRef(String ref) {
            this.ref = ref;
        }

        public String getField() {
            return field;
        }

        public void setField(String field) {
            this.field = field;
        }
    }

    /** 字面量值表达式。 */
    public static class ValueExpr implements Expr {
        private Object value;

        public ValueExpr() {
        }

        public ValueExpr(Object value) {
            this.value = value;
        }

        public ExprKind getKind() {
            return ExprKind.VALUE;
        }

        public Object getValue() {
            return value;
        }

        public void setValue(Object value) {
            this.value = value;
        }
    }

    /** 受治理的函数调用表达式。 */
    public static class FunctionExpr implements Expr {
        private String namespace;
        private String name;
        private List<Expr> args = new ArrayList<Expr>();

        public ExprKind getKind() {
            return ExprKind.FUNCTION;
        }

        public String getNamespace() {
            return namespace;
        }

        public void setNamespace(String namespace) {
            this.namespace = namespace;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public List<Expr> getArgs() {
            return args;
        }

        public void setArgs(List<Expr> args) {
            this.args = args == null ? new ArrayList<Expr>() : args;
        }
    }

    /** 对象级、聚合前过滤条件的标记接口。 */
    public interface Condition {
        ConditionKind getKind();
    }

    /** 使用值或子查询比较字段/表达式的叶子条件。 */
    public static class PredicateCondition implements Condition {
        private String ref;
        private String field;
        private Expr left;
        private String operator;
        private List<Object> values = new ArrayList<Object>();
        private OqlQuery subquery;

        public ConditionKind getKind() {
            return ConditionKind.PREDICATE;
        }

        public String getRef() {
            return ref;
        }

        public void setRef(String ref) {
            this.ref = ref;
        }

        public String getField() {
            return field;
        }

        public void setField(String field) {
            this.field = field;
        }

        public Expr getLeft() {
            return left;
        }

        public void setLeft(Expr left) {
            this.left = left;
        }

        public String getOperator() {
            return operator;
        }

        public void setOperator(String operator) {
            this.operator = operator;
        }

        public List<Object> getValues() {
            return values;
        }

        public void setValues(List<Object> values) {
            this.values = values == null ? new ArrayList<Object>() : values;
        }

        public OqlQuery getSubquery() {
            return subquery;
        }

        public void setSubquery(OqlQuery subquery) {
            this.subquery = subquery;
        }
    }

    /** 子条件的布尔组合。 */
    public static class ConditionGroup implements Condition {
        private Relation relation;
        private List<Condition> children = new ArrayList<Condition>();

        public ConditionKind getKind() {
            return ConditionKind.GROUP;
        }

        public Relation getRelation() {
            return relation;
        }

        public void setRelation(Relation relation) {
            this.relation = relation;
        }

        public List<Condition> getChildren() {
            return children;
        }

        public void setChildren(List<Condition> children) {
            this.children = children == null ? new ArrayList<Condition>() : children;
        }
    }

    /** 聚合后过滤条件的标记接口。 */
    public interface AggregateFilter {
        AggregateFilterKind getKind();
    }

    /** 使用值比较聚合指标别名的叶子聚合过滤条件。 */
    public static class MetricPredicateFilter implements AggregateFilter {
        private String metricAlias;
        private String operator;
        private List<Object> values = new ArrayList<Object>();

        public AggregateFilterKind getKind() {
            return AggregateFilterKind.METRIC_PREDICATE;
        }

        public String getMetricAlias() {
            return metricAlias;
        }

        public void setMetricAlias(String metricAlias) {
            this.metricAlias = metricAlias;
        }

        public String getOperator() {
            return operator;
        }

        public void setOperator(String operator) {
            this.operator = operator;
        }

        public List<Object> getValues() {
            return values;
        }

        public void setValues(List<Object> values) {
            this.values = values == null ? new ArrayList<Object>() : values;
        }
    }

    /** 聚合指标谓词的布尔组合。 */
    public static class AggregateFilterGroup implements AggregateFilter {
        private Relation relation;
        private List<AggregateFilter> children = new ArrayList<AggregateFilter>();

        public AggregateFilterKind getKind() {
            return AggregateFilterKind.GROUP;
        }

        public Relation getRelation() {
            return relation;
        }

        public void setRelation(Relation relation) {
            this.relation = relation;
        }

        public List<AggregateFilter> getChildren() {
            return children;
        }

        public void setChildren(List<AggregateFilter> children) {
            this.children = children == null ? new ArrayList<AggregateFilter>() : children;
        }
    }

    public static List<String> fieldReturns(List<ReturnDecl> returns) {
        if (returns == null || returns.isEmpty()) {
            return Collections.emptyList();
        }
        List<String> fields = new ArrayList<String>();
        for (ReturnDecl ret : returns) {
            if (ret.getKind() == ReturnKind.FIELDS) {
                fields.addAll(ret.getFields());
            } else if (ret.getAlias() != null) {
                fields.add(ret.getAlias());
            }
        }
        return fields;
    }
}
