#include <bits/stdc++.h>
using namespace std;

static string reason_phrase(const string &reason) {
    if (reason == "生病") {
        return "生病就醫";
    }
    if (reason == "家庭") {
        return "家庭因素";
    }
    if (reason == "技術問題") {
        return "技術問題";
    }
    return "其他個人因素";
}

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
    while (!reason.empty() && (reason.back() == '\r' || reason.back() == '\n')) {
        reason.pop_back();
    }
    if (reason.empty()) {
        reason = "其他";
    }

    const string phrase = reason_phrase(reason);

    cout << "教授您好：\n\n";
    cout << "我是修課學生，想誠懇地請求將專題報告截止日期延後" << days << "天。";
    cout << "因為" << phrase << "影響進度，目前已完成約70%內容，剩餘部分主要是測試與文件整理。";
    cout << "若能獲得延期，我會在新期限前提交完整版本並願意補充相關證明。";
    cout << "對於造成的不便深感抱歉，感謝您的理解與指導。\n\n";
    cout << "學生 敬上\n";
    return 0;
}
