package com.onology.oac.metadata;

import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class SchemaRegistry {
    private final Map<String, Map<String, ObjectSchema>> snapshots;

    public SchemaRegistry() {
        Map<String, FieldMapping> orderFields = Map.of(
                "id", new FieldMapping("mysql_main", "orders", "id", true),
                "orderNo", new FieldMapping("mysql_main", "orders", "order_no", false),
                "status", new FieldMapping("mysql_main", "orders", "status", false),
                "amount", new FieldMapping("mysql_main", "orders", "amount", false)
        );
        Map<String, FieldMapping> userFields = Map.of(
                "id", new FieldMapping("mysql_main", "users", "id", true),
                "firstName", new FieldMapping("mysql_main", "users", "first_name", false),
                "email", new FieldMapping("pg_profile", "user_profile", "email", false)
        );
        this.snapshots = Map.of("demo.sales.v1", Map.of(
                "Order", new ObjectSchema("Order", "mysql_main", "id", orderFields),
                "User", new ObjectSchema("User", "mysql_main", "id", userFields)
        ));
    }

    public Map<String, ObjectSchema> getSnapshot(String schemaRef) {
        Map<String, ObjectSchema> snapshot = snapshots.get(schemaRef);
        if (snapshot == null) {
            throw new IllegalArgumentException("schemaRef not found: " + schemaRef);
        }
        return snapshot;
    }
}
