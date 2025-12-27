#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <sys/time.h> // [修正 1] 加入這個標頭檔以定義 struct timeval

typedef struct {
    char host [100];
    int port;
} Target;

void check (const char *host , int port) {
    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons (port);

    if (inet_pton (AF_INET , host , &server.sin_addr) <= 0) {
        struct hostent *he = gethostbyname (host);
        if (he == NULL) {
            printf ("fail\n");
            return;
        }
        // [修正 2] 將 he->h_addr 改為標準的 he->h_addr_list[0]
        server.sin_addr = *((struct in_addr *)he->h_addr_list [0]);
    }

    int sock = socket (AF_INET , SOCK_STREAM , 0);
    if (sock == -1) {
        printf ("fail\n");
        return;
    }

    struct timeval timeout;
    timeout.tv_sec = 3;
    timeout.tv_usec = 0;
    setsockopt (sock , SOL_SOCKET , SO_SNDTIMEO , (const char *)&timeout , sizeof (timeout));

    if (connect (sock , (struct sockaddr *)&server , sizeof (server)) < 0) {
        printf ("fail\n");
    }
    else {
        printf ("good\n");
    }
    close (sock);
}

int main () {
    Target targets [] = {
        {"1.1.1.1", 53},
        {"9.9.9.9", 53},
        {"www.google.com", 443},
        {"github.com", 443}
    };

    int num_targets = sizeof (targets) / sizeof (targets [0]);

    for (int i = 0; i < num_targets; i++) {
        check (targets [i].host , targets [i].port);
    }
    return 0;
}