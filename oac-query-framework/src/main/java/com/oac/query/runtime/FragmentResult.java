package com.oac.query.runtime;

import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * 单个物理源查询分片的执行结果。
 */
public class FragmentResult {
    private final String fragmentId;
    private final boolean success;
    private final List<Map<String, Object>> rows;
    private final List<OqlError> errors;

    public FragmentResult(String fragmentId, boolean success, List<Map<String, Object>> rows) {
        this(fragmentId, success, rows, new ArrayList<OqlError>());
    }

    public FragmentResult(String fragmentId, boolean success, List<Map<String, Object>> rows, List<OqlError> errors) {
        this.fragmentId = fragmentId;
        this.success = success;
        this.rows = rows == null ? new ArrayList<Map<String, Object>>() : new ArrayList<Map<String, Object>>(rows);
        this.errors = errors == null ? new ArrayList<OqlError>() : new ArrayList<OqlError>(errors);
    }

    public static FragmentResult empty(String fragmentId) {
        return new FragmentResult(fragmentId, true, new ArrayList<Map<String, Object>>());
    }

    public static FragmentResult failed(String fragmentId, OqlError error) {
        List<OqlError> errors = new ArrayList<OqlError>();
        errors.add(error);
        return new FragmentResult(fragmentId, false, new ArrayList<Map<String, Object>>(), errors);
    }

    public String getFragmentId() {
        return fragmentId;
    }

    public boolean isSuccess() {
        return success;
    }

    public List<Map<String, Object>> getRows() {
        return Collections.unmodifiableList(rows);
    }

    public List<OqlError> getErrors() {
        return Collections.unmodifiableList(errors);
    }

    public boolean isEmpty() {
        return rows.isEmpty();
    }
}
