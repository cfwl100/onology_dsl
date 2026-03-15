package com.onology.oac.compiler;

import com.onology.oac.model.Condition;
import com.onology.oac.model.OrderBy;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class DialectTranslator {

    public PhysicalPlan toPhysical(LogicalPlan logicalPlan) {
        Map<String, List<BoundField>> groups = new LinkedHashMap<>();
        for (BoundField field : logicalPlan.boundFields()) {
            groups.computeIfAbsent(field.source(), k -> new ArrayList<>()).add(field);
        }

        List<PhysicalNode> nodes = new ArrayList<>();
        String primaryNodeId = null;
        int idx = 1;
        for (Map.Entry<String, List<BoundField>> entry : groups.entrySet()) {
            String nodeId = "N" + idx;
            if (primaryNodeId == null) {
                primaryNodeId = nodeId;
            }
            List<String> columns = entry.getValue().stream()
                    .map(f -> f.column() + " AS " + f.logicalField())
                    .toList();
            String whereClause = renderWhere(logicalPlan.filters());
            String orderClause = renderOrder(logicalPlan.orders());
            String statement = "SELECT " + String.join(", ", columns)
                    + " FROM " + entry.getValue().get(0).table()
                    + whereClause + orderClause
                    + " LIMIT " + logicalPlan.limit();
            List<String> deps = nodeId.equals(primaryNodeId) ? List.of() : List.of(primaryNodeId);
            nodes.add(new PhysicalNode(nodeId, entry.getKey(), statement, deps));
            idx++;
        }

        boolean degraded = groups.size() > 1;
        List<String> hints = degraded ? List.of("cross-source merge in OAC") : List.of("single-source pushdown");
        return new PhysicalPlan(nodes, degraded, hints);
    }

    private String renderWhere(List<Condition> conditions) {
        if (conditions.isEmpty()) {
            return "";
        }
        List<String> expressions = conditions.stream()
                .map(c -> c.field() + " " + mapOp(c.op()) + " '" + c.value() + "'")
                .toList();
        return " WHERE " + String.join(" AND ", expressions);
    }

    private String renderOrder(List<OrderBy> orders) {
        if (orders.isEmpty()) {
            return "";
        }
        List<String> expressions = orders.stream()
                .map(o -> o.field() + " " + o.direction())
                .toList();
        return " ORDER BY " + String.join(", ", expressions);
    }

    private String mapOp(String op) {
        return switch (op) {
            case "eq" -> "=";
            case "ne" -> "!=";
            case "gt" -> ">";
            case "gte" -> ">=";
            case "lt" -> "<";
            case "lte" -> "<=";
            case "like" -> "LIKE";
            default -> "=";
        };
    }
}
