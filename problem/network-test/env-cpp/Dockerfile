FROM gcc:11

# 安裝必要的工具和庫
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 預設命令
CMD ["/bin/bash"]
