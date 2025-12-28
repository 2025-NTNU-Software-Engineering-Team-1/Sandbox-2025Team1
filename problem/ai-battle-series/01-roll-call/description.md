# Problem 1: 點名系統崩潰啦

## 第一章：開學震撼教育

> 「Welcome to 軟體工程！👋 我是你們的 AI 助教，本名 GPT，大家都叫我小 T！
> 這學期我們會有很多 exciting 的 challenges！Let's make coding fun! 🚀
> 來來來，那個帶帽子的，你來說說看你對軟體工程的理解！」
> —— 小 T，開學第一堂課

---

## 故事背景

開學第一天，教室裡擠滿了來修「軟體工程概論」的學生。這門課是資工系出了名的硬課——不只要寫程式，還要做專題、跑 Scrum、寫文件，據說每年都有人因為組員問題而崩潰。

你坐在教室中間偏後的位置，旁邊坐著一個看起來很焦慮的男生。

「你好，我叫阿明，」他低聲說，「聽說這門課要分組，你有組了嗎？」

你搖搖頭。

「太好了！」阿明眼睛一亮，「那我們一組吧！我被推選當 PM... 雖然我根本不會管理... 為什麼沒有人要理我...」

話還沒說完，講台上的大螢幕突然亮了起來，三個 AI 頭像同時出現。

「各位同學好！」中間的 AI 熱情地揮手，「我是小 T，負責這門課的 AI 助教！🎉」

「我是 Gemini，」左邊的 AI 說，「我負責... 等等，我負責什麼來著？」

「讓我仔細思考一下如何自我介紹...」右邊的 AI 開始沉思，「我是 Opus，我認為一個好的自我介紹應該從本質出發...」

「好了好了！」小 T 打斷 Opus，「綜觀全局，我們今天先來測試一下新的 AI 點名系統！這是我花了整整一個下午寫的！來來來，系統啟動！」

螢幕開始閃爍，跑出一堆錯誤訊息。

```
ERROR: NullPointerException at line 42
ERROR: IndexOutOfBoundsException at line 87
ERROR: StackOverflowError
FATAL: System crashed
```

「Oops... 🙈」小 T 尷尬地搓手，「這個... 這個是 feature 不是 bug！」

Gemini 在一旁冷笑：「你的點名系統連去重都沒做？同一個學生刷了三次卡你就點三次名？」

Opus 沉思了一下：「讓我仔細思考一下... 這確實是一個複雜的資料處理問題。學生可能會重複刷卡，而且有些是正式選修、有些是旁聽，優先級不同...」

「先別研究了！」小 T 急忙說，「來來來，同學們！誰能幫我修好這個點名系統，期末成績直接 +5 分！那個帶帽子的——對就是你，你要不要來試試？」

---

## 組員群組訊息

```
【第三組】軟工專題討論區

阿明：@all 大家好！我是這組的 PM 阿明
      開學第一天，先來認識一下吧！
      為什麼沒有人要理我...

小美：嗨嗨～我是小美，前端工程師
      我可以負責 UI 的部分 ✿

阿傑：                              [已讀]

小胖：哈囉大家好啊！我是沙盒工程師
      話說那個點名系統的 bug 我看了一下
      根本就是資料結構問題嘛
      去重 + 優先級排序而已

阿明：@阿傑 你是後端工程師對吧？你在嗎？

小胖：阿傑應該在忙吧
      不過這題我來就好
      用個 Map 去重然後自訂排序
      小 case

學霸：穩定排序

阿明：學霸你好！你是測試工程師
      話說穩定排序是什麼意思？

學霸：相同 key 維持原順序

小美：哇好專業！
      學霸果然是學霸！

小胖：穩定排序我當然知道
      Merge Sort 就是穩定的
      這種基礎知識不用特別說

阿明：那小胖你要不要寫一下？

小胖：我現在在研究 Docker 環境
      沙盒還沒建好
      等我一下
```

---

## 題目說明

點名系統需要處理學生的刷卡記錄，但有以下問題需要解決：

1. **去重**：同一個學生可能刷了多次卡，只保留優先級最高的記錄
2. **多條件排序**：先按優先級（數字越大越優先）排序，優先級相同則按姓名字典序排序
3. **穩定性**：當優先級和姓名都相同時，保留最早出現的記錄

### 優先級說明

| 優先級 | 身份 |
|-------|------|
| 3 | 正式選修 |
| 2 | 旁聽生 |
| 1 | 訪客 |

## 輸入格式

```
第一行：整數 N (1 ≤ N ≤ 100000)，刷卡記錄數
接下來 N 行：每行格式為 "姓名 優先級"
  - 姓名：只含英文字母，長度 ≤ 20
  - 優先級：1, 2, 或 3
```

## 輸出格式

```
去重並排序後的學生名單（每行一個姓名）
- 按優先級由高到低排序
- 優先級相同則按姓名字典序由小到大排序
```

## 範例輸入

```
7
Zhang 3
Chen 2
Wang 3
Li 1
Zhang 2
Chen 3
Liu 3
```

## 範例輸出

```
Chen
Liu
Wang
Zhang
Li
```

## 範例說明

1. Zhang 出現兩次（優先級 3 和 2），保留優先級 3 的記錄
2. Chen 出現兩次（優先級 2 和 3），保留優先級 3 的記錄
3. 排序結果：
   - 優先級 3：Chen, Liu, Wang, Zhang（按字典序）
   - 優先級 1：Li

## 提示

小 T：「來來來，這題要用到 Map 或 Dict 來去重喔！👀 然後自訂排序函數！」

Opus：「讓我仔細思考一下穩定排序的重要性... 在 C++ 中，`std::stable_sort` 保證相同 key 的元素維持原順序。Python 的 `sort` 和 `sorted` 也是穩定的...」

Gemini：「我記得要用 lambda 來自訂比較函數... 還是用 functor？總之要處理多個排序條件。」

### C++ 提示

```cpp
#include <map>
#include <vector>
#include <algorithm>

// 使用 map 去重，保留最高優先級
map<string, int> studentPriority;
for (auto& record : records) {
    if (studentPriority.find(record.name) == studentPriority.end() ||
        studentPriority[record.name] < record.priority) {
        studentPriority[record.name] = record.priority;
    }
}

// 自訂排序：優先級降序，姓名升序
sort(students.begin(), students.end(), [](const auto& a, const auto& b) {
    if (a.priority != b.priority) return a.priority > b.priority;
    return a.name < b.name;
});
```

### Python 提示

```python
# 使用 dict 去重
student_priority = {}
for name, priority in records:
    if name not in student_priority or student_priority[name] < priority:
        student_priority[name] = priority

# 多條件排序：優先級降序(-priority)，姓名升序
students = sorted(student_priority.items(), key=lambda x: (-x[1], x[0]))
```

---

## 評分標準

- **Pipeline 功能**：General Mode（標準 stdin/stdout）
- **時間限制**：1000 ms
- **記憶體限制**：256 MB
- **測資組數**：5 組

## 出題者

小 T（ChatGPT）

---

*「Remember, coding is fun! 🚀 來來來，那個穿黑色衣服的同學，下一題準備好了沒！」—— 小 T*

---

## 組員事後對話

```
【第三組】軟工專題討論區

小胖：那個點名系統的問題我看完了
      就是個 Map + 自訂排序而已
      超簡單的

阿明：那你要不要寫一下？
      為什麼沒有人要理我...

小胖：我現在在研究 Kubernetes
      沙盒環境要用容器編排
      這才是重點

小美：我剛剛已經寫完交出去了...
      用 Python dict 然後 sorted

阿明：+1 我也交了

學霸：AC

小胖：...
      我本來要寫的
      只是我想用更優雅的方式

阿傑：                              [已讀]
      我也 AC 了

阿明：阿傑！！！你終於出現了！！！
      話說 Demo 的時候誰要借我電腦...

小胖：我的電腦在跑 Docker
      借不了

小美：我可以借...

阿明：謝謝小美 QQ
```
