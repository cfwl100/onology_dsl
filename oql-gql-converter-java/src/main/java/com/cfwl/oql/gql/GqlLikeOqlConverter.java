package com.cfwl.oql.gql;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.BooleanNode;
import com.fasterxml.jackson.databind.node.DoubleNode;
import com.fasterxml.jackson.databind.node.IntNode;
import com.fasterxml.jackson.databind.node.NullNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.TextNode;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Converts the OQL-GQL Profile surface syntax into Canonical JSON OQL.
 *
 * <p>This converter intentionally implements a conservative subset documented in
 * {@code oql-gql-profile-spec.md}:
 * MATCH / WHERE / RETURN / GROUP BY / AGGREGATE FILTER / ORDER BY / LIMIT / OFFSET.
 * It is not a full GQL/Cypher parser. Unsupported constructs fail fast so that
 * callers do not accidentally execute ambiguous or dialect-specific queries.</p>
 */
public final class GqlLikeOqlConverter {
    private static final ObjectMapper MAPPER = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

    private static final Set<String> AGGREGATE_FUNCTIONS = Set.of("COUNT", "SUM", "AVG", "MIN", "MAX");
    private static final Set<String> BUILTIN_FUNCTIONS = Set.of(
            "ABS", "ROUND",
            "LENGTH", "LOWER", "UPPER", "TRIM", "SUBSTRING",
            "NOW", "DATE_TRUNC", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "DATE_ADD", "DATE_SUB", "DATEDIFF",
            "COALESCE", "IFNULL"
    );

    /** Converts a GQL-like OQL statement to Canonical JSON OQL. */
    public ObjectNode convert(String gql, ConverterOptions options) {
        Objects.requireNonNull(gql, "gql must not be null");
        ConverterOptions opts = options == null ? ConverterOptions.defaults() : options;
        ParsedQuery query = parseClauses(gql);
        QueryModel model = parseMatch(query.matchClause());
        parseReturn(query.returnClause(), model);
        if (query.groupByClause() != null) {
            parseGroupBy(query.groupByClause(), model);
        }
        if (query.whereClause() != null) {
            model.conditions = parsePredicateExpression(query.whereClause());
        }
        if (query.aggregateFilterClause() != null) {
            model.aggregateFilter = parseAggregateFilter(query.aggregateFilterClause());
        }
        if (query.orderByClause() != null) {
            parseOrderBy(query.orderByClause(), model);
        }
        model.limit = query.limitClause() == null ? opts.defaultLimit() : parsePositiveInt(query.limitClause(), "LIMIT");
        model.offset = query.offsetClause() == null ? 0 : parseNonNegativeInt(query.offsetClause(), "OFFSET");
        if (model.limit > opts.maxLimit()) {
            throw new OqlConversionException("LIMIT exceeds maxLimit: " + model.limit + " > " + opts.maxLimit());
        }
        String operation = inferOperation(model);
        return toCanonicalJson(model, operation, opts);
    }

    /** Converts and serializes as pretty JSON. */
    public String convertToJson(String gql, ConverterOptions options) {
        try {
            return MAPPER.writeValueAsString(convert(gql, options));
        } catch (JsonProcessingException e) {
            throw new OqlConversionException("Failed to serialize canonical JSON OQL", e);
        }
    }

    private ParsedQuery parseClauses(String gql) {
        String normalized = stripComments(gql).trim();
        if (normalized.isEmpty()) {
            throw new OqlConversionException("Query is empty");
        }
        Map<String, Integer> positions = findClausePositions(normalized);
        requireClause(positions, "MATCH");
        requireClause(positions, "RETURN");
        String match = sliceClause(normalized, positions, "MATCH");
        String where = sliceClause(normalized, positions, "WHERE");
        String ret = sliceClause(normalized, positions, "RETURN");
        String groupBy = sliceClause(normalized, positions, "GROUP BY");
        String aggregateFilter = sliceClause(normalized, positions, "AGGREGATE FILTER");
        String orderBy = sliceClause(normalized, positions, "ORDER BY");
        String limit = sliceClause(normalized, positions, "LIMIT");
        String offset = sliceClause(normalized, positions, "OFFSET");
        return new ParsedQuery(match, where, ret, groupBy, aggregateFilter, orderBy, limit, offset);
    }

    private String stripComments(String text) {
        StringBuilder sb = new StringBuilder();
        for (String line : text.replace("\r\n", "\n").split("\n")) {
            int idx = line.indexOf("--");
            sb.append(idx >= 0 ? line.substring(0, idx) : line).append('\n');
        }
        return sb.toString();
    }

    private Map<String, Integer> findClausePositions(String text) {
        String upper = text.toUpperCase(Locale.ROOT);
        List<String> clauseNames = List.of("AGGREGATE FILTER", "GROUP BY", "ORDER BY", "MATCH", "WHERE", "RETURN", "LIMIT", "OFFSET");
        Map<String, Integer> positions = new LinkedHashMap<>();
        for (String clause : clauseNames) {
            Matcher matcher = Pattern.compile("(?<![A-Z0-9_])" + Pattern.quote(clause) + "(?![A-Z0-9_])", Pattern.CASE_INSENSITIVE).matcher(upper);
            if (matcher.find()) {
                positions.put(clause, matcher.start());
            }
        }
        return positions;
    }

    private void requireClause(Map<String, Integer> positions, String clause) {
        if (!positions.containsKey(clause)) {
            throw new OqlConversionException("Missing required clause: " + clause);
        }
    }

    private String sliceClause(String text, Map<String, Integer> positions, String clause) {
        Integer start = positions.get(clause);
        if (start == null) {
            return null;
        }
        int contentStart = start + clause.length();
        int end = text.length();
        for (Map.Entry<String, Integer> entry : positions.entrySet()) {
            int pos = entry.getValue();
            if (pos > start && pos < end) {
                end = pos;
            }
        }
        return text.substring(contentStart, end).trim();
    }

    private QueryModel parseMatch(String match) {
        if (match == null || match.isBlank()) {
            throw new OqlConversionException("MATCH clause is empty");
        }
        QueryModel model = new QueryModel();
        List<String> tokens = tokenizeMatch(match);
        if (tokens.isEmpty() || !isNodeToken(tokens.get(0))) {
            throw new OqlConversionException("MATCH must start with a node pattern: " + match);
        }
        NodePattern firstNode = parseNode(tokens.get(0));
        model.addObject(firstNode.alias(), firstNode.objectType());
        String previousAlias = firstNode.alias();
        for (int i = 1; i < tokens.size(); ) {
            if (i + 1 >= tokens.size()) {
                throw new OqlConversionException("Relationship token must be followed by node token in MATCH: " + match);
            }
            RelationshipPattern rel = parseRelationship(tokens.get(i));
            NodePattern nextNode = parseNode(tokens.get(i + 1));
            model.addObject(nextNode.alias(), nextNode.objectType());
            String from = rel.inbound() ? nextNode.alias() : previousAlias;
            String to = rel.inbound() ? previousAlias : nextNode.alias();
            model.relationships.add(new RelationshipModel(rel.alias(), rel.relationshipType(), from, to, rel.inbound() ? "INBOUND" : "OUTBOUND", rel.pathPolicy()));
            previousAlias = nextNode.alias();
            i += 2;
        }
        return model;
    }

    private List<String> tokenizeMatch(String match) {
        String compact = match.replace("\n", " ").trim();
        List<String> tokens = new ArrayList<>();
        int i = 0;
        while (i < compact.length()) {
            char c = compact.charAt(i);
            if (Character.isWhitespace(c)) {
                i++;
                continue;
            }
            if (c == '(') {
                int end = findMatching(compact, i, '(', ')');
                tokens.add(compact.substring(i, end + 1));
                i = end + 1;
            } else if (c == '-' || c == '<') {
                int nextNode = compact.indexOf('(', i);
                if (nextNode < 0) {
                    throw new OqlConversionException("Invalid relationship pattern in MATCH: " + match);
                }
                tokens.add(compact.substring(i, nextNode).trim());
                i = nextNode;
            } else {
                throw new OqlConversionException("Unexpected MATCH token near: " + compact.substring(i));
            }
        }
        return tokens;
    }

    private boolean isNodeToken(String token) {
        return token.startsWith("(") && token.endsWith(")");
    }

    private NodePattern parseNode(String token) {
        Matcher m = Pattern.compile("^\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)$").matcher(token);
        if (!m.matches()) {
            throw new OqlConversionException("Invalid node pattern: " + token);
        }
        return new NodePattern(m.group(1), m.group(2));
    }

    private RelationshipPattern parseRelationship(String token) {
        boolean inbound = token.startsWith("<-");
        Pattern pattern = inbound
                ? Pattern.compile("^<-\\s*\\[\\s*([A-Za-z_][A-Za-z0-9_]*)?\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)(\\s*\\{.*})?\\s*]\\s*-$")
                : Pattern.compile("^-\\s*\\[\\s*([A-Za-z_][A-Za-z0-9_]*)?\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)(\\s*\\{.*})?\\s*]\\s*->$");
        Matcher m = pattern.matcher(token);
        if (!m.matches()) {
            throw new OqlConversionException("Invalid relationship pattern: " + token);
        }
        String alias = m.group(1) == null || m.group(1).isBlank() ? "r" : m.group(1);
        String type = m.group(2);
        Map<String, Object> pathPolicy = parsePathPolicy(m.group(3));
        return new RelationshipPattern(alias, type, inbound, pathPolicy);
    }

    private Map<String, Object> parsePathPolicy(String raw) {
        if (raw == null || raw.isBlank()) {
            return Map.of();
        }
        String body = raw.trim();
        if (!body.startsWith("{") || !body.endsWith("}")) {
            throw new OqlConversionException("Invalid path policy: " + raw);
        }
        body = body.substring(1, body.length() - 1).trim();
        Map<String, Object> out = new LinkedHashMap<>();
        if (body.isBlank()) {
            return out;
        }
        for (String part : splitTopLevel(body, ',')) {
            String[] kv = part.split(":", 2);
            if (kv.length != 2) {
                throw new OqlConversionException("Invalid path policy entry: " + part);
            }
            String key = kv[0].trim();
            String value = kv[1].trim();
            if (!Set.of("minDepth", "maxDepth", "maxFanout", "maxPaths", "cyclePolicy", "returnPath").contains(key)) {
                throw new OqlConversionException("Unsupported path policy key: " + key);
            }
            out.put(key, parseLiteral(value));
        }
        return out;
    }

    private void parseReturn(String clause, QueryModel model) {
        if (clause == null || clause.isBlank()) {
            throw new OqlConversionException("RETURN clause is empty");
        }
        for (String item : splitTopLevel(clause, ',')) {
            ReturnItem ret = parseReturnItem(item);
            if (ret.kind == ReturnKind.FIELD) {
                model.returnFields.computeIfAbsent(ret.ref, ignored -> new LinkedHashSet<>()).add(ret.field);
                model.returnAliases.add(ret.alias);
            } else if (ret.kind == ReturnKind.EXPR) {
                model.exprReturns.add(ret);
                model.returnAliases.add(ret.alias);
            } else if (ret.kind == ReturnKind.METRIC) {
                model.metricReturns.add(ret);
                model.metricAliases.add(ret.alias);
                model.returnAliases.add(ret.alias);
            }
        }
    }

    private ReturnItem parseReturnItem(String item) {
        String[] aliasSplit = splitAsAlias(item.trim());
        String expr = aliasSplit[0].trim();
        String alias = aliasSplit[1].trim();
        if ("*".equals(expr) || expr.endsWith(".*")) {
            throw new OqlConversionException("RETURN * is not allowed: " + item);
        }
        FunctionCall function = tryParseFunction(expr).orElse(null);
        if (function != null) {
            String name = function.name().toUpperCase(Locale.ROOT);
            if (AGGREGATE_FUNCTIONS.contains(name)) {
                if ("COUNT".equals(name) && function.args().size() == 1 && "*".equals(function.args().get(0).trim())) {
                    return ReturnItem.metric(name, null, "*", alias);
                }
                if (function.args().size() != 1) {
                    throw new OqlConversionException("Aggregate function requires exactly one argument: " + expr);
                }
                FieldRef fieldRef = parseFieldRef(function.args().get(0).trim());
                return ReturnItem.metric(name, fieldRef.ref(), fieldRef.field(), alias);
            }
            return ReturnItem.expr(convertExpression(expr), alias);
        }
        FieldRef fieldRef = parseFieldRef(expr);
        return ReturnItem.field(fieldRef.ref(), fieldRef.field(), alias);
    }

    private String[] splitAsAlias(String item) {
        Matcher m = Pattern.compile("(?i)^(.+?)\\s+AS\\s+([A-Za-z_][A-Za-z0-9_]*)$").matcher(item.trim());
        if (!m.matches()) {
            throw new OqlConversionException("RETURN item must use explicit AS alias: " + item);
        }
        return new String[]{m.group(1), m.group(2)};
    }

    private void parseGroupBy(String clause, QueryModel model) {
        for (String item : splitTopLevel(clause, ',')) {
            String raw = item.trim();
            if (raw.isBlank()) {
                continue;
            }
            String exprPart = raw;
            String alias = null;
            Matcher as = Pattern.compile("(?i)^(.+?)\\s+AS\\s+([A-Za-z_][A-Za-z0-9_]*)$").matcher(raw);
            if (as.matches()) {
                exprPart = as.group(1).trim();
                alias = as.group(2).trim();
            }
            if (tryParseFunction(exprPart).isPresent()) {
                if (alias == null) {
                    throw new OqlConversionException("Function GROUP BY item must use AS alias: " + raw);
                }
                model.groupByExprs.add(new GroupByExpr(convertExpression(exprPart), alias));
            } else {
                FieldRef ref = parseFieldRef(exprPart);
                model.groupByFields.add(new GroupByField(ref.ref(), ref.field(), alias == null ? ref.field() : alias));
            }
        }
    }

    private JsonNode parsePredicateExpression(String clause) {
        List<String> orParts = splitLogical(clause, "OR");
        if (orParts.size() > 1) {
            return groupNode("OR", orParts.stream().map(this::parsePredicateExpression).toList());
        }
        List<String> andParts = splitLogical(clause, "AND");
        if (andParts.size() > 1) {
            return groupNode("AND", andParts.stream().map(this::parsePredicateExpression).toList());
        }
        String trimmed = stripOuterParentheses(clause.trim());
        if (trimmed.toUpperCase(Locale.ROOT).startsWith("NOT ")) {
            return groupNode("NOT", List.of(parsePredicateExpression(trimmed.substring(4).trim())));
        }
        return parseSinglePredicate(trimmed);
    }

    private JsonNode parseSinglePredicate(String text) {
        Matcher isNull = Pattern.compile("(?i)^(.+?)\\s+IS\\s+(NOT\\s+)?NULL$").matcher(text);
        if (isNull.matches()) {
            ObjectNode node = predicateLeftNode(isNull.group(1).trim());
            node.put("operator", isNull.group(2) == null ? "IS_NULL" : "IS_NOT_NULL");
            return node;
        }
        Matcher between = Pattern.compile("(?i)^(.+?)\\s+BETWEEN\\s+(.+?)\\s+AND\\s+(.+)$").matcher(text);
        if (between.matches()) {
            ObjectNode node = predicateLeftNode(between.group(1).trim());
            node.put("operator", "BETWEEN");
            ArrayNode values = MAPPER.createArrayNode();
            values.add(literalNode(parseLiteralOrExpr(between.group(2).trim())));
            values.add(literalNode(parseLiteralOrExpr(between.group(3).trim())));
            node.set("values", values);
            return node;
        }
        Matcher in = Pattern.compile("(?i)^(.+?)\\s+(NOT\\s+)?IN\\s*\\[(.*)]$").matcher(text);
        if (in.matches()) {
            ObjectNode node = predicateLeftNode(in.group(1).trim());
            node.put("operator", in.group(2) == null ? "IN" : "NOT_IN");
            ArrayNode values = MAPPER.createArrayNode();
            for (String v : splitTopLevel(in.group(3), ',')) {
                values.add(literalNode(parseLiteralOrExpr(v.trim())));
            }
            node.set("values", values);
            return node;
        }
        String[][] ops = {{">=", "GTE"}, {"<=", "LTE"}, {"==", "EQ"}, {"!=", "NE"}, {">", "GT"}, {"<", "LT"}, {" LIKE ", "LIKE"}};
        for (String[] op : ops) {
            int idx = indexOfOperator(text, op[0]);
            if (idx >= 0) {
                String left = text.substring(0, idx).trim();
                String right = text.substring(idx + op[0].length()).trim();
                ObjectNode node = predicateLeftNode(left);
                node.put("operator", op[1]);
                ArrayNode values = MAPPER.createArrayNode();
                Object value = parseLiteralOrExpr(right);
                values.add(literalNode(value));
                node.set("values", values);
                return node;
            }
        }
        throw new OqlConversionException("Unsupported predicate: " + text);
    }

    private ObjectNode predicateLeftNode(String left) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("kind", "PREDICATE");
        if (tryParseFunction(left).isPresent()) {
            node.set("left", convertExpression(left));
        } else {
            FieldRef field = parseFieldRef(left);
            node.put("ref", field.ref());
            node.put("field", field.field());
        }
        return node;
    }

    private JsonNode groupNode(String relation, List<JsonNode> children) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("kind", "GROUP");
        node.put("relation", relation);
        ArrayNode arr = MAPPER.createArrayNode();
        children.forEach(arr::add);
        node.set("children", arr);
        return node;
    }

    private List<String> splitLogical(String text, String keyword) {
        List<String> parts = new ArrayList<>();
        int depth = 0;
        boolean inString = false;
        int start = 0;
        String upper = text.toUpperCase(Locale.ROOT);
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '"' && (i == 0 || text.charAt(i - 1) != '\\')) inString = !inString;
            if (inString) continue;
            if (c == '(') depth++;
            if (c == ')') depth--;
            if (depth == 0 && upper.startsWith(" " + keyword + " ", i)) {
                parts.add(text.substring(start, i).trim());
                start = i + keyword.length() + 2;
                i = start - 1;
            }
        }
        parts.add(text.substring(start).trim());
        return parts.size() == 1 && parts.get(0).equals(text.trim()) ? List.of(text.trim()) : parts;
    }

    private JsonNode parseAggregateFilter(String clause) {
        JsonNode node = parseMetricPredicateExpression(clause);
        return node;
    }

    private JsonNode parseMetricPredicateExpression(String clause) {
        List<String> orParts = splitLogical(clause, "OR");
        if (orParts.size() > 1) return groupNode("OR", orParts.stream().map(this::parseMetricPredicateExpression).toList());
        List<String> andParts = splitLogical(clause, "AND");
        if (andParts.size() > 1) return groupNode("AND", andParts.stream().map(this::parseMetricPredicateExpression).toList());
        String text = stripOuterParentheses(clause.trim());
        String[][] ops = {{">=", "GTE"}, {"<=", "LTE"}, {"==", "EQ"}, {"!=", "NE"}, {">", "GT"}, {"<", "LT"}};
        for (String[] op : ops) {
            int idx = indexOfOperator(text, op[0]);
            if (idx >= 0) {
                String metricAlias = text.substring(0, idx).trim();
                String right = text.substring(idx + op[0].length()).trim();
                ObjectNode node = MAPPER.createObjectNode();
                node.put("kind", "METRIC_PREDICATE");
                node.put("metricAlias", metricAlias);
                node.put("operator", op[1]);
                ArrayNode values = MAPPER.createArrayNode();
                values.add(literalNode(parseLiteral(right)));
                node.set("values", values);
                return node;
            }
        }
        throw new OqlConversionException("Unsupported AGGREGATE FILTER predicate: " + text);
    }

    private void parseOrderBy(String clause, QueryModel model) {
        for (String item : splitTopLevel(clause, ',')) {
            String[] parts = item.trim().split("\\s+");
            if (parts.length == 0 || parts[0].isBlank()) continue;
            String expr = parts[0].trim();
            String direction = parts.length > 1 ? parts[1].toUpperCase(Locale.ROOT) : "ASC";
            if (!direction.equals("ASC") && !direction.equals("DESC")) {
                throw new OqlConversionException("ORDER BY direction must be ASC or DESC: " + item);
            }
            if (expr.contains(".")) {
                FieldRef ref = parseFieldRef(expr);
                model.orders.add(new OrderModel(ref.ref(), ref.field(), direction));
            } else {
                model.orders.add(new OrderModel(null, expr, direction));
            }
        }
    }

    private JsonNode convertExpression(String expr) {
        Optional<FunctionCall> maybeFunction = tryParseFunction(expr.trim());
        if (maybeFunction.isPresent()) {
            FunctionCall fn = maybeFunction.get();
            String namespace = null;
            String name = fn.name();
            if (name.contains(".")) {
                String[] ns = name.split("\\.", 2);
                namespace = ns[0];
                name = ns[1];
            }
            String upperName = name.toUpperCase(Locale.ROOT);
            if (namespace == null && !BUILTIN_FUNCTIONS.contains(upperName) && !AGGREGATE_FUNCTIONS.contains(upperName)) {
                throw new OqlConversionException("Unsupported built-in function or missing namespace for extension function: " + name);
            }
            ObjectNode node = MAPPER.createObjectNode();
            node.put("kind", "FUNCTION");
            if (namespace != null) node.put("namespace", namespace);
            node.put("name", upperName);
            ArrayNode args = MAPPER.createArrayNode();
            for (String arg : fn.args()) {
                String trimmed = arg.trim();
                if (trimmed.equals("*")) {
                    args.add("*");
                } else if (tryParseFunction(trimmed).isPresent() || trimmed.matches("[A-Za-z_][A-Za-z0-9_]*\\.[A-Za-z_][A-Za-z0-9_]*")) {
                    args.add(convertExpression(trimmed));
                } else {
                    args.add(literalNode(parseLiteral(trimmed)));
                }
            }
            node.set("args", args);
            return node;
        }
        if (expr.matches("[A-Za-z_][A-Za-z0-9_]*\\.[A-Za-z_][A-Za-z0-9_]*")) {
            FieldRef field = parseFieldRef(expr);
            ObjectNode node = MAPPER.createObjectNode();
            node.put("kind", "FIELD");
            node.put("ref", field.ref());
            node.put("field", field.field());
            return node;
        }
        return literalNode(parseLiteral(expr));
    }

    private Optional<FunctionCall> tryParseFunction(String expr) {
        int open = expr.indexOf('(');
        if (open <= 0 || !expr.endsWith(")")) {
            return Optional.empty();
        }
        String name = expr.substring(0, open).trim();
        if (!name.matches("[A-Za-z_][A-Za-z0-9_]*(\\.[A-Za-z_][A-Za-z0-9_]*)?")) {
            return Optional.empty();
        }
        int close = findMatching(expr, open, '(', ')');
        if (close != expr.length() - 1) {
            return Optional.empty();
        }
        String argsBody = expr.substring(open + 1, close).trim();
        List<String> args = argsBody.isEmpty() ? List.of() : splitTopLevel(argsBody, ',');
        return Optional.of(new FunctionCall(name, args));
    }

    private Object parseLiteralOrExpr(String text) {
        if (tryParseFunction(text).isPresent()) {
            return convertExpression(text);
        }
        return parseLiteral(text);
    }

    private Object parseLiteral(String text) {
        String v = text.trim();
        if (v.startsWith("\"") && v.endsWith("\"")) return unquote(v);
        if (v.equalsIgnoreCase("true")) return Boolean.TRUE;
        if (v.equalsIgnoreCase("false")) return Boolean.FALSE;
        if (v.equalsIgnoreCase("null")) return null;
        if (v.matches("-?\\d+")) return Integer.parseInt(v);
        if (v.matches("-?\\d+\\.\\d+")) return Double.parseDouble(v);
        return v;
    }

    private JsonNode literalNode(Object value) {
        if (value instanceof JsonNode node) return node;
        if (value == null) return NullNode.getInstance();
        if (value instanceof Integer i) return IntNode.valueOf(i);
        if (value instanceof Double d) return DoubleNode.valueOf(d);
        if (value instanceof Boolean b) return BooleanNode.valueOf(b);
        return TextNode.valueOf(String.valueOf(value));
    }

    private FieldRef parseFieldRef(String expr) {
        Matcher m = Pattern.compile("^([A-Za-z_][A-Za-z0-9_]*)\\.([A-Za-z_][A-Za-z0-9_]*)$").matcher(expr.trim());
        if (!m.matches()) {
            throw new OqlConversionException("Expected property reference alias.property, got: " + expr);
        }
        return new FieldRef(m.group(1), m.group(2));
    }

    private int indexOfOperator(String text, String op) {
        int depth = 0;
        boolean inString = false;
        for (int i = 0; i <= text.length() - op.length(); i++) {
            char c = text.charAt(i);
            if (c == '"' && (i == 0 || text.charAt(i - 1) != '\\')) inString = !inString;
            if (inString) continue;
            if (c == '(') depth++;
            if (c == ')') depth--;
            if (depth == 0 && text.regionMatches(true, i, op, 0, op.length())) return i;
        }
        return -1;
    }

    private String stripOuterParentheses(String s) {
        String t = s.trim();
        while (t.startsWith("(") && t.endsWith(")") && findMatching(t, 0, '(', ')') == t.length() - 1) {
            t = t.substring(1, t.length() - 1).trim();
        }
        return t;
    }

    private int findMatching(String s, int openIndex, char open, char close) {
        int depth = 0;
        boolean inString = false;
        for (int i = openIndex; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"' && (i == 0 || s.charAt(i - 1) != '\\')) inString = !inString;
            if (inString) continue;
            if (c == open) depth++;
            if (c == close) {
                depth--;
                if (depth == 0) return i;
            }
        }
        throw new OqlConversionException("Unbalanced expression: " + s);
    }

    private List<String> splitTopLevel(String text, char delimiter) {
        List<String> out = new ArrayList<>();
        int depthParen = 0;
        int depthBrace = 0;
        int depthBracket = 0;
        boolean inString = false;
        int start = 0;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '"' && (i == 0 || text.charAt(i - 1) != '\\')) inString = !inString;
            if (inString) continue;
            if (c == '(') depthParen++;
            else if (c == ')') depthParen--;
            else if (c == '{') depthBrace++;
            else if (c == '}') depthBrace--;
            else if (c == '[') depthBracket++;
            else if (c == ']') depthBracket--;
            else if (c == delimiter && depthParen == 0 && depthBrace == 0 && depthBracket == 0) {
                out.add(text.substring(start, i).trim());
                start = i + 1;
            }
        }
        out.add(text.substring(start).trim());
        return out.stream().filter(s -> !s.isBlank()).toList();
    }

    private String unquote(String text) {
        String body = text.substring(1, text.length() - 1);
        return body.replace("\\\"", "\"").replace("\\n", "\n").replace("\\t", "\t");
    }

    private int parsePositiveInt(String text, String name) {
        int v = parseNonNegativeInt(text, name);
        if (v <= 0) throw new OqlConversionException(name + " must be positive");
        return v;
    }

    private int parseNonNegativeInt(String text, String name) {
        String trimmed = text.trim().split("\\s+")[0];
        if (!trimmed.matches("\\d+")) throw new OqlConversionException(name + " must be an integer: " + text);
        return Integer.parseInt(trimmed);
    }

    private String inferOperation(QueryModel model) {
        if (!model.metricReturns.isEmpty() || !model.groupByFields.isEmpty() || !model.groupByExprs.isEmpty() || model.aggregateFilter != null) {
            return "AGGREGATE";
        }
        if (!model.relationships.isEmpty()) {
            return "ASSOCIATION_QUERY";
        }
        return "QUERY";
    }

    private ObjectNode toCanonicalJson(QueryModel model, String operation, ConverterOptions opts) {
        ObjectNode root = MAPPER.createObjectNode();
        root.put("version", opts.version());
        root.put("schemaRef", opts.schemaRef());
        root.put("strict", true);
        root.put("operation", operation);

        ArrayNode objects = MAPPER.createArrayNode();
        for (ObjectModel obj : model.objects.values()) {
            ObjectNode node = MAPPER.createObjectNode();
            node.put("objectType", obj.objectType);
            node.put("alias", obj.alias);
            objects.add(node);
        }
        root.set("objects", objects);

        if (!model.relationships.isEmpty()) {
            ArrayNode rels = MAPPER.createArrayNode();
            for (RelationshipModel rel : model.relationships) {
                ObjectNode node = MAPPER.createObjectNode();
                node.put("relationshipType", rel.relationshipType);
                node.put("alias", rel.alias);
                node.put("from", rel.from);
                node.put("to", rel.to);
                node.put("direction", rel.direction);
                node.put("mode", "LIST");
                if (!rel.pathPolicy.isEmpty()) {
                    ObjectNode policy = MAPPER.createObjectNode();
                    rel.pathPolicy.forEach((k, v) -> policy.set(k, literalNode(v)));
                    if (!policy.has("cyclePolicy")) policy.put("cyclePolicy", "NO_REPEAT_VERTEX");
                    node.set("pathPolicy", policy);
                }
                rels.add(node);
            }
            root.set("relationships", rels);
        }

        if (model.conditions != null) root.set("conditions", model.conditions);

        ArrayNode returns = MAPPER.createArrayNode();
        if ("AGGREGATE".equals(operation)) {
            Set<String> seenGroupAliases = new LinkedHashSet<>();
            for (GroupByField f : model.groupByFields) {
                if (seenGroupAliases.add(f.alias)) {
                    ObjectNode n = MAPPER.createObjectNode();
                    n.put("kind", "GROUP_BY");
                    n.put("ref", f.ref);
                    n.put("field", f.field);
                    n.put("alias", f.alias);
                    returns.add(n);
                }
            }
            for (GroupByExpr e : model.groupByExprs) {
                if (seenGroupAliases.add(e.alias)) {
                    ObjectNode n = MAPPER.createObjectNode();
                    n.put("kind", "GROUP_BY");
                    n.set("expr", e.expr);
                    n.put("alias", e.alias);
                    returns.add(n);
                }
            }
            for (ReturnItem metric : model.metricReturns) {
                ObjectNode n = MAPPER.createObjectNode();
                n.put("kind", "METRIC");
                n.put("function", metric.function);
                if (metric.ref != null) n.put("ref", metric.ref);
                n.put("field", metric.field);
                n.put("alias", metric.alias);
                returns.add(n);
            }
        } else {
            for (Map.Entry<String, Set<String>> entry : model.returnFields.entrySet()) {
                ObjectNode n = MAPPER.createObjectNode();
                n.put("kind", "FIELDS");
                n.put("ref", entry.getKey());
                ArrayNode fields = MAPPER.createArrayNode();
                entry.getValue().forEach(fields::add);
                n.set("fields", fields);
                returns.add(n);
            }
            for (ReturnItem expr : model.exprReturns) {
                ObjectNode n = MAPPER.createObjectNode();
                n.put("kind", "EXPR");
                n.set("expr", expr.expr);
                n.put("alias", expr.alias);
                returns.add(n);
            }
        }
        if (returns.isEmpty()) throw new OqlConversionException("RETURN clause produced no canonical returns");
        root.set("returns", returns);

        if (model.aggregateFilter != null) root.set("aggregateFilter", model.aggregateFilter);

        if (!model.orders.isEmpty()) {
            ArrayNode orders = MAPPER.createArrayNode();
            for (OrderModel order : model.orders) {
                ObjectNode n = MAPPER.createObjectNode();
                if (order.ref != null) n.put("ref", order.ref);
                n.put("field", order.field);
                n.put("direction", order.direction);
                orders.add(n);
            }
            root.set("orders", orders);
        }

        ObjectNode maxResults = MAPPER.createObjectNode();
        maxResults.put("limit", model.limit);
        maxResults.put("offset", model.offset);
        root.set("maxResults", maxResults);
        return root;
    }

    public record ConverterOptions(String schemaRef, String version, int defaultLimit, int maxLimit) {
        public static ConverterOptions defaults() {
            return new ConverterOptions("default", "2.0", 1000, 100000);
        }
        public ConverterOptions withSchemaRef(String schemaRef) {
            return new ConverterOptions(schemaRef, version, defaultLimit, maxLimit);
        }
    }

    public static final class OqlConversionException extends RuntimeException {
        public OqlConversionException(String message) { super(message); }
        public OqlConversionException(String message, Throwable cause) { super(message, cause); }
    }

    private record ParsedQuery(String matchClause, String whereClause, String returnClause, String groupByClause,
                               String aggregateFilterClause, String orderByClause, String limitClause, String offsetClause) {}
    private record NodePattern(String alias, String objectType) {}
    private record RelationshipPattern(String alias, String relationshipType, boolean inbound, Map<String, Object> pathPolicy) {}
    private record FieldRef(String ref, String field) {}
    private record FunctionCall(String name, List<String> args) {}
    private record ObjectModel(String alias, String objectType) {}
    private record RelationshipModel(String alias, String relationshipType, String from, String to, String direction, Map<String, Object> pathPolicy) {}
    private record GroupByField(String ref, String field, String alias) {}
    private record GroupByExpr(JsonNode expr, String alias) {}
    private record OrderModel(String ref, String field, String direction) {}

    private enum ReturnKind { FIELD, EXPR, METRIC }

    private static final class ReturnItem {
        ReturnKind kind;
        String ref;
        String field;
        String alias;
        String function;
        JsonNode expr;
        static ReturnItem field(String ref, String field, String alias) {
            ReturnItem item = new ReturnItem(); item.kind = ReturnKind.FIELD; item.ref = ref; item.field = field; item.alias = alias; return item;
        }
        static ReturnItem expr(JsonNode expr, String alias) {
            ReturnItem item = new ReturnItem(); item.kind = ReturnKind.EXPR; item.expr = expr; item.alias = alias; return item;
        }
        static ReturnItem metric(String function, String ref, String field, String alias) {
            ReturnItem item = new ReturnItem(); item.kind = ReturnKind.METRIC; item.function = function; item.ref = ref; item.field = field; item.alias = alias; return item;
        }
    }

    private static final class QueryModel {
        final Map<String, ObjectModel> objects = new LinkedHashMap<>();
        final List<RelationshipModel> relationships = new ArrayList<>();
        final Map<String, Set<String>> returnFields = new LinkedHashMap<>();
        final List<ReturnItem> exprReturns = new ArrayList<>();
        final List<ReturnItem> metricReturns = new ArrayList<>();
        final List<GroupByField> groupByFields = new ArrayList<>();
        final List<GroupByExpr> groupByExprs = new ArrayList<>();
        final List<OrderModel> orders = new ArrayList<>();
        final Set<String> metricAliases = new LinkedHashSet<>();
        final Set<String> returnAliases = new LinkedHashSet<>();
        JsonNode conditions;
        JsonNode aggregateFilter;
        int limit;
        int offset;
        void addObject(String alias, String objectType) {
            ObjectModel existing = objects.get(alias);
            if (existing != null && !existing.objectType.equals(objectType)) {
                throw new OqlConversionException("Alias reused for different object types: " + alias);
            }
            objects.putIfAbsent(alias, new ObjectModel(alias, objectType));
        }
    }
}
