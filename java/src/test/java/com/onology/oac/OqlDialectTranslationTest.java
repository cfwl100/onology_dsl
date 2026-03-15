package com.onology.oac;

import com.onology.oac.compiler.DialectTranslator;
import com.onology.oac.compiler.OntologyBinder;
import com.onology.oac.metadata.SchemaRegistry;
import com.onology.oac.model.OqlRequest;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 基于本体模型元数据 source 映射，验证 OQL DSL 到 SQL/nGQL 的翻译行为。
 */
class OqlDialectTranslationTest {

    private final OntologyBinder binder = new OntologyBinder(new SchemaRegistry());
    private final DialectTranslator translator = new DialectTranslator();

    @Test
    void userQueryShouldTranslateToSqlAndCrossSourcePlan() {
        var logical = binder.bind(OqlRequest.sampleQuery());
        var physical = translator.toPhysical(logical);

        assertEquals(2, physical.nodes().size());
        assertTrue(physical.degraded());

        // mysql_main 节点
        String stmt1 = physical.nodes().get(0).statement();
        assertTrue(stmt1.startsWith("SELECT"));
        assertTrue(stmt1.contains("FROM users"));

        // pg_profile 节点
        String stmt2 = physical.nodes().get(1).statement();
        assertTrue(stmt2.startsWith("SELECT"));
        assertTrue(stmt2.contains("FROM user_profile"));
    }

    @Test
    void employeeQueryShouldTranslateToNgql() {
        var logical = binder.bind(OqlRequest.sampleGraphQuery());
        var physical = translator.toPhysical(logical);

        assertEquals(1, physical.nodes().size());
        assertTrue(!physical.degraded());

        String stmt = physical.nodes().get(0).statement();
        assertTrue(stmt.startsWith("LOOKUP ON employee"));
        assertTrue(stmt.contains("YIELD employee.id AS id"));
    }
}
