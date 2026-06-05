package com.oac.query.binding;

import com.oac.query.dsl.OqlQuery;
import com.oac.query.dsl.OqlQuery.ObjectDecl;
import com.oac.query.dsl.OqlQuery.RelationshipDecl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 本体对象、关系、数据源和能力信息的绑定视图。
 *
 * 物理规划通过该图判断查询应下推、在内存中合并，还是拆分为带依赖的 DAG 查询分片。
 */
public class BindingGraph {
    private final Map<String, ObjectBinding> objectBindings = new LinkedHashMap<String, ObjectBinding>();
    private final Map<String, RelationshipBinding> relationshipBindings = new LinkedHashMap<String, RelationshipBinding>();
    private boolean dependencyRequired;

    public void addObjectBinding(String alias, ObjectBinding binding) {
        objectBindings.put(alias, binding);
    }

    public void addRelationshipBinding(String alias, RelationshipBinding binding) {
        relationshipBindings.put(alias, binding);
    }

    public ObjectBinding objectBinding(String alias) {
        return objectBindings.get(alias);
    }

    public RelationshipBinding relationshipBinding(String alias) {
        return relationshipBindings.get(alias);
    }

    public Map<String, ObjectBinding> getObjectBindings() {
        return Collections.unmodifiableMap(objectBindings);
    }

    public Map<String, RelationshipBinding> getRelationshipBindings() {
        return Collections.unmodifiableMap(relationshipBindings);
    }

    public boolean isSingleDatasource() {
        return datasourceIds().size() <= 1;
    }

    public boolean isCrossDatasource() {
        return datasourceIds().size() > 1;
    }

    public boolean isSingleTable() {
        Set<String> tables = new LinkedHashSet<String>();
        for (ObjectBinding binding : objectBindings.values()) {
            for (FieldBinding field : binding.getFieldBindings().values()) {
                tables.add(field.getDatasourceId() + ":" + field.getPhysicalContainer());
            }
        }
        return tables.size() <= 1;
    }

    public boolean requiresJoin() {
        return objectBindings.size() > 1 || !relationshipBindings.isEmpty();
    }

    public boolean requiresMemoryMerge() {
        return isCrossDatasource() && !dependencyRequired;
    }

    public boolean canPushdownJoin() {
        return allCapabilitiesSupport("join");
    }

    public boolean canPushdownAggregation() {
        return allCapabilitiesSupport("aggregation");
    }

    public boolean canPushdownHaving() {
        return allCapabilitiesSupport("having");
    }

    public boolean hasNativeAssociation() {
        if (relationshipBindings.isEmpty()) {
            return false;
        }
        for (RelationshipBinding binding : relationshipBindings.values()) {
            if (!binding.getCapability().isNativeAssociation()) {
                return false;
            }
        }
        return true;
    }

    public boolean isDependencyRequired() {
        return dependencyRequired;
    }

    public void setDependencyRequired(boolean dependencyRequired) {
        this.dependencyRequired = dependencyRequired;
    }

    public Set<String> datasourceIds() {
        Set<String> ids = new LinkedHashSet<String>();
        for (ObjectBinding binding : objectBindings.values()) {
            for (FieldBinding field : binding.getFieldBindings().values()) {
                ids.add(field.getDatasourceId());
            }
        }
        for (RelationshipBinding binding : relationshipBindings.values()) {
            ids.add(binding.getDatasourceId());
        }
        return ids;
    }

    public DatasourceType primaryType() {
        for (ObjectBinding binding : objectBindings.values()) {
            for (FieldBinding field : binding.getFieldBindings().values()) {
                return field.getDatasourceType();
            }
        }
        for (RelationshipBinding binding : relationshipBindings.values()) {
            return binding.getDatasourceType();
        }
        return DatasourceType.SQL;
    }

    public DatasourceCapability primaryCapability() {
        for (ObjectBinding binding : objectBindings.values()) {
            for (FieldBinding field : binding.getFieldBindings().values()) {
                return field.getCapability();
            }
        }
        return DatasourceCapability.basicSql();
    }

    public List<FieldBinding> fieldBindingsForDatasource(String datasourceId) {
        List<FieldBinding> bindings = new ArrayList<FieldBinding>();
        for (ObjectBinding object : objectBindings.values()) {
            for (FieldBinding field : object.getFieldBindings().values()) {
                if (datasourceId.equals(field.getDatasourceId())) {
                    bindings.add(field);
                }
            }
        }
        return bindings;
    }

    private boolean allCapabilitiesSupport(String feature) {
        for (ObjectBinding binding : objectBindings.values()) {
            for (FieldBinding field : binding.getFieldBindings().values()) {
                DatasourceCapability capability = field.getCapability();
                if ("join".equals(feature) && !capability.isJoin()) {
                    return false;
                }
                if ("aggregation".equals(feature) && !capability.isAggregation()) {
                    return false;
                }
                if ("having".equals(feature) && !capability.isHaving()) {
                    return false;
                }
            }
        }
        return true;
    }

    public static BindingGraph forQuery(OqlQuery query, MockOntologyMetadata metadata) {
        BindingGraph graph = new BindingGraph();
        for (ObjectDecl object : query.getObjects()) {
            graph.addObjectBinding(object.getAlias(), metadata.objectBinding(object.getObjectType()));
            if (object.getFromSource() != null && !object.getFromSource().trim().isEmpty()) {
                graph.setDependencyRequired(true);
            }
        }
        for (RelationshipDecl relationship : query.getRelationships()) {
            graph.addRelationshipBinding(relationship.getAlias(), metadata.relationshipBinding(relationship.getRelationshipType()));
        }
        return graph;
    }

    /** SplitStrategySelector 使用的数据源能力标记。 */
    public static class DatasourceCapability {
        private final boolean join;
        private final boolean aggregation;
        private final boolean having;
        private final boolean nativeAssociation;

        public DatasourceCapability(boolean join, boolean aggregation, boolean having, boolean nativeAssociation) {
            this.join = join;
            this.aggregation = aggregation;
            this.having = having;
            this.nativeAssociation = nativeAssociation;
        }

        public static DatasourceCapability basicSql() {
            return new DatasourceCapability(true, true, true, false);
        }

        public static DatasourceCapability noJoin(DatasourceType type) {
            return new DatasourceCapability(false, type == DatasourceType.DAC || type == DatasourceType.ES, type == DatasourceType.DAC, false);
        }

        public static DatasourceCapability graph() {
            return new DatasourceCapability(false, false, false, true);
        }

        public boolean isJoin() {
            return join;
        }

        public boolean isAggregation() {
            return aggregation;
        }

        public boolean isHaving() {
            return having;
        }

        public boolean isNativeAssociation() {
            return nativeAssociation;
        }
    }

    /** 将一个本体字段映射到可信的物理数据源字段。 */
    public static class FieldBinding {
        private final String objectType;
        private final String logicalField;
        private final String datasourceId;
        private final DatasourceType datasourceType;
        private final String physicalContainer;
        private final String physicalField;
        private final DatasourceCapability capability;

        public FieldBinding(String objectType, String logicalField, String datasourceId, DatasourceType datasourceType,
                            String physicalContainer, String physicalField, DatasourceCapability capability) {
            this.objectType = objectType;
            this.logicalField = logicalField;
            this.datasourceId = datasourceId;
            this.datasourceType = datasourceType;
            this.physicalContainer = physicalContainer;
            this.physicalField = physicalField;
            this.capability = capability;
        }

        public String getObjectType() {
            return objectType;
        }

        public String getLogicalField() {
            return logicalField;
        }

        public String getDatasourceId() {
            return datasourceId;
        }

        public DatasourceType getDatasourceType() {
            return datasourceType;
        }

        public String getPhysicalContainer() {
            return physicalContainer;
        }

        public String getPhysicalField() {
            return physicalField;
        }

        public DatasourceCapability getCapability() {
            return capability;
        }
    }

    /** 一个本体对象类型下的全部字段绑定。 */
    public static class ObjectBinding {
        private final String objectType;
        private final Map<String, FieldBinding> fieldBindings = new LinkedHashMap<String, FieldBinding>();

        public ObjectBinding(String objectType) {
            this.objectType = objectType;
        }

        public ObjectBinding add(FieldBinding fieldBinding) {
            fieldBindings.put(fieldBinding.getLogicalField(), fieldBinding);
            return this;
        }

        public String getObjectType() {
            return objectType;
        }

        public Map<String, FieldBinding> getFieldBindings() {
            return Collections.unmodifiableMap(fieldBindings);
        }

        public FieldBinding field(String name) {
            return fieldBindings.get(name);
        }
    }

    /** 将一个本体关系类型映射到物理边、关系表或路径。 */
    public static class RelationshipBinding {
        private final String relationshipType;
        private final String datasourceId;
        private final DatasourceType datasourceType;
        private final String physicalName;
        private final DatasourceCapability capability;

        public RelationshipBinding(String relationshipType, String datasourceId, DatasourceType datasourceType,
                                   String physicalName, DatasourceCapability capability) {
            this.relationshipType = relationshipType;
            this.datasourceId = datasourceId;
            this.datasourceType = datasourceType;
            this.physicalName = physicalName;
            this.capability = capability;
        }

        public String getRelationshipType() {
            return relationshipType;
        }

        public String getDatasourceId() {
            return datasourceId;
        }

        public DatasourceType getDatasourceType() {
            return datasourceType;
        }

        public String getPhysicalName() {
            return physicalName;
        }

        public DatasourceCapability getCapability() {
            return capability;
        }
    }
}
