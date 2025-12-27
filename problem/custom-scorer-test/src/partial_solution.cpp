#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    // 故意只輸出前 3 個數字
    // 這會導致 Task 1 (N≤3) AC，但 Task 2、3 (N>3) WA
    for (int i = 0; i < min(n, 3); i++) {
        int num;
        cin >> num;
        cout << num << endl;
    }
    
    // 剩餘數字不處理（會導致輸出數量不足）
    
    return 0;
}
