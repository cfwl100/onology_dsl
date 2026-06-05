package com.oac.query.assembly;

/**
 * 通过 sum/count 合并局部 AVG，避免使用 avg(avg1, avg2) 这种错误算法。
 */
public class AvgAccumulator {
    private double sum;
    private long count;

    public void add(Number sumPart, Number countPart) {
        if (sumPart == null || countPart == null) {
            return;
        }
        this.sum += sumPart.doubleValue();
        this.count += countPart.longValue();
    }

    public double average() {
        if (count == 0) {
            return 0D;
        }
        return sum / count;
    }

    public double getSum() {
        return sum;
    }

    public long getCount() {
        return count;
    }
}
