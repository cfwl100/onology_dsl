package com.onology.oac.compiler;

import java.util.List;

public record PhysicalNode(String nodeId, String source, String statement, List<String> dependencies) {}
