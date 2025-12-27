import urllib.request
import urllib.error
import sys


def fetch_data(param):
    """發送HTTP GET請求並返回回應內容"""
    # 使用 Docker 網路別名 'local_service' 連接到 local service 容器
    url = f"http://local_service:8080/api/data/{param}"

    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.URLError as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def main():
    n = int(input().strip())

    for _ in range(n):
        param = input().strip()
        result = fetch_data(param)
        if result:
            print(result)


if __name__ == "__main__":
    main()
