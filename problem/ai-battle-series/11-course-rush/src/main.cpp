#include <bits/stdc++.h>
using namespace std;

struct Course {
    string name;
    string professor;
    string title;
    int capacity;
    int enrolled;
    string dept;
};

struct Result {
    const Course *course;
    double popularity;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string dept;
    int threshold = 0;
    if (!(cin >> dept)) {
        return 0;
    }
    if (!(cin >> threshold)) {
        return 0;
    }

    vector<Course> courses = {
        {"進階機器學習", "陳教授", "教授", 30, 28, "CS"},
        {"資料結構", "王教授", "副教授", 50, 45, "CS"},
        {"計算機組織", "李教授", "助理教授", 40, 12, "CS"},
        {"微積分", "張教授", "教授", 60, 50, "MATH"},
    };

    vector<Result> results;
    for (const auto &course : courses) {
        if (course.dept != dept) {
            continue;
        }
        double popularity = course.enrolled * 100.0 / course.capacity;
        if (popularity + 1e-9 < threshold) {
            continue;
        }
        results.push_back({&course, popularity});
    }

    if (results.empty()) {
        cout << "No matching courses
";
        return 0;
    }

    sort(results.begin(), results.end(), [](const Result &a, const Result &b) {
        if (a.popularity != b.popularity) {
            return a.popularity > b.popularity;
        }
        return a.course->name < b.course->name;
    });

    cout.setf(ios::fixed);
    cout << setprecision(1);
    for (const auto &r : results) {
        const auto *c = r.course;
        cout << c->name << " by " << c->professor << " (" << c->title << ") - "
             << r.popularity << "% (" << c->enrolled << "/" << c->capacity << ")
";
    }
    return 0;
}
