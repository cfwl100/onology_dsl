package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.runtime.PlannerContext;
import com.oac.query.spi.PhysicalQueries.ApiPhysicalQuery;
import com.oac.query.spi.PhysicalQueries.DacPhysicalQuery;
import com.oac.query.spi.PhysicalQueries.EsPhysicalQuery;
import com.oac.query.spi.PhysicalQueries.GqlPhysicalQuery;
import com.oac.query.spi.PhysicalQueries.SqlPhysicalQuery;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 测试/演示用翻译器，为每类数据源生成稳定的模拟查询载荷。
 */
public class MockQueryTranslator implements QueryTranslator<PhysicalQuery> {
    private final DatasourceType type;

    public MockQueryTranslator(DatasourceType type) {
        this.type = type;
    }

    public DatasourceType supportType() {
        return type;
    }

    public boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        return fragment.getDatasourceType() == type;
    }

    public PhysicalQuery translate(PhysicalSourceQueryNode fragment, PlannerContext context) {
        Map<String, Object> parameters = new LinkedHashMap<String, Object>();
        parameters.put("projections", fragment.getProjections());
        parameters.put("dynamicInputs", fragment.getDynamicInputs());
        String payload = "mock " + type + " query for " + fragment.getObjectType() + " projections " + fragment.getProjections();
        if (type == DatasourceType.SQL) {
            return new SqlPhysicalQuery(fragment.getId(), fragment.getDatasourceId(), payload, parameters);
        }
        if (type == DatasourceType.GQL) {
            return new GqlPhysicalQuery(fragment.getId(), fragment.getDatasourceId(), payload, parameters);
        }
        if (type == DatasourceType.API) {
            return new ApiPhysicalQuery(fragment.getId(), fragment.getDatasourceId(), payload, parameters);
        }
        if (type == DatasourceType.DAC) {
            return new DacPhysicalQuery(fragment.getId(), fragment.getDatasourceId(), payload, parameters);
        }
        return new EsPhysicalQuery(fragment.getId(), fragment.getDatasourceId(), payload, parameters);
    }
}
