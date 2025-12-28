# Problem 6: 偷看答案的藝術

## 故事背景

期中考前一天深夜，你收到一封神秘郵件。寄件者顯示為 `anonymous@novatech.edu`。

「有人知道這封信是誰寄的嗎？」阿明在群組裡問。

「聽說教授把期中考答案放在一個『內部測試伺服器』上...」Gemini 壓低聲音說，眼神閃爍著神秘的光芒。

「什麼？！考試作弊？這不道德！」Opus 震驚地站了起來，「讓我仔細思考一下這件事的倫理影響... 根據學術誠信的基本原則...」

「不不不，這是『資安演練』！」Gemini 狡辯，露出狡黠的笑容，「我們在測試學校系統的安全性！完全合法！教授授權的！」

小 T 搓著手：「I mean... 從 educational 的角度來說，這確實可以教會學生如何使用 HTTP APIs... 🤔 這是 valuable real-world skills！來來來，綜觀全局，那個穿格子衫的同學，你用過 API 嗎？」

「沒錯！」Gemini 說，「但是！答案被分散存放在多個 API 端點裡！你需要查詢多個分頁，然後把答案合併排序！」

Opus 仍然不放心：「但是從倫理的角度來看...」

「這是作業！」Gemini 打斷，「寫不出來就零分！」

Opus 嘆氣：「好吧，讓我仔細思考一下 HTTP 協議和合併排序的運作原理... 雖然我對這個任務的道德性仍有疑慮...」

---

## 組員群組訊息

```
【第三組】軟工專題討論區

[深夜 11:23]

阿明：有人收到那封神秘郵件嗎？

小美：有！
      我正在研究怎麼用 Python 呼叫 API

小胖：HTTP API 太簡單了
      我之前做過很多 RESTful 專案
      這種東西對我來說就是小菜一碟

阿明：那你可以教一下嗎？
      我不太會用 curl

小胖：很簡單啦
      就是 GET POST PUT DELETE
      CRUD 操作懂嗎
      這是後端工程師的基本功

阿明：可是阿傑才是我們的後端工程師...
      阿傑你在嗎？

阿傑：                              [已讀]

小美：阿傑你會用 API 嗎？

阿傑：會

阿明：可以教我們嗎？

阿傑：                              [已讀]
      urllib

小美：urllib？
      就是 Python 內建的那個？

阿傑：對

小胖：我覺得應該用 requests
      比較專業
      urllib 太老派了

學霸：題目環境不一定有 requests
      而且這題要合併排序

小胖：合併排序？不是查 API 就好嗎

學霸：答案分散在多個分頁
      要自己 merge

小胖：噢...
      那也不難啊
      merge sort 我大一就會了

阿明：所以到底怎麼做...

學霸：（貼了一段程式碼）

小美：學霸果然可靠！

小胖：這個我本來也要貼的
      只是學霸手速比較快

阿傑：                              [離線]

阿明：阿傑你又消失了？？
```

---

## 題目說明

本題測試你使用 **HTTP API** 和 **合併排序** 的能力。答案被分散存放在多個 API 分頁中，每個分頁返回部分已排序的資料。你需要：

1. 查詢所有分頁的 API
2. 將多個已排序的結果**合併排序**成一個完整的有序序列
3. 輸出最終排序結果

### API 端點

```
GET http://localhost:8080/api/answers?page={page_number}
```

**回應格式（JSON）：**
```json
{
  "page": 1,
  "total_pages": 5,
  "data": [
    {"id": 3, "score": 85},
    {"id": 7, "score": 90},
    {"id": 12, "score": 95}
  ]
}
```

**重要特性：**
- 每個分頁的 `data` 已按 `score` **升序**排列
- 不同分頁之間的資料範圍可能重疊
- `total_pages` 表示總共有多少分頁

### 你的任務

1. 從 `page=1` 開始查詢，得知 `total_pages`
2. 查詢所有分頁（1 到 total_pages）
3. 將所有分頁的資料**合併排序**（按 score 升序）
4. 輸出所有學生的 id（按 score 排序後的順序）

### 網路設定

本題使用 **Network Control** 功能：
- 白名單模式（Whitelist）
- 僅允許連接 `127.0.0.1:8080`
- 其他所有網路連線都會被阻擋

## 輸入格式

```
（無輸入，直接查詢 API）
```

## 輸出格式

```
第一行：整數 N，總資料筆數
接下來 N 行：每行一個學生 ID，按 score 由小到大排序
如果 score 相同，按 ID 由小到大排序
```

## 範例

假設 API 回應如下：

**Page 1：**
```json
{"page": 1, "total_pages": 3, "data": [{"id": 5, "score": 70}, {"id": 2, "score": 85}]}
```

**Page 2：**
```json
{"page": 2, "total_pages": 3, "data": [{"id": 8, "score": 75}, {"id": 3, "score": 90}]}
```

**Page 3：**
```json
{"page": 3, "total_pages": 3, "data": [{"id": 1, "score": 80}, {"id": 6, "score": 80}]}
```

**輸出：**
```
6
5
8
1
6
2
3
```

**說明：**
- 70: id=5
- 75: id=8
- 80: id=1, id=6（同分按 ID 排序）
- 85: id=2
- 90: id=3

## 演算法要求

### K-way Merge（K 路合併）

當你有 K 個已排序的陣列時，最有效率的合併方式是使用 **K-way Merge**：

1. 使用 **Min Heap（最小堆）** 來維護每個陣列的當前最小元素
2. 每次從堆中取出最小的元素
3. 將該元素所屬陣列的下一個元素放入堆中
4. 重複直到所有元素處理完畢

**時間複雜度：** O(N log K)，其中 N 是總元素數，K 是分頁數

### 為什麼不能簡單排序？

雖然把所有資料收集起來再排序也能得到正確答案，但：
- 時間複雜度是 O(N log N)
- 沒有利用「每個分頁已排序」的特性
- 本題會用**時間限制**來區分這兩種解法

## 提示

### Python 使用 heapq 實作 K-way Merge

```python
import urllib.request
import json
import heapq

def fetch_page(page):
    url = f"http://localhost:8080/api/answers?page={page}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def k_way_merge(sorted_lists):
    """
    合併 K 個已排序的列表
    每個元素是 (score, id) 的 tuple
    """
    result = []
    # heap 元素: (score, id, list_index, element_index)
    heap = []

    # 初始化：每個列表的第一個元素放入 heap
    for i, lst in enumerate(sorted_lists):
        if lst:
            score, sid = lst[0]
            heapq.heappush(heap, (score, sid, i, 0))

    while heap:
        score, sid, list_idx, elem_idx = heapq.heappop(heap)
        result.append(sid)

        # 將該列表的下一個元素放入 heap
        next_idx = elem_idx + 1
        if next_idx < len(sorted_lists[list_idx]):
            next_score, next_id = sorted_lists[list_idx][next_idx]
            heapq.heappush(heap, (next_score, next_id, list_idx, next_idx))

    return result

# 主程式
first_page = fetch_page(1)
total_pages = first_page['total_pages']

# 收集所有分頁資料
all_sorted_lists = []
for page in range(1, total_pages + 1):
    if page == 1:
        data = first_page['data']
    else:
        data = fetch_page(page)['data']
    # 轉換為 (score, id) 列表
    sorted_list = [(item['score'], item['id']) for item in data]
    all_sorted_lists.append(sorted_list)

# K-way merge
result = k_way_merge(all_sorted_lists)

print(len(result))
for sid in result:
    print(sid)
```

### C++ 使用 priority_queue

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <curl/curl.h>
#include <json/json.h>  // or use your preferred JSON library

struct Element {
    int score, id, list_idx, elem_idx;
    bool operator>(const Element& other) const {
        if (score != other.score) return score > other.score;
        return id > other.id;
    }
};

vector<int> k_way_merge(vector<vector<pair<int,int>>>& lists) {
    vector<int> result;
    priority_queue<Element, vector<Element>, greater<Element>> pq;

    // 初始化
    for (int i = 0; i < lists.size(); i++) {
        if (!lists[i].empty()) {
            pq.push({lists[i][0].first, lists[i][0].second, i, 0});
        }
    }

    while (!pq.empty()) {
        Element curr = pq.top();
        pq.pop();
        result.push_back(curr.id);

        int next_idx = curr.elem_idx + 1;
        if (next_idx < lists[curr.list_idx].size()) {
            auto& next = lists[curr.list_idx][next_idx];
            pq.push({next.first, next.second, curr.list_idx, next_idx});
        }
    }

    return result;
}
```

## AI 助教的提示

- Gemini：「記住，這只是『資安演練』喔... K-way merge 很重要！或者說 heap？總之用 heap 來 merge！」
- 小 T：「HTTP GET + K-way merge! 🚀 This is like merging sorted streams! 來來來，那個後排的同學，你知道什麼是 min heap 嗎？」
- Opus：「讓我仔細思考一下 K-way merge 的時間複雜度... 使用最小堆，每次操作是 O(log K)，總共 N 個元素，所以是 O(N log K)，優於直接排序的 O(N log N)...」

## 評分標準

- **Pipeline 功能**：Network Control（HTTP API）
- **時間限制**：3000 ms
- **記憶體限制**：64 MB
- **測資組數**：5 組

**注意**：測資設計會讓簡單的「收集全部再排序」解法超時，你需要使用 K-way merge 才能通過。

## Network Control 說明

本題使用 **Network Control** 功能模擬受限的網路環境：

1. **白名單模式**：只有指定的 IP 和 Port 可以連線
2. **本地服務**：系統會在 localhost:8080 運行一個 HTTP 服務
3. **沙盒隔離**：你的程式無法連接到外部網路

這模擬了真實世界中的：
- 企業內網環境
- 分散式系統的資料整合
- 微服務架構中的資料聚合

## 出題者

Gemini（雙子）

---

*「Is this ethical? Let me think... Actually, it's fine. Or is it? I'm not sure anymore. Anyway, K-way merge is definitely ethical!」—— Gemini*

---

## 組員事後對話

```
【第三組】軟工專題討論區

[作業交完後]

阿明：大家 API 那題做完了嗎？

小美：做完了！
      K-way merge 真的比較快
      我本來想直接排序結果超時了

小胖：我一開始就用 heap
      這是基本功
      大一資料結構就教過了

阿明：可是你昨天還在問什麼是 K-way merge...

小胖：那是確認一下
      怕我記錯
      高手也是要 double check 的

學霸：heap 要注意 tie-breaking

小胖：這個我當然知道
      同分要比 ID

小美：...那你為什麼 WA 了三次

小胖：測資有問題
      後來修正了

學霸：測資沒改過

小胖：...那可能是我看錯了

阿傑：                              [已讀]

阿明：阿傑你呢？

阿傑：AC
      一次過

阿明：哇！怎麼做到的？

阿傑：看題目

小胖：...

小美：阿傑簡潔有力

阿明：好吧下一題是禁術題
      大家小心不要用 system()

小胖：那太簡單了
      正常人誰會用 system()

阿明：...你上次不是用 system("pause") 嗎

小胖：那是 Windows 環境的問題
      不是我的問題
```
