package com.onology.oac.compiler;

import java.util.List;

public record PhysicalPlan(List<PhysicalNode> nodes, boolean degraded, List<String> hints) {}
