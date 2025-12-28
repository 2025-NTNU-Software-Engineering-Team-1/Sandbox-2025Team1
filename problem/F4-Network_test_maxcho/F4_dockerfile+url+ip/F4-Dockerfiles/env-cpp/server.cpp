// server.cpp
#include <iostream>
#include <unistd.h>
#include <netinet/in.h>
#include <cstring>
#include <sys/socket.h>

int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int addrlen = sizeof(address);

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("Socket failed");
        return 1;
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(8080); 

    // 3. Bind & Listen
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("Bind failed");
        return 1;
    }
    if (listen(server_fd, 3) < 0) {
        perror("Listen failed");
        return 1;
    }

    std::cout << "C++ Server is running on port 8080..." << std::endl;

    while(true) {
        new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
        if (new_socket > 0) {
            const char* response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHello from C++ File!";
            write(new_socket, response, strlen(response));
            close(new_socket);
        }
    }
    return 0;
}