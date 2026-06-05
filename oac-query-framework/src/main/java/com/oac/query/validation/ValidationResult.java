package com.oac.query.validation;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 累积 OQL 校验错误，而不是遇到第一个问题就抛异常。
 */
public class ValidationResult {
    private final List<OqlError> errors = new ArrayList<OqlError>();

    public static ValidationResult ok() {
        return new ValidationResult();
    }

    public boolean isSuccess() {
        return errors.isEmpty();
    }

    public void add(OqlError error) {
        if (error != null) {
            errors.add(error);
        }
    }

    public void add(String code, String message, String path) {
        add(OqlError.of(code, message, path));
    }

    public List<OqlError> getErrors() {
        return Collections.unmodifiableList(errors);
    }
}
