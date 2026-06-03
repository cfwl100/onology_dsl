package com.onology.oac.queryframework;

import com.onology.oac.queryframework.assembler.ObjectAssembler;
import com.onology.oac.queryframework.assembler.RelationRows;
import com.onology.oac.queryframework.assembler.MetricRows;
import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import com.onology.oac.queryframework.domain.ResultModels.OntologyObjectInstance;
import com.onology.oac.queryframework.domain.ResultModels.OntologyRelationshipInstance;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ResultAssemblerTest {
    @Test
    void testObjectAssembler() {
        var assembler = new ObjectAssembler();
        var fragment = new FragmentResult("f1", "mysql_1", List.of(Map.of("objectType", "Cell", "rid", "Cell:1", "cellId", "123")), Map.of());
        var objects = assembler.assemble(Map.of(fragment.fragmentId(), fragment));
        assertEquals(1, objects.size());
        OntologyObjectInstance obj = objects.get(0);
        assertEquals("Cell", obj.objectType());
    }

    @Test
    void testRelationRows() {
        var assembler = new RelationRows();
        var fragment = new FragmentResult("f1", "mysql_1", List.of(Map.of("relationshipType", "locatedIn", "relationshipRid", "rel:1", "sourceRid", "Cell:1", "targetRid", "Grid:1")), Map.of());
        List<OntologyRelationshipInstance> relationships = assembler.build(Map.of(fragment.fragmentId(), fragment));
        assertEquals(1, relationships.size());
    }

    @Test
    void testMetricRows() {
        var collector = new MetricRows();
        var fragment = new FragmentResult("f1", "mysql_1", List.of(Map.of("city", "sh", "avgPrb", 50)), Map.of());
        var rows = collector.collect(Map.of(fragment.fragmentId(), fragment));
        assertEquals(1, rows.size());
    }
}
