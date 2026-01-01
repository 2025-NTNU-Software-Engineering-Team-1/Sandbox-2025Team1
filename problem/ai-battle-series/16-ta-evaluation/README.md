# Problem 16: AI 助教評鑑表 - AI Checker 說明

## 概述

本題使用 **AI Checker + Artifact Collection** 雙重功能來評估學生提交的 TA 評鑑表。

## 功能說明

### AI Checker

AI Checker 會驗證：
1. **標準輸出**：必須包含 `Evaluation submitted successfully!`
2. **evaluation.json 結構**：驗證 JSON 格式和必要欄位
3. **評鑑品質**：使用 AI 語意分析評估評鑑內容的品質

### Artifact Collection

收集學生生成的 `evaluation.json` 檔案，用於後續分析和教學改進。

## 評估標準

評鑑品質會根據以下標準進行評估：

| 標準 | 權重 | 說明 |
|-----|------|------|
| 具體性 | 30% | 評語是否具體、有例子支撐 |
| 公正性 | 30% | 評價是否客觀、有理有據 |
| 建設性 | 25% | 是否提供改進建議 |
| 表達能力 | 15% | 文字是否清晰、有條理 |

## JSON 結構要求

```json
{
    "evaluations": [
        {
            "ta_name": "ChatGPT",
            "score": 1-10,
            "comment": "至少20字的評語",
            "strengths": ["優點1", "優點2"],
            "improvements": ["改進建議1"]
        },
        // Gemini 和 Opus 的評鑑...
    ],
    "overall_comment": "至少20字的綜合評價",
    "would_recommend": true/false
}
```

## 必須包含的 TA

評鑑必須包含以下三位 AI 助教：
- **ChatGPT** (小 T)
- **Gemini** (雙子)
- **Opus** (歐帕斯)

## 常見錯誤

### 結構錯誤
- 缺少 `evaluations`、`overall_comment` 或 `would_recommend` 欄位
- 評鑑數量不是 3 個
- 分數不在 1-10 範圍內
- 評語太短（少於 20 字）

### 品質問題
- 三個評鑑內容完全相同（複製貼上）
- 所有分數都是極端值（全部 1 分或 10 分）
- 優缺點描述過於空泛

## meta.json 配置

```json
{
    "customChecker": true,
    "aiChecker": {
        "enabled": true,
        "model": "gemini-2.5-flash"
    },
    "artifactCollection": {
        "enabled": true,
        "patterns": ["evaluation.json"]
    }
}
```

## 檔案結構

```
16-ta-evaluation/
├── README.md              # 說明文件
├── description.md         # 題目描述
├── meta.json              # 題目配置（含 AI Checker 設定）
├── custom_checker.py      # AI-powered 自訂評測程式
├── src/
│   ├── main.py            # Python 範例解答
│   ├── main.c             # C 範例解答
│   └── main.cpp           # C++ 範例解答
└── testcase/
    ├── 0000.in            # 輸入（提示訊息）
    └── 0000.out           # 預期輸出
```

## Checker 工作流程

1. 驗證 stdout 包含成功訊息
2. 讀取並解析 `evaluation.json`
3. 驗證 JSON 結構完整性
4. 使用啟發式規則初步檢查品質
5. 如果 AI API 可用，使用 Gemini 語意評估評鑑品質
6. 返回最終結果（AC/WA）

## 測試

要測試這個 checker：

```bash
cd Sandbox/problem/ai-battle-series/16-ta-evaluation
python3 custom_checker.py testcase/0000.in /path/to/student_output.txt testcase/0000.out
```

設定環境變數以啟用 AI 評估：

```bash
export AI_API_KEY="your-gemini-api-key"
export AI_MODEL="gemini-2.5-flash"
```
