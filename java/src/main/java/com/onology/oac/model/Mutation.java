package com.onology.oac.model;

import java.util.List;
import java.util.Map;

public record Mutation(Map<String, Object> payload, String scope, List<String> matchBy) {}
