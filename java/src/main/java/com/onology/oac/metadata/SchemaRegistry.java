package com.onology.oac.metadata;

import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 本体模型元数据注册中心（示例内存实现）。
 *
 * <p>该类模拟外部 schema/mapping registry，维护：
 * <ul>
 *   <li>schemaRef -> objectType -> ObjectSchema</li>
 *   <li>对象属性 -> 物理数据源/表(或tag)/列(或属性)</li>
 * </ul>
 *
 * <p>用于 OAC 编译阶段完成 OQL 字段绑定与分源规划。
 */
@Component
public class SchemaRegistry {
    private final Map<String, Map<String, ObjectSchema>> snapshots;

    public SchemaRegistry() {
        // 关系型示例：Order 映射到 mysql_main.orders
        Map<String, FieldMapping> orderFields = Map.of(
                "id", new FieldMapping("mysql_main", "orders", "id", true),
                "orderNo", new FieldMapping("mysql_main", "orders", "order_no", false),
                "status", new FieldMapping("mysql_main", "orders", "status", false),
                "amount", new FieldMapping("mysql_main", "orders", "amount", false)
        );

        // 跨源示例：User.email 位于 pg_profile
        Map<String, FieldMapping> userFields = Map.of(
                "id", new FieldMapping("mysql_main", "users", "id", true),
                "firstName", new FieldMapping("mysql_main", "users", "first_name", false),
                "email", new FieldMapping("pg_profile", "user_profile", "email", false)
        );

        // 图谱示例：Employee 属性位于 NebulaGraph（source 前缀 nebula_）
        Map<String, FieldMapping> employeeFields = Map.of(
                "id", new FieldMapping("nebula_graph", "employee", "id", true),
                "name", new FieldMapping("nebula_graph", "employee", "name", false),
                "title", new FieldMapping("nebula_graph", "employee", "title", false)
        );

        this.snapshots = Map.of("demo.sales.v1", Map.of(
                "Order", new ObjectSchema("Order", "mysql_main", "id", orderFields),
                "User", new ObjectSchema("User", "mysql_main", "id", userFields),
                "Employee", new ObjectSchema("Employee", "nebula_graph", "id", employeeFields)
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
