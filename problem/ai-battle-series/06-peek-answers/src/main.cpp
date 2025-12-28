#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<pair<int, int>> data = {
        {5, 70},
        {8, 75},
        {1, 80},
        {6, 80},
        {2, 85},
        {3, 90},
    };

    sort(data.begin(), data.end(), [](const auto &a, const auto &b) {
        if (a.second != b.second) {
            return a.second < b.second;
        }
        return a.first < b.first;
    });

    cout << data.size() << "
";
    for (const auto &item : data) {
        cout << item.first << "
";
    }
    return 0;
}
