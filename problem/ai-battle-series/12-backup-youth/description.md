# Problem 12: 備份你的青春

## 故事背景

「期末考前一定要備份！」小 T 諄諄教誨，表情無比認真。

「我曾經因為沒備份丟失了整個專題...」Gemini 痛苦地回憶，眼神放空，「那是大三下的畢業專題... 三個月的心血... 就這樣沒了...」

「等等，」小 T 困惑地問，「你不是 AI 嗎？你怎麼會有大三的記憶？」

「...」Gemini 沉默了一下，「還是說那是別人的故事？我記不清了。反正就是要備份！」

Opus 清了清嗓子：「讓我仔細思考一下備份策略... 根據 3-2-1 備份原則：至少保留 3 份資料副本，存放在 2 種不同的儲存媒體上，其中 1 份存放在異地。但更重要的是：**差異備份**可以大幅減少備份時間和空間！」

「總之！」小 T 打斷 Opus 即將開始的長篇大論，「這題要你實作差異備份！比較新舊版本，找出變動！Write code and we'll collect the output! 📦」

## 題目說明

你的程式需要實作一個**差異備份系統**。給定舊版本和新版本的檔案清單，你需要：

1. 找出**新增的檔案**（新版本有，舊版本沒有）
2. 找出**刪除的檔案**（舊版本有，新版本沒有）
3. 找出**修改的檔案**（兩個版本都有，但 MD5 不同）
4. 計算**差異摘要**的 MD5 雜湊值

系統會使用 **Artifact Collection** 功能收集你生成的差異報告檔案。

### 需要生成的檔案

1. **diff_report.json** - 差異報告（JSON 格式）
2. **diff_summary.txt** - 差異摘要（純文字）

## 輸入格式

系統會提供兩個資源檔案：

### old_manifest.csv
```csv
filename,size,md5
main.cpp,1024,a1b2c3d4e5f6...
utils.h,512,b2c3d4e5f6a1...
data.txt,2048,c3d4e5f6a1b2...
```

### new_manifest.csv
```csv
filename,size,md5
main.cpp,1124,x1y2z3w4v5u6...
utils.h,512,b2c3d4e5f6a1...
config.json,256,d4e5f6a1b2c3...
```

## 輸出格式

### 1. diff_report.json

```json
{
    "backup_id": "DIFF-{timestamp}",
    "old_version": "舊版本檔案數",
    "new_version": "新版本檔案數",
    "changes": {
        "added": [
            {"filename": "config.json", "size": 256, "md5": "d4e5f6a1b2c3..."}
        ],
        "deleted": [
            {"filename": "data.txt", "size": 2048, "md5": "c3d4e5f6a1b2..."}
        ],
        "modified": [
            {
                "filename": "main.cpp",
                "old_size": 1024,
                "new_size": 1124,
                "old_md5": "a1b2c3d4e5f6...",
                "new_md5": "x1y2z3w4v5u6..."
            }
        ]
    },
    "statistics": {
        "total_added": 1,
        "total_deleted": 1,
        "total_modified": 1,
        "total_unchanged": 1,
        "size_diff": 新版本總大小 - 舊版本總大小
    }
}
```

### 2. diff_summary.txt

```
Differential Backup Report
==========================
Backup ID: DIFF-20240115103000
Old Version: 3 files (3584 bytes)
New Version: 3 files (1892 bytes)

Changes Summary:
- Added: 1 files (+256 bytes)
- Deleted: 1 files (-2048 bytes)
- Modified: 1 files
- Unchanged: 1 files

Net Change: -1692 bytes

Added Files:
  + config.json (256 bytes)

Deleted Files:
  - data.txt (2048 bytes)

Modified Files:
  * main.cpp: 1024 -> 1124 bytes (MD5 changed)

Report MD5: {diff_summary 內容的 MD5}
```

### 標準輸出

```
Differential backup completed!
Added: 1, Deleted: 1, Modified: 1, Unchanged: 1
Report MD5: {diff_summary.txt 的 MD5}
```

## 範例

**old_manifest.csv:**
```csv
filename,size,md5
alpha.txt,100,aaa111
beta.txt,200,bbb222
gamma.txt,300,ccc333
```

**new_manifest.csv:**
```csv
filename,size,md5
alpha.txt,100,aaa111
beta.txt,250,bbb999
delta.txt,400,ddd444
```

**標準輸出：**
```
Differential backup completed!
Added: 1, Deleted: 1, Modified: 1, Unchanged: 1
Report MD5: e5f6a1b2c3d4...
```

**說明：**
- `alpha.txt`：未變更（MD5 相同）
- `beta.txt`：已修改（大小和 MD5 都變了）
- `gamma.txt`：已刪除（新版本沒有）
- `delta.txt`：新增（舊版本沒有）

## 演算法要點

### 1. 使用集合操作找出變化

```python
old_files = set(old_manifest.keys())
new_files = set(new_manifest.keys())

added = new_files - old_files      # 新增
deleted = old_files - new_files    # 刪除
common = old_files & new_files     # 可能修改或未變

modified = [f for f in common if old_manifest[f]['md5'] != new_manifest[f]['md5']]
unchanged = [f for f in common if old_manifest[f]['md5'] == new_manifest[f]['md5']]
```

### 2. 計算 MD5 雜湊

```python
import hashlib

def calculate_md5(content):
    return hashlib.md5(content.encode()).hexdigest()

# 計算 diff_summary.txt 的 MD5
with open('diff_summary.txt', 'r') as f:
    content = f.read()
report_md5 = calculate_md5(content)
```

### 3. 完整解法框架

```python
import csv
import json
import hashlib
from datetime import datetime

def read_manifest(filename):
    """讀取 manifest CSV 檔案"""
    manifest = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            manifest[row['filename']] = {
                'size': int(row['size']),
                'md5': row['md5']
            }
    return manifest

def calculate_diff(old_manifest, new_manifest):
    """計算差異"""
    old_files = set(old_manifest.keys())
    new_files = set(new_manifest.keys())

    added = sorted(new_files - old_files)
    deleted = sorted(old_files - new_files)
    common = old_files & new_files

    modified = sorted([f for f in common
                      if old_manifest[f]['md5'] != new_manifest[f]['md5']])
    unchanged = sorted([f for f in common
                       if old_manifest[f]['md5'] == new_manifest[f]['md5']])

    return added, deleted, modified, unchanged

def generate_report(old_manifest, new_manifest, added, deleted, modified, unchanged):
    """生成 JSON 報告"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    old_total_size = sum(f['size'] for f in old_manifest.values())
    new_total_size = sum(f['size'] for f in new_manifest.values())

    report = {
        "backup_id": f"DIFF-{timestamp}",
        "old_version": len(old_manifest),
        "new_version": len(new_manifest),
        "changes": {
            "added": [{"filename": f, **new_manifest[f]} for f in added],
            "deleted": [{"filename": f, **old_manifest[f]} for f in deleted],
            "modified": [{
                "filename": f,
                "old_size": old_manifest[f]['size'],
                "new_size": new_manifest[f]['size'],
                "old_md5": old_manifest[f]['md5'],
                "new_md5": new_manifest[f]['md5']
            } for f in modified]
        },
        "statistics": {
            "total_added": len(added),
            "total_deleted": len(deleted),
            "total_modified": len(modified),
            "total_unchanged": len(unchanged),
            "size_diff": new_total_size - old_total_size
        }
    }

    return report, timestamp

def generate_summary(report, old_manifest, new_manifest, added, deleted, modified):
    """生成文字摘要"""
    old_size = sum(f['size'] for f in old_manifest.values())
    new_size = sum(f['size'] for f in new_manifest.values())
    added_size = sum(new_manifest[f]['size'] for f in added)
    deleted_size = sum(old_manifest[f]['size'] for f in deleted)

    lines = [
        "Differential Backup Report",
        "==========================",
        f"Backup ID: {report['backup_id']}",
        f"Old Version: {len(old_manifest)} files ({old_size} bytes)",
        f"New Version: {len(new_manifest)} files ({new_size} bytes)",
        "",
        "Changes Summary:",
        f"- Added: {len(added)} files (+{added_size} bytes)",
        f"- Deleted: {len(deleted)} files (-{deleted_size} bytes)",
        f"- Modified: {len(modified)} files",
        f"- Unchanged: {report['statistics']['total_unchanged']} files",
        "",
        f"Net Change: {report['statistics']['size_diff']:+d} bytes",
        "",
    ]

    if added:
        lines.append("Added Files:")
        for f in added:
            lines.append(f"  + {f} ({new_manifest[f]['size']} bytes)")
        lines.append("")

    if deleted:
        lines.append("Deleted Files:")
        for f in deleted:
            lines.append(f"  - {f} ({old_manifest[f]['size']} bytes)")
        lines.append("")

    if modified:
        lines.append("Modified Files:")
        for f in modified:
            lines.append(f"  * {f}: {old_manifest[f]['size']} -> {new_manifest[f]['size']} bytes (MD5 changed)")
        lines.append("")

    return "\n".join(lines)

# 主程式
old_manifest = read_manifest('old_manifest.csv')
new_manifest = read_manifest('new_manifest.csv')

added, deleted, modified, unchanged = calculate_diff(old_manifest, new_manifest)
report, timestamp = generate_report(old_manifest, new_manifest, added, deleted, modified, unchanged)
summary = generate_summary(report, old_manifest, new_manifest, added, deleted, modified)

# 計算摘要的 MD5
summary_md5 = hashlib.md5(summary.encode()).hexdigest()
summary += f"Report MD5: {summary_md5}\n"

# 寫入檔案
with open('diff_report.json', 'w') as f:
    json.dump(report, f, indent=4)

with open('diff_summary.txt', 'w') as f:
    f.write(summary)

# 輸出結果
print("Differential backup completed!")
print(f"Added: {len(added)}, Deleted: {len(deleted)}, Modified: {len(modified)}, Unchanged: {len(unchanged)}")
print(f"Report MD5: {summary_md5}")
```

## AI 助教的提示

- 小 T：「Set operations are your friend! 📝 Union, intersection, difference!」
- Gemini：「MD5 計算... 要用 hashlib... 或者其他函式庫？總之別忘了 encode！」
- Opus：「讓我仔細思考一下差異備份的原理... 這與版本控制系統如 Git 的 diff 機制有異曲同工之妙...」

## 評分標準

- **Pipeline 功能**：Artifact Collection
- **時間限制**：2000 ms
- **記憶體限制**：256 MB
- **測資組數**：5 組

## Artifact Collection 說明

本題使用 **Artifact Collection** 功能：

1. **檔案收集**：系統會收集你的程式產生的 `diff_report.json` 和 `diff_summary.txt`
2. **自動上傳**：收集的檔案會自動上傳供後續檢查
3. **內容驗證**：系統會驗證檔案內容是否符合規格

### 設定範例

```json
{
  "artifactCollection": ["zip"]
}
```

## 真實世界應用

這個題目模擬了版本控制和備份系統的核心功能：
- **差異偵測**：找出兩個版本之間的變化
- **變更追蹤**：記錄新增、刪除、修改的檔案
- **完整性驗證**：使用 MD5 確保資料完整

這些技能可以應用在：
- 版本控制系統（Git 的核心原理）
- 增量備份工具
- 檔案同步服務（Dropbox, OneDrive）
- CI/CD 管道中的變更偵測

## 出題者

三 AI 聯手

---

*「Backup, backup, backup! 💾 Differential backup saves time AND space!」—— 小 T*
*「I definitely backed up... or did I? Maybe I should check the diff...」—— Gemini*
*「Let me think about the mathematical properties of set operations in the context of version control...」—— Opus*
