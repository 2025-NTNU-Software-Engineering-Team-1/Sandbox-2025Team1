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
    // 使用標準寫法 h_addr_list[0]
    server.sin_addr = *((struct in_addr *)he->h_addr_list [0]);
    std::cout << "debug: IP resolved to " << inet_ntoa (server.sin_addr) << std::endl;

    std::cout << "debug: connecting to " << host << ":" << port << "..." << std::endl;
    if (connect (sock , (struct sockaddr *)&server , sizeof (server)) < 0) {
        std::cout << "fail (debug: connection failed)" << std::endl;
        close (sock);
        return 0;
    }

    // 3. 根據 Port 分流
    if (port == 6379) {
        // --- Redis Logic ---
        std::cout << "debug: Mode = Redis" << std::endl;
        const char *auth_cmd = "AUTH noj_secret_pass\r\n";
        send (sock , auth_cmd , strlen (auth_cmd) , 0);

        char buffer [1024];
        memset (buffer , 0 , sizeof (buffer));
        int len = recv (sock , buffer , sizeof (buffer) - 1 , 0);

        if (len > 0) {
            std::string resp (buffer);
            // 移除換行符號
            while (!resp.empty () && (resp.back () == '\n' || resp.back () == '\r')) {
                resp.pop_back ();
            }
            std::cout << "debug: Redis response [" << resp << "]" << std::endl;

            if (resp.find ("+OK") == 0) {
                std::cout << "good" << std::endl;
            }
            else {
                std::cout << "fail (debug: Redis AUTH failed)" << std::endl;
            }
        }
        else {
            std::cout << "fail (debug: Redis recv error)" << std::endl;
        }
    }
    else if (port == 8080) {
        // --- HTTP Logic ---
        std::cout << "debug: Mode = HTTP" << std::endl;
        std::string msg = "GET / HTTP/1.0\r\nHost: " + host + "\r\n\r\n";
        send (sock , msg.c_str () , msg.length () , 0);

        char buffer [4096];
        std::string response = "";
        int len;
        std::cout << "debug: Receiving HTTP data..." << std::endl;
        while ((len = recv (sock , buffer , sizeof (buffer) - 1 , 0)) > 0) {
            buffer [len] = '\0';
            response += buffer;
        }

        std::cout << "debug: Total bytes: " << response.length () << std::endl;

        if (response.find ("verify_env_args_success") != std::string::npos) {
            std::cout << "good" << std::endl;
        }
        else {
            std::cout << "fail (debug: secret keyword not found)" << std::endl;
        }
    }
    else {
        std::cout << "fail (debug: unknown port)" << std::endl;
    }

    close (sock);
    return 0;
}