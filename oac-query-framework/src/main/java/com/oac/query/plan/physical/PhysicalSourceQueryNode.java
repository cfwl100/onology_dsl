package com.oac.query.plan.physical;

import com.oac.query.binding.DatasourceType;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.AggregateFilter;
import com.oac.query.dsl.OqlQuery.Condition;
import com.oac.query.dsl.OqlQuery.MaxResults;
import com.oac.query.dsl.OqlQuery.OperationType;
import com.oac.query.dsl.OqlQuery.OrderDecl;
import com.oac.query.dsl.OqlQuery.ReturnDecl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 物理 DAG 中面向单个数据源的查询分片。
 */
public class PhysicalSourceQueryNode implements PhysicalPlan.PhysicalPlanNode {
    private final String id;
    private final String datasourceId;
    private final DatasourceType datasourceType;
    private final String objectAlias;
    private final String objectType;
    private final List<String> projections;
    private final Condition condition;
    private final List<PhysicalFieldBinding> fieldBindings;
    private final OperationType operation;
    private final List<ReturnDecl> returns;
    private final AggregateFilter aggregateFilter;
    private final List<OrderDecl> orders;
    private final MaxResults maxResults;
    private final Map<String, List<Object>> dynamicInputs = new LinkedHashMap<String, List<Object>>();

    public PhysicalSourceQueryNode(String id, String datasourceId, DatasourceType datasourceType, String objectAlias,
                                   String objectType, List<String> projections, Condition condition) {
        this(id, datasourceId, datasourceType, objectAlias, objectType, projections, condition,
                Collections.<PhysicalFieldBinding>emptyList(), OperationType.QUERY,
                Collections.<ReturnDecl>emptyList(), null, Collections.<OrderDecl>emptyList(), null);
    }

    public PhysicalSourceQueryNode(String id, String datasourceId, DatasourceType datasourceType, String objectAlias,
                                   String objectType, List<String> projections, Condition condition,
                                   List<PhysicalFieldBinding> fieldBindings, OperationType operation,
                                   List<ReturnDecl> returns, AggregateFilter aggregateFilter,
                                   List<OrderDecl> orders, MaxResults maxResults) {
        this.id = id;
        this.datasourceId = datasourceId;
        this.datasourceType = datasourceType;
        this.objectAlias = objectAlias;
        this.objectType = objectType;
        this.projections = new ArrayList<String>(projections);
        this.condition = condition;
        this.fieldBindings = fieldBindings == null
                ? new ArrayList<PhysicalFieldBinding>()
                : new ArrayList<PhysicalFieldBinding>(fieldBindings);
        this.operation = operation == null ? OperationType.QUERY : operation;
        this.returns = returns == null ? new ArrayList<ReturnDecl>() : new ArrayList<ReturnDecl>(returns);
        this.aggregateFilter = aggregateFilter;
        this.orders = orders == null ? new ArrayList<OrderDecl>() : new ArrayList<OrderDecl>(orders);
        this.maxResults = maxResults;
    }

    public String getId() {
        return id;
    }

    public String getNodeType() {
        return "PhysicalSourceQueryNode";
    }

    public String getDatasourceId() {
        return datasourceId;
    }

    public DatasourceType getDatasourceType() {
        return datasourceType;
    }

    public String getObjectAlias() {
        return objectAlias;
    }

    public String getObjectType() {
        return objectType;
    }

    public List<String> getProjections() {
        return Collections.unmodifiableList(projections);
    }

    public Condition getCondition() {
        return condition;
    }

    public List<PhysicalFieldBinding> getFieldBindings() {
        return Collections.unmodifiableList(fieldBindings);
    }

    public OperationType getOperation() {
        return operation;
    }

    public List<ReturnDecl> getReturns() {
        return Collections.unmodifiableList(returns);
    }

    public AggregateFilter getAggregateFilter() {
        return aggregateFilter;
    }

    public List<OrderDecl> getOrders() {
        return Collections.unmodifiableList(orders);
    }

    public MaxResults getMaxResults() {
        return maxResults;
    }

    public PhysicalFieldBinding findFieldBinding(String ref, String field) {
        if (field == null) {
            return null;
        }
        PhysicalFieldBinding fallback = null;
        for (PhysicalFieldBinding binding : fieldBindings) {
            if (!field.equals(binding.getLogicalField()) && !field.equals(binding.getPhysicalField())) {
                continue;
            }
            if (ref == null || ref.trim().isEmpty() || ref.equals(binding.getObjectAlias())) {
                return binding;
            }
            if (fallback == null) {
                fallback = binding;
            }
        }
        return fallback;
    }

    public void putDynamicInput(String field, List<Object> values) {
        // 动态输入会在上游查询分片完成后注入，例如：
        // A.rows[*].cellId -> B.cell_id IN (...)
        dynamicInputs.put(field, new ArrayList<Object>(values));
    }

    public Map<String, List<Object>> getDynamicInputs() {
        return Collections.unmodifiableMap(dynamicInputs);
    }
}
