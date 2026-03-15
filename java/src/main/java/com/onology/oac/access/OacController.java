package com.onology.oac.access;

import com.onology.oac.model.OacResponse;
import com.onology.oac.model.OqlRequest;
import com.onology.oac.operation.OacService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/oac")
public class OacController {
    private final OacService oacService;

    public OacController(OacService oacService) {
        this.oacService = oacService;
    }

    @PostMapping("/{mode}")
    public OacResponse process(@PathVariable String mode, @RequestBody OqlRequest request) {
        return oacService.process(mode, request);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String, Object> badRequest(IllegalArgumentException ex) {
        return Map.of("code", "OAC_BAD_REQUEST", "message", ex.getMessage());
    }
}
