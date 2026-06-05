package com.oac.query;

import com.oac.query.dsl.OqlParser;
import com.oac.query.dsl.OqlQuery;
import com.oac.query.validation.OqlValidator;
import com.oac.query.validation.ValidationResult;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 覆盖应在绑定/执行前失败的 DSL 校验规则。
 */
class OqlValidatorTest {
    private final OqlParser parser = new OqlParser();
    private final OqlValidator validator = new OqlValidator();

    @Test
    void queryRejectsRelationshipsAndAggregateFilter() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\","
                + "\"schemaRef\":\"sales-v1\","
                + "\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"},{\"objectType\":\"Invoice\",\"alias\":\"i\"}],"
                + "\"relationships\":[{\"relationshipType\":\"has_invoice\",\"alias\":\"r1\",\"from\":\"o\",\"to\":\"i\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[\"id\"]}],"
                + "\"aggregateFilter\":{\"kind\":\"METRIC_PREDICATE\",\"metricAlias\":\"x\",\"operator\":\"GT\",\"values\":[1]}"
                + "}");

        ValidationResult result = validator.validate(query);

        assertFalse(result.isSuccess());
        assertTrue(result.getErrors().stream().anyMatch(e -> "relationships".equals(e.getPath())));
        assertTrue(result.getErrors().stream().anyMatch(e -> "aggregateFilter".equals(e.getPath())));
    }

    @Test
    void aggregateFilterMustReferenceMetricAlias() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\","
                + "\"schemaRef\":\"sales-v1\","
                + "\"operation\":\"AGGREGATE\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"returns\":[{\"kind\":\"METRIC\",\"function\":\"SUM\",\"ref\":\"o\",\"field\":\"amount\",\"alias\":\"totalAmount\"}],"
                + "\"aggregateFilter\":{\"kind\":\"METRIC_PREDICATE\",\"metricAlias\":\"missing\",\"operator\":\"GT\",\"values\":[1]}"
                + "}");

        ValidationResult result = validator.validate(query);

        assertFalse(result.isSuccess());
        assertTrue(result.getErrors().stream().anyMatch(e -> e.getPath().endsWith("metricAlias")));
    }

    @Test
    void associationRequiresRelationshipAliasesToReferenceObjects() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\","
                + "\"schemaRef\":\"sales-v1\","
                + "\"operation\":\"ASSOCIATION_QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"relationships\":[{\"relationshipType\":\"has_invoice\",\"alias\":\"r1\",\"from\":\"o\",\"to\":\"missing\"}],"
                + "\"returns\":[{\"kind\":\"FIELDS\",\"ref\":\"o\",\"fields\":[\"id\"]}]"
                + "}");

        ValidationResult result = validator.validate(query);

        assertFalse(result.isSuccess());
        assertTrue(result.getErrors().stream().anyMatch(e -> e.getPath().endsWith(".to")));
    }

    @Test
    void aggregateFunctionCannotBeUsedAsFunctionExpression() {
        OqlQuery query = parser.parse("{"
                + "\"version\":\"2.0\","
                + "\"schemaRef\":\"sales-v1\","
                + "\"operation\":\"QUERY\","
                + "\"objects\":[{\"objectType\":\"Order\",\"alias\":\"o\"}],"
                + "\"returns\":[{\"kind\":\"EXPR\",\"alias\":\"badAvg\",\"expr\":{\"kind\":\"FUNCTION\",\"name\":\"AVG\",\"args\":[{\"kind\":\"FIELD\",\"ref\":\"o\",\"field\":\"amount\"}]}}]"
                + "}");

        ValidationResult result = validator.validate(query);

        assertFalse(result.isSuccess());
        assertTrue(result.getErrors().stream().anyMatch(e -> e.getMessage().contains("METRIC")));
    }
}
