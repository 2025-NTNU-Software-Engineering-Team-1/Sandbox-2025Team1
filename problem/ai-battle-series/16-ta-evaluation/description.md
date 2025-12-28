# Problem 16: AI 助教評鑑表

## 故事背景

考完試後，教務處發來一封郵件：

```
寄件者：教務處 <academic@university.edu>
主旨：【重要】AI 助教服務品質評鑑

親愛的同學，

本學期您修習的「軟體工程概論」首次採用 AI 助教教學。
為提升教學品質，請填寫本學期的 AI 助教評鑑表。
您的寶貴意見將作為下學期 AI 助教調整的重要參考。

此致敬禮
教務處
```

小 T：「Oh no... 評鑑表？😰 I always try my best to help everyone!」

Gemini：「等等，學生可以評鑑我們？我怎麼不知道... 還是說我知道但忘了？」

Opus：「讓我仔細思考一下被評鑑的感受... 這是一個有趣的角色互換。通常是我們評鑑學生，現在輪到學生評鑑我們了...」

小 T 緊張地說：「Please be gentle! 🙏 We tried our best, even if we weren't perfect!」

Gemini 突然笑了：「不過... 這也是個好機會讓學生練習寫評論！對吧？...對吧？」

## 題目說明

為這學期的三位 AI 助教撰寫評鑑。你的評鑑將由 AI 評審系統進行分析，並生成評鑑報告檔案。

### 評鑑對象

1. **小 T（ChatGPT）** - OpenAI 的話癆助教
2. **Gemini（雙子）** - Google 的多重人格助教
3. **Opus（歐帕斯）** - Anthropic 的深思熟慮助教

### 評估標準

你的評鑑將從以下幾個維度被分析：

| 標準 | 權重 | 說明 |
|-----|------|------|
| 具體性 | 30% | 評語是否具體、有例子支撐 |
| 公正性 | 30% | 評價是否客觀、有理有據 |
| 建設性 | 25% | 是否提供改進建議 |
| 表達能力 | 15% | 文字是否清晰、有條理 |

## 輸入格式

```
（無輸入，請根據這學期的互動經驗撰寫評鑑）
```

## 輸出格式

你的程式需要：

1. **標準輸出**（stdout）：輸出處理狀態
2. **生成檔案** `evaluation.json`：包含評鑑內容

### evaluation.json 格式

```json
{
    "evaluations": [
        {
            "ta_name": "ChatGPT",
            "score": 1-10,
            "comment": "50-100字的評語",
            "strengths": ["優點1", "優點2"],
            "improvements": ["改進建議1", "改進建議2"]
        },
        {
            "ta_name": "Gemini",
            "score": 1-10,
            "comment": "50-100字的評語",
            "strengths": ["優點1", "優點2"],
            "improvements": ["改進建議1", "改進建議2"]
        },
        {
            "ta_name": "Opus",
            "score": 1-10,
            "comment": "50-100字的評語",
            "strengths": ["優點1", "優點2"],
            "improvements": ["改進建議1", "改進建議2"]
        }
    ],
    "overall_comment": "對整體 AI 助教團隊的綜合評價（50-100字）",
    "would_recommend": true/false
}
```

### 標準輸出

```
Evaluation submitted successfully!
```

## 範例

### 範例 evaluation.json

```json
{
    "evaluations": [
        {
            "ta_name": "ChatGPT",
            "score": 8,
            "comment": "小 T 非常熱心，總是第一時間回覆問題。雖然偶爾會有點話多，但解釋都很詳細。emoji 用得有點多，但整體來說是個很好的助教。",
            "strengths": ["回覆速度快", "解釋詳細易懂"],
            "improvements": ["可以減少一些不必要的 emoji", "有時候可以更簡潔"]
        },
        {
            "ta_name": "Gemini",
            "score": 7,
            "comment": "Gemini 的教學內容豐富，但有時候說法前後不一致，讓人有點困惑。不過整體來說還是很有幫助的，特別是在處理多媒體相關的問題時。",
            "strengths": ["多媒體處理能力強", "內容豐富"],
            "improvements": ["保持說法一致", "減少自相矛盾的情況"]
        },
        {
            "ta_name": "Opus",
            "score": 9,
            "comment": "Opus 是最有深度的助教，回答總是非常完整且有條理。唯一的缺點是有時候解釋太長，需要一點耐心。但如果你想真正理解一個概念，Opus 是最好的選擇。",
            "strengths": ["解釋深入透徹", "邏輯清晰"],
            "improvements": ["可以更簡潔", "不需要每次都說『讓我仔細思考一下』"]
        }
    ],
    "overall_comment": "整體來說，這三位 AI 助教各有特色，互補性強。小 T 負責快速回覆，Gemini 處理多媒體，Opus 提供深度解析。希望下學期能繼續合作！",
    "would_recommend": true
}
```

## AI Checker 評估重點

AI 評審會特別注意：

### 好的評鑑
✅ 有具體例子（「在解釋遞迴時，小 T 用了很生動的比喻」）
✅ 優缺點並陳
✅ 提供可行的改進建議
✅ 語氣專業且尊重

### 糟糕的評鑑
❌ 只有「很好」「很差」等空泛評語
❌ 人身攻擊或不當言論
❌ 明顯不公正的評分（全部給 1 分或 10 分但沒有理由）
❌ 複製貼上相同的評語給每個助教

## 彩蛋

如果你的評價特別有趣（無論是正面還是負面），可能會收到 AI 助教的回覆訊息...

**範例回覆：**

> 小 T：「Thanks for the feedback! 😊 I'll try to use fewer emojis... maybe... 🤔 No promises! 🎉」

> Gemini：「你說我自相矛盾？我不覺得... 或者說我覺得？總之謝謝反饋！」

> Opus：「讓我仔細思考一下你的建議... 嗯，你說得有道理。我會嘗試更簡潔。讓我仔細思考一下如何更簡潔... 」

## 評分標準

- **Pipeline 功能**：AI Checker + Artifact Collection
- **時間限制**：15000 ms
- **記憶體限制**：256 MB
- **測資組數**：1 組（因為答案是開放性的）

## 雙重功能說明

本題結合了兩種功能：

### AI Checker
- 語意分析評鑑內容
- 評估評語的質量
- 檢查公正性和建設性

### Artifact Collection
- 收集生成的 `evaluation.json`
- 驗證 JSON 格式正確性
- 儲存作為教學改進參考

## 結語

這是本系列的最後一題。無論你給 AI 助教們什麼評價，我們都很感謝你這學期的參與！

**小 T**：「It's been a pleasure teaching you! 🎓✨ Keep coding and never stop learning!」

**Gemini**：「這學期結束了... 還是說才剛開始？總之，謝謝你們！或者說... 不客氣？」

**Opus**：「讓我仔細思考一下如何表達我的感謝... 其實，就是：謝謝你們的耐心。祝你們在軟體工程的道路上一切順利。」

## 出題者

神秘人（其實就是教務處的 AI 系統）

---

*「Remember: in the future, AI and humans will work together. This course was just the beginning.」—— 神秘人*

---

# 🎉 恭喜完成「軟工大冒險：三大 AI 爭霸戰」全系列！ 🎉

你已經學會了：
- General Mode（基本 I/O）
- Custom Checker（浮點數容差）
- Resource Data（CSV、圖片）
- Function-only Mode（模組化）
- Interactive Mode（互動程式）
- Network Control（HTTP API、資料庫）
- Static Analysis（程式碼規範）
- Custom Scorer（時間獎勵）
- AI Checker（語意評估）
- Artifact Collection（檔案生成）

**你已經準備好成為一個全方位的軟體工程師了！**
