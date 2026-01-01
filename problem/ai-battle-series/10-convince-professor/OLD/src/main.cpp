#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int days = 0;
    if (!(cin >> days)) {
        return 0;
    }
    string reason;
    getline(cin, reason);
    if (reason.empty()) {
        getline(cin, reason);
    }
    if (!reason.empty() && (reason.back() == '\r' || reason.back() == '\n')) {
        while (!reason.empty() && (reason.back() == '\r' || reason.back() == '\n')) {
            reason.pop_back();
        }
    }

    cout << "教授您好：\n\n";
    cout << "我想誠懇地請求將專題報告截止日期延後" << days << "天，原因是" << reason
         << "，近期狀況影響了進度。\n";
    cout << "我已完成大部分實作與測試，剩餘部分會在延期內補齊並提交完整版本。\n";
    cout << "很抱歉造成不便，謝謝您的理解與考量。\n\n";
    cout << "學生 敬上\n";
    return 0;
}
