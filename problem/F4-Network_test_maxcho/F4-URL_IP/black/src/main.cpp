#include <iostream>
#include <string>
#include <vector>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

struct Target {
    std::string host;
    int port;
};

void check (std::string host , int port) {
    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons (port);

    if (inet_pton (AF_INET , host.c_str () , &server.sin_addr) <= 0) {
        struct hostent *he = gethostbyname (host.c_str ());
        if (he == NULL) {
            std::cout << "fail" << std::endl;
            return;
        }
        server.sin_addr = *((struct in_addr *)he->h_addr);
    }

    int sock = socket (AF_INET , SOCK_STREAM , 0);
    if (sock == -1) {
        std::cout << "fail" << std::endl;
        return;
    }

    struct timeval timeout;
    timeout.tv_sec = 3;
    timeout.tv_usec = 0;
    setsockopt (sock , SOL_SOCKET , SO_SNDTIMEO , &timeout , sizeof (timeout));

    if (connect (sock , (struct sockaddr *)&server , sizeof (server)) < 0) {
        std::cout << "fail" << std::endl;
    }
    else {
        std::cout << "good" << std::endl;
    }
    close (sock);
}

int main () {
    std::vector<Target> targets = {
        {"1.1.1.1", 53},
        {"9.9.9.9", 53},
        {"www.google.com", 443},
        {"github.com", 443}
    };

    for (const auto &t : targets) {
        check (t.host , t.port);
    }
    return 0;
}