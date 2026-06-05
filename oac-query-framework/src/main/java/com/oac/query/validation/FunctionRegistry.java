package com.oac.query.validation;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * 受治理 OQL 函数的注册表。
 *
 * 核心函数是可移植的语义函数；扩展函数必须先注册到这里，
 * 校验器才允许智能体生成的 OQL 文档使用它们。
 */
public class FunctionRegistry {
    public static final String CONDITIONS_LEFT = "conditions.left";
    public static final String RETURNS_EXPR = "returns.expr";
    public static final String RETURNS_GROUP_BY_EXPR = "returns.groupByExpr";
    public static final String MUTATION_SET = "mutation.set";

    private final Map<String, FunctionDescriptor> descriptors = new LinkedHashMap<String, FunctionDescriptor>();

    public static FunctionRegistry withCoreFunctions() {
        FunctionRegistry registry = new FunctionRegistry();
        Set<String> defaultLocations = locations(CONDITIONS_LEFT, RETURNS_EXPR, RETURNS_GROUP_BY_EXPR, MUTATION_SET);
        for (String name : Arrays.asList(
                "ABS", "ROUND", "CEIL", "FLOOR",
                "LENGTH", "LOWER", "UPPER", "TRIM", "SUBSTRING", "CONCAT",
                "NOW", "DATE_TRUNC", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
                "DATE_ADD", "DATE_SUB", "DATEDIFF",
                "COALESCE", "IFNULL")) {
            registry.register(new FunctionDescriptor(null, name, 0, Integer.MAX_VALUE, defaultLocations, true));
        }
        return registry;
    }

    public static Set<String> locations(String... locations) {
        return new LinkedHashSet<String>(Arrays.asList(locations));
    }

    public void register(FunctionDescriptor descriptor) {
        descriptors.put(key(descriptor.getNamespace(), descriptor.getName()), descriptor);
    }

    public FunctionDescriptor resolve(String namespace, String name) {
        return descriptors.get(key(namespace, name));
    }

    public boolean contains(String namespace, String name) {
        return resolve(namespace, name) != null;
    }

    private String key(String namespace, String name) {
        String normalizedNamespace = namespace == null || namespace.trim().isEmpty() ? "core" : namespace.trim();
        return normalizedNamespace + ":" + (name == null ? "" : name.trim().toUpperCase());
    }
}
