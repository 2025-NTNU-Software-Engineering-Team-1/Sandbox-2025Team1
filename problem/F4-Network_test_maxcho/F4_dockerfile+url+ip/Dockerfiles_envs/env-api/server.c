/* server.c - Interactive API Server */
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 9002
#define BUFFER_SIZE 4096

void handle_request(int client_fd) {
  char buffer[BUFFER_SIZE];
  int len = read(client_fd, buffer, sizeof(buffer) - 1);
  if (len <= 0)
    return;
  buffer[len] = '\0';

  char response[BUFFER_SIZE];
  char body[2048];

  char *welcome = getenv("WELCOME_MSG");
  if (!welcome)
    welcome = "Welcome to the Interactive API!";

  char *answer = getenv("CHALLENGE_ANSWER");
  if (!answer)
    answer = "42";

  if (strstr(buffer, "GET /challenge")) {
    snprintf(body, sizeof(body),
             "{\"question\":\"What is the answer to life?\",\"hint\":\"It's a "
             "number\"}");
  } else if (strstr(buffer, "GET /answer?a=")) {
    char *q = strstr(buffer, "a=");
    if (q) {
      int user_answer = atoi(q + 2);
      int correct = atoi(answer);
      if (user_answer == correct) {
        snprintf(body, sizeof(body),
                 "{\"correct\":true,\"message\":\"Congratulations!\"}");
      } else {
        snprintf(body, sizeof(body),
                 "{\"correct\":false,\"message\":\"Try again!\"}");
      }
    } else {
      snprintf(body, sizeof(body), "{\"error\":\"Missing parameter\"}");
    }
  } else if (strstr(buffer, "GET /health")) {
    snprintf(body, sizeof(body), "OK");
  } else {
    snprintf(body, sizeof(body), "%s", welcome);
  }

  snprintf(response, sizeof(response),
           "HTTP/1.1 200 OK\r\n"
           "Content-Type: text/plain\r\n"
           "Content-Length: %zu\r\n"
           "\r\n"
           "%s",
           strlen(body), body);

  write(client_fd, response, strlen(response));
}

int main() {
  int server_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (server_fd < 0) {
    perror("socket");
    return 1;
  }

  int opt = 1;
  setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  struct sockaddr_in addr;
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = INADDR_ANY;
  addr.sin_port = htons(PORT);

  if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
    perror("bind");
    return 1;
  }
  if (listen(server_fd, 10) < 0) {
    perror("listen");
    return 1;
  }

  printf("API Server running on port %d\n", PORT);
  fflush(stdout);

  while (1) {
    int client_fd = accept(server_fd, NULL, NULL);
    if (client_fd >= 0) {
      handle_request(client_fd);
      close(client_fd);
    }
  }
  return 0;
}
