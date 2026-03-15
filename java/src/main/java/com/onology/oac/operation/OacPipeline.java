package com.onology.oac.operation;

import com.onology.oac.compiler.DialectTranslator;
import com.onology.oac.compiler.LogicalPlan;
import com.onology.oac.compiler.OntologyBinder;
import com.onology.oac.compiler.PhysicalPlan;
import com.onology.oac.execution.DagOrchestrator;
import com.onology.oac.model.OqlRequest;
import com.onology.oac.result.ResultAssembler;
import org.springframework.stereotype.Component;

@Component
public class OacPipeline {
    private final OntologyBinder binder;
    private final DialectTranslator translator;
    private final DagOrchestrator orchestrator;
    private final ResultAssembler assembler;

    public OacPipeline(OntologyBinder binder, DialectTranslator translator, DagOrchestrator orchestrator, ResultAssembler assembler) {
        this.binder = binder;
        this.translator = translator;
        this.orchestrator = orchestrator;
        this.assembler = assembler;
    }

    public CompiledPlan compile(OqlRequest request) {
        request.validate();
        LogicalPlan logical = binder.bind(request);
        PhysicalPlan physical = translator.toPhysical(logical);
        return new CompiledPlan(logical, physical);
    }

    public DagOrchestrator orchestrator() { return orchestrator; }
    public ResultAssembler assembler() { return assembler; }

    public record CompiledPlan(LogicalPlan logical, PhysicalPlan physical) {}
}
