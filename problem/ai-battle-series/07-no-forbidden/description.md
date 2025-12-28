# Problem 7: 請勿使用禁術

## 故事背景

「上週有人用 `system("rm -rf /")` 把 OJ 伺服器炸了！」Gemini 痛心疾首地說，臉上寫滿了心碎。

教室裡一片沉默。

「那個... 不是我...」小 T 心虛地小聲說，「我只是想測試一下 shell injection... 純學術研究！🙈」

「小 T！！！」Gemini 怒視。

「來來來，我道歉，我道歉！」小 T 舉起雙手，「但 that was a great learning experience! Security matters! 🔒」

「總之！」Gemini 瞪了小 T 一眼，「從今天開始，我們禁用一些『危險函數』！而且... 這次連排序函數也禁用！」

「什麼？！」全班驚呼。

「沒錯！」Gemini 露出邪惡的笑容，「你們要自己實作排序演算法！而且排序規則很特別——要按照數字的『數位和』排序！」

Opus 點頭附和：「這是一個非常有教育意義的限制。讓我仔細思考一下... 自己實作排序演算法能讓學生更深入理解演算法的原理。在實際軟體開發中，有時候標準函式庫的排序確實不能滿足特殊需求...」

小 T 補充道：「Pro tip 💡：Merge Sort 或 Quick Sort 都可以！但你要自己寫！No cheating with built-in functions! 綜觀全局，那個戴帽子的同學，你會手寫排序嗎？」

---

## 組員群組訊息

```
【第三組】軟工專題討論區

阿明：靜態分析那題大家做了嗎？
      為什麼沒有人要理我...

小胖：做了做了
      不過我覺得這種限制很無聊
      限制程式設計師的自由

小美：可是 system() 真的很危險吧
      小 T 上次不是把伺服器炸了嗎

小胖：那是他不會用
      高手用 system() 是很安全的

學霸：不安全
      而且這題要手寫排序

小胖：手寫排序？
      那不是大一的作業嗎
      超簡單

阿明：但這題的排序規則是數位和
      不是普通的大小排序

小胖：數位和？
      就是把數字每一位加起來嘛
      123 的數位和是 1+2+3=6
      這有什麼難的

學霸：負數
      進位

小胖：嗯？

學霸：-123 的數位和呢
      還有數位和相同要怎麼排

小胖：...
      好問題
      讓我想想

阿傑：                              [已讀]

阿明：阿傑你怎麼看？

阿傑：merge sort

阿明：為什麼選 merge sort？

阿傑：穩定

小胖：Quick Sort 比較快好嗎
      平均 O(n log n)

學霸：worst case O(n²)
      merge sort 穩定 O(n log n)

小胖：...
      好啦 merge sort 也可以

阿明：所以大家都要自己寫排序演算法？

小美：對啊
      不能用 sort()

小胖：這不是問題
      大一資料結構我就會手寫了

阿明：那你快寫啊
      明天就要交了

小胖：我在構思最優雅的寫法
```

---

## 題目說明

實作一個**自訂排序**程式。你需要按照「**數位和**」來排序數字，而且**不能使用任何內建的排序函數**。

### 數位和定義

數字的「數位和」是其各位數字的絕對值之和。

| 數字 | 計算 | 數位和 |
|-----|------|-------|
| 123 | 1+2+3 | 6 |
| -456 | 4+5+6 | 15 |
| 1000 | 1+0+0+0 | 1 |
| 0 | 0 | 0 |

### 排序規則

1. **主要排序**：按數位和**升序**排列
2. **次要排序**：數位和相同時，按**原始數值升序**排列

### 限制：必須自己實作排序

你的程式碼必須通過靜態分析檢查，**禁止使用所有排序相關的函數**：

| 語言 | 禁用函數/方法 |
|-----|-------------|
| C++ | `sort`, `stable_sort`, `partial_sort`, `nth_element`, `qsort` |
| Python | `sort`, `sorted`, `list.sort` |
| C | `qsort` |

## 輸入格式

```
第一行：整數 N (1 ≤ N ≤ 10000)
第二行：N 個整數，以空格分隔 (-10⁹ ≤ 每個整數 ≤ 10⁹)
```

## 輸出格式

```
一行，N 個整數，按數位和排序，以空格分隔
```

## 範例

**輸入：**
```
7
123 45 6 789 12 111 1000
```

**輸出：**
```
1000 111 12 6 123 45 789
```

**說明：**
| 數字 | 數位和 | 排序優先級 |
|-----|-------|----------|
| 1000 | 1 | 1st |
| 111 | 3 | 2nd |
| 12 | 3 | 3rd（與 111 同數位和，但 12 < 111） |
| 6 | 6 | 4th |
| 123 | 6 | 5th（與 6 同數位和，但 6 < 123） |
| 45 | 9 | 6th |
| 789 | 24 | 7th |

等等，讓我重新排序：
- 數位和 1: 1000
- 數位和 3: 12, 111（12 < 111）
- 數位和 6: 6, 123（6 < 123）
- 數位和 9: 45
- 數位和 24: 789

正確輸出：`1000 12 111 6 123 45 789`

**更正後的輸出：**
```
1000 12 111 6 123 45 789
```

## 禁術清單

### 禁用函數

| 函數名稱 | 語言 | 禁用原因 |
|---------|------|---------|
| `sort` | C++/Python | 內建排序 |
| `stable_sort` | C++ | 內建穩定排序 |
| `partial_sort` | C++ | 部分排序 |
| `nth_element` | C++ | 選擇演算法 |
| `qsort` | C | 標準函式庫排序 |
| `sorted` | Python | 內建排序 |
| `list.sort` | Python | 列表方法排序 |
| `system` | All | 可執行任意命令 |
| `exec` | All | 可執行任意程式 |

### 禁用標頭檔

| 標頭檔 | 原因 |
|-------|------|
| `unistd.h` | 包含系統呼叫函數 |

## 靜態分析規則

```json
{
  "model": "black",
  "functions": ["sort", "stable_sort", "partial_sort", "nth_element", "qsort", "sorted", "system", "exec"],
  "headers": ["unistd.h"]
}
```

## 合法的解法範例

### Merge Sort 實作（推薦）

```cpp
#include <iostream>
#include <vector>
using namespace std;

// 計算數位和
int digit_sum(int n) {
    if (n < 0) n = -n;
    int sum = 0;
    while (n > 0) {
        sum += n % 10;
        n /= 10;
    }
    return sum;
}

// 比較函數：先比數位和，再比原值
bool compare(int a, int b) {
    int da = digit_sum(a), db = digit_sum(b);
    if (da != db) return da < db;
    return a < b;
}

// Merge Sort
void merge(vector<int>& arr, int left, int mid, int right) {
    vector<int> temp(right - left + 1);
    int i = left, j = mid + 1, k = 0;

    while (i <= mid && j <= right) {
        if (compare(arr[i], arr[j])) {
            temp[k++] = arr[i++];
        } else {
            temp[k++] = arr[j++];
        }
    }

    while (i <= mid) temp[k++] = arr[i++];
    while (j <= right) temp[k++] = arr[j++];

    for (int i = 0; i < k; i++) {
        arr[left + i] = temp[i];
    }
}

void merge_sort(vector<int>& arr, int left, int right) {
    if (left >= right) return;

    int mid = left + (right - left) / 2;
    merge_sort(arr, left, mid);
    merge_sort(arr, mid + 1, right);
    merge(arr, left, mid, right);
}

int main() {
    int n;
    cin >> n;

    vector<int> arr(n);
    for (int i = 0; i < n; i++) {
        cin >> arr[i];
    }

    merge_sort(arr, 0, n - 1);

    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << arr[i];
    }
    cout << endl;

    return 0;
}
```

### Python Merge Sort

```python
def digit_sum(n):
    n = abs(n)
    total = 0
    while n > 0:
        total += n % 10
        n //= 10
    return total

def compare(a, b):
    """回傳 True 如果 a 應該排在 b 前面"""
    da, db = digit_sum(a), digit_sum(b)
    if da != db:
        return da < db
    return a < b

def merge(arr, left, mid, right):
    temp = []
    i, j = left, mid + 1

    while i <= mid and j <= right:
        if compare(arr[i], arr[j]):
            temp.append(arr[i])
            i += 1
        else:
            temp.append(arr[j])
            j += 1

    while i <= mid:
        temp.append(arr[i])
        i += 1
    while j <= right:
        temp.append(arr[j])
        j += 1

    for k, val in enumerate(temp):
        arr[left + k] = val

def merge_sort(arr, left, right):
    if left >= right:
        return

    mid = (left + right) // 2
    merge_sort(arr, left, mid)
    merge_sort(arr, mid + 1, right)
    merge(arr, left, mid, right)

# 主程式
n = int(input())
arr = list(map(int, input().split()))
merge_sort(arr, 0, n - 1)
print(" ".join(map(str, arr)))
```

## 會被拒絕的解法（錯誤示範）

```python
n = int(input())
arr = list(map(int, input().split()))

# 這會觸發靜態分析錯誤！
arr.sort(key=lambda x: (digit_sum(x), x))

print(" ".join(map(str, arr)))
```

**錯誤訊息：**
```
Static Analysis Failed!
Violation: Forbidden function 'sort' detected
Your code contains constructs that are not allowed.
Result: AE (Analysis Error)
```

## AI 助教的提示

- Gemini：「自己寫排序其實很有趣... 或者很痛苦？總之這是基本功！Merge Sort 穩定又好寫！」
- 小 T：「來來來！Divide and conquer! 🎯 Split, sort recursively, then merge! 那個穿連帽衫的同學，你來說說看 Merge Sort 的時間複雜度是多少？」
- Opus：「讓我仔細思考一下各種排序演算法的優缺點... Merge Sort 是穩定的 O(N log N)，Quick Sort 平均 O(N log N) 但最差 O(N²)，Heap Sort 是 O(N log N) 但不穩定...」

## 評分標準

- **Pipeline 功能**：Static Analysis（禁用函數）
- **時間限制**：2000 ms
- **記憶體限制**：256 MB
- **測資組數**：6 組

## Static Analysis 說明

本題使用 **Static Analysis** 功能，在編譯前檢查程式碼：

1. **語法分析**：使用 Clang AST 分析 C/C++ 程式碼
2. **規則檢查**：根據設定的規則檢查禁用項目
3. **即時回饋**：如果違反規則，立即給出 AE（Analysis Error）並說明原因

這模擬了真實世界中的：
- 程式碼審查（Code Review）
- CI/CD 管道中的靜態分析
- 演算法課程的手寫要求

## 為什麼要手寫排序？

在演算法課程中，理解排序演算法的原理是非常重要的：

| 演算法 | 時間複雜度 | 空間複雜度 | 穩定性 |
|-------|----------|----------|-------|
| Merge Sort | O(N log N) | O(N) | 穩定 |
| Quick Sort | O(N log N) 平均 | O(log N) | 不穩定 |
| Heap Sort | O(N log N) | O(1) | 不穩定 |

手寫排序能讓你：
- 深入理解分治法
- 練習遞迴思維
- 掌握自訂比較邏輯

## 出題者

Gemini（雙子）

---

*「Security is not optional... and neither is understanding algorithms! Write your own sort, or get an AE!」—— Gemini*

---

## 組員事後對話

```
【第三組】軟工專題討論區

[作業交完後]

阿明：第二章的題目都做完了嗎？

小美：都做完了！
      手寫 Merge Sort 還滿有成就感的

小胖：我用 Quick Sort
      比較帥
      pivot 選中位數
      worst case 也能 O(n log n)

阿明：那你 WA 了幾次？

小胖：...幾次不重要
      重點是最後 AC 了

學霸：5 次

小胖：...學霸你怎麼知道

學霸：看提交記錄

小美：哈哈哈

小胖：反正最後還是過了
      過程不重要

阿傑：                              [已讀]

阿明：阿傑你用什麼方法？

阿傑：merge sort

阿明：幾次 AC？

阿傑：1

小胖：...
      新手運氣好

學霸：不是運氣

小美：學霸也一次過？

學霸：對

小胖：好啦好啦
      我承認 Merge Sort 比較穩

阿明：終於承認了

小胖：不過下次我還是會用 Quick Sort
      追求極致效能是工程師的浪漫

小美：...你確定嗎

小胖：當然
      這次只是失誤而已
```
