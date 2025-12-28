# Problem 9: 死線前的奇蹟

## 故事背景

「讓我仔細思考一下時間的本質...」Opus 陷入沉思，眼神望向遠方。

「專題報告的 deadline 是明天早上八點。現在是凌晨兩點。」

Gemini 驚叫：「什麼？！我們還有 6 個 bug 沒修！而且我記得... 還是不記得... 總之好像還有什麼事沒做！」

小 T 端著咖啡走過來，臉上帶著堅定的笑容：「Don't worry! 來來來，We can do this! 💪 Just need some coffee and determination! You know what they say: 'The best code is written at 3 AM!' 🌙 綜觀全局，deadline 就是 motivation！」

「那是最糟糕的程式設計迷思之一，」Opus 皺眉，「讓我仔細思考一下睡眠不足對程式品質的影響...」

「沒時間讓你思考了！」Gemini 打斷，「這題測試你們在時間壓力下的表現！越快完成，分數越高！」

Opus 點頭：「說得對。這題我設計了一個特殊的評分系統：除了正確性之外，執行效率也會影響分數。讓我仔細解釋這個評分公式...」

## 題目說明

給定一個長度為 N 的整數序列，找出其中**最長嚴格遞增子序列（LIS, Longest Increasing Subsequence）**的長度。

### 什麼是最長嚴格遞增子序列？

從原序列中選取若干元素（可以不連續），使得這些元素嚴格遞增排列，且選取的元素數量最多。

**例如**：序列 `[10, 9, 2, 5, 3, 7, 101, 18]`
- 一個遞增子序列：`[2, 5, 7, 101]`，長度 4
- 另一個遞增子序列：`[2, 3, 7, 18]`，長度 4
- LIS 長度為 4

## 輸入格式

```
第一行：整數 N (1 ≤ N ≤ 100000)
第二行：N 個整數，以空格分隔 (-10⁹ ≤ 每個整數 ≤ 10⁹)
```

## 輸出格式

```
一個整數，最長嚴格遞增子序列的長度
```

## 範例

**輸入：**
```
8
10 9 2 5 3 7 101 18
```

**輸出：**
```
4
```

## 評分標準

本題使用 **Custom Scorer** 進行評分，除了正確性外，還考慮執行效率：

### 基礎分數計算

| 條件 | 分數 |
|-----|------|
| 全部 AC | 80 分 |
| 部分 AC | 每個 AC 測資給相應比例分數（最高 80 分） |

### 時間獎勵（加分項目）

| 平均執行時間 | 獎勵 |
|------------|------|
| < 50 ms | +20 分（咖啡因超載！🚀） |
| < 200 ms | +10 分（正常發揮） |
| < 500 ms | +5 分（還行吧） |
| ≥ 500 ms | +0 分（需要更多咖啡） |

### 遲交扣分

| 遲交時間 | 扣分 |
|---------|------|
| 每小時 | -5 分 |
| 最多扣 | -50 分 |

### 分數公式

```
最終分數 = min(100, 基礎分數 + 時間獎勵 - 遲交扣分)
```

**注意**：最終分數上限為 100 分，不會超過。

## 提示

### O(N²) 解法（可以 AC，但拿不到時間獎勵）

```cpp
int lis_n2(vector<int>& nums) {
    int n = nums.size();
    vector<int> dp(n, 1);

    for (int i = 1; i < n; i++) {
        for (int j = 0; j < i; j++) {
            if (nums[j] < nums[i]) {
                dp[i] = max(dp[i], dp[j] + 1);
            }
        }
    }

    return *max_element(dp.begin(), dp.end());
}
```

### O(N log N) 解法（可以拿到時間獎勵！）

使用二分搜尋 + 動態規劃：

```cpp
int lis_nlogn(vector<int>& nums) {
    vector<int> tails;

    for (int num : nums) {
        auto it = lower_bound(tails.begin(), tails.end(), num);
        if (it == tails.end()) {
            tails.push_back(num);
        } else {
            *it = num;
        }
    }

    return tails.size();
}
```

## AI 助教的提示

- Opus：「讓我仔細思考一下這個問題的最優解... 這是一個經典的動態規劃問題，有 O(N²) 和 O(N log N) 兩種解法...（此處省略演算法證明 3000 字）」
- Gemini：「我記得這題用二分搜尋可以優化... 還是用線段樹？或者兩個都可以？我不確定。」
- 小 T：「來來來！Pro tip 💡：`lower_bound` is your friend! It's like binary search but cooler! 😎 綜觀全局，這就是演算法優化的精髓！」

## 評分標準

- **Pipeline 功能**：Custom Scorer（時間獎勵、部分給分）
- **時間限制**：2000 ms
- **記憶體限制**：256 MB
- **測資組數**：6 組

## Custom Scorer 說明

本題使用 **Custom Scorer** 功能：

1. **多維度評分**：不只看對錯，還看效率
2. **時間獎勵**：鼓勵優化演算法
3. **部分給分**：部分正確也有分數
4. **遲交懲罰**：模擬真實世界的 deadline

這模擬了真實世界中的：
- 程式競賽的多層次評分
- 軟體專案的時程管理
- 效能導向的開發文化

### Custom Scorer 程式碼範例

```python
def calculate_score(data):
    # 計算基礎分（滿分 80）
    total_cases = sum(len(t['results']) for t in data['tasks'])
    passed_cases = sum(
        1 for t in data['tasks']
        for r in t['results']
        if r['status'] == 'AC'
    )
    base_score = (passed_cases / total_cases) * 80

    # 計算時間獎勵（加分項目）
    avg_time = data['stats']['avgRunTime']
    if avg_time < 50:
        time_bonus = 20
    elif avg_time < 200:
        time_bonus = 10
    elif avg_time < 500:
        time_bonus = 5
    else:
        time_bonus = 0

    # 計算遲交扣分
    late_hours = data['lateSeconds'] / 3600
    late_penalty = min(50, late_hours * 5)

    # 最終分數（上限 100）
    final_score = min(100, base_score + time_bonus - late_penalty)
    final_score = max(0, final_score)  # 不能為負

    return {
        "score": int(final_score),
        "message": f"基礎: {base_score:.0f}, 時間獎勵: +{time_bonus}, 遲交扣分: -{late_penalty:.0f}",
        "breakdown": {
            "base": base_score,
            "timeBonus": time_bonus,
            "latePenalty": late_penalty
        }
    }
```

## 出題者

Opus（歐帕斯）

---

*「Time is a construct... but deadlines are very real. Let me think about this paradox...」—— Opus*
