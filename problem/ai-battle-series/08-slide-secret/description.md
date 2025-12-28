# Problem 8: 投影片裡的祕密

## 故事背景

> 「各位同學，讓我仔細思考一下如何說明這些題目...
> 首先，我認為我們需要從軟體工程的本質談起。
> 什麼是軟體？什麼是工程？這兩個概念的交集又是什麼？
> ... [3000 字後] ...
> 好，接下來是題目說明。」
> —— Opus，專題報告指導會議

「讓我仔細思考一下...」Opus 用他標誌性的開場白開始。

全班發出一陣哀嚎。又來了。

「專題報告需要視覺化呈現，」Opus 繼續說道，完全無視學生們的反應，「我在投影片中嵌入了一些『彩蛋』—— 用隱寫術把重要資訊藏在圖片的像素中。」

Gemini 的眼睛亮了起來：「等等，你是說... 圖片裡藏了考試答案？」

「不是答案，是『啟發性提示』。」Opus 用指頭比了個引號的手勢，「這個技術叫做 LSB Steganography —— 將資訊編碼在每個像素的最低有效位元（Least Significant Bit）中。讓我仔細解釋一下這個概念...」

「不用了！」Gemini 急忙打斷。

小 T 興奮地說：「Wow! 這就像 spy movie 裡的場景！🕵️ How cool is that! We're like secret agents! 來來來，綜觀全局，這是很有趣的 algorithm！」

「請讀取我提供的 BMP 圖片，」Opus 說，「從每個像素的 R 通道提取最低位元，組合成隱藏訊息。每 8 個位元組成一個 ASCII 字元。」

## 題目說明

系統會提供一個 BMP 格式的圖片檔案。你需要讀取這個圖片，從每個像素的 R（紅色）通道中提取最低有效位元（LSB），將這些位元組合成 ASCII 字元，還原隱藏的訊息。

### LSB 隱寫術原理

每個像素的 R 值是 0-255 的整數。它的二進位表示的最後一位就是 LSB：
- R = 120 = 01111000₂，LSB = 0
- R = 121 = 01111001₂，LSB = 1

將連續 8 個 LSB 組合起來，就形成一個 ASCII 字元：
- 例如：01001000₂ = 72 = 'H'

訊息以 `\0`（ASCII 0）作為結束標記。

## BMP 檔案格式

BMP（Bitmap）是一種常見的圖片格式。本題使用 24-bit 無壓縮 BMP：

### BMP 檔案結構

1. **檔頭（14 bytes）**：包含檔案大小等資訊
2. **資訊頭（40 bytes）**：包含圖片寬高、位元深度等
3. **像素資料**：BGR 順序，每像素 3 bytes

### 讀取 BMP 的關鍵

```cpp
// 跳過 54 bytes 的檔頭
fseek(file, 54, SEEK_SET);

// 讀取像素（注意：BMP 是 BGR 順序，且由下往上存）
unsigned char bgr[3];
fread(bgr, 1, 3, file);
int r = bgr[2];  // R 在第三個 byte
```

**注意事項：**
- BMP 的 row 有 4 bytes 對齊，需要處理 padding
- 像素是 BGR 順序，不是 RGB
- 圖片是從左下角開始存放（bottom-up）

## 輸入格式

```
第一行：圖片檔名（例如 secret.bmp）
```

圖片檔案會在當前目錄中。

## 輸出格式

```
隱藏的訊息字串
```

## 範例

假設 `secret.bmp` 是一個包含隱藏訊息的 BMP 圖片。

假設隱藏訊息是 "Hi"：
- 'H' = 72 = 01001000₂
- 'i' = 105 = 01101001₂

需要 16 個像素來儲存這兩個字元（每個字元 8 個位元）。

**範例說明：**

假設 secret.bmp 中前 8 個像素的 R 值為：
`120, 121, 120, 120, 121, 120, 120, 120`

LSB 分別為：0, 1, 0, 0, 1, 0, 0, 0

組合：01001000₂ = 72 = 'H'

**輸出：**
```
H...（後續字元依此類推）
```

## 提示

### 讀取 BMP 檔案

**C++：**
```cpp
#include <fstream>
#include <vector>

vector<int> read_bmp_r_values(const string& filename) {
    ifstream file(filename, ios::binary);

    // 讀取 BMP 檔頭
    unsigned char header[54];
    file.read((char*)header, 54);

    // 從檔頭解析寬高
    int width = *(int*)&header[18];
    int height = *(int*)&header[22];

    // 計算每行的 padding（BMP 行對齊到 4 bytes）
    int row_padded = (width * 3 + 3) & (~3);

    vector<int> r_values;
    vector<unsigned char> row(row_padded);

    for (int i = 0; i < height; i++) {
        file.read((char*)row.data(), row_padded);
        for (int j = 0; j < width; j++) {
            // BMP 是 BGR 順序，R 在 index 2
            r_values.push_back(row[j * 3 + 2]);
        }
    }
    return r_values;
}
```

**Python：**
```python
def read_bmp_r_values(filename):
    with open(filename, "rb") as f:
        # 跳過 BMP 檔頭
        header = f.read(54)

        # 解析寬高（little-endian）
        width = int.from_bytes(header[18:22], 'little')
        height = int.from_bytes(header[22:26], 'little')

        # 計算 row padding
        row_padded = (width * 3 + 3) & (~3)

        r_values = []
        for _ in range(height):
            row = f.read(row_padded)
            for j in range(width):
                # BMP 是 BGR，R 在 offset 2
                r_values.append(row[j * 3 + 2])

        return r_values
```

### 提取 LSB 並組合字元

```python
def extract_message(r_values):
    message = ""
    for i in range(0, len(r_values), 8):
        if i + 8 > len(r_values):
            break
        byte = 0
        for j in range(8):
            bit = r_values[i + j] & 1  # 取 LSB
            byte = (byte << 1) | bit
        if byte == 0:  # 遇到 \0 結束
            break
        message += chr(byte)
    return message
```

## AI 助教的提示

- Opus：「讓我仔細思考一下隱寫術的歷史... 這個技術可以追溯到古希臘時期...（此處省略 5000 字歷史課）」
- Gemini：「這題要用位元運算... 或者不用？我記得有更簡單的方法... 還是沒有？」
- 小 T：「來來來！Bit manipulation is fun! 🎮 Just remember: `x & 1` gets the LSB! 綜觀全局，這就是位元操作的精髓！」

## 評分標準

- **Pipeline 功能**：Resource Data（圖片檔案 BMP 格式）
- **時間限制**：1000 ms
- **記憶體限制**：64 MB
- **測資組數**：4 組

## Resource Data 說明

本題使用 **Resource Data** 功能：

1. 系統會在執行前將圖片檔案放入工作目錄
2. 你的程式可以直接讀取這個檔案
3. 不同測資會提供不同的圖片

這模擬了真實世界中的：
- 多媒體處理應用
- 資料分析管道
- 資安鑑識工具

## 出題者

Opus（歐帕斯）

---

*「The art of hiding information in plain sight... Let me think about this more carefully... Actually, let me think about the nature of information itself first...」—— Opus*
