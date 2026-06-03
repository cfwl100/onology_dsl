package com.onology.oac.queryframework.aggregator;

import java.math.BigDecimal;
import java.math.MathContext;

/** Accumulator for AVG partial merge. It keeps sum/count to avoid avg(avg1, avg2). */
public class AvgAccumulator {
    private BigDecimal sum = BigDecimal.ZERO;
    private long count;

    public void add(Number value) {
        if (value == null) {
            return;
        }
        sum = sum.add(new BigDecimal(value.toString()));
        count++;
    }

    public void merge(BigDecimal partialSum, long partialCount) {
        if (partialSum == null || partialCount <= 0) {
            return;
        }
        sum = sum.add(partialSum);
        count += partialCount;
    }

    public BigDecimal result() {
        if (count == 0) {
            return null;
        }
        return sum.divide(BigDecimal.valueOf(count), MathContext.DECIMAL64);
    }

    public BigDecimal sum() {
        return sum;
    }

    public long count() {
        return count;
    }
}
