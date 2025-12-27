#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

int main () {
    char host [100];
    int port;

    // 1. 讀取輸入
    if (scanf ("%99s %d" , host , &port) != 2) return 0;

    printf ("debug: resolving hostname %s\n" , host);
    struct hostent *he = gethostbyname (host);
    if (!he) {
        printf ("fail (debug: dns resolution failed)\n");
        return 0;
    }

    // 2. 建立 Socket
    int sock = socket (AF_INET , SOCK_STREAM , 0);
    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons (port);
    server.sin_addr = *((struct in_addr *)he->h_addr_list [0]);
    printf ("debug: IP resolved to %s\n" , inet_ntoa (server.sin_addr));

    if (connect (sock , (struct sockaddr *)&server , sizeof (server)) < 0) {
        printf ("fail (debug: connection failed)\n");
        close (sock);
        return 0;
    }

    // 3. 發送 HTTP Request
    printf ("debug: sending HTTP GET...\n");
    char msg [256];
    snprintf (msg , sizeof (msg) , "GET / HTTP/1.0\r\nHost: %s\r\n\r\n" , host);
    send (sock , msg , strlen (msg) , 0);

    // 4. 接收回應
    printf ("debug: receiving data...\n");
    char buffer [4096];
    int total_len = 0;
    int len;

    while ((len = recv (sock , buffer + total_len , sizeof (buffer) - total_len - 1 , 0)) > 0) {
        total_len += len;
        if (total_len >= sizeof (buffer) - 1) break;
    }
    buffer [total_len] = '\0';

    printf ("debug: total bytes: %d\n" , total_len);

    // 5. 驗證內容
    int is_good = 0;
    if (port == 8000) { // env-python
        if (strstr (buffer , "Hello from Server Container!")) {
            printf ("debug: Matched Python env signature\n");
            is_good = 1;
        }
        else {
            printf ("fail (debug: Python env signature not found)\n");
        }
    }
    else if (port == 8080) { // env-cpp
        if (strstr (buffer , "Hello from C++ File!")) {
            printf ("debug: Matched C++ env signature\n");
            is_good = 1;
        }
        else {
            printf ("fail (debug: C++ env signature not found)\n");
        }
    }
    else {
        printf ("fail (debug: Unknown port %d)\n" , port);
    }

    if (is_good) {
        printf ("good\n");
    }

    close (sock);
    return 0;
}