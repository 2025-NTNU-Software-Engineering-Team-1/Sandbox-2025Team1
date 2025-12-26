#include <iostream>
#include <string>
#include <cstring>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

int main () {
    std::string host;
    int port;

    // 1. 讀取輸入
    if (!(std::cin >> host >> port)) return 0;

    std::cout << "debug: resolving hostname " << host << std::endl;
    struct hostent *he = gethostbyname (host.c_str ());
    if (!he) {
        std::cout << "fail (debug: dns resolution failed)" << std::endl;
        return 0;
    }

    // 2. 建立 Socket
    int sock = socket (AF_INET , SOCK_STREAM , 0);
    if (sock == -1) {
        std::cout << "fail (debug: socket creation failed)" << std::endl;
        return 0;
    }

    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons (port);
    server.sin_addr = *((struct in_addr *)he->h_addr_list [0]); // 使用標準寫法
    std::cout << "debug: IP resolved to " << inet_ntoa (server.sin_addr) << std::endl;

    std::cout << "debug: connecting to " << host << ":" << port << "..." << std::endl;
    if (connect (sock , (struct sockaddr *)&server , sizeof (server)) < 0) {
        std::cout << "fail (debug: connection failed)" << std::endl;
        close (sock);
        return 0;
    }

    // 3. 發送 HTTP Request
    std::cout << "debug: sending HTTP GET..." << std::endl;
    std::string msg = "GET / HTTP/1.0\r\nHost: " + host + "\r\n\r\n";
    send (sock , msg.c_str () , msg.length () , 0);

    // 4. 接收回應
    std::cout << "debug: receiving data..." << std::endl;
    char buffer [4096];
    std::string response = "";
    int len;
    while ((len = recv (sock , buffer , sizeof (buffer) - 1 , 0)) > 0) {
        buffer [len] = '\0';
        response += buffer;
    }

    std::cout << "debug: total bytes: " << response.length () << std::endl;

    // 5. 驗證內容
    bool is_good = false;
    if (port == 8000) { // env-python
        if (response.find ("Hello from Server Container!") != std::string::npos) {
            std::cout << "debug: Matched Python env signature" << std::endl;
            is_good = true;
        }
        else {
            std::cout << "fail (debug: Python env signature not found)" << std::endl;
        }
    }
    else if (port == 8080) { // env-cpp
        if (response.find ("Hello from C++ File!") != std::string::npos) {
            std::cout << "debug: Matched C++ env signature" << std::endl;
            is_good = true;
        }
        else {
            std::cout << "fail (debug: C++ env signature not found)" << std::endl;
        }
    }
    else {
        std::cout << "fail (debug: Unknown port)" << std::endl;
    }

    if (is_good) {
        std::cout << "good" << std::endl;
    }

    close (sock);
    return 0;
}