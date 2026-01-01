#include <bits/stdc++.h>
using namespace std;

struct Entry {
    int priority;
    int order;
};

struct Item {
    string name;
    int priority;
    int order;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = 0;
    if (!(cin >> n)) {
        return 0;
    }
    if (n <= 0) {
        return 0;
    }

    unordered_map<string, Entry> best;
    best.reserve(static_cast<size_t>(n) * 2);

    for (int i = 0; i < n; i++) {
        string name;
        int priority = 0;
        cin >> name >> priority;
        auto it = best.find(name);
        if (it == best.end() || priority > it->second.priority) {
            best[name] = {priority, i};
        }
    }

    vector<Item> items;
    items.reserve(best.size());
    for (const auto &kv : best) {
        items.push_back({kv.first, kv.second.priority, kv.second.order});
    }

    sort(items.begin(), items.end(), [](const auto &a, const auto &b) {
        if (a.priority != b.priority) {
            return a.priority > b.priority;
        }
        if (a.name != b.name) {
            return a.name < b.name;
        }
        return a.order < b.order;
    });

    for (const auto &item : items) {
        cout << item.name << "\n";
    }
    return 0;
}
