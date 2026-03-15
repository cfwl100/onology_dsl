package com.onology.oac;

import com.onology.oac.model.OqlRequest;
import com.onology.oac.operation.OacService;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

public class OacServiceTestMain {
    public static void main(String[] args) {
        try (ConfigurableApplicationContext context = new SpringApplicationBuilder(Main.class)
                .web(WebApplicationType.NONE)
                .run()) {
            OacService service = context.getBean(OacService.class);
            OqlRequest sample = OqlRequest.sampleQuery();

            var validate = service.process("validate", sample);
            assert validate.success();

            var explain = service.process("explain", sample);
            assert explain.success();
            assert Boolean.TRUE.equals(explain.metadata().get("degraded"));

            var execute = service.process("execute", sample);
            assert execute.success();
        }

        System.out.println("Java OAC tests passed");
    }
}
