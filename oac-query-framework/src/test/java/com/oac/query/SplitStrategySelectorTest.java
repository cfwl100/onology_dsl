package com.oac.query;

import com.oac.query.binding.BindingGraph;
import com.oac.query.binding.BindingResolver;
import com.oac.query.binding.BindingGraph.DatasourceCapability;
import com.oac.query.binding.BindingGraph.FieldBinding;
import com.oac.query.binding.BindingGraph.ObjectBinding;
import com.oac.query.binding.BindingGraph.RelationshipBinding;
import com.oac.query.binding.DatasourceType;
import com.oac.query.dsl.OqlParser;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.strategy.SplitStrategy;
import com.oac.query.strategy.SplitStrategySelector;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * 验证基于 operation 类型和 BindingGraph 能力的策略选择。
 */
class SplitStrategySelectorTest {
    private static final Set<SplitStrategy> COVERED_STRATEGIES = EnumSet.noneOf(SplitStrategy.class);

    private final OqlParser parser = new OqlParser();
    private final BindingResolver resolver = new BindingResolver();
    private final SplitStrategySelector selector = new SplitStrategySelector();

    @AfterAll
    static void coversEverySplitStrategy() {
        assertEquals(EnumSet.allOf(SplitStrategy.class), COVERED_STRATEGIES);
    }

    @Test
    void selectsSingleSourceSingleTable() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"sales-v1\",\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[\"id\",\"orderNo\"]}]"
                + "}");
        BindingGraph graph = resolver.resolve(query).getGraph();

        assertStrategy(SplitStrategy.SINGLE_SOURCE_SINGLE_TABLE, query, graph);
    }

    @Test
    void selectsSingleSourceMultiTableJoin() {
        OqlQuery query = operationQuery("QUERY");
        BindingGraph graph = new BindingGraph();
        DatasourceCapability sqlCapability = new DatasourceCapability(true, true, true, false);
        ObjectBinding objectBinding = new ObjectBinding("OrderComposite");
        objectBinding.add(field("OrderComposite", "orderId", "mysql-sales", DatasourceType.SQL, "orders", "order_id", sqlCapability));
        objectBinding.add(field("OrderComposite", "customerName", "mysql-sales", DatasourceType.SQL, "customers", "customer_name", sqlCapability));
        graph.addObjectBinding("o", objectBinding);

        assertStrategy(SplitStrategy.SINGLE_SOURCE_MULTI_TABLE_JOIN, query, graph);
    }

    @Test
    void selectsCrossSourceMemoryMerge() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"telecom-v1\",\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Cell\",\"alias\":\"c\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"c\",\"fields\":[\"cellId\",\"cellName\",\"prbUsage\",\"alarmCount\"]}]"
                + "}");
        BindingGraph graph = resolver.resolve(query).getGraph();

        assertStrategy(SplitStrategy.CROSS_SOURCE_MEMORY_MERGE, query, graph);
    }

    @Test
    void selectsDagDependentQuery() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"telecom-v1\",\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Cell\",\"alias\":\"c\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"c\",\"fields\":[\"cellId\",\"prbUsage\"]}]"
                + "}");
        BindingGraph graph = resolver.resolve(query).getGraph();
        graph.setDependencyRequired(true);

        assertStrategy(SplitStrategy.DAG_DEPENDENT_QUERY, query, graph);
    }

    @Test
    void selectsAssociationGraphPushdown() {
        OqlQuery query = operationQuery("ASSOCIATION_QUERY");
        BindingGraph graph = new BindingGraph();
        DatasourceCapability graphCapability = DatasourceCapability.graph();
        graph.addObjectBinding("d", objectBinding("Device", field("Device", "id", "gql-topology", DatasourceType.GQL, "device", "id", graphCapability)));
        graph.addObjectBinding("s", objectBinding("Site", field("Site", "id", "gql-topology", DatasourceType.GQL, "site", "id", graphCapability)));
        graph.addRelationshipBinding("r1", new RelationshipBinding("installed_on", "gql-topology", DatasourceType.GQL, "installed_on", graphCapability));

        assertStrategy(SplitStrategy.ASSOCIATION_GRAPH_PUSHDOWN, query, graph);
    }

    @Test
    void selectsAssociationRelationalJoin() {
        OqlQuery query = operationQuery("ASSOCIATION_QUERY");
        BindingGraph graph = new BindingGraph();
        DatasourceCapability sqlCapability = new DatasourceCapability(true, true, true, false);
        graph.addObjectBinding("o", objectBinding("Order", field("Order", "id", "mysql-sales", DatasourceType.SQL, "orders", "id", sqlCapability)));
        graph.addObjectBinding("i", objectBinding("Invoice", field("Invoice", "id", "mysql-sales", DatasourceType.SQL, "invoices", "id", sqlCapability)));
        graph.addRelationshipBinding("r1", new RelationshipBinding("has_invoice", "mysql-sales", DatasourceType.SQL, "order_invoice", sqlCapability));

        assertStrategy(SplitStrategy.ASSOCIATION_RELATIONAL_JOIN, query, graph);
    }

    @Test
    void selectsAssociationMultiStageAssemble() {
        OqlQuery query = operationQuery("ASSOCIATION_QUERY");
        BindingGraph graph = new BindingGraph();
        DatasourceCapability sqlCapability = new DatasourceCapability(true, true, true, false);
        DatasourceCapability apiCapability = new DatasourceCapability(false, false, false, false);
        graph.addObjectBinding("o", objectBinding("Order", field("Order", "id", "mysql-sales", DatasourceType.SQL, "orders", "id", sqlCapability)));
        graph.addObjectBinding("i", objectBinding("Invoice", field("Invoice", "id", "invoice-api", DatasourceType.API, "/invoices", "id", apiCapability)));
        graph.addRelationshipBinding("r1", new RelationshipBinding("has_invoice", "mysql-sales", DatasourceType.SQL, "order_invoice", sqlCapability));

        assertStrategy(SplitStrategy.ASSOCIATION_MULTI_STAGE_ASSEMBLE, query, graph);
    }

    @Test
    void selectsAggregatePushdown() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"sales-v1\",\"operation\":\"AGGREGATE\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"returns\":[{\"kind\":\"METRIC\",\"function\":\"SUM\",\"ref\":\"o\",\"field\":\"amount\",\"alias\":\"totalAmount\"}]"
                + "}");
        BindingGraph pushdownGraph = resolver.resolve(query).getGraph();

        assertStrategy(SplitStrategy.AGGREGATE_PUSHDOWN, query, pushdownGraph);
    }

    @Test
    void selectsAggregatePartialPushdownMerge() {
        OqlQuery query = operationQuery("AGGREGATE");
        BindingGraph graph = new BindingGraph();
        DatasourceCapability metricCapability = new DatasourceCapability(false, true, false, false);
        graph.addObjectBinding("a", objectBinding("MetricA", field("MetricA", "value", "dac-a", DatasourceType.DAC, "metric_a", "value", metricCapability)));
        graph.addObjectBinding("b", objectBinding("MetricB", field("MetricB", "value", "dac-b", DatasourceType.DAC, "metric_b", "value", metricCapability)));

        assertStrategy(SplitStrategy.AGGREGATE_PARTIAL_PUSHDOWN_MERGE, query, graph);
    }

    @Test
    void selectsAggregateMemory() {
        OqlQuery query = operationQuery("AGGREGATE");
        BindingGraph memoryGraph = new BindingGraph();
        ObjectBinding objectBinding = new ObjectBinding("NoAgg");
        objectBinding.add(new FieldBinding("NoAgg", "value", "api", DatasourceType.API, "/values", "value",
                new DatasourceCapability(false, false, false, false)));
        memoryGraph.addObjectBinding("n", objectBinding);

        assertStrategy(SplitStrategy.AGGREGATE_MEMORY, query, memoryGraph);
    }

    @Test
    void selectsDagDependentAggregate() {
        OqlQuery query = operationQuery("AGGREGATE");
        BindingGraph graph = new BindingGraph();
        DatasourceCapability sqlCapability = new DatasourceCapability(true, true, true, false);
        graph.addObjectBinding("o", objectBinding("Order", field("Order", "amount", "mysql-sales", DatasourceType.SQL, "orders", "amount", sqlCapability)));
        graph.setDependencyRequired(true);

        assertStrategy(SplitStrategy.DAG_DEPENDENT_AGGREGATE, query, graph);
    }

    private void assertStrategy(SplitStrategy expected, OqlQuery query, BindingGraph graph) {
        SplitStrategy actual = selector.select(query.getOperation(), graph, query).getStrategy();
        COVERED_STRATEGIES.add(actual);
        assertEquals(expected, actual);
    }

    private OqlQuery operationQuery(String operation) {
        return parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"strategy-test\",\"operation\":\"" + operation + "\","
                + "\"objects\":[{\"objectType\":\"StrategyObject\",\"alias\":\"o\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[\"id\"]}]"
                + "}");
    }

    private ObjectBinding objectBinding(String objectType, FieldBinding fieldBinding) {
        ObjectBinding objectBinding = new ObjectBinding(objectType);
        objectBinding.add(fieldBinding);
        return objectBinding;
    }

    private FieldBinding field(String objectType, String logicalField, String datasourceId, DatasourceType datasourceType,
                               String physicalContainer, String physicalField, DatasourceCapability capability) {
        return new FieldBinding(objectType, logicalField, datasourceId, datasourceType, physicalContainer, physicalField, capability);
    }
}
