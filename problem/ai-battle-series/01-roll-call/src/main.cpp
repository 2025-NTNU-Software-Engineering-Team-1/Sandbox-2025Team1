#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = 0;
    if (!(cin >> n)) {
        return 0;
    }

    unordered_map<string, int> best;
    best.reserve(static_cast<size_t>(n) * 2);

    for (int i = 0; i < n; i++) {
        string name;
        int priority = 0;
        cin >> name >> priority;
        auto it = best.find(name);
        if (it == best.end() || priority > it->second) {
            best[name] = priority;
        }
    }

    vector<pair<string, int>> items;
    items.reserve(best.size());
    for (const auto &kv : best) {
        items.push_back(kv);
    }

    sort(items.begin(), items.end(), [](const auto &a, const auto &b) {
        if (a.second != b.second) {
            return a.second > b.second;
        }
        return a.first < b.first;
    });

    for (const auto &item : items) {
        cout << item.first << "
";
    }
    return 0;
}
