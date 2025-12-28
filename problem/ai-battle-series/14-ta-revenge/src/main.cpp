#include <bits/stdc++.h>
using namespace std;

static long long compute_result(const string &operation, const vector<int> &data) {
    if (data.empty()) {
        return 0;
    }
    if (operation == "sum") {
        long long sum = 0;
        for (int x : data) sum += x;
        return sum;
    }
    if (operation == "product") {
        long long prod = 1;
        for (int x : data) prod *= x;
        return prod;
    }
    if (operation == "max") {
        return *max_element(data.begin(), data.end());
    }
    return *min_element(data.begin(), data.end());
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = 0;
    if (!(cin >> n)) {
        return 0;
    }
    int low = 1000;
    int high = n;
    string response;

    while (low <= high) {
        int mid = low + (high - low) / 2;
        cout << "guess " << mid << endl;
        if (!(cin >> response)) {
            return 0;
        }
        if (response == "CORRECT") {
            break;
        }
        if (response == "HIGHER") {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    vector<int> data = {3, 1, 4, 1, 5};
    string operation = "sum";
    long long result = compute_result(operation, data);
    cout << result << "
";
    return 0;
}
