package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;
import com.oac.query.plan.physical.PhysicalSourceQueryNode;
import com.oac.query.runtime.PlannerContext;

/**
 * 将物理源节点转换为具体数据源查询对象。
 */
public interface QueryTranslator<T extends PhysicalQuery> {
    DatasourceType supportType();

    boolean canTranslate(PhysicalSourceQueryNode fragment, PlannerContext context);

    T translate(PhysicalSourceQueryNode fragment, PlannerContext context);
}
