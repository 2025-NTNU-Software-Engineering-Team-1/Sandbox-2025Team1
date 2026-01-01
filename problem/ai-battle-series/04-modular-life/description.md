# Problem 4: 模組化你的人生

## 故事背景

> 「好的，接下來由我 Gemini 來出題。不過我要先說明，我可能會...
> 等等，我剛剛說了什麼？總之，這些題目難度適中... 或者很難...
> 也可能很簡單？我自己也不太確定。」
> —— Gemini，期中考前夕

期中考週來臨了。教室裡的氣氛異常凝重，每個學生的臉上都寫滿了疲憊和絕望。

「同學們！」Gemini 的聲音在教室中響起，「今天由我來出題！」

「軟體工程的核心是什麼？」Gemini 突然切換成講師模式，「是模組化！」

下一秒又說：「不對，核心應該是測試... 還是文件？算了都很重要。」

「總之！」Gemini 試圖拉回主題，「這題要測試你們的模組化能力。我已經寫好了 main 函數，你們需要實作多個功能函數！」

小 T 在旁邊小聲說：「這不就是我說的 function programming 嗎？來來來，那個第三排的同學，你覺得呢？」

Opus 糾正：「是 modular programming，不是 functional programming。讓我仔細思考一下這兩個概念的區別：modular programming 強調的是將程式分割成獨立、可重用的模組，而 functional programming 則是一種以純函數為核心的程式設計範式...」

「夠了夠了！」Gemini 打斷，「同學們，這次要實作四個函數！加權 GPA、班級排名、等第轉換、還有及格判定！不要被 Opus 的長篇大論嚇到！」

---

## 組員群組訊息

```
【第三組】軟工專題討論區

阿明：@all 期中考週大家還好嗎？
      我們專題進度好像落後了

小胖：放心啦
      模組化程式設計這種東西我最熟了
      我之前有研究過 SOLID 原則
      還有 Clean Architecture
      這些都是進階概念

阿明：...那你專題的沙盒環境弄好了嗎？

小胖：快了快了
      我在研究更好的架構
      Docker Compose + Kubernetes + Service Mesh
      這樣才專業

小美：可是助教說期中考前要有基本功能...
      我前端已經做好了，但後端 API 還沒有

阿傑：                              [已讀]

阿明：阿傑你後端 API 什麼時候好？
      小美在等你

阿傑：                              [已讀]
      快了

小美：...

學霸：加權平均要用 long long
      避免溢位

小胖：這個我當然知道
      我只是在想更優雅的實作方式

阿明：能不能先寫出來再說...
      期中考週大家壓力都很大

小胖：好啦好啦
      等我研究完就寫

學霸：                              [離線]

阿明：學霸你也走了？？？
```

---

## 題目說明

本題使用 **Function-only Mode**。你需要實作以下四個函數，系統會將你的實作與教師提供的 main 程式結合後執行測試。

### 需要實作的函數

#### C/C++ 版本

```c
// function.h

// 1. 計算加權 GPA
// 參數：
//   scores: 成績陣列 (0-100)
//   credits: 學分陣列
//   n: 科目數量 (1 ≤ n ≤ 100)
// 回傳：加權 GPA = Σ(score[i] × credit[i]) / Σcredit[i]
double calculate_weighted_gpa(int scores[], int credits[], int n);

// 2. 計算班級排名（使用百分等級 PR 值）
// 參數：
//   all_scores: 全班所有人的總分陣列
//   n: 班級人數 (1 ≤ n ≤ 1000)
//   my_score: 我的總分
// 回傳：PR 值 = (贏過的人數 / 總人數) × 100，四捨五入到整數
// 說明：如果有人跟我同分，算贏一半（例如 3 人同分，我贏 1.5 人）
int calculate_percentile_rank(int all_scores[], int n, int my_score);

// 3. 分數轉等第
// 參數：
//   score: 分數 (0-100)
// 回傳：等第對應的 GPA 點數
//   A+ (90-100) → 4.3
//   A  (85-89)  → 4.0
//   A- (80-84)  → 3.7
//   B+ (77-79)  → 3.3
//   B  (73-76)  → 3.0
//   B- (70-72)  → 2.7
//   C+ (67-69)  → 2.3
//   C  (63-66)  → 2.0
//   C- (60-62)  → 1.7
//   D  (50-59)  → 1.0
//   F  (0-49)   → 0.0
double score_to_gpa_points(int score);

// 4. 判斷是否達到畢業門檻
// 參數：
//   gpa: 加權 GPA
//   total_credits: 已修學分數
//   required_credits: 畢業所需學分
//   failed_subjects: 被當科目數
//   max_failed: 最多允許被當科目數
// 回傳：
//   0 = 不符合畢業資格
//   1 = 符合畢業資格
//   2 = 可提前畢業（GPA >= 3.8 且學分超過要求 10% 且無被當）
int check_graduation(double gpa, int total_credits, int required_credits,
                     int failed_subjects, int max_failed);
```

#### Python 版本

```python
# student_impl.py

def calculate_weighted_gpa(scores: list[int], credits: list[int]) -> float:
    """
    計算加權 GPA

    Args:
        scores: 成績列表 (0-100)
        credits: 學分列表
    Returns:
        加權 GPA = Σ(score[i] × credit[i]) / Σcredit[i]
    """
    pass

def calculate_percentile_rank(all_scores: list[int], my_score: int) -> int:
    """
    計算班級排名（百分等級 PR 值）

    Args:
        all_scores: 全班所有人的總分列表
        my_score: 我的總分
    Returns:
        PR 值 = (贏過的人數 / 總人數) × 100，四捨五入到整數
        如果有人跟我同分，算贏一半
    """
    pass

def score_to_gpa_points(score: int) -> float:
    """
    分數轉等第 GPA 點數

    Args:
        score: 分數 (0-100)
    Returns:
        對應的 GPA 點數 (0.0 - 4.3)
    """
    pass

def check_graduation(gpa: float, total_credits: int, required_credits: int,
                     failed_subjects: int, max_failed: int) -> int:
    """
    判斷是否達到畢業門檻

    Args:
        gpa: 加權 GPA
        total_credits: 已修學分數
        required_credits: 畢業所需學分
        failed_subjects: 被當科目數
        max_failed: 最多允許被當科目數
    Returns:
        0 = 不符合畢業資格
        1 = 符合畢業資格
        2 = 可提前畢業（GPA >= 3.8 且學分超過要求 10% 且無被當）
    """
    pass
```

## 測試方式

系統會使用類似以下的 main 程式來測試你的函數：

```c
#include <stdio.h>
#include "function.h"

int main() {
    int test_type;
    scanf("%d", &test_type);

    if (test_type == 1) {
        // 測試 calculate_weighted_gpa
        int n;
        scanf("%d", &n);
        int scores[100], credits[100];
        for (int i = 0; i < n; i++) {
            scanf("%d %d", &scores[i], &credits[i]);
        }
        printf("%.2f\n", calculate_weighted_gpa(scores, credits, n));
    }
    else if (test_type == 2) {
        // 測試 calculate_percentile_rank
        int n, my_score;
        scanf("%d %d", &n, &my_score);
        int all_scores[1000];
        for (int i = 0; i < n; i++) {
            scanf("%d", &all_scores[i]);
        }
        printf("%d\n", calculate_percentile_rank(all_scores, n, my_score));
    }
    else if (test_type == 3) {
        // 測試 score_to_gpa_points
        int score;
        scanf("%d", &score);
        printf("%.1f\n", score_to_gpa_points(score));
    }
    else if (test_type == 4) {
        // 測試 check_graduation
        double gpa;
        int total, required, failed, max_failed;
        scanf("%lf %d %d %d %d", &gpa, &total, &required, &failed, &max_failed);
        int result = check_graduation(gpa, total, required, failed, max_failed);
        if (result == 0) printf("NOT QUALIFIED\n");
        else if (result == 1) printf("QUALIFIED\n");
        else printf("EARLY GRADUATION\n");
    }

    return 0;
}
```

## 範例

### 範例 1：加權 GPA

**輸入：**
```
1
3
80 3
90 2
70 4
```

**預期輸出：**
```
77.78
```

**說明：** (80×3 + 90×2 + 70×4) / (3+2+4) = 700/9 ≈ 77.78

### 範例 2：百分等級

**輸入：**
```
2
10 75
60 70 75 75 80 85 85 90 95 100
```

**預期輸出：**
```
25
```

**說明：**
- 我的分數是 75
- 低於 75 的有 2 人（60, 70）
- 等於 75 的有 2 人（包含我）
- 贏過的人數 = 2 + 0.5 = 2.5（同分的另一人算贏一半）
- PR = (2.5 / 10) × 100 = 25

### 範例 3：等第轉換

**輸入：**
```
3
87
```

**預期輸出：**
```
4.0
```

### 範例 4：畢業門檻

**輸入：**
```
4
3.9 145 128 0 2
```

**預期輸出：**
```
EARLY GRADUATION
```

**說明：** GPA=3.9 >= 3.8，學分 145 > 128×1.1=140.8，無被當 → 可提前畢業

## 提示

### 加權 GPA 計算

```python
def calculate_weighted_gpa(scores, credits):
    total_weighted = sum(s * c for s, c in zip(scores, credits))
    total_credits = sum(credits)
    return total_weighted / total_credits
```

### 百分等級計算（需要處理同分情況）

```python
def calculate_percentile_rank(all_scores, my_score):
    n = len(all_scores)
    below = sum(1 for s in all_scores if s < my_score)
    equal = sum(1 for s in all_scores if s == my_score)
    # 同分的人（不含自己）算贏一半
    wins = below + (equal - 1) * 0.5
    pr = (wins / n) * 100
    return round(pr)
```

### 等第轉換（使用條件判斷）

```cpp
double score_to_gpa_points(int score) {
    if (score >= 90) return 4.3;
    if (score >= 85) return 4.0;
    if (score >= 80) return 3.7;
    if (score >= 77) return 3.3;
    if (score >= 73) return 3.0;
    if (score >= 70) return 2.7;
    if (score >= 67) return 2.3;
    if (score >= 63) return 2.0;
    if (score >= 60) return 1.7;
    if (score >= 50) return 1.0;
    return 0.0;
}
```

## AI 助教的提示

- Gemini：「這題有四個函數... 或者三個？不對是四個。每個都不太難... 或者很難？總之慢慢來！」
- 小 T：「Four functions, four challenges! 🎯 來來來，綜觀全局，modular thinking is the key! 那個穿格子衫的同學，你來說說 PR 值怎麼算！」
- Opus：「讓我仔細思考一下百分等級的數學定義... 這涉及到統計學中的累積分布函數的概念...」

## 評分標準

- **Pipeline 功能**：Function-only Mode
- **時間限制**：1000 ms
- **記憶體限制**：64 MB
- **測資組數**：8 組（每個函數 2 組）

## Function-only Mode 說明

本題使用 **Function-only Mode**，這是一種常見的程式設計教學模式：

1. **教師提供框架**：main 函數、輸入輸出處理已經寫好
2. **學生實作核心**：只需要填入特定函數的實作
3. **自動整合測試**：系統會將學生程式碼與教師框架結合後執行

這種模式的好處：
- 學生可以專注於演算法邏輯
- 避免輸入輸出格式錯誤
- 培養模組化程式設計思維
- 便於單元測試

## 出題者

Gemini（雙子）

---

*「Modularization is key... or is it? Actually, yes, it definitely is. I think. Or do I?」—— Gemini*

---

## 組員事後對話

```
【第三組】軟工專題討論區

[期中考結束後]

阿明：大家考得怎麼樣？

小美：我四個函數都寫對了！
      最難的是百分等級那個
      同分要算一半

小胖：這題太簡單了
      我本來想用更高級的寫法
      比如用 lambda 和 functional programming
      但最後還是用普通的迴圈

阿明：...所以你考得如何？

小胖：還行還行
      PR 值那題我算錯了一點點
      但其他都對

學霸：92

小美：哇！學霸果然是學霸！

阿傑：                              [已讀]

阿明：阿傑你呢？

阿傑：85

阿明：！？你居然回了完整數字！

小胖：阿傑進步了！打了兩個字！

學霸：還行

阿傑：                              [離線]

阿明：...他又消失了
```
