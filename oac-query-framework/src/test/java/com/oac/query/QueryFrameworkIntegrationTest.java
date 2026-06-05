package com.oac.query;

import com.oac.query.assembly.OntologyQueryResult;
import com.oac.query.dsl.OqlParser;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.runtime.ExecutionContext;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.runtime.QueryFrameworkService;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 从 OQL JSON 解析到 OntologyQueryResult 的端到端测试。
 */
class QueryFrameworkIntegrationTest {
    private final OqlParser parser = new OqlParser();
    private final QueryFrameworkService service = new QueryFrameworkService();

    @Test
    void runsQueryEndToEnd() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"sales-v1\",\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"conditions\":{\"kind\":\"PREDICATE\",\"ref\":\"o\",\"field\":\"status\",\"operator\":\"EQ\",\"values\":[\"completed\"]},"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[\"id\",\"orderNo\",\"amount\",\"status\"]}],"
                + "\"maxResults\":{\"limit\":100,\"offset\":0}"
                + "}");

        OntologyQueryResult result = service.run(query, PlannerContext.defaults(), ExecutionContext.defaults());

        assertTrue(result.isSuccess());
        assertFalse(result.getObjects().isEmpty());
    }

    @Test
    void runsAggregateWithAggregateFilterEndToEnd() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"telecom-kpi-v1\",\"operation\":\"AGGREGATE\","
                + "\"objects\":[{\"objectType\":\"CellKpi\",\"alias\":\"ck\"}],"
                + "\"returns\":["
                + "{\"kind\":\"GROUP_BY\",\"ref\":\"ck\",\"field\":\"cellId\",\"alias\":\"cellId\"},"
                + "{\"kind\":\"METRIC\",\"function\":\"AVG\",\"ref\":\"ck\",\"field\":\"prbUsage\",\"alias\":\"avgPrbUsage\"},"
                + "{\"kind\":\"METRIC\",\"function\":\"COUNT\",\"ref\":\"ck\",\"field\":\"*\",\"alias\":\"sampleCount\"}"
                + "],"
                + "\"aggregateFilter\":{\"kind\":\"METRIC_PREDICATE\",\"metricAlias\":\"avgPrbUsage\",\"operator\":\"GT\",\"values\":[80]},"
                + "\"maxResults\":{\"limit\":100,\"offset\":0}"
                + "}");

        OntologyQueryResult result = service.run(query, PlannerContext.defaults(), ExecutionContext.defaults());

        assertTrue(result.isSuccess());
        assertFalse(result.getMetrics().isEmpty());
    }

    @Test
    void runsAssociationQueryEndToEnd() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\",\"schemaRef\":\"sales-v1\",\"operation\":\"ASSOCIATION_QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"},{\"objectType\":\"Invoice\",\"alias\":\"i\"}],"
                + "\"relationships\":[{\"relationshipType\":\"has_invoice\",\"alias\":\"r1\",\"from\":\"o\",\"to\":\"i\",\"direction\":\"OUTBOUND\",\"mode\":\"LIST\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"i\",\"fields\":[\"id\",\"invoiceNo\",\"amount\"]}]"
                + "}");

        OntologyQueryResult result = service.run(query, PlannerContext.defaults(), ExecutionContext.defaults());

        assertTrue(result.isSuccess());
        assertFalse(result.getObjects().isEmpty());
    }
}
