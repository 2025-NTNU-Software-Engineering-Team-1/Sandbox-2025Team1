# Problem 13: Code Review 生存戰

## 故事背景

「我來 review 你們的 code！」小 T 自告奮勇，戴上一副想像中的眼鏡。

「我會檢查：命名規範、程式風格、還有是否使用禁術！」

Gemini 補充：「對了，這題的 checker 會同時檢查正確性和程式風格！不只要對，還要寫得好看！」

Opus 若有所思：「讓我仔細思考一下好的程式風格的標準... Martin Fowler 曾說：『任何傻瓜都能寫出電腦能理解的程式。好的程式設計師寫的是人類能理解的程式。』」

「太長了！」Gemini 打斷。

「總之，」小 T 接話，「這題你們不只要寫出正確的程式，還要寫得漂亮！而且這次的統計計算比較複雜——要算**中位數**、**標準差**、還有**百分位數**！We're looking for clean, readable code with proper algorithms! ✨」

## 題目說明

實作一個程式，讀取一串數字，輸出它們的**進階統計資訊**：

1. **最大值** (Max)
2. **最小值** (Min)
3. **平均值** (Mean)
4. **中位數** (Median)
5. **標準差** (Standard Deviation)
6. **指定百分位數** (Percentile)

**但是！** 你的程式碼會被雙重檢查：

1. **正確性檢查**（60%）：輸出是否正確
2. **風格檢查**（40%）：程式碼是否符合規範

### 風格規範

| 規則 | 扣分 | 說明 |
|-----|------|------|
| 使用 `goto` | -20% | goto 是邪惡的 |
| 使用 `gets` | -20% | 緩衝區溢位風險 |
| 單字母變數（除了 i,j,k,n,m） | -10% | 變數名稱要有意義 |
| 函數過長（>50 行） | -5% | 函數應該簡短 |
| 沒有註解 | -5% | 重要邏輯需要註解 |

## 輸入格式

```
第一行：整數 N 和 P (1 ≤ N ≤ 10000, 1 ≤ P ≤ 99)
  - N: 數字個數
  - P: 要計算的百分位數
第二行：N 個整數，以空格分隔 (-10⁹ ≤ 每個整數 ≤ 10⁹)
```

## 輸出格式

```
Max: 最大值
Min: 最小值
Mean: 平均值（保留兩位小數）
Median: 中位數（保留兩位小數）
StdDev: 標準差（保留兩位小數）
P{P}: 第 P 百分位數（保留兩位小數）
```

## 統計公式

### 中位數 (Median)

將資料排序後：
- 如果 N 是奇數：中位數 = 第 (N+1)/2 個數
- 如果 N 是偶數：中位數 = (第 N/2 個數 + 第 N/2+1 個數) / 2

### 標準差 (Standard Deviation)

使用**母體標準差**公式：

$$\sigma = \sqrt{\frac{\sum_{i=1}^{N}(x_i - \bar{x})^2}{N}}$$

其中 $\bar{x}$ 是平均值。

### 百分位數 (Percentile)

使用**線性插值法**：

1. 將資料排序
2. 計算位置：$L = P \times (N + 1) / 100$
3. 如果 L 是整數：第 P 百分位數 = 第 L 個數
4. 如果 L 不是整數：
   - $k = \lfloor L \rfloor$
   - $d = L - k$
   - 第 P 百分位數 = $x_k + d \times (x_{k+1} - x_k)$

## 範例

**輸入：**
```
10 25
15 20 35 40 50 55 60 70 80 95
```

**輸出：**
```
Max: 95
Min: 15
Mean: 52.00
Median: 52.50
StdDev: 24.11
P25: 31.25
```

**計算過程：**

1. **Max**: 95
2. **Min**: 15
3. **Mean**: (15+20+35+40+50+55+60+70+80+95) / 10 = 520 / 10 = 52.00
4. **Median**: 排序後 [15,20,35,40,50,55,60,70,80,95]
   - N=10 是偶數，中位數 = (50+55)/2 = 52.50
5. **StdDev**:
   - 變異數 = [(15-52)² + (20-52)² + ... + (95-52)²] / 10 = 5810 / 10 = 581
   - 標準差 = √581 ≈ 24.10
6. **P25** (第 25 百分位數):
   - L = 25 × (10+1) / 100 = 2.75
   - k = 2, d = 0.75
   - P25 = x[2] + 0.75 × (x[3] - x[2]) = 20 + 0.75 × (35-20) = 20 + 11.25 = 31.25

## 好的程式碼範例

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <numeric>
using namespace std;

// 計算平均值
double calculateMean(const vector<long long>& numbers) {
    long long sum = accumulate(numbers.begin(), numbers.end(), 0LL);
    return static_cast<double>(sum) / numbers.size();
}

// 計算中位數（假設已排序）
double calculateMedian(const vector<long long>& sortedNumbers) {
    int n = sortedNumbers.size();
    if (n % 2 == 1) {
        return sortedNumbers[n / 2];
    } else {
        return (sortedNumbers[n / 2 - 1] + sortedNumbers[n / 2]) / 2.0;
    }
}

// 計算母體標準差
double calculateStdDev(const vector<long long>& numbers, double mean) {
    double sumSquaredDiff = 0;
    for (long long num : numbers) {
        double diff = num - mean;
        sumSquaredDiff += diff * diff;
    }
    return sqrt(sumSquaredDiff / numbers.size());
}

// 計算百分位數（使用線性插值，假設已排序）
double calculatePercentile(const vector<long long>& sortedNumbers, int percentile) {
    int n = sortedNumbers.size();
    double position = percentile * (n + 1) / 100.0;

    if (position <= 1) return sortedNumbers[0];
    if (position >= n) return sortedNumbers[n - 1];

    int lowerIndex = static_cast<int>(position) - 1;
    double fraction = position - static_cast<int>(position);

    return sortedNumbers[lowerIndex] +
           fraction * (sortedNumbers[lowerIndex + 1] - sortedNumbers[lowerIndex]);
}

int main() {
    int n, p;
    cin >> n >> p;

    vector<long long> numbers(n);
    for (int i = 0; i < n; i++) {
        cin >> numbers[i];
    }

    // 計算基本統計量
    long long maxValue = *max_element(numbers.begin(), numbers.end());
    long long minValue = *min_element(numbers.begin(), numbers.end());
    double mean = calculateMean(numbers);

    // 排序以計算中位數和百分位數
    vector<long long> sortedNumbers = numbers;
    sort(sortedNumbers.begin(), sortedNumbers.end());

    double median = calculateMedian(sortedNumbers);
    double stdDev = calculateStdDev(numbers, mean);
    double percentileValue = calculatePercentile(sortedNumbers, p);

    // 輸出結果
    cout << fixed << setprecision(2);
    cout << "Max: " << maxValue << endl;
    cout << "Min: " << minValue << endl;
    cout << "Mean: " << mean << endl;
    cout << "Median: " << median << endl;
    cout << "StdDev: " << stdDev << endl;
    cout << "P" << p << ": " << percentileValue << endl;

    return 0;
}
```

**這個程式碼的優點：**
- ✅ 有意義的變數名稱（`maxValue`, `minValue`, `mean`）
- ✅ 適當的註解
- ✅ 函數短小精悍
- ✅ 邏輯清晰
- ✅ 正確處理邊界情況

## 糟糕的程式碼範例

```cpp
#include <iostream>
using namespace std;
int main() {
    int n,p;cin>>n>>p;
    long long a[10000];long long x=-1e18,y=1e18;double z=0;
    for(int i=0;i<n;i++){cin>>a[i];if(a[i]>x)x=a[i];if(a[i]<y)y=a[i];z+=a[i];}
    z/=n;double s=0;for(int i=0;i<n;i++)s+=(a[i]-z)*(a[i]-z);s=sqrt(s/n);
    // 省略排序和其他計算...
    return 0;
}
```

**這個程式碼的問題：**
- ❌ 變數名稱 `x`, `y`, `z`, `s` 毫無意義
- ❌ 沒有任何有用的註解
- ❌ 魔術數字（-1e18, 1e18）
- ❌ 所有邏輯塞在一起，難以閱讀

## 評分計算

```
最終分數 = 正確性分數 × 0.6 + 風格分數 × 0.4
```

**範例：**
- 全部 AC + 完美風格 = 60 + 40 = 100 分
- 全部 AC + 使用 goto = 60 + (40-20) = 80 分
- 部分 AC + 糟糕風格 = 30 + 10 = 40 分

## AI 助教的提示

- 小 T：「Clean code is happy code! 🧹 And don't forget the algorithms - median needs sorting, stddev needs squares!」
- Gemini：「中位數要排序... 百分位數要插值... 或者不用？我記得有很多種算法...」
- Opus：「讓我仔細思考一下統計學的基本原理... 標準差有母體和樣本兩種，記得確認是哪一種...」

## 評分標準

- **Pipeline 功能**：Custom Checker + Static Analysis
- **時間限制**：1000 ms
- **記憶體限制**：256 MB
- **測資組數**：6 組

## 雙重檢查機制

本題結合了兩種 Pipeline 功能：

### 1. Static Analysis（編譯前）
- 檢查禁用函數
- 分析變數命名
- 計算函數長度

### 2. Custom Checker（執行後）
- 驗證輸出正確性（浮點數容差 10⁻²）
- 綜合風格分數

### 檢查流程

```
程式碼 → Static Analysis → 編譯 → 執行 → Custom Checker → 最終分數
          (風格檢查)                      (正確性+風格綜合)
```

## 數學提示

### 排序演算法

計算中位數和百分位數需要先排序。你可以使用：
- `std::sort()` (C++)
- `sorted()` (Python)

時間複雜度：O(N log N)

### 浮點數精度

使用 `double` 而非 `float`，以確保足夠的精度。

### 溢位處理

對於大量數據的求和，使用 `long long` 避免溢位。

## 出題者

三 AI 聯手

---

*「Write code for humans, not just for machines! 👥 And make sure your statistics are correct!」—— 小 T*
*「Is this code readable? I can't tell... or can I? At least the math should be right...」—— Gemini*
*「Code readability is a form of communication. Let me think about the relationship between clean code and correct algorithms...」—— Opus*
