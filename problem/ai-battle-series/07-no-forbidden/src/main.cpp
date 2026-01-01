#include <iostream>
#include <vector>

using namespace std;

struct Item {
    int value;
    int digit_sum;
};

static int calc_digit_sum(int v) {
    int n = v < 0 ? -v : v;
    int sum = 0;
    if (n == 0) {
        return 0;
    }
    while (n > 0) {
        sum += n % 10;
        n /= 10;
    }
    return sum;
}

static bool less_item(const Item &a, const Item &b) {
    if (a.digit_sum != b.digit_sum) {
        return a.digit_sum < b.digit_sum;
    }
    return a.value < b.value;
}

static void merge_step(vector<Item> &arr, vector<Item> &tmp, int left, int mid, int right) {
    int i = left;
    int j = mid;
    int k = left;
    while (i < mid && j < right) {
        if (less_item(arr[i], arr[j])) {
            tmp[k++] = arr[i++];
        } else {
            tmp[k++] = arr[j++];
        }
    }
    while (i < mid) {
        tmp[k++] = arr[i++];
    }
    while (j < right) {
        tmp[k++] = arr[j++];
    }
    for (i = left; i < right; i++) {
        arr[i] = tmp[i];
    }
}

static void merge_order(vector<Item> &arr, vector<Item> &tmp, int left, int right) {
    if (right - left <= 1) {
        return;
    }
    int mid = left + (right - left) / 2;
    merge_order(arr, tmp, left, mid);
    merge_order(arr, tmp, mid, right);
    merge_step(arr, tmp, left, mid, right);
}

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

    vector<Item> arr(n);
    for (int i = 0; i < n; i++) {
        int v = 0;
        cin >> v;
        arr[i].value = v;
        arr[i].digit_sum = calc_digit_sum(v);
    }

    vector<Item> tmp(n);
    merge_order(arr, tmp, 0, n);

    for (int i = 0; i < n; i++) {
        if (i) {
            cout << ' ';
        }
        cout << arr[i].value;
    }
    cout << ' ';
    return 0;
}
