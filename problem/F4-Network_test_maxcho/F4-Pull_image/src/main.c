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

    // 2. 建立連線
    int sock = socket (AF_INET , SOCK_STREAM , 0);
    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons (port);
    // 使用標準寫法
    server.sin_addr = *((struct in_addr *)he->h_addr_list [0]);
    printf ("debug: IP resolved to %s\n" , inet_ntoa (server.sin_addr));

    if (connect (sock , (struct sockaddr *)&server , sizeof (server)) < 0) {
        printf ("fail (debug: connection failed)\n");
        close (sock);
        return 0;
    }

    // 3. 根據 Port 分流
    if (port == 6379) {
        // --- Redis Logic ---
        printf ("debug: Mode = Redis\n");
        const char *auth_cmd = "AUTH noj_secret_pass\r\n";
        send (sock , auth_cmd , strlen (auth_cmd) , 0);

        char buffer [1024];
        memset (buffer , 0 , sizeof (buffer));
        int len = recv (sock , buffer , sizeof (buffer) - 1 , 0);

        if (len > 0) {
            // 移除換行符號
            buffer [strcspn (buffer , "\r\n")] = 0;
            printf ("debug: Redis response [%s]\n" , buffer);

            if (strncmp (buffer , "+OK" , 3) == 0) {
                printf ("good\n");
            }
            else {
                printf ("fail (debug: Redis AUTH failed)\n");
            }
        }
        else {
            printf ("fail (debug: Redis recv error)\n");
        }
    }
    else if (port == 8080) {
        // --- HTTP Logic ---
        printf ("debug: Mode = HTTP\n");
        char msg [256];
        snprintf (msg , sizeof (msg) , "GET / HTTP/1.0\r\nHost: %s\r\n\r\n" , host);
        send (sock , msg , strlen (msg) , 0);

        char buffer [4096];
        int total_len = 0;
        int len;

        printf ("debug: Receiving HTTP data...\n");
        while ((len = recv (sock , buffer + total_len , sizeof (buffer) - total_len - 1 , 0)) > 0) {
            total_len += len;
            if (total_len >= sizeof (buffer) - 1) break;
        }
        buffer [total_len] = '\0';

        printf ("debug: Total bytes: %d\n" , total_len);

        if (strstr (buffer , "verify_env_args_success")) {
            printf ("good\n");
        }
        else {
            printf ("fail (debug: secret keyword not found)\n");
        }
    }
    else {
        printf ("fail (debug: unknown port %d)\n" , port);
    }

    close (sock);
    return 0;
}