package com.onology.oac.execution;

import com.onology.oac.compiler.PhysicalNode;
import com.onology.oac.compiler.PhysicalPlan;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

@Component
public class DagOrchestrator {
    private final AdapterFactory adapterFactory;

    public DagOrchestrator(AdapterFactory adapterFactory) {
        this.adapterFactory = adapterFactory;
    }

    public Map<String, Object> run(PhysicalPlan plan) {
        Map<String, PhysicalNode> pending = new HashMap<>();
        for (PhysicalNode node : plan.nodes()) {
            pending.put(node.nodeId(), node);
        }

        Map<String, Object> output = new HashMap<>();
        Set<String> completed = new HashSet<>();

        while (!pending.isEmpty()) {
            boolean progress = false;
            for (var entry : new HashMap<>(pending).entrySet()) {
                PhysicalNode node = entry.getValue();
                if (completed.containsAll(node.dependencies())) {
                    output.put(node.nodeId(), adapterFactory.create(node.source()).execute(node));
                    completed.add(node.nodeId());
                    pending.remove(node.nodeId());
                    progress = true;
                }
            }
            if (!progress) {
                throw new IllegalStateException("physical DAG has unresolved dependencies");
            }
        }
        return output;
    }
}
