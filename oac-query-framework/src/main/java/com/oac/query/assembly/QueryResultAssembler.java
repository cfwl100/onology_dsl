package com.oac.query.assembly;

import com.oac.query.dsl.OqlQuery;
import com.oac.query.runtime.FragmentResult;
import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.List;

/**
 * 根据查询类型选择对象、关系或指标结果的装配方式。
 */
public class QueryResultAssembler {
    private final ObjectAssembler objectAssembler;
    private final RelationAssembler relationAssembler;
    private final MetricAssembler metricAssembler;

    public QueryResultAssembler() {
        this(new ObjectAssembler(), new RelationAssembler(), new MetricAssembler());
    }

    public QueryResultAssembler(ObjectAssembler objectAssembler, RelationAssembler relationAssembler, MetricAssembler metricAssembler) {
        this.objectAssembler = objectAssembler;
        this.relationAssembler = relationAssembler;
        this.metricAssembler = metricAssembler;
    }

    public OntologyQueryResult assemble(OqlQuery query, List<FragmentResult> fragmentResults, String traceId) {
        List<OqlError> errors = collectErrors(fragmentResults);
        if (!errors.isEmpty()) {
            return OntologyQueryResult.failure(errors, traceId);
        }
        OntologyQueryResult result = OntologyQueryResult.success(traceId);
        if (query.getOperation() == OqlQuery.OperationType.AGGREGATE) {
            result.setMetrics(metricAssembler.assemble(fragmentResults));
        } else if (query.getOperation() == OqlQuery.OperationType.ASSOCIATION_QUERY) {
            result.setObjects(objectAssembler.assemble(fragmentResults));
            result.setRelationships(relationAssembler.assemble(fragmentResults));
        } else {
            result.setObjects(objectAssembler.assemble(fragmentResults));
        }
        return result;
    }

    private List<OqlError> collectErrors(List<FragmentResult> fragmentResults) {
        List<OqlError> errors = new ArrayList<OqlError>();
        for (FragmentResult fragmentResult : fragmentResults) {
            if (!fragmentResult.isSuccess()) {
                errors.addAll(fragmentResult.getErrors());
            }
        }
        return errors;
    }
}
