package com.oac.query.assembly;

import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * QueryFrameworkService 返回的统一响应对象。
 */
public class OntologyQueryResult {
    private boolean success;
    private List<Map<String, Object>> objects = new ArrayList<Map<String, Object>>();
    private List<Map<String, Object>> relationships = new ArrayList<Map<String, Object>>();
    private List<Map<String, Object>> metrics = new ArrayList<Map<String, Object>>();
    private List<String> warnings = new ArrayList<String>();
    private List<OqlError> errors = new ArrayList<OqlError>();
    private String traceId;

    public static OntologyQueryResult success(String traceId) {
        OntologyQueryResult result = new OntologyQueryResult();
        result.setSuccess(true);
        result.setTraceId(traceId);
        return result;
    }

    public static OntologyQueryResult failure(List<OqlError> errors, String traceId) {
        OntologyQueryResult result = new OntologyQueryResult();
        result.setSuccess(false);
        result.setTraceId(traceId);
        result.setErrors(errors);
        return result;
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public List<Map<String, Object>> getObjects() {
        return Collections.unmodifiableList(objects);
    }

    public void setObjects(List<Map<String, Object>> objects) {
        this.objects = objects == null ? new ArrayList<Map<String, Object>>() : new ArrayList<Map<String, Object>>(objects);
    }

    public List<Map<String, Object>> getRelationships() {
        return Collections.unmodifiableList(relationships);
    }

    public void setRelationships(List<Map<String, Object>> relationships) {
        this.relationships = relationships == null ? new ArrayList<Map<String, Object>>() : new ArrayList<Map<String, Object>>(relationships);
    }

    public List<Map<String, Object>> getMetrics() {
        return Collections.unmodifiableList(metrics);
    }

    public void setMetrics(List<Map<String, Object>> metrics) {
        this.metrics = metrics == null ? new ArrayList<Map<String, Object>>() : new ArrayList<Map<String, Object>>(metrics);
    }

    public List<String> getWarnings() {
        return Collections.unmodifiableList(warnings);
    }

    public void setWarnings(List<String> warnings) {
        this.warnings = warnings == null ? new ArrayList<String>() : new ArrayList<String>(warnings);
    }

    public List<OqlError> getErrors() {
        return Collections.unmodifiableList(errors);
    }

    public void setErrors(List<OqlError> errors) {
        this.errors = errors == null ? new ArrayList<OqlError>() : new ArrayList<OqlError>(errors);
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }
}
