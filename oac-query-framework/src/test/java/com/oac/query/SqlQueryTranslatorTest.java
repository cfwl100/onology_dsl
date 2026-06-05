package com.oac.query;

import com.oac.query.binding.BindingGraph;
import com.oac.query.binding.BindingResolver;
import com.oac.query.dsl.OqlParser;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.plan.logical.LogicalPlanBuilder;
import com.oac.query.plan.physical.PhysicalPlan;
import com.oac.query.plan.physical.PhysicalPlanBuilder;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.spi.PhysicalQuery;
import com.oac.query.spi.SqlQueryTranslator;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 验证 SQL 翻译器把物理 source 节点拼接为参数化 SQL，而不是 mock 文本。
 */
class SqlQueryTranslatorTest {
    private final OqlParser parser = new OqlParser();
    private final BindingResolver bindingResolver = new BindingResolver();
    private final LogicalPlanBuilder logicalPlanBuilder = new LogicalPlanBuilder();
    private final PhysicalPlanBuilder physicalPlanBuilder = new PhysicalPlanBuilder();
    private final SqlQueryTranslator translator = new SqlQueryTranslator();

    @Test
    void translatesQueryToParameterizedSelectWhereOrderAndLimit() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"sales-v1\",\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"conditions\":{\"kind\":\"PREDICATE\",\"ref\":\"o\",\"field\":\"status\",\"operator\":\"EQ\",\"values\":[\"completed\"]},"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[\"id\",\"orderNo\",\"amount\",\"status\"]}],"
                + "\"orders\":[{\"ref\":\"o\",\"field\":\"createdAt\",\"direction\":\"DESC\"}],"
                + "\"maxResults\":{\"limit\":10,\"offset\":5}"
                + "}");

        PhysicalQuery physicalQuery = translator.translate(firstSourceNode(query), PlannerContext.defaults());

        assertEquals("SELECT t0.`id` AS `id`, t0.`order_no` AS `orderNo`, t0.`amount` AS `amount`, t0.`status` AS `status`"
                + " FROM `orders` t0"
                + " WHERE t0.`status` = :p1"
                + " ORDER BY t0.`created_at` DESC"
                + " LIMIT :limit2 OFFSET :offset3", physicalQuery.payload());
        Map<String, Object> namedParameters = namedParameters(physicalQuery);
        assertEquals("completed", namedParameters.get("p1"));
        assertEquals(10, namedParameters.get("limit2"));
        assertEquals(5, namedParameters.get("offset3"));
    }

    @Test
    void translatesAggregateToGroupByMetricAndHaving() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"sales-v1\",\"operation\":\"AGGREGATE\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"returns\":["
                + "{\"kind\":\"GROUP_BY\",\"ref\":\"o\",\"field\":\"region\",\"alias\":\"region\"},"
                + "{\"kind\":\"METRIC\",\"function\":\"SUM\",\"ref\":\"o\",\"field\":\"amount\",\"alias\":\"totalAmount\"}"
                + "],"
                + "\"aggregateFilter\":{\"kind\":\"METRIC_PREDICATE\",\"metricAlias\":\"totalAmount\",\"operator\":\"GT\",\"values\":[1000]}"
                + "}");

        PhysicalQuery physicalQuery = translator.translate(firstSourceNode(query), PlannerContext.defaults());

        assertEquals("SELECT t0.`region` AS `region`, SUM(t0.`amount`) AS `totalAmount`"
                + " FROM `orders` t0"
                + " GROUP BY t0.`region`"
                + " HAVING `totalAmount` > :p1", physicalQuery.payload());
        assertEquals(1000L, namedParameters(physicalQuery).get("p1"));
    }

    @Test
    void translatesDagDynamicInputToInPredicate() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"telecom-v1\",\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Cell\",\"alias\":\"c\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"c\",\"fields\":[\"cellId\"]}]"
                + "}");
        PhysicalSourceQueryNode sourceNode = firstSourceNode(query);
        sourceNode.putDynamicInput("cell_id", Arrays.<Object>asList("cell-001", "cell-002"));

        PhysicalQuery physicalQuery = translator.translate(sourceNode, PlannerContext.defaults());

        assertTrue(physicalQuery.payload().contains("WHERE t0.`cell_id` IN (:d1, :d2)"));
        Map<String, Object> namedParameters = namedParameters(physicalQuery);
        assertEquals("cell-001", namedParameters.get("d1"));
        assertEquals("cell-002", namedParameters.get("d2"));
    }

    private PhysicalSourceQueryNode firstSourceNode(OqlQuery query) {
        BindingGraph graph = bindingResolver.resolve(query).getGraph();
        PhysicalPlan plan = physicalPlanBuilder.build(logicalPlanBuilder.build(query), query, graph);
        return plan.getSourceNodes().get(0);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> namedParameters(PhysicalQuery physicalQuery) {
        return (Map<String, Object>) physicalQuery.parameters().get("namedParameters");
    }
}
