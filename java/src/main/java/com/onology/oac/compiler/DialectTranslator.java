package com.onology.oac.compiler;

import com.onology.oac.model.Condition;
import com.onology.oac.model.OrderBy;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 将 LogicalPlan 翻译为按 source 切分的 PhysicalPlan。
 *
 * <p>规则：
 * <ul>
 *   <li>关系型 source（默认）生成 SQL</li>
 *   <li>图谱 source（source 以 nebula_ 开头）生成 nGQL</li>
 * </ul>
 */
@Component
public class DialectTranslator {

    public PhysicalPlan toPhysical(LogicalPlan logicalPlan) {
        // 按 source 分组，体现 “单源优先下推，跨源拆分编排” 原则。
        Map<String, List<BoundField>> groups = new LinkedHashMap<>();
        for (BoundField field : logicalPlan.boundFields()) {
            groups.computeIfAbsent(field.source(), k -> new ArrayList<>()).add(field);
        }

        List<PhysicalNode> nodes = new ArrayList<>();
        String primaryNodeId = null;
        int idx = 1;
        for (Map.Entry<String, List<BoundField>> entry : groups.entrySet()) {
            String source = entry.getKey();
            String nodeId = "N" + idx;
            if (primaryNodeId == null) {
                primaryNodeId = nodeId;
            }

            String statement = isGraphSource(source)
                    ? buildNgql(entry.getValue(), logicalPlan)
                    : buildSql(entry.getValue(), logicalPlan);

            List<String> deps = nodeId.equals(primaryNodeId) ? List.of() : List.of(primaryNodeId);
            nodes.add(new PhysicalNode(nodeId, source, statement, deps));
            idx++;
        }

        boolean degraded = groups.size() > 1;
        List<String> hints = degraded ? List.of("cross-source merge in OAC") : List.of("single-source pushdown");
        return new PhysicalPlan(nodes, degraded, hints);
    }

    private String buildSql(List<BoundField> fields, LogicalPlan logicalPlan) {
        List<String> columns = fields.stream()
                .map(f -> f.column() + " AS " + f.logicalField())
                .toList();
        String whereClause = renderSqlWhere(logicalPlan.filters());
        String orderClause = renderSqlOrder(logicalPlan.orders());
        return "SELECT " + String.join(", ", columns)
                + " FROM " + fields.get(0).table()
                + whereClause + orderClause
                + " LIMIT " + logicalPlan.limit();
    }

    private String buildNgql(List<BoundField> fields, LogicalPlan logicalPlan) {
        // 简化版 nGQL：按 tag（table 字段）进行 LOOKUP。
        String tag = fields.get(0).table();
        List<String> yields = fields.stream()
                .map(f -> tag + "." + f.column() + " AS " + f.logicalField())
                .toList();
        String whereClause = renderNgqlWhere(logicalPlan.filters(), tag);
        return "LOOKUP ON " + tag + whereClause
                + " YIELD " + String.join(", ", yields)
                + " | LIMIT " + logicalPlan.limit();
    }

    private String renderSqlWhere(List<Condition> conditions) {
        if (conditions.isEmpty()) {
            return "";
        }
        List<String> expressions = conditions.stream()
                .map(c -> c.field() + " " + mapSqlOp(c.op()) + " '" + c.value() + "'")
                .toList();
        return " WHERE " + String.join(" AND ", expressions);
    }

    private String renderNgqlWhere(List<Condition> conditions, String tag) {
        if (conditions.isEmpty()) {
            return "";
        }
        List<String> expressions = conditions.stream()
                .map(c -> tag + "." + c.field() + " " + mapNgqlOp(c.op()) + " '" + c.value() + "'")
                .toList();
        return " WHERE " + String.join(" AND ", expressions);
    }

    private String renderSqlOrder(List<OrderBy> orders) {
        if (orders.isEmpty()) {
            return "";
        }
        List<String> expressions = orders.stream()
                .map(o -> o.field() + " " + o.direction())
                .toList();
        return " ORDER BY " + String.join(", ", expressions);
    }

    private String mapSqlOp(String op) {
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



    private String mapNgqlOp(String op) {
        return switch (op) {
            case "eq" -> "=";
            case "ne" -> "!=";
            case "gt" -> ">";
            case "gte" -> ">=";
            case "lt" -> "<";
            case "lte" -> "<=";
            case "like" -> "CONTAINS";
            default -> "=";
        };
    }
    private boolean isGraphSource(String source) {
        return source != null && source.startsWith("nebula_");
    }
}
