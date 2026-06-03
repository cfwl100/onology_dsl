package com.onology.oac.queryframework.sql;

/** Helper for conservative SQL identifiers. */
public final class SqlName {
    private SqlName() {
    }

    public static String safe(String name) {
        if (name == null || !name.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalArgumentException("invalid SQL identifier: " + name);
        }
        return name;
    }
}
