package com.oac.query.validation;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * 单个受治理 OQL 函数的注册元数据。
 */
public class FunctionDescriptor {
    private final String namespace;
    private final String name;
    private final int minArgs;
    private final int maxArgs;
    private final Set<String> allowedIn;
    private final boolean fallbackAllowed;

    public FunctionDescriptor(String namespace, String name, int minArgs, int maxArgs, Set<String> allowedIn, boolean fallbackAllowed) {
        this.namespace = namespace;
        this.name = name;
        this.minArgs = minArgs;
        this.maxArgs = maxArgs;
        this.allowedIn = new LinkedHashSet<String>(allowedIn);
        this.fallbackAllowed = fallbackAllowed;
    }

    public String getNamespace() {
        return namespace;
    }

    public String getName() {
        return name;
    }

    public int getMinArgs() {
        return minArgs;
    }

    public int getMaxArgs() {
        return maxArgs;
    }

    public Set<String> getAllowedIn() {
        return Collections.unmodifiableSet(allowedIn);
    }

    public boolean isFallbackAllowed() {
        return fallbackAllowed;
    }

    public boolean allows(String location) {
        return allowedIn.contains(location);
    }
}
