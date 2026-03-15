package com.onology.oac.execution;

import com.onology.oac.compiler.PhysicalNode;

import java.util.List;
import java.util.Map;

public interface SourceAdapter {
    List<Map<String, Object>> execute(PhysicalNode node);
}
