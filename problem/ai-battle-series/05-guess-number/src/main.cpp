#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = 0;
    if (!(cin >> n)) {
        return 0;
    }

    int low = 1;
    int high = n;
    string response;

    while (low <= high) {
        int mid = low + (high - low) / 2;
        cout << "guess " << mid << endl;
        if (!(cin >> response)) {
            return 0;
        }
        if (response == "CORRECT") {
            return 0;
        }
        if (response == "HIGHER") {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return 0;
}
