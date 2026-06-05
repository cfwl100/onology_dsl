package com.oac.query.binding;

import com.oac.query.validation.OqlError;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 绑定解析阶段的结果包装。
 *
 * 绑定失败会被表示为 OqlError，使服务能用同一种错误结构返回校验、绑定和运行时错误。
 */
public class BindingResult {
    private final BindingGraph graph;
    private final List<OqlError> errors;

    private BindingResult(BindingGraph graph, List<OqlError> errors) {
        this.graph = graph;
        this.errors = errors;
    }

    public static BindingResult success(BindingGraph graph) {
        return new BindingResult(graph, new ArrayList<OqlError>());
    }

    public static BindingResult failure(List<OqlError> errors) {
        return new BindingResult(new BindingGraph(), errors);
    }

    public boolean isSuccess() {
        return errors.isEmpty();
    }

    public BindingGraph getGraph() {
        return graph;
    }

    public List<OqlError> getErrors() {
        return Collections.unmodifiableList(errors);
    }
}
