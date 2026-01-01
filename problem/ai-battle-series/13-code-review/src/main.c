#include <stdio.h>
#include <stdlib.h>
#include <math.h>

static int cmp_ll(const void *a, const void *b) {
    long long aa = *(const long long *)a;
    long long bb = *(const long long *)b;
    if (aa < bb) return -1;
    if (aa > bb) return 1;
    return 0;
}

int main(void) {
    int n = 0;
    int p = 0;
    if (scanf("%d %d", &n, &p) != 2) {
        return 0;
    }
    if (n <= 0) {
        return 0;
    }

    long long *nums = (long long *)malloc(sizeof(long long) * (size_t)n);
    if (!nums) {
        return 0;
    }

    long double sum = 0.0L;
    for (int i = 0; i < n; i++) {
        scanf("%lld", &nums[i]);
        sum += nums[i];
    }

    long double mean = sum / n;

    long long *sorted = (long long *)malloc(sizeof(long long) * (size_t)n);
    if (!sorted) {
        free(nums);
        return 0;
    }
    for (int i = 0; i < n; i++) {
        sorted[i] = nums[i];
    }
    qsort(sorted, n, sizeof(long long), cmp_ll);

    long long max_val = sorted[n - 1];
    long long min_val = sorted[0];
    long double median = 0.0L;
    if (n % 2 == 1) {
        median = sorted[n / 2];
    } else {
        median = (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0L;
    }

    long double variance = 0.0L;
    for (int i = 0; i < n; i++) {
        long double diff = nums[i] - mean;
        variance += diff * diff;
    }
    variance /= n;
    long double stddev = sqrtl(variance);

    long double position = p * (n + 1) / 100.0L;
    long double percentile = 0.0L;
    if (position <= 1.0L) {
        percentile = sorted[0];
    } else if (position >= n) {
        percentile = sorted[n - 1];
    } else {
        long long k = (long long)floorl(position);
        long double d = position - k;
        long double lower = sorted[k - 1];
        long double upper = sorted[k];
        percentile = lower + d * (upper - lower);
    }

    printf("Max: %lld\n", max_val);
    printf("Min: %lld\n", min_val);
    printf("Mean: %.2Lf\n", mean);
    printf("Median: %.2Lf\n", median);
    printf("StdDev: %.2Lf\n", stddev);
    printf("P%d: %.2Lf\n", p, percentile);

    free(nums);
    free(sorted);
    return 0;
}
