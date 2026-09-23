package com.cfwl.oql.gql;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GqlLikeOqlConverterTest {
    private final GqlLikeOqlConverter converter = new GqlLikeOqlConverter();
    private final GqlLikeOqlConverter.ConverterOptions options = GqlLikeOqlConverter.ConverterOptions.defaults().withSchemaRef("test-v1");

    @Test
    void convertsSimpleObjectQuery() {
        JsonNode json = converter.convert("""
                MATCH (o:Order)
                WHERE o.status == "completed"
                RETURN o.id AS id, o.orderNo AS orderNo, o.amount AS amount, o.status AS status
                ORDER BY o.createdAt DESC
                LIMIT 1000
                """, options);

        assertEquals("QUERY", json.get("operation").asText());
        assertEquals("Order", json.get("objects").get(0).get("objectType").asText());
        assertEquals("status", json.get("conditions").get("field").asText());
        assertEquals("EQ", json.get("conditions").get("operator").asText());
        assertEquals("FIELDS", json.get("returns").get(0).get("kind").asText());
        assertEquals("createdAt", json.get("orders").get(0).get("field").asText());
        assertEquals(1000, json.get("maxResults").get("limit").asInt());
    }

    @Test
    void convertsAssociationQuery() {
        JsonNode json = converter.convert("""
                MATCH (a:Alarm)-[r:happenOn]->(ne:Ne)
                WHERE a.alarmName LIKE "LinkDown"
                RETURN ne.neId AS neId, ne.name AS name
                LIMIT 1000
                """, options);

        assertEquals("ASSOCIATION_QUERY", json.get("operation").asText());
        assertEquals(2, json.get("objects").size());
        assertEquals("happenOn", json.get("relationships").get(0).get("relationshipType").asText());
        assertEquals("a", json.get("relationships").get(0).get("from").asText());
        assertEquals("ne", json.get("relationships").get(0).get("to").asText());
        assertEquals("alarmName", json.get("conditions").get("field").asText());
    }

    @Test
    void convertsAggregateQueryWithAggregateFilter() {
        JsonNode json = converter.convert("""
                MATCH (ck:CellKpi)
                WHERE ck.collectTime >= DATE_SUB(NOW(), "PT1H")
                RETURN ck.cellId AS cellId, AVG(ck.prbUsage) AS avgPrbUsage, COUNT(*) AS sampleCount
                GROUP BY ck.cellId
                AGGREGATE FILTER avgPrbUsage > 80 AND sampleCount >= 100
                ORDER BY avgPrbUsage DESC
                LIMIT 1000
                """, options);

        assertEquals("AGGREGATE", json.get("operation").asText());
        assertEquals("FUNCTION", json.get("conditions").get("values").get(0).get("kind").asText());
        assertEquals("DATE_SUB", json.get("conditions").get("values").get(0).get("name").asText());
        assertEquals("GROUP_BY", json.get("returns").get(0).get("kind").asText());
        assertEquals("METRIC", json.get("returns").get(1).get("kind").asText());
        assertEquals("AVG", json.get("returns").get(1).get("function").asText());
        assertEquals("GROUP", json.get("aggregateFilter").get("kind").asText());
        assertEquals("avgPrbUsage", json.get("orders").get(0).get("field").asText());
    }

    @Test
    void convertsFunctionGroupBy() {
        JsonNode json = converter.convert("""
                MATCH (ck:CellKpi)
                WHERE ck.collectTime >= DATE_SUB(NOW(), "P1D")
                RETURN DATE_TRUNC("hour", ck.collectTime) AS collectHour, ck.cellId AS cellId, AVG(ck.prbUsage) AS avgPrbUsage
                GROUP BY DATE_TRUNC("hour", ck.collectTime) AS collectHour, ck.cellId
                ORDER BY collectHour ASC
                LIMIT 1000
                """, options);

        assertEquals("AGGREGATE", json.get("operation").asText());
        assertEquals("GROUP_BY", json.get("returns").get(0).get("kind").asText());
        assertTrue(json.get("returns").get(0).has("expr"));
        assertEquals("DATE_TRUNC", json.get("returns").get(0).get("expr").get("name").asText());
        assertEquals("collectHour", json.get("orders").get(0).get("field").asText());
    }

    @Test
    void rejectsReturnStar() {
        assertThrows(GqlLikeOqlConverter.OqlConversionException.class, () -> converter.convert("""
                MATCH (o:Order)
                RETURN o.*
                LIMIT 1000
                """, options));
    }
}
