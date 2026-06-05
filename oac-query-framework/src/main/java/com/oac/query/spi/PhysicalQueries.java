package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * v1 支持的数据源类型对应的内置 PhysicalQuery 值对象。
 */
public final class PhysicalQueries {
    private PhysicalQueries() {
    }

    /** 具体物理查询类型共享的不可变基础实现。 */
    public abstract static class AbstractPhysicalQuery implements PhysicalQuery {
        private final String fragmentId;
        private final String datasourceId;
        private final DatasourceType datasourceType;
        private final String payload;
        private final Map<String, Object> parameters;

        protected AbstractPhysicalQuery(String fragmentId, String datasourceId, DatasourceType datasourceType,
                                        String payload, Map<String, Object> parameters) {
            this.fragmentId = fragmentId;
            this.datasourceId = datasourceId;
            this.datasourceType = datasourceType;
            this.payload = payload;
            this.parameters = parameters == null ? new LinkedHashMap<String, Object>() : new LinkedHashMap<String, Object>(parameters);
        }

        public String getFragmentId() {
            return fragmentId;
        }

        public String datasourceId() {
            return datasourceId;
        }

        public DatasourceType datasourceType() {
            return datasourceType;
        }

        public String payload() {
            return payload;
        }

        public Map<String, Object> parameters() {
            return Collections.unmodifiableMap(parameters);
        }
    }

    /** SQL 查询载荷，通常对应参数化 SQL。 */
    public static class SqlPhysicalQuery extends AbstractPhysicalQuery {
        public SqlPhysicalQuery(String fragmentId, String datasourceId, String payload, Map<String, Object> parameters) {
            super(fragmentId, datasourceId, DatasourceType.SQL, payload, parameters);
        }
    }

    /** 图查询载荷，例如 GQL/Nebula 风格的查询文本。 */
    public static class GqlPhysicalQuery extends AbstractPhysicalQuery {
        public GqlPhysicalQuery(String fragmentId, String datasourceId, String payload, Map<String, Object> parameters) {
            super(fragmentId, datasourceId, DatasourceType.GQL, payload, parameters);
        }
    }

    /** HTTP/API 数据源请求载荷。 */
    public static class ApiPhysicalQuery extends AbstractPhysicalQuery {
        public ApiPhysicalQuery(String fragmentId, String datasourceId, String payload, Map<String, Object> parameters) {
            super(fragmentId, datasourceId, DatasourceType.API, payload, parameters);
        }
    }

    /** DAC 指标或查询载荷。 */
    public static class DacPhysicalQuery extends AbstractPhysicalQuery {
        public DacPhysicalQuery(String fragmentId, String datasourceId, String payload, Map<String, Object> parameters) {
            super(fragmentId, datasourceId, DatasourceType.DAC, payload, parameters);
        }
    }

    /** Elasticsearch DSL 查询载荷。 */
    public static class EsPhysicalQuery extends AbstractPhysicalQuery {
        public EsPhysicalQuery(String fragmentId, String datasourceId, String payload, Map<String, Object> parameters) {
            super(fragmentId, datasourceId, DatasourceType.ES, payload, parameters);
        }
    }
}
