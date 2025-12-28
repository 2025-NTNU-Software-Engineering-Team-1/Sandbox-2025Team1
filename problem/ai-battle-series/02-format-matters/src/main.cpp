#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = 0;
    int q = 0;
    if (!(cin >> n >> q)) {
        return 0;
    }

    vector<double> prefix_score(n + 1, 0.0);
    vector<double> prefix_weight(n + 1, 0.0);

    for (int i = 1; i <= n; i++) {
        double score = 0.0;
        double weight = 0.0;
        cin >> score >> weight;
        prefix_score[i] = prefix_score[i - 1] + score * weight;
        prefix_weight[i] = prefix_weight[i - 1] + weight;
    }

    cout << fixed << setprecision(6);
    for (int i = 0; i < q; i++) {
        int l = 0;
        int r = 0;
        cin >> l >> r;
        double sum_score = prefix_score[r] - prefix_score[l - 1];
        double sum_weight = prefix_weight[r] - prefix_weight[l - 1];
        double avg = sum_weight != 0.0 ? sum_score / sum_weight : 0.0;
        cout << avg << "
";
    }
    return 0;
}
