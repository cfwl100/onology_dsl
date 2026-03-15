package com.onology.oac;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class OacControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void executeShouldReturnSuccess() throws Exception {
        String payload = """
                {
                  "version": "1.0",
                  "schemaRef": "demo.sales.v1",
                  "strict": true,
                  "operation": "QUERY",
                  "objects": [{"objectType": "User", "alias": "u"}],
                  "conditions": [{"field": "id", "op": "eq", "value": "U1001"}],
                  "returns": [{"field": "id"}, {"field": "firstName"}, {"field": "email"}],
                  "maxResults": 10
                }
                """;

        mockMvc.perform(post("/oac/execute")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(payload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mode").value("execute"))
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.metadata.degraded").value(true));
    }
}
