#include <iostream>
#include <string>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

std::string http_get(const std::string& host, int port, const std::string& path) {
    // 創建 socket
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return "";
    }

    // 解析主機名
    struct hostent* server = gethostbyname(host.c_str());
    if (!server) {
        close(sock);
        return "";
    }

    // 設置服務器地址
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    memcpy(&server_addr.sin_addr.s_addr, server->h_addr, server->h_length);

    // 連接到服務器
    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        close(sock);
        return "";
    }

    // 構建 HTTP GET 請求
    std::string request = "GET " + path + " HTTP/1.1\r\n";
    request += "Host: " + host + "\r\n";
    request += "Connection: close\r\n";
    request += "\r\n";

    // 發送請求
    if (send(sock, request.c_str(), request.length(), 0) < 0) {
        close(sock);
        return "";
    }

    // 接收響應
    std::string response;
    char buffer[4096];
    int bytes_received;
    while ((bytes_received = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[bytes_received] = '\0';
        response += buffer;
    }

    close(sock);

    // 解析 HTTP 響應，提取 body
    size_t header_end = response.find("\r\n\r\n");
    if (header_end != std::string::npos) {
        return response.substr(header_end + 4);
    }

    return response;
}

int main() {
    int n;
    std::cin >> n;

    for (int i = 0; i < n; i++) {
        std::string param;
        std::cin >> param;

        // 使用 Docker 網路別名 'local_service'
        std::string body = http_get("local_service", 8080, "/api/data/" + param);
        if (!body.empty()) {
            std::cout << body << std::endl;
        }
    }

    return 0;
}
