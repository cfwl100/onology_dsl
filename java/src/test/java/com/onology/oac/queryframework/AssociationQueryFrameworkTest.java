package com.onology.oac.queryframework;

import com.onology.oac.queryframework.assembler.RelationRows;
import com.onology.oac.queryframework.core.SplitStrategySelector;
import com.onology.oac.queryframework.domain.MetadataModels;
import com.onology.oac.queryframework.domain.OqlModels;
import com.onology.oac.queryframework.domain.PlanModels;
import com.onology.oac.queryframework.domain.ResultModels.FragmentResult;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AssociationQueryFrameworkTest {
    @Test
    void shouldSelectRelationalJoinForAssociationQuery() {
        var relation = new MetadataModels.RelationshipBinding("schema", "locatedIn", "Cell", "Grid",
                MetadataModels.RelationshipStorageType.RELATIONAL_JOIN_TABLE, "mysql_1", MetadataModels.DatasourceType.MYSQL,
                "cell_grid", "cell_id", "grid_id", "id", "id", null, null, null);
        var graph = new PlanModels.BindingGraph(
                List.of(new PlanModels.ObjectBindingNode("c", "Cell"), new PlanModels.ObjectBindingNode("g", "Grid")),
                List.of(),
                List.of(new PlanModels.RelationshipBindingNode("r", relation)),
                List.of(),
                List.of(),
                Map.of("mysql_1", capability()));
        var query = new OqlModels.OqlQuery("1.0", "schema", true, OqlModels.OperationType.ASSOCIATION_QUERY,
                List.of(new OqlModels.OqlObject("Cell", "c", null), new OqlModels.OqlObject("Grid", "g", null)),
                List.of(new OqlModels.OqlRelationship("locatedIn", "r", "c", "g", OqlModels.RelationshipDirection.OUTBOUND,
                        OqlModels.RelationshipMode.ONE)),
                null, List.of(new OqlModels.OqlReturnItem(OqlModels.ReturnKind.FIELDS, "c", List.of("id"), null,
                        null, null, null)),
                null, List.of(), null, List.of(), Map.of(), Map.of());

        var decision = new SplitStrategySelector().select(OqlModels.OperationType.ASSOCIATION_QUERY, graph, query);

        assertEquals(PlanModels.SplitStrategy.ASSOCIATION_RELATIONAL_JOIN, decision.strategy());
    }

    @Test
    void shouldAssembleRelationshipRows() {
        FragmentResult fragment = new FragmentResult("f1", "mysql_1",
                List.of(Map.of("relationshipType", "locatedIn", "relationshipRid", "r1", "sourceRid", "Cell:1", "targetRid", "Grid:1")),
                Map.of());
        var relationships = new RelationRows().build(Map.of(fragment.fragmentId(), fragment));
        assertEquals(1, relationships.size());
        assertEquals("locatedIn", relationships.get(0).relationshipType());
    }

    private MetadataModels.DatasourceCapability capability() {
        return new MetadataModels.DatasourceCapability("mysql_1", MetadataModels.DatasourceType.MYSQL,
                true, true, true, true, true, true, true, true, true, false, true, false);
    }
}
