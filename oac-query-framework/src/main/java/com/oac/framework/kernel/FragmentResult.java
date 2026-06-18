package com.oac.framework.kernel;

public interface FragmentResult {
    String fragmentId();
    boolean isSuccess();
    Object data();
}
