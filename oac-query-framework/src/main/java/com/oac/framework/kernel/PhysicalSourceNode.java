package com.oac.framework.kernel;

public interface PhysicalSourceNode {
    String nodeId();
    String datasourceKind();
    Object query();
}
