package com.onology.oac.queryframework.sql;

import com.onology.oac.queryframework.domain.MetadataModels.DatasourceType;
import com.onology.oac.queryframework.domain.PlanModels.PhysicalSourceQueryNode;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.PlannerContext;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.QueryTranslator;
import com.onology.oac.queryframework.spi.QueryFrameworkSpi.SqlPhysicalQuery;

import java.util.ArrayList;
import java.util.StringJoiner;

/** Builds a parameterized SQL physical query from one source fragment. */
public class SqlSourceTranslator implements QueryTranslator<SqlPhysicalQuery> {
    @Override
    public DatasourceType supportType() {
        return DatasourceType.MYSQL;
    }

    @Override
    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.datasourceType() == DatasourceType.MYSQL
                || fragment.datasourceType() == DatasourceType.GAUSSDB
                || fragment.datasourceType() == DatasourceType.POSTGRESQL;
    }

    @Override
    public SqlPhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        if (fragment.properties().isEmpty()) {
            throw new IllegalArgumentException("SQL fragment requires at least one property binding");
        }
        String table = SqlName.safe(fragment.properties().get(0).binding().tableName());
        StringJoiner columns = new StringJoiner(", ");
        fragment.properties().forEach(item -> columns.add(SqlName.safe(item.binding().fieldName()) + " AS " + SqlName.safe(item.propertyName())));
        String text = "SELECT " + columns + " FROM " + table;
        return new SqlPhysicalQuery(fragment.datasourceId(), fragment.datasourceType(), text, new ArrayList<>(), fragment.datasourceType().name());
    }
}
