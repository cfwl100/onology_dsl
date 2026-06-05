package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;

import java.util.Map;

/**
 * 已翻译物理查询载荷的统一抽象，与具体数据源实现解耦。
 */
public interface PhysicalQuery {
    String getFragmentId();

    String datasourceId();

    DatasourceType datasourceType();

    String payload();

    Map<String, Object> parameters();
}
