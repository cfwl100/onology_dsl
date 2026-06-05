package com.oac.query.plan.physical;

import com.oac.query.binding.BindingGraph;
import com.oac.query.binding.DatasourceType;

/**
 * 物理查询阶段使用的字段绑定快照。
 *
 * BindingGraph.FieldBinding 只描述“本体字段 -> 物理字段”，这里额外保存对象别名，
 * 让 SQL/GQL/API 等翻译器可以区分 o.id 和 i.id 这类同名字段。
 */
public final class PhysicalFieldBinding {
    private final String objectAlias;
    private final BindingGraph.FieldBinding fieldBinding;

    public PhysicalFieldBinding(String objectAlias, BindingGraph.FieldBinding fieldBinding) {
        if (fieldBinding == null) {
            throw new IllegalArgumentException("fieldBinding must not be null");
        }
        this.objectAlias = objectAlias;
        this.fieldBinding = fieldBinding;
    }

    public String getObjectAlias() {
        return objectAlias;
    }

    public BindingGraph.FieldBinding getFieldBinding() {
        return fieldBinding;
    }

    public String getObjectType() {
        return fieldBinding.getObjectType();
    }

    public String getLogicalField() {
        return fieldBinding.getLogicalField();
    }

    public String getQualifiedLogicalField() {
        return objectAlias + "." + fieldBinding.getLogicalField();
    }

    public String getDatasourceId() {
        return fieldBinding.getDatasourceId();
    }

    public DatasourceType getDatasourceType() {
        return fieldBinding.getDatasourceType();
    }

    public String getPhysicalContainer() {
        return fieldBinding.getPhysicalContainer();
    }

    public String getPhysicalField() {
        return fieldBinding.getPhysicalField();
    }
}
