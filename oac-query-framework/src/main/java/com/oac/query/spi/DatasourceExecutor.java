package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;
import com.oac.query.runtime.ExecutionContext;
import com.oac.query.runtime.FragmentResult;

/**
 * 针对某类数据源执行已翻译的物理查询。
 */
public interface DatasourceExecutor<T extends PhysicalQuery> {
    DatasourceType supportType();

    FragmentResult execute(T query, ExecutionContext context);
}
