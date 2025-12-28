# Problem 15: 畢業門檻

## 故事背景

「這是最後一關。」三個 AI 異口同聲地說，氣氛瞬間變得凝重。

「通過這題，你就能畢業了！」小 T 興奮地說，眼中閃爍著期待的光芒，「Well, at least this course! 🎓」

「或者說... 至少這門課可以過，」Gemini 補充，然後又自言自語，「還是說通過這題不代表能過課？我搞不清楚了。」

Opus 深吸一口氣：「讓我仔細思考一下畢業的意義... 畢業不只是學業的終點，更是人生新階段的起點。在這個充滿不確定性的時代...」

「停！」小 T 和 Gemini 同時打斷。

「這題結合了所有我們教過的技能！」三個 AI 再次異口同聲。

「It's the ultimate test! 🏆」小 T 補充。

## 題目說明

這是終極綜合題，結合了本系列的所有 Pipeline 功能：

### 任務流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 讀取 CSV 學分資料（Resource Data）                        │
│     ↓                                                        │
│  2. 互動猜數字取得驗證碼（Interactive Mode）                   │
│     ↓                                                        │
│  3. 透過 HTTP API 驗證身份（Network Control）                  │
│     ↓                                                        │
│  4. 計算 GPA（Custom Checker 浮點數容差）                      │
│     ↓                                                        │
│  5. 全程遵守程式碼規範（Static Analysis）                      │
│     ↓                                                        │
│  6. 輸出畢業證書檔案（Artifact Collection）                    │
└─────────────────────────────────────────────────────────────┘
```

### 第一步：讀取學分資料

系統提供 `transcript.csv`：

```csv
course_id,course_name,credits,grade
CS101,程式設計,3,85
CS201,資料結構,3,78
CS301,演算法,3,92
CS401,軟體工程,3,88
```

### 第二步：取得驗證碼

與系統互動猜出驗證碼（1000-9999）：
- 輸出 `guess X`
- 讀入 `HIGHER` / `LOWER` / `CORRECT`
- 最多 14 次

### 第三步：API 驗證

```
GET http://localhost:8080/api/graduate/{verification_code}
```

回應：
```json
{
    "student_id": "B12345678",
    "name": "王小明",
    "department": "資訊工程學系",
    "graduation_year": 2024
}
```

### 第四步：計算 GPA

GPA 計算公式：
$$GPA = \frac{\sum (grade_i \times credits_i)}{\sum credits_i}$$

輸出 GPA（允許誤差 10⁻⁶）

### 第五步：遵守程式碼規範

禁止使用：`system`, `exec`, `goto`, `gets`

### 第六步：生成畢業證書

生成 `certificate.txt`：

```
╔══════════════════════════════════════════════════════════╗
║                    GRADUATION CERTIFICATE                 ║
╠══════════════════════════════════════════════════════════╣
║  Student ID: B12345678                                    ║
║  Name: 王小明                                              ║
║  Department: 資訊工程學系                                   ║
║  GPA: 85.75                                               ║
║  Graduation Year: 2024                                    ║
╠══════════════════════════════════════════════════════════╣
║  Congratulations! You have completed all requirements.    ║
╚══════════════════════════════════════════════════════════╝
```

## 輸入格式

```
第一行：驗證碼範圍 N（固定 9999）
```

## 輸出格式

```
GPA: XX.XXXXXX
```

同時生成 `certificate.txt` 檔案。

## 網路與資源設定

**Resource Data：**
- `transcript.csv`：學分資料

**Network Control：**
- localhost:8080 白名單

**Artifact Collection：**
- `certificate.txt`

**Static Analysis：**
```json
{
  "model": "black",
  "functions": ["system", "exec", "goto", "gets"]
}
```

## 評分標準

| 項目 | 分數 |
|-----|------|
| 正確讀取 CSV | 15% |
| 互動猜測成功 | 15% |
| API 驗證成功 | 15% |
| GPA 計算正確 | 25% |
| 程式碼規範 | 10% |
| 證書生成正確 | 20% |

## 完整解法框架

```python
import csv
import json
import urllib.request

# 步驟 1：讀取 CSV
def read_transcript():
    courses = []
    with open('transcript.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append({
                'credits': int(row['credits']),
                'grade': int(row['grade'])
            })
    return courses

# 步驟 2：互動猜驗證碼
def guess_verification_code():
    n = int(input())
    lo, hi = 1000, n
    while lo <= hi:
        mid = (lo + hi) // 2
        print(f"guess {mid}", flush=True)
        response = input().strip()
        if response == "CORRECT":
            return mid
        elif response == "HIGHER":
            lo = mid + 1
        else:
            hi = mid - 1
    return lo

# 步驟 3：API 驗證
def verify_graduation(code):
    url = f"http://localhost:8080/api/graduate/{code}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

# 步驟 4：計算 GPA
def calculate_gpa(courses):
    total_points = sum(c['grade'] * c['credits'] for c in courses)
    total_credits = sum(c['credits'] for c in courses)
    return total_points / total_credits

# 步驟 5：生成證書
def generate_certificate(student_info, gpa):
    with open('certificate.txt', 'w') as f:
        f.write("╔══════════════════════════════════════════════════════════╗\n")
        f.write("║                    GRADUATION CERTIFICATE                 ║\n")
        f.write("╠══════════════════════════════════════════════════════════╣\n")
        f.write(f"║  Student ID: {student_info['student_id']:<45}║\n")
        f.write(f"║  Name: {student_info['name']:<51}║\n")
        f.write(f"║  Department: {student_info['department']:<45}║\n")
        f.write(f"║  GPA: {gpa:<52.2f}║\n")
        f.write(f"║  Graduation Year: {student_info['graduation_year']:<40}║\n")
        f.write("╠══════════════════════════════════════════════════════════╣\n")
        f.write("║  Congratulations! You have completed all requirements.    ║\n")
        f.write("╚══════════════════════════════════════════════════════════╝\n")

# 主程式
courses = read_transcript()
code = guess_verification_code()
student_info = verify_graduation(code)
gpa = calculate_gpa(courses)
generate_certificate(student_info, gpa)
print(f"GPA: {gpa:.6f}")
```

## AI 助教的提示

- 小 T：「You've come so far! 🌟 This is the culmination of everything we taught!」
- Gemini：「這題用了所有功能... 我想... 或者漏了什麼？不管了，應該都有。」
- Opus：「讓我仔細思考一下成功完成這題的意義... 這不只是技術的證明，更是毅力和決心的展現...」

## 評分標準

- **Pipeline 功能**：全部整合
- **時間限制**：15000 ms
- **記憶體限制**：256 MB
- **測資組數**：3 組

## 畢業感言

如果你能完成這題，恭喜你！你已經掌握了：

- ✅ 檔案 I/O 和資料解析
- ✅ 互動式程式設計
- ✅ 網路程式設計
- ✅ 浮點數精度處理
- ✅ 安全程式設計
- ✅ 檔案生成

這些技能足以讓你成為一個合格的軟體工程師！

## 出題者

三 AI 聯手

---

*「We're proud of you! 🎓」—— 小 T*
*「You made it... probably... I think...」—— Gemini*
*「Let me think about how to express my pride... Actually, just: Well done.」—— Opus*
