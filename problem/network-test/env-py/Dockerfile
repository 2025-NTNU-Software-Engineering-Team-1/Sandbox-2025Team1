FROM python:3.11-slim

# 安裝必要的工具和庫
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安裝常用的Python網路庫
RUN pip install --no-cache-dir \
    requests \
    urllib3

# 設置工作目錄
WORKDIR /app

# 預設命令
CMD ["/bin/bash"]
