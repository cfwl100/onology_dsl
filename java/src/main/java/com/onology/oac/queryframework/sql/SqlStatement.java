package com.onology.oac.queryframework.sql;

import java.util.List;

/** Immutable SQL statement and bind values. */
public record SqlStatement(String text, List<Object> values) {
}
