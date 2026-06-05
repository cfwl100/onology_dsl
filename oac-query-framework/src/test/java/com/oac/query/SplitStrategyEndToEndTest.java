package com.oac.query;

import com.oac.query.assembly.OntologyQueryResult;
import com.oac.query.assembly.QueryResultAssembler;
import com.oac.query.binding.BindingGraph.DatasourceCapability;
import com.oac.query.binding.BindingGraph.FieldBinding;
import com.oac.query.binding.BindingGraph.ObjectBinding;
import com.oac.query.binding.BindingGraph.RelationshipBinding;
import com.oac.query.binding.BindingResolver;
import com.oac.query.binding.DatasourceType;
import com.oac.query.binding.MockOntologyMetadata;
import com.oac.query.dsl.OqlParser;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.logical.LogicalPlanBuilder;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.plan.physical.PhysicalPlanBuilder;
import com.oac.query.runtime.ExecutionContext;
import com.oac.query.runtime.FragmentResult;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.runtime.QueryExecutionEngine;
import com.oac.query.runtime.QueryFrameworkService;
import com.oac.query.spi.QueryExtensionRegistry;
import com.oac.query.strategy.SplitStrategy;
import com.oac.query.validation.OqlValidator;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 从 OQL 入口完整跑到执行与装配阶段，验证每种 SplitStrategy 都有对应端到端场景。
 */
class SplitStrategyEndToEndTest {
    private static final Set<SplitStrategy> COVERED_STRATEGIES = EnumSet.noneOf(SplitStrategy.class);

    private final OqlParser parser = new OqlParser();

    @AfterAll
    static void coversEverySplitStrategyEndToEnd() {
        assertEquals(EnumSet.allOf(SplitStrategy.class), COVERED_STRATEGIES);
    }

    @Test
    void runsSingleSourceSingleTableEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("SingleTable",
                field("SingleTable", "id", "mysql-main", DatasourceType.SQL, "single_table", "id", sql())));

        assertEndToEnd(SplitStrategy.SINGLE_SOURCE_SINGLE_TABLE, query("QUERY", "SingleTable", "id"), metadata);
    }

    @Test
    void runsSingleSourceMultiTableJoinEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("SingleSourceJoin",
                field("SingleSourceJoin", "orderId", "mysql-main", DatasourceType.SQL, "orders", "order_id", sql()),
                field("SingleSourceJoin", "customerName", "mysql-main", DatasourceType.SQL, "customers", "customer_name", sql())));

        assertEndToEnd(SplitStrategy.SINGLE_SOURCE_MULTI_TABLE_JOIN, query("QUERY", "SingleSourceJoin", "orderId", "customerName"), metadata);
    }

    @Test
    void runsCrossSourceMemoryMergeEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("CrossSourceQuery",
                field("CrossSourceQuery", "cellId", "mysql-cell", DatasourceType.SQL, "dim_cell", "cell_id", sql()),
                field("CrossSourceQuery", "prbUsage", "dac-kpi", DatasourceType.DAC, "cell_kpi", "prb_usage", metricNoHaving())));

        assertEndToEnd(SplitStrategy.CROSS_SOURCE_MEMORY_MERGE, query("QUERY", "CrossSourceQuery", "cellId", "prbUsage"), metadata);
    }

    @Test
    void runsDagDependentQueryEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("DagQuery",
                field("DagQuery", "cellId", "mysql-cell", DatasourceType.SQL, "dim_cell", "cell_id", sql()),
                field("DagQuery", "prbUsage", "dac-kpi", DatasourceType.DAC, "cell_kpi", "prb_usage", metricNoHaving())));

        assertEndToEnd(SplitStrategy.DAG_DEPENDENT_QUERY, queryFromSource("QUERY", "DagQuery", "upstream_cells", "cellId", "prbUsage"), metadata);
    }

    @Test
    void runsAssociationGraphPushdownEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(
                object("GraphDevice", field("GraphDevice", "id", "gql-topology", DatasourceType.GQL, "device", "id", graph())),
                object("GraphSite", field("GraphSite", "id", "gql-topology", DatasourceType.GQL, "site", "id", graph())),
                relationship("installed_on_e2e", "gql-topology", DatasourceType.GQL, "installed_on", graph()));

        assertEndToEnd(SplitStrategy.ASSOCIATION_GRAPH_PUSHDOWN,
                associationQuery("GraphDevice", "d", "GraphSite", "s", "installed_on_e2e", "id"), metadata);
    }

    @Test
    void runsAssociationRelationalJoinEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(
                object("RelOrder", field("RelOrder", "id", "mysql-sales", DatasourceType.SQL, "orders", "id", sql())),
                object("RelInvoice", field("RelInvoice", "id", "mysql-sales", DatasourceType.SQL, "invoices", "id", sql())),
                relationship("has_invoice_e2e", "mysql-sales", DatasourceType.SQL, "order_invoice", sql()));

        assertEndToEnd(SplitStrategy.ASSOCIATION_RELATIONAL_JOIN,
                associationQuery("RelOrder", "o", "RelInvoice", "i", "has_invoice_e2e", "id"), metadata);
    }

    @Test
    void runsAssociationMultiStageAssembleEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(
                object("MultiStageOrder", field("MultiStageOrder", "id", "mysql-sales", DatasourceType.SQL, "orders", "id", sql())),
                object("MultiStageInvoice", field("MultiStageInvoice", "id", "invoice-api", DatasourceType.API, "/invoices", "id", noCapability())),
                relationship("cross_source_invoice_e2e", "mysql-sales", DatasourceType.SQL, "order_invoice", sql()));

        assertEndToEnd(SplitStrategy.ASSOCIATION_MULTI_STAGE_ASSEMBLE,
                associationQuery("MultiStageOrder", "o", "MultiStageInvoice", "i", "cross_source_invoice_e2e", "id"), metadata);
    }

    @Test
    void runsAggregatePushdownEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("AggPushdown",
                field("AggPushdown", "amount", "mysql-sales", DatasourceType.SQL, "orders", "amount", sql())));

        assertEndToEnd(SplitStrategy.AGGREGATE_PUSHDOWN, aggregateQuery("AggPushdown", "amount"), metadata);
    }

    @Test
    void runsAggregatePartialPushdownMergeEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("AggPartial",
                field("AggPartial", "amount", "dac-a", DatasourceType.DAC, "metric_a", "amount", metricNoHaving()),
                field("AggPartial", "sampleCount", "dac-b", DatasourceType.DAC, "metric_b", "sample_count", metricNoHaving())));

        assertEndToEnd(SplitStrategy.AGGREGATE_PARTIAL_PUSHDOWN_MERGE, aggregateQuery("AggPartial", "amount"), metadata);
    }

    @Test
    void runsAggregateMemoryEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("AggMemory",
                field("AggMemory", "amount", "order-api", DatasourceType.API, "/orders", "amount", noCapability())));

        assertEndToEnd(SplitStrategy.AGGREGATE_MEMORY, aggregateQuery("AggMemory", "amount"), metadata);
    }

    @Test
    void runsDagDependentAggregateEndToEnd() {
        MockOntologyMetadata metadata = metadataWith(object("DagAggregate",
                field("DagAggregate", "amount", "mysql-sales", DatasourceType.SQL, "orders", "amount", sql())));

        assertEndToEnd(SplitStrategy.DAG_DEPENDENT_AGGREGATE,
                aggregateQueryFromSource("DagAggregate", "upstream_orders", "amount"), metadata);
    }

    private void assertEndToEnd(SplitStrategy expected, OqlQuery query, MockOntologyMetadata metadata) {
        CapturingExecutionEngine executionEngine = new CapturingExecutionEngine(QueryExtensionRegistry.mockDefaults());
        QueryFrameworkService service = new QueryFrameworkService(
                new OqlValidator(),
                new BindingResolver(metadata),
                new LogicalPlanBuilder(),
                new PhysicalPlanBuilder(),
                executionEngine,
                new QueryResultAssembler());

        OntologyQueryResult result = service.run(query, PlannerContext.defaults(), ExecutionContext.defaults());

        assertTrue(result.isSuccess(), "端到端执行应成功，错误：" + result.getErrors());
        assertEquals(expected, executionEngine.capturedPlan.getStrategy());
        COVERED_STRATEGIES.add(executionEngine.capturedPlan.getStrategy());
    }

    private OqlQuery query(String operation, String objectType, String... fields) {
        return queryFromSource(operation, objectType, null, fields);
    }

    private OqlQuery queryFromSource(String operation, String objectType, String fromSource, String... fields) {
        StringBuilder json = new StringBuilder();
        json.append("{\"version\":\"2.0\",\"schemaRef\":\"strategy-e2e\",\"operation\":\"").append(operation).append("\",");
        json.append("\"objects\":[{\"objectType\":\"").append(objectType).append("\",\"alias\":\"o\"");
        if (fromSource != null) {
            json.append(",\"fromSource\":\"").append(fromSource).append("\"");
        }
        json.append("}],\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[");
        appendQuotedArray(json, fields);
        json.append("]}]}");
        return parser.parse(json.toString());
    }

    private OqlQuery aggregateQuery(String objectType, String metricField) {
        return aggregateQueryFromSource(objectType, null, metricField);
    }

    private OqlQuery aggregateQueryFromSource(String objectType, String fromSource, String metricField) {
        StringBuilder json = new StringBuilder();
        json.append("{\"version\":\"2.0\",\"schemaRef\":\"strategy-e2e\",\"operation\":\"AGGREGATE\",");
        json.append("\"objects\":[{\"objectType\":\"").append(objectType).append("\",\"alias\":\"o\"");
        if (fromSource != null) {
            json.append(",\"fromSource\":\"").append(fromSource).append("\"");
        }
        json.append("}],");
        json.append("\"returns\":[{\"kind\":\"METRIC\",\"function\":\"SUM\",\"ref\":\"o\",\"field\":\"")
                .append(metricField)
                .append("\",\"alias\":\"totalValue\"}]}");
        return parser.parse(json.toString());
    }

    private OqlQuery associationQuery(String fromType, String fromAlias, String toType, String toAlias,
                                      String relationshipType, String returnField) {
        String json = "{"
                + "\"version\":\"2.0\",\"schemaRef\":\"strategy-e2e\",\"operation\":\"ASSOCIATION_QUERY\","
                + "\"objects\":["
                + "{\"objectType\":\"" + fromType + "\",\"alias\":\"" + fromAlias + "\"},"
                + "{\"objectType\":\"" + toType + "\",\"alias\":\"" + toAlias + "\"}"
                + "],"
                + "\"relationships\":[{\"relationshipType\":\"" + relationshipType + "\",\"alias\":\"r1\",\"from\":\""
                + fromAlias + "\",\"to\":\"" + toAlias + "\",\"direction\":\"OUTBOUND\",\"mode\":\"LIST\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"" + toAlias + "\",\"fields\":[\"" + returnField + "\"]}]"
                + "}";
        return parser.parse(json);
    }

    private void appendQuotedArray(StringBuilder json, String[] values) {
        for (int i = 0; i < values.length; i++) {
            if (i > 0) {
                json.append(",");
            }
            json.append("\"").append(values[i]).append("\"");
        }
    }

    private MockOntologyMetadata metadataWith(Object... bindings) {
        MockOntologyMetadata metadata = new MockOntologyMetadata();
        for (Object binding : bindings) {
            if (binding instanceof ObjectBinding) {
                metadata.register((ObjectBinding) binding);
            } else if (binding instanceof RelationshipBinding) {
                metadata.register((RelationshipBinding) binding);
            }
        }
        return metadata;
    }

    private ObjectBinding object(String objectType, FieldBinding... fields) {
        ObjectBinding binding = new ObjectBinding(objectType);
        for (FieldBinding field : fields) {
            binding.add(field);
        }
        return binding;
    }

    private FieldBinding field(String objectType, String logicalField, String datasourceId, DatasourceType datasourceType,
                               String physicalContainer, String physicalField, DatasourceCapability capability) {
        return new FieldBinding(objectType, logicalField, datasourceId, datasourceType, physicalContainer, physicalField, capability);
    }

    private RelationshipBinding relationship(String relationshipType, String datasourceId, DatasourceType datasourceType,
                                             String physicalName, DatasourceCapability capability) {
        return new RelationshipBinding(relationshipType, datasourceId, datasourceType, physicalName, capability);
    }

    private DatasourceCapability sql() {
        return new DatasourceCapability(true, true, true, false);
    }

    private DatasourceCapability metricNoHaving() {
        return new DatasourceCapability(false, true, false, false);
    }

    private DatasourceCapability graph() {
        return DatasourceCapability.graph();
    }

    private DatasourceCapability noCapability() {
        return new DatasourceCapability(false, false, false, false);
    }

    private static class CapturingExecutionEngine extends QueryExecutionEngine {
        private PhysicalPlan capturedPlan;

        CapturingExecutionEngine(QueryExtensionRegistry registry) {
            super(registry);
        }

        @Override
        public List<FragmentResult> execute(PhysicalPlan plan, PlannerContext plannerContext, ExecutionContext executionContext) {
            this.capturedPlan = plan;
            return super.execute(plan, plannerContext, executionContext);
        }
    }
}
