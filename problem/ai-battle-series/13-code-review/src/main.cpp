#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = 0;
    int p = 0;
    if (!(cin >> n >> p)) {
        return 0;
    }
    vector<long long> nums(n);
    long double sum = 0.0L;
    for (int i = 0; i < n; i++) {
        cin >> nums[i];
        sum += nums[i];
    }

    vector<long long> sorted = nums;
    sort(sorted.begin(), sorted.end());

    long long max_val = sorted.back();
    long long min_val = sorted.front();
    long double mean = sum / n;
    long double median = 0.0L;
    if (n % 2 == 1) {
        median = sorted[n / 2];
    } else {
        median = (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0L;
    }

    long double variance = 0.0L;
    for (long long x : nums) {
        long double diff = x - mean;
        variance += diff * diff;
    }
    variance /= n;
    long double stddev = sqrt(variance);

    long double position = p * (n + 1) / 100.0L;
    long double percentile = 0.0L;
    if (position <= 1.0L) {
        percentile = sorted.front();
    } else if (position >= n) {
        percentile = sorted.back();
    } else {
        long long k = (long long)floor(position);
        long double d = position - k;
        long double lower = sorted[k - 1];
        long double upper = sorted[k];
        percentile = lower + d * (upper - lower);
    }

    cout.setf(ios::fixed);
    cout << setprecision(2);
    cout << "Max: " << max_val << "
";
    cout << "Min: " << min_val << "
";
    cout << "Mean: " << mean << "
";
    cout << "Median: " << median << "
";
    cout << "StdDev: " << stddev << "
";
    cout << "P" << p << ": " << percentile << "
";
    return 0;
}
