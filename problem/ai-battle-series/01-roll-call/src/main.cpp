#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int n = 0;
    if (!(std::cin >> n)) {
        return 0;
    }

    std::unordered_map<std::string, int> best_priority;
    best_priority.reserve(static_cast<size_t>(n));

    for (int i = 0; i < n; i++) {
        std::string name;
        int priority = 0;
        if (!(std::cin >> name >> priority)) {
            break;
        }
        auto it = best_priority.find(name);
        if (it == best_priority.end() || priority > it->second) {
            best_priority[name] = priority;
        }
    }

    std::vector<std::pair<std::string, int>> entries;
    entries.reserve(best_priority.size());
    for (const auto &kv : best_priority) {
        entries.emplace_back(kv.first, kv.second);
    }

    std::sort(entries.begin(), entries.end(), [](const auto &a, const auto &b) {
        if (a.second != b.second) {
            return a.second > b.second;
        }
        return a.first < b.first;
    });

    for (const auto &item : entries) {
        std::cout << item.first << '\n';
    }

    return 0;
}
