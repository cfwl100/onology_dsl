package com.oac.query.binding;

import com.oac.query.binding.BindingGraph.DatasourceCapability;
import com.oac.query.binding.BindingGraph.FieldBinding;
import com.oac.query.binding.BindingGraph.ObjectBinding;
import com.oac.query.binding.BindingGraph.RelationshipBinding;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * v1 框架使用的内存版元数据样例。
 *
 * 它提供足够的本体到物理映射，用来覆盖 SQL、GQL、DAC 和 ES 的规划路径，
 * 无需依赖外部元数据服务。
 */
public class MockOntologyMetadata {
    private final Map<String, ObjectBinding> objects = new LinkedHashMap<String, ObjectBinding>();
    private final Map<String, RelationshipBinding> relationships = new LinkedHashMap<String, RelationshipBinding>();

    public static MockOntologyMetadata defaults() {
        MockOntologyMetadata metadata = new MockOntologyMetadata();
        DatasourceCapability sql = DatasourceCapability.basicSql();
        DatasourceCapability dac = new DatasourceCapability(false, true, true, false);
        DatasourceCapability es = new DatasourceCapability(false, true, false, false);
        DatasourceCapability gql = DatasourceCapability.graph();

        metadata.register(new ObjectBinding("Order")
                .add(new FieldBinding("Order", "id", "mysql-sales", DatasourceType.SQL, "orders", "id", sql))
                .add(new FieldBinding("Order", "orderNo", "mysql-sales", DatasourceType.SQL, "orders", "order_no", sql))
                .add(new FieldBinding("Order", "amount", "mysql-sales", DatasourceType.SQL, "orders", "amount", sql))
                .add(new FieldBinding("Order", "status", "mysql-sales", DatasourceType.SQL, "orders", "status", sql))
                .add(new FieldBinding("Order", "region", "mysql-sales", DatasourceType.SQL, "orders", "region", sql))
                .add(new FieldBinding("Order", "createdAt", "mysql-sales", DatasourceType.SQL, "orders", "created_at", sql)));

        metadata.register(new ObjectBinding("Invoice")
                .add(new FieldBinding("Invoice", "id", "mysql-sales", DatasourceType.SQL, "invoices", "id", sql))
                .add(new FieldBinding("Invoice", "invoiceNo", "mysql-sales", DatasourceType.SQL, "invoices", "invoice_no", sql))
                .add(new FieldBinding("Invoice", "amount", "mysql-sales", DatasourceType.SQL, "invoices", "amount", sql)));

        metadata.register(new ObjectBinding("Cell")
                .add(new FieldBinding("Cell", "rid", "mysql-cell", DatasourceType.SQL, "dim_cell", "rid", sql))
                .add(new FieldBinding("Cell", "cellId", "mysql-cell", DatasourceType.SQL, "dim_cell", "cell_id", sql))
                .add(new FieldBinding("Cell", "cellName", "mysql-cell", DatasourceType.SQL, "dim_cell", "cell_name", sql))
                .add(new FieldBinding("Cell", "prbUsage", "dac-kpi", DatasourceType.DAC, "prb_usage", "prb_usage", dac))
                .add(new FieldBinding("Cell", "alarmCount", "es-alarm", DatasourceType.ES, "alarm_index", "alarm_count", es)));

        metadata.register(new ObjectBinding("CellKpi")
                .add(new FieldBinding("CellKpi", "cellId", "dac-kpi", DatasourceType.DAC, "cell_kpi", "cell_id", dac))
                .add(new FieldBinding("CellKpi", "collectTime", "dac-kpi", DatasourceType.DAC, "cell_kpi", "collect_time", dac))
                .add(new FieldBinding("CellKpi", "prbUsage", "dac-kpi", DatasourceType.DAC, "cell_kpi", "prb_usage", dac)));

        metadata.register(new ObjectBinding("Device")
                .add(new FieldBinding("Device", "id", "gql-topology", DatasourceType.GQL, "device", "id", gql))
                .add(new FieldBinding("Device", "name", "gql-topology", DatasourceType.GQL, "device", "name", gql)));

        metadata.register(new ObjectBinding("Site")
                .add(new FieldBinding("Site", "id", "gql-topology", DatasourceType.GQL, "site", "id", gql))
                .add(new FieldBinding("Site", "name", "gql-topology", DatasourceType.GQL, "site", "name", gql)));

        metadata.register(new RelationshipBinding("has_invoice", "mysql-sales", DatasourceType.SQL, "order_invoice", sql));
        metadata.register(new RelationshipBinding("installed_on", "gql-topology", DatasourceType.GQL, "installed_on", gql));
        return metadata;
    }

    public void register(ObjectBinding objectBinding) {
        objects.put(objectBinding.getObjectType(), objectBinding);
    }

    public void register(RelationshipBinding relationshipBinding) {
        relationships.put(relationshipBinding.getRelationshipType(), relationshipBinding);
    }

    public ObjectBinding objectBinding(String objectType) {
        ObjectBinding binding = objects.get(objectType);
        if (binding == null) {
            throw new IllegalArgumentException("No object binding registered for " + objectType);
        }
        return binding;
    }

    public RelationshipBinding relationshipBinding(String relationshipType) {
        RelationshipBinding binding = relationships.get(relationshipType);
        if (binding == null) {
            throw new IllegalArgumentException("No relationship binding registered for " + relationshipType);
        }
        return binding;
    }
}
