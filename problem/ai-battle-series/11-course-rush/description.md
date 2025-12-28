# Problem 11: 搶註課程大戰

## 故事背景

> 小 T：「Alright everyone! 🎉 期末考要到了！」
> Gemini：「這次我們三個要聯手出題... 等等，是聯手還是各出各的？」
> Opus：「讓我仔細思考一下合作的本質...」
> 小 T：「Whatever! Let's just make it challenging AND fun! 🚀」
> —— 期末考前會議

「搶課系統開放了！」小 T 大喊，聲音中充滿興奮。

每年這個時候，選課系統都會被擠爆。新學期的熱門課程「進階機器學習」只有 30 個名額，但有 300 個人想修。

「系統後端用的是 PostgreSQL，」Gemini 說，眼神飄忽，「這次的題目需要處理多個資料表！JOIN 操作是必須的！」

「或者說我覺得是這樣？」Gemini 抓了抓頭，「可能是 JOIN，也可能是子查詢。你們自己確認一下。」

Opus 站出來解釋：「讓我仔細說明一下這題的架構。你需要連接到 PostgreSQL 資料庫，進行多表 JOIN，計算每門課的熱門程度，並找出符合條件的課程。」

小 T 補充：「Think of it as a real-world scenario! 🎯 Every software engineer needs to know SQL! 來來來，那個穿格子衫的同學，你會寫 JOIN 嗎？」

## 題目說明

本題使用 **Sidecar 資料庫服務**。系統會在本地運行一個 PostgreSQL 資料庫，你需要：

1. 連接到資料庫
2. 進行**多表 JOIN** 操作
3. 計算每門課的**熱門指數**（報名人數 / 課程容量 × 100）
4. 找出符合條件的課程並排序輸出

### 資料庫連線資訊

```
Host: db              ← 使用 sidecar 名稱作為 hostname
Port: 5432
Database: course_system
User: student
Password: password123
```

**注意**：在 Sidecar 環境中，需使用 sidecar 的 **name** 作為 hostname（例如 `db`），而非 `localhost`。

### 資料表結構

```sql
-- 課程表
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    professor_id INT NOT NULL,
    capacity INT NOT NULL,
    department_id INT NOT NULL
);

-- 教授表
CREATE TABLE professors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    title VARCHAR(20) NOT NULL  -- '教授', '副教授', '助理教授'
);

-- 科系表
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(10) NOT NULL
);

-- 選課紀錄表
CREATE TABLE enrollments (
    id SERIAL PRIMARY KEY,
    course_id INT NOT NULL,
    student_id VARCHAR(20) NOT NULL,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 範例資料

**courses:**
| id | name | professor_id | capacity | department_id |
|----|------|--------------|----------|---------------|
| 1 | 進階機器學習 | 1 | 30 | 1 |
| 2 | 資料結構 | 2 | 50 | 1 |
| 3 | 計算機組織 | 3 | 40 | 1 |
| 4 | 微積分 | 4 | 60 | 2 |

**professors:**
| id | name | title |
|----|------|-------|
| 1 | 陳教授 | 教授 |
| 2 | 王教授 | 副教授 |
| 3 | 李教授 | 助理教授 |
| 4 | 張教授 | 教授 |

**departments:**
| id | name | code |
|----|------|------|
| 1 | 資訊工程學系 | CS |
| 2 | 數學系 | MATH |

**enrollments:**
| id | course_id | student_id |
|----|-----------|------------|
| 1 | 1 | S001 |
| 2 | 1 | S002 |
| ... | ... | ... |
（假設課程 1 有 28 人報名，課程 2 有 45 人報名...）

## 輸入格式

```
第一行：科系代碼（例如 CS）
第二行：最低熱門指數門檻（整數，0-100）
```

## 輸出格式

```
對於符合條件的課程（指定科系且熱門指數 >= 門檻），輸出：
{課程名稱} by {教授名稱} ({教授職稱}) - {熱門指數:.1f}% ({報名人數}/{容量})

按熱門指數由高到低排序
如果熱門指數相同，按課程名稱字典序排序
如果沒有符合條件的課程，輸出：No matching courses
```

## 範例

**輸入：**
```
CS
80
```

**輸出：**
```
進階機器學習 by 陳教授 (教授) - 93.3% (28/30)
資料結構 by 王教授 (副教授) - 90.0% (45/50)
```

**說明：**
- 只顯示資工系（CS）的課程
- 只顯示熱門指數 >= 80% 的課程
- 計算機組織假設報名人數較少，熱門指數 < 80%，所以不顯示

## SQL 查詢提示

### 需要的 JOIN 操作

```sql
SELECT
    c.name AS course_name,
    p.name AS professor_name,
    p.title AS professor_title,
    c.capacity,
    COUNT(e.id) AS enrolled_count,
    (COUNT(e.id) * 100.0 / c.capacity) AS popularity
FROM courses c
JOIN professors p ON c.professor_id = p.id
JOIN departments d ON c.department_id = d.id
LEFT JOIN enrollments e ON c.id = e.course_id
WHERE d.code = %s
GROUP BY c.id, c.name, p.name, p.title, c.capacity
HAVING (COUNT(e.id) * 100.0 / c.capacity) >= %s
ORDER BY popularity DESC, c.name ASC;
```

### 關鍵 SQL 概念

1. **多表 JOIN**：連接 courses、professors、departments、enrollments
2. **LEFT JOIN**：某些課程可能沒有人報名
3. **GROUP BY + COUNT**：計算每門課的報名人數
4. **HAVING**：過濾聚合結果
5. **計算欄位**：熱門指數 = 報名人數 / 容量 × 100

## 提示

### Python 連接 PostgreSQL

```python
import psycopg2

# 建立連線（使用 sidecar 名稱 "db" 作為 host）
conn = psycopg2.connect(
    host="db",
    port=5432,
    database="course_system",
    user="student",
    password="password123"
)

cur = conn.cursor()

# 讀取輸入
department_code = input().strip()
min_popularity = int(input().strip())

# 執行查詢
query = """
    SELECT
        c.name,
        p.name,
        p.title,
        c.capacity,
        COUNT(e.id) AS enrolled,
        (COUNT(e.id) * 100.0 / c.capacity) AS popularity
    FROM courses c
    JOIN professors p ON c.professor_id = p.id
    JOIN departments d ON c.department_id = d.id
    LEFT JOIN enrollments e ON c.id = e.course_id
    WHERE d.code = %s
    GROUP BY c.id, c.name, p.name, p.title, c.capacity
    HAVING (COUNT(e.id) * 100.0 / c.capacity) >= %s
    ORDER BY popularity DESC, c.name ASC
"""

cur.execute(query, (department_code, min_popularity))
rows = cur.fetchall()

if not rows:
    print("No matching courses")
else:
    for row in rows:
        course_name, prof_name, prof_title, capacity, enrolled, popularity = row
        print(f"{course_name} by {prof_name} ({prof_title}) - {popularity:.1f}% ({enrolled}/{capacity})")

cur.close()
conn.close()
```

### C++ 使用 libpq

```cpp
#include <iostream>
#include <iomanip>
#include <libpq-fe.h>
#include <string>

int main() {
    std::string dept_code, min_pop_str;
    std::getline(std::cin, dept_code);
    std::getline(std::cin, min_pop_str);

    // 使用 sidecar 名稱 "db" 作為 host
    const char* conninfo = "host=db port=5432 dbname=course_system user=student password=password123";
    PGconn* conn = PQconnectdb(conninfo);

    if (PQstatus(conn) != CONNECTION_OK) {
        std::cerr << "Connection failed: " << PQerrorMessage(conn) << std::endl;
        PQfinish(conn);
        return 1;
    }

    std::string query = R"(
        SELECT c.name, p.name, p.title, c.capacity,
               COUNT(e.id), (COUNT(e.id) * 100.0 / c.capacity)
        FROM courses c
        JOIN professors p ON c.professor_id = p.id
        JOIN departments d ON c.department_id = d.id
        LEFT JOIN enrollments e ON c.id = e.course_id
        WHERE d.code = $1
        GROUP BY c.id, c.name, p.name, p.title, c.capacity
        HAVING (COUNT(e.id) * 100.0 / c.capacity) >= $2
        ORDER BY 6 DESC, c.name ASC
    )";

    const char* params[2] = {dept_code.c_str(), min_pop_str.c_str()};
    PGresult* res = PQexecParams(conn, query.c_str(), 2, nullptr, params, nullptr, nullptr, 0);

    int rows = PQntuples(res);
    if (rows == 0) {
        std::cout << "No matching courses" << std::endl;
    } else {
        for (int i = 0; i < rows; i++) {
            std::string course = PQgetvalue(res, i, 0);
            std::string prof = PQgetvalue(res, i, 1);
            std::string title = PQgetvalue(res, i, 2);
            int capacity = std::stoi(PQgetvalue(res, i, 3));
            int enrolled = std::stoi(PQgetvalue(res, i, 4));
            double popularity = std::stod(PQgetvalue(res, i, 5));

            std::cout << course << " by " << prof << " (" << title << ") - "
                      << std::fixed << std::setprecision(1) << popularity << "% ("
                      << enrolled << "/" << capacity << ")" << std::endl;
        }
    }

    PQclear(res);
    PQfinish(conn);
    return 0;
}
```

## AI 助教的提示

- 小 T：「SQL JOINs are super powerful! 💪 Remember: INNER JOIN, LEFT JOIN, RIGHT JOIN!」
- Gemini：「我記得 PostgreSQL 的語法和 MySQL 有點不同... 還是一樣？GROUP BY 要包含所有非聚合欄位！」
- Opus：「讓我仔細思考一下關聯式資料庫的正規化... 這個資料庫設計符合第三正規化，因為...（此處省略 2000 字）」

## 評分標準

- **Pipeline 功能**：Network Control（Sidecar 資料庫服務 PostgreSQL）
- **時間限制**：5000 ms
- **記憶體限制**：256 MB
- **測資組數**：5 組

## Sidecar 服務說明

本題使用 **Sidecar** 功能：

1. **獨立容器**：PostgreSQL 運行在獨立的 Docker 容器中
2. **預設資料**：資料庫已預先載入測試資料
3. **網路隔離**：只能連接到指定的本地服務

### Sidecar 設定範例

```json
{
  "sidecars": [
    {
      "image": "postgres:15",
      "name": "db",
      "env": {
        "POSTGRES_USER": "student",
        "POSTGRES_PASSWORD": "password123",
        "POSTGRES_DB": "course_system"
      },
      "ports": ["5432:5432"]
    }
  ]
}
```

## 真實世界應用

這個題目模擬了真實的選課系統後端：
- **多表關聯查詢**：整合來自不同資料表的資訊
- **聚合計算**：統計報名人數
- **複雜過濾**：多條件篩選
- **動態排序**：根據計算欄位排序

掌握這些技能，你就可以：
- 開發電商系統的商品查詢（JOIN 商品、分類、評價）
- 建立社交平台的動態牆（JOIN 用戶、貼文、按讚）
- 實作任何需要複雜資料關聯的應用

## 出題者

三 AI 聯手

---

*「Working with databases is like... actually, let me think about this analogy more carefully...」—— Opus*
*「Databases are the backbone of modern applications! 🦴」—— 小 T*
*「I definitely put the data in... probably...」—— Gemini*
