package com.oac.framework.kernel;

public final class DatasourceKind {
    public static final DatasourceKind MYSQL = new DatasourceKind("MYSQL");
    public static final DatasourceKind GAUSSDB = new DatasourceKind("GAUSSDB");
    public static final DatasourceKind NEBULA_GRAPH = new DatasourceKind("NEBULA_GRAPH");
    public static final DatasourceKind API = new DatasourceKind("API");
    public static final DatasourceKind DAC = new DatasourceKind("DAC");
    public static final DatasourceKind ES = new DatasourceKind("ES");

    private final String code;

    public DatasourceKind(String code) {
        if (code == null || code.trim().isEmpty()) {
            throw new IllegalArgumentException("datasource kind code must not be blank");
        }
        this.code = code;
    }

    public String code() {
        return code;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        DatasourceKind that = (DatasourceKind) o;
        return code.equals(that.code);
    }

    @Override
    public int hashCode() {
        return code.hashCode();
    }

    @Override
    public String toString() {
        return "DatasourceKind{" + code + "}";
    }
}
