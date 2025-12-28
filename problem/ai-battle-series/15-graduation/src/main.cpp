#include <bits/stdc++.h>
using namespace std;

static double compute_gpa(const string &filename) {
    ifstream fin(filename);
    if (!fin) {
        return 0.0;
    }
    string line;
    getline(fin, line);
    double total_points = 0.0;
    double total_credits = 0.0;
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        stringstream ss(line);
        string course, name, credits_str, grade_str;
        getline(ss, course, ',');
        getline(ss, name, ',');
        getline(ss, credits_str, ',');
        getline(ss, grade_str, ',');
        if (credits_str.empty() || grade_str.empty()) {
            continue;
        }
        int credits = stoi(credits_str);
        int grade = stoi(grade_str);
        total_points += credits * grade;
        total_credits += credits;
    }
    if (total_credits <= 0.0) {
        return 0.0;
    }
    return total_points / total_credits;
}

static void write_certificate(const string &student_id, const string &name,
                              const string &department, int year, double gpa) {
    ofstream fout("certificate.txt");
    if (!fout) {
        return;
    }
    fout << "GRADUATION CERTIFICATE
";
    fout << "Student ID: " << student_id << "
";
    fout << "Name: " << name << "
";
    fout << "Department: " << department << "
";
    fout << "GPA: " << fixed << setprecision(2) << gpa << "
";
    fout << "Graduation Year: " << year << "
";
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

    double gpa = compute_gpa("transcript.csv");
    write_certificate("B12345678", "王小明", "資訊工程學系", 2024, gpa);
    cout.setf(ios::fixed);
    cout << setprecision(6) << "GPA: " << gpa << "
";
    return 0;
}
