#include <iostream>
#include <iomanip>
using namespace std;

int main () {
    int n;
    cin >> n;

    // Output each number on a separate line with high precision
    for (int i = 0; i < n; i++) {
        double num;
        cin >> num;
        cout << fixed << setprecision (10) << num - 1 << endl;
    }

    return 0;
}
