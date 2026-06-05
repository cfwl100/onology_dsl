package com.oac.query.validation;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 校验、绑定、规划或执行阶段返回的结构化错误。
 */
public class OqlError {
    private String code;
    private String message;
    private String path;
    private Map<String, Object> details = new LinkedHashMap<String, Object>();
    private String operation;
    private String alias;
    private String objectType;
    private String field;
    private String datasourceId;
    private String fragmentId;
    private String translatorName;
    private String executorName;

    public OqlError() {
    }

    public OqlError(String code, String message, String path) {
        this.code = code;
        this.message = message;
        this.path = path;
    }

    public static OqlError of(String code, String message, String path) {
        return new OqlError(code, message, path);
    }

    public OqlError detail(String key, Object value) {
        this.details.put(key, value);
        return this;
    }

    public OqlError operation(String operation) {
        this.operation = operation;
        return this;
    }

    public OqlError alias(String alias) {
        this.alias = alias;
        return this;
    }

    public OqlError objectType(String objectType) {
        this.objectType = objectType;
        return this;
    }

    public OqlError field(String field) {
        this.field = field;
        return this;
    }

    public OqlError datasourceId(String datasourceId) {
        this.datasourceId = datasourceId;
        return this;
    }

    public OqlError fragmentId(String fragmentId) {
        this.fragmentId = fragmentId;
        return this;
    }

    public OqlError translatorName(String translatorName) {
        this.translatorName = translatorName;
        return this;
    }

    public OqlError executorName(String executorName) {
        this.executorName = executorName;
        return this;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    public void setDetails(Map<String, Object> details) {
        this.details = details == null ? new LinkedHashMap<String, Object>() : details;
    }

    public String getOperation() {
        return operation;
    }

    public void setOperation(String operation) {
        this.operation = operation;
    }

    public String getAlias() {
        return alias;
    }

    public void setAlias(String alias) {
        this.alias = alias;
    }

    public String getObjectType() {
        return objectType;
    }

    public void setObjectType(String objectType) {
        this.objectType = objectType;
    }

    public String getField() {
        return field;
    }

    public void setField(String field) {
        this.field = field;
    }

    public String getDatasourceId() {
        return datasourceId;
    }

    public void setDatasourceId(String datasourceId) {
        this.datasourceId = datasourceId;
    }

    public String getFragmentId() {
        return fragmentId;
    }

    public void setFragmentId(String fragmentId) {
        this.fragmentId = fragmentId;
    }

    public String getTranslatorName() {
        return translatorName;
    }

    public void setTranslatorName(String translatorName) {
        this.translatorName = translatorName;
    }

    public String getExecutorName() {
        return executorName;
    }

    public void setExecutorName(String executorName) {
        this.executorName = executorName;
    }
}
