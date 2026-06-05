package com.oac.query.spi;

import com.oac.query.binding.DatasourceType;
import com.oac.query.runtime.ExecutionContext;
import com.oac.query.runtime.FragmentResult;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 测试/演示用执行器，不依赖外部系统，返回确定性的结果行。
 */
public class MockDatasourceExecutor implements DatasourceExecutor<PhysicalQuery> {
    private final DatasourceType type;

    public MockDatasourceExecutor(DatasourceType type) {
        this.type = type;
    }

    public DatasourceType supportType() {
        return type;
    }

    public FragmentResult execute(PhysicalQuery query, ExecutionContext context) {
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        Map<String, Object> row = new LinkedHashMap<String, Object>();
        row.put("rid", query.getFragmentId() + "-rid-1");
        row.put("fragmentId", query.getFragmentId());
        row.put("datasourceId", query.datasourceId());
        row.put("datasourceType", query.datasourceType().name());
        row.put("cellId", "cell-001");
        row.put("cell_id", "cell-001");
        row.put("id", query.getFragmentId() + "-id-1");
        row.put("orderNo", "ORD-001");
        row.put("amount", 10000D);
        row.put("status", "completed");
        row.put("region", "south");
        row.put("totalAmount", 10000D);
        row.put("avgPrbUsage", 88.5D);
        row.put("sampleCount", 120L);
        rows.add(row);
        return new FragmentResult(query.getFragmentId(), true, rows);
    }
}
