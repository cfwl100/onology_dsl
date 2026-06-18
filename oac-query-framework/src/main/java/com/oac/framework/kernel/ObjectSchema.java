package com.oac.framework.kernel;

import java.util.List;

public interface ObjectSchema {
    String objectType();
    List<ObjectField> fields();
}
