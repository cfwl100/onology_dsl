package com.onology.oac.model;

import com.fasterxml.jackson.annotation.JsonIgnore;

import java.util.List;

/**
 * OQL canonical 请求模型（Spring MVC 反序列化用）。
 *
 * <p>该模型在 pipeline compile 前执行语义校验，确保操作类型与请求结构匹配。
 */
public class OqlRequest {
    private String version = "1.0";
    private String schemaRef;
    private boolean strict = true;
    private OperationType operation;
    private List<ObjectRef> objects = List.of();
    private List<Condition> conditions = List.of();
    private List<ReturnField> returns = List.of();
    private List<OrderBy> orders = List.of();
    private int maxResults = 100;
    private Mutation mutation;

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

    public List<ObjectRef> getObjects() {
        return objects;
    }

    public void setObjects(List<ObjectRef> objects) {
        this.objects = objects == null ? List.of() : objects;
    }

    public List<Condition> getConditions() {
        return conditions;
    }

    public void setConditions(List<Condition> conditions) {
        this.conditions = conditions == null ? List.of() : conditions;
    }

    public List<ReturnField> getReturns() {
        return returns;
    }

    public void setReturns(List<ReturnField> returns) {
        this.returns = returns == null ? List.of() : returns;
    }

    public List<OrderBy> getOrders() {
        return orders;
    }

    public void setOrders(List<OrderBy> orders) {
        this.orders = orders == null ? List.of() : orders;
    }

    public int getMaxResults() {
        return maxResults;
    }

    public void setMaxResults(int maxResults) {
        this.maxResults = maxResults <= 0 ? 100 : maxResults;
    }

    public Mutation getMutation() {
        return mutation;
    }

    public void setMutation(Mutation mutation) {
        this.mutation = mutation;
    }

    @JsonIgnore
    public void validate() {
        if (operation == null) {
            throw new IllegalArgumentException("operation is required");
        }
        if (schemaRef == null || schemaRef.isBlank()) {
            throw new IllegalArgumentException("schemaRef is required");
        }
        // 写操作必须带 mutation。
        if ((operation == OperationType.UPDATE || operation == OperationType.DELETE) && mutation == null) {
            throw new IllegalArgumentException("UPDATE/DELETE requires mutation block");
        }
        // UPSERT 必须指定 matchBy。
        if (operation == OperationType.UPSERT && (mutation == null || mutation.matchBy() == null || mutation.matchBy().isEmpty())) {
            throw new IllegalArgumentException("UPSERT requires mutation.matchBy");
        }
        // BATCH 之外必须声明目标对象。
        if (operation != OperationType.BATCH && (objects == null || objects.isEmpty())) {
            throw new IllegalArgumentException("non-BATCH request must declare objects");
        }
    }

    public static OqlRequest sampleQuery() {
        OqlRequest req = new OqlRequest();
        req.setSchemaRef("demo.sales.v1");
        req.setOperation(OperationType.QUERY);
        req.setObjects(List.of(new ObjectRef("User", "u")));
        req.setConditions(List.of(new Condition("id", "eq", "U1001")));
        req.setReturns(List.of(new ReturnField("id", null), new ReturnField("firstName", null), new ReturnField("email", null)));
        req.setMaxResults(10);
        return req;
    }

    public static OqlRequest sampleGraphQuery() {
        OqlRequest req = new OqlRequest();
        req.setSchemaRef("demo.sales.v1");
        req.setOperation(OperationType.QUERY);
        req.setObjects(List.of(new ObjectRef("Employee", "e")));
        req.setConditions(List.of(new Condition("id", "eq", "E1001")));
        req.setReturns(List.of(new ReturnField("id", null), new ReturnField("name", null)));
        req.setMaxResults(5);
        return req;
    }
}
