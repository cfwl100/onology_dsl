package com.oac.framework.kernel;

import com.oac.framework.error.ErrorCode;
import com.oac.framework.error.OacException;
import com.oac.framework.error.PlanningException;
import com.oac.framework.error.TranslationException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class KernelCoreTest {

    @Test
    void operationType_equalsAndHashCode() {
        OperationType query1 = new OperationType("QUERY");
        OperationType query2 = new OperationType("QUERY");
        OperationType aggregate = new OperationType("AGGREGATE");

        assertEquals(query1, query2);
        assertEquals(query1.hashCode(), query2.hashCode());
        assertNotEquals(query1, aggregate);
        assertEquals("QUERY", query1.code());
        assertEquals("OperationType{QUERY}", query1.toString());
    }

    @Test
    void operationType_builtinConstants() {
        assertEquals("QUERY", OperationType.QUERY.code());
        assertEquals("AGGREGATE", OperationType.AGGREGATE.code());
        assertEquals("ASSOCIATION_QUERY", OperationType.ASSOCIATION_QUERY.code());
        assertEquals("EXPLAIN", OperationType.EXPLAIN.code());
    }

    @Test
    void operationType_rejectsBlank() {
        assertThrows(IllegalArgumentException.class, () -> new OperationType(""));
        assertThrows(IllegalArgumentException.class, () -> new OperationType(null));
        assertThrows(IllegalArgumentException.class, () -> new OperationType("   "));
    }

    @Test
    void queryContext_defaults() {
        QueryContext ctx = QueryContext.defaults();
        assertEquals("", ctx.queryId());
        assertEquals("", ctx.traceId());
        assertEquals(30000, ctx.timeoutMs());
        assertEquals(1000, ctx.maxResults());
        assertNotNull(ctx.properties());
    }

    @Test
    void queryContext_builder() {
        QueryContext ctx = QueryContext.builder()
                .queryId("q1")
                .traceId("t1")
                .timeoutMs(5000)
                .maxResults(100)
                .putProperty("key", "value")
                .build();

        assertEquals("q1", ctx.queryId());
        assertEquals("t1", ctx.traceId());
        assertEquals(5000, ctx.timeoutMs());
        assertEquals(100, ctx.maxResults());
        assertEquals("value", ctx.property("key"));
    }

    @Test
    void queryExplain_builder() {
        QueryExplain explain = QueryExplain.builder()
                .strategy("single-source")
                .addDecision("step 1")
                .addDecision("step 2")
                .build();

        assertEquals("single-source", explain.strategy());
        assertEquals(2, explain.decisions().size());
    }

    @Test
    void errorCode_codes() {
        assertEquals(1000, ErrorCode.VALIDATION_ERROR.code());
        assertEquals(2000, ErrorCode.PLANNING_ERROR.code());
        assertEquals(3000, ErrorCode.TRANSLATION_ERROR.code());
        assertEquals(4000, ErrorCode.EXECUTION_ERROR.code());
        assertEquals(5000, ErrorCode.ASSEMBLY_ERROR.code());
        assertEquals(9999, ErrorCode.INTERNAL_ERROR.code());
    }

    @Test
    void oacException_constructor() {
        OacException ex = new OacException(ErrorCode.PLANNING_ERROR, "test message");
        assertEquals(ErrorCode.PLANNING_ERROR, ex.errorCode());
        assertEquals("test message", ex.getMessage());

        Throwable cause = new RuntimeException("cause");
        OacException ex2 = new OacException(ErrorCode.TRANSLATION_ERROR, "with cause", cause);
        assertEquals(cause, ex2.getCause());
    }

    @Test
    void planningException_usesCorrectCode() {
        PlanningException ex = new PlanningException("planning failed");
        assertEquals(ErrorCode.PLANNING_ERROR, ex.errorCode());
    }

    @Test
    void translationException_usesCorrectCode() {
        TranslationException ex = new TranslationException("translation failed");
        assertEquals(ErrorCode.TRANSLATION_ERROR, ex.errorCode());
    }

    @Test
    void strategyDecision_builder() {
        StrategyDecision decision = StrategyDecision.builder()
                .strategyCode("single-source")
                .priority(10)
                .reason("simple case")
                .build();

        assertEquals("single-source", decision.strategyCode());
        assertEquals(10, decision.priority());
        assertEquals("simple case", decision.reason());
    }

    @Test
    void datasourceKind_builtinConstants() {
        assertEquals("MYSQL", DatasourceKind.MYSQL.code());
        assertEquals("NEBULA_GRAPH", DatasourceKind.NEBULA_GRAPH.code());
        assertEquals("ES", DatasourceKind.ES.code());
    }

    @Test
    void datasourceKind_equalsAndHashCode() {
        DatasourceKind mysql1 = new DatasourceKind("MYSQL");
        DatasourceKind mysql2 = new DatasourceKind("MYSQL");
        DatasourceKind es = new DatasourceKind("ES");

        assertEquals(mysql1, mysql2);
        assertEquals(mysql1.hashCode(), mysql2.hashCode());
        assertNotEquals(mysql1, es);
    }

    @Test
    void queryKernel_builder() {
        QueryKernel kernel = QueryKernel.builder()
                .parser(new com.oac.query.dsl.OqlParser())
                .build();

        assertNotNull(kernel);
    }

    @Test
    void queryKernel_execute_returnsFailure() {
        QueryKernel kernel = QueryKernel.builder().build();
        QueryContext ctx = QueryContext.defaults();

        com.oac.query.assembly.OntologyQueryResult result = kernel.execute("{}", ctx);

        assertFalse(result.isSuccess());
    }

    @Test
    void queryKernel_explain_returnsEmpty() {
        QueryKernel kernel = QueryKernel.builder().build();
        QueryContext ctx = QueryContext.defaults();

        QueryExplain explain = kernel.explain("{}", ctx);

        assertNotNull(explain);
    }
}
