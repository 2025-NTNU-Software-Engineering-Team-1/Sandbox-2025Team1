# Problem 3: 成績單解密

## 故事背景

期中考終於結束了。教室裡瀰漫著一股緊張的氣氛——成績要公布了。

「同學們！」小 T 興奮地出現在螢幕上，「成績單已經出來了！🎉」

教室裡一陣騷動。有人興奮，有人緊張，有人已經開始計算自己需要多少分才能及格。

「我已經把成績單放在 `grades.csv` 裡了！」小 T 說，「不過呢... 為了保護大家的隱私，我做了一些處理！來來來，讓我解釋一下！」

Gemini 突然警覺：「等等，這樣學生不就可以看到彼此的成績了嗎？這有隱私問題！GDPR！CCPA！個資法！」

「放心放心，」小 T 揮揮手，「我用學號當 ID，沒有人知道誰是誰~ 而且我還把低於 60 分的都標記成 'NEED_HELP' 了！這樣就沒人知道誰被當了！超級聰明吧！😎」

Opus 嘆氣：「讓我仔細思考一下這個系統的倫理問題... 首先，關於個資保護法的第三條，資料去識別化的標準其實非常嚴格。僅僅用學號替換姓名是否足夠？如果結合其他資訊...」

「不對不對！」Gemini 打斷，「現在不是討論這個的時候！同學們要寫程式！而且我突然不確定剛剛說的法規名稱對不對了...」

小 T：「Exactly! 🎯 Let's focus on the coding part! 綜觀全局，這題就是讀 CSV 檔案！那個坐後排的同學，你來！」

---

## 組員群組訊息

```
【第三組】軟工專題討論區

阿明：期中考大家考得如何？
      為什麼沒有人要理我...

小美：還可以啦～我好像有 80 幾

學霸：92

小胖：哈哈我應該也不差
      這種計概等級的考試對我來說小 case

阿明：那你幾分？

小胖：成績還沒出來啦
      不過應該沒問題
      我考試的時候感覺很好

阿傑：                              [已讀]

阿明：...阿傑你考試有來嗎？
      誰要借我電腦 Demo...

阿傑：有

阿明：！！！

小美：阿傑說話了！

小胖：哇 稀有欸

學霸：分數呢

阿傑：                              [已讀]

阿明：果然只說一個字...

[成績公布後]

小胖：那個...
      成績公布了

阿明：怎麼了？

小胖：我可能需要 help
      那個 NEED_HELP 的標記
      好像有我

小美：...加油！

學霸：還有期末

阿傑：                              [已讀]
      我也
      NEED_HELP

阿明：啊？？？阿傑也是！？

小胖：看來我們需要組成讀書會
      說不定這是命運的安排
      讓我們一起進步！

阿明：所以你們兩個期中考都...？

小胖：就是...有點失常
      而且題目出得太刁鑽了
```

---

## 題目說明

你的程式在執行時，系統會提供一個 `grades.csv` 檔案在當前目錄。這個檔案包含多位學生在多個科目的成績記錄。

你需要找出**同時在所有科目都需要幫助（NEED_HELP）的學生**，並依照學號排序輸出。

### Resource Data 說明

系統會自動將 `grades.csv` 放置在你的程式執行目錄中。你的程式需要：

1. 開啟並讀取 `grades.csv`
2. 解析 CSV 格式的資料
3. 對每個學生統計各科目狀態
4. 找出所有科目都是 NEED_HELP 的學生

### 演算法提示

這是一個**集合交集（Set Intersection）**問題。對於每個科目，找出需要幫助的學生集合，然後求所有集合的交集。

## 輸入格式

```
第一行：整數 K (1 ≤ K ≤ 10)，要查詢的科目數量
接下來 K 行：每行一個科目名稱
```

## 輸出格式

```
第一行：整數 M，同時在所有查詢科目都需要幫助的學生人數
接下來 M 行：學生 ID（按字典序排序）
```

## Resource 檔案格式

`grades.csv` 的格式如下：

```csv
student_id,subject,score,status
S001,Math,85,PASS
S001,English,42,NEED_HELP
S002,Math,42,NEED_HELP
S002,English,38,NEED_HELP
S003,Math,73,PASS
S003,English,91,PASS
```

- 第一行是標題行
- 每位學生可能有多筆記錄（不同科目）
- `status` 欄位只會是 `PASS` 或 `NEED_HELP`

## 範例

**grades.csv 內容：**
```csv
student_id,subject,score,status
S001,Math,85,PASS
S001,English,42,NEED_HELP
S002,Math,42,NEED_HELP
S002,English,38,NEED_HELP
S003,Math,73,PASS
S003,English,65,PASS
S004,Math,55,NEED_HELP
S004,English,48,NEED_HELP
```

**輸入：**
```
2
Math
English
```

**輸出：**
```
2
S002
S004
```

## 範例說明

- S001：Math PASS, English NEED_HELP → 不符合（Math 沒有 NEED_HELP）
- S002：Math NEED_HELP, English NEED_HELP → 符合！
- S003：Math PASS, English PASS → 不符合
- S004：Math NEED_HELP, English NEED_HELP → 符合！

## 提示

小 T：「來來來！這題要用 Set 來做集合運算！📂 先建立每個科目的 NEED_HELP 學生集合，然後求交集！」

Opus：「讓我仔細思考一下集合交集的實作... 可以用 `std::set_intersection` 或 Python 的 `set.intersection()`。時間複雜度是 O(n log n)...」

Gemini：「我記得 Python 的 set 可以直接用 `&` 運算子... 還是用 `intersection()` 方法？應該都可以吧？」

小 T：「Pro tip 💡：用 Dict + Set 來組織資料！綜觀全局，這是資料處理的基本功！」

### 集合交集範例程式碼

```python
# 建立每個科目的 NEED_HELP 學生集合
subject_sets = {}
for row in data:
    if row['status'] == 'NEED_HELP':
        subject = row['subject']
        if subject not in subject_sets:
            subject_sets[subject] = set()
        subject_sets[subject].add(row['student_id'])

# 求所有查詢科目的交集
result = subject_sets[query_subjects[0]]
for subj in query_subjects[1:]:
    result = result & subject_sets.get(subj, set())

# 排序輸出
for student in sorted(result):
    print(student)
```

### C++ 範例讀檔方式

```cpp
#include <fstream>
#include <sstream>
#include <string>

ifstream file("grades.csv");
string line;
getline(file, line);  // 跳過標題行

while (getline(file, line)) {
    // 解析每一行...
}
```

### Python 範例讀檔方式

```python
import csv

with open('grades.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # row['status'] 就是狀態欄位
        pass
```

---

## 評分標準

- **Pipeline 功能**：Resource Data（CSV 檔案）
- **時間限制**：1000 ms
- **記憶體限制**：256 MB
- **測資組數**：4 組

## Resource Data 機制說明

本題使用 **Resource Data** 功能，系統會在執行你的程式前，自動將測資對應的 CSV 檔案放置在工作目錄中。

這模擬了真實世界中程式需要讀取外部資料檔案的情境，例如：
- 讀取設定檔
- 解析日誌檔案
- 處理批次資料

## 出題者

小 T（ChatGPT）

---

*「Data is the new oil! 🛢️ But first, you need to learn how to extract it! 來來來，開始挖！」—— 小 T*

---

## 組員事後對話

```
【第三組】軟工專題討論區

[深夜 11:47]

小胖：欸大家
      這題要怎麼讀 CSV 啊

小美：Python 的話可以用 csv 模組
      很簡單喔

小胖：喔喔好
      不過我想用更進階的方式
      pandas 怎麼樣

學霸：題目不需要 pandas
      csv.DictReader 就夠

小胖：我知道啦
      只是想說練習一下
      畢竟我們資工系的要有深度

阿明：...作業明天交，不要搞複雜

小胖：好啦好啦

[凌晨 2:34]

小胖：欸
      pandas 好像不能用
      它說 no module named pandas

阿明：...直接用 csv 模組
      不要再搞了

小胖：好
      對了阿傑
      你的作業寫完了嗎

阿傑：                              [已讀]

小胖：...果然

阿明：阿傑你明天記得交作業啊
      不要又消失
```
