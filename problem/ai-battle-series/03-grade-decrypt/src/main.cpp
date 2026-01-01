#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int k = 0;
    if (!(cin >> k)) {
        return 0;
    }
    if (k <= 0) {
        cout << 0 << "\n";
        return 0;
    }

    vector<string> subjects(k);
    unordered_set<string> subject_set;
    subject_set.reserve(k * 2);
    for (int i = 0; i < k; i++) {
        cin >> subjects[i];
        subject_set.insert(subjects[i]);
    }

    unordered_map<string, unordered_set<string>> need_help;
    need_help.reserve(k * 2);
    for (const auto &subj : subjects) {
        need_help.emplace(subj, unordered_set<string>());
    }

    ifstream fin("grades.csv");
    if (!fin) {
        cout << 0 << "\n";
        return 0;
    }

    string line;
    getline(fin, line);
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        stringstream ss(line);
        string student;
        string subject;
        string score;
        string status;
        getline(ss, student, ',');
        getline(ss, subject, ',');
        getline(ss, score, ',');
        getline(ss, status, ',');
        if (student.empty() || subject.empty() || status.empty()) {
            continue;
        }
        if (status == "NEED_HELP" && subject_set.count(subject)) {
            need_help[subject].insert(student);
        }
    }

    vector<string> result;
    const auto &first_set = need_help[subjects[0]];
    for (const auto &student : first_set) {
        bool ok = true;
        for (int i = 1; i < k; i++) {
            if (!need_help[subjects[i]].count(student)) {
                ok = false;
                break;
            }
        }
        if (ok) {
            result.push_back(student);
        }
    }

    sort(result.begin(), result.end());
    cout << result.size() << "\n";
    for (const auto &student : result) {
        cout << student << "\n";
    }
    return 0;
}
