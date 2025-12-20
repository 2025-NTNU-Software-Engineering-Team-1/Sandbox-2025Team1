FROM python:3.11-slim

# 安裝必要的工具
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 複製服務檔案
COPY . /app

# 安裝 Python 依賴（如果有）
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# 設置執行權限
RUN chmod +x start.sh

# 預設命令（start.sh 會在 Sandbox 中執行）
CMD ["/bin/bash"]
