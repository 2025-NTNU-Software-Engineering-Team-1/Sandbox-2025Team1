#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

void debug_log(const char *msg) {
  printf("[DEBUG] %s\n", msg);
  fflush(stdout);
}

void debug_logf(const char *fmt, ...) {
  char buffer[512];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buffer, sizeof(buffer), fmt, args);
  va_end(args);
  printf("[DEBUG] %s\n", buffer);
  fflush(stdout);
}

int is_ip_address(const char *str) {
  struct in_addr addr;
  return inet_pton(AF_INET, str, &addr) == 1;
}

int check_connection(const char *host, int port, int timeout_sec) {
  struct sockaddr_in server;
  char log_buf[256];

  server.sin_family = AF_INET;
  server.sin_port = htons(port);

  if (!is_ip_address(host)) {
    snprintf(log_buf, sizeof(log_buf), "Resolving hostname: %s", host);
    debug_log(log_buf);

    struct hostent *he = gethostbyname(host);
    if (!he) {
      debug_log("DNS resolution failed");
      return 0;
    }
    server.sin_addr = *((struct in_addr *)he->h_addr_list[0]);

    char *resolved = inet_ntoa(server.sin_addr);
    snprintf(log_buf, sizeof(log_buf), "Resolved to: %s", resolved);
    debug_log(log_buf);

    if (strcmp(resolved, "0.0.0.0") == 0) {
      debug_log("DNS sinkholed");
      return 0;
    }
  } else {
    inet_pton(AF_INET, host, &server.sin_addr);
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    debug_log("Socket creation failed");
    return 0;
  }

  struct timeval tv;
  tv.tv_sec = timeout_sec;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
  setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  snprintf(log_buf, sizeof(log_buf), "Connecting to %s:%d", host, port);
  debug_log(log_buf);

  int result = connect(sock, (struct sockaddr *)&server, sizeof(server)) >= 0;
  close(sock);

  if (result) {
    debug_log("Connection successful");
  } else {
    snprintf(log_buf, sizeof(log_buf), "Connection failed: %s",
             strerror(errno));
    debug_log(log_buf);
  }
  return result;
}

int send_http_request(const char *host, int port, const char *path,
                      char *response, int resp_size) {
  struct sockaddr_in server;

  server.sin_family = AF_INET;
  server.sin_port = htons(port);

  if (!is_ip_address(host)) {
    struct hostent *he = gethostbyname(host);
    if (!he)
      return 0;
    server.sin_addr = *((struct in_addr *)he->h_addr_list[0]);
  } else {
    inet_pton(AF_INET, host, &server.sin_addr);
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1)
    return 0;

  struct timeval tv;
  tv.tv_sec = 5;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    close(sock);
    return 0;
  }

  char request[512];
  snprintf(request, sizeof(request), "GET %s HTTP/1.0\r\nHost: %s\r\n\r\n",
           path, host);
  send(sock, request, strlen(request), 0);

  int total = 0;
  int len;
  while ((len = recv(sock, response + total, resp_size - total - 1, 0)) > 0) {
    total += len;
    if (total >= resp_size - 1)
      break;
  }
  response[total] = '\0';
  close(sock);

  char log_buf[64];
  snprintf(log_buf, sizeof(log_buf), "Response length: %d bytes", total);
  debug_log(log_buf);

  return 1;
}

int test_docker_env(const char *env_name, int port, const char *signature) {
  char log_buf[256];
  snprintf(log_buf, sizeof(log_buf), "Testing Docker env: %s:%d", env_name,
           port);
  debug_log(log_buf);
  snprintf(log_buf, sizeof(log_buf), "Expected signature: %s", signature);
  debug_log(log_buf);

  char response[4096];
  if (!send_http_request(env_name, port, "/", response, sizeof(response))) {
    debug_log("HTTP request failed");
    return 0;
  }

  if (strstr(response, signature)) {
    debug_log("Signature matched!");
    return 1;
  } else {
    debug_log("Signature NOT found");
    return 0;
  }
}

int test_connectivity(const char *target, int port, int expect_connect) {
  char log_buf[128];
  snprintf(log_buf, sizeof(log_buf), "Testing: %s:%d, expecting %s", target,
           port, expect_connect ? "connect" : "block");
  debug_log(log_buf);

  int result = check_connection(target, port, 5);

  if (result == expect_connect) {
    debug_log("Result as expected");
    return 1;
  } else {
    debug_log("Unexpected result");
    return 0;
  }
}

int main() {
  printf("============================================================\n");
  printf("Network Test Client (C)\n");
  printf("============================================================\n");

  char line[512];
  int total = 0, passed = 0;

  while (fgets(line, sizeof(line), stdin)) {
    // Remove newline
    line[strcspn(line, "\r\n")] = 0;

    if (strlen(line) == 0 || line[0] == '#')
      continue;

    char type[32], target[128], expect_str[32], signature[256];
    int port;

    int parts =
        sscanf(line, "%31s %127s %d %255[^\n]", type, target, &port, signature);
    if (parts < 3)
      continue;

    printf("\n------------------------------------------------------------\n");
    printf("Test: %s %s:%d\n", type, target, port);
    printf("------------------------------------------------------------\n");

    int result = 0;

    if (strcmp(type, "DOCKER") == 0) {
      result = test_docker_env(target, port, signature);
    } else if (strcmp(type, "IP") == 0 || strcmp(type, "URL") == 0) {
      int expect_connect = 1;
      if (parts >= 4 && strcmp(signature, "block") == 0) {
        expect_connect = 0;
      }
      result = test_connectivity(target, port, expect_connect);
    } else {
      char log_buf[64];
      snprintf(log_buf, sizeof(log_buf), "Unknown test type: %s", type);
      debug_log(log_buf);
    }

    printf("Result: [%s]\n", result ? "PASS" : "FAIL");
    total++;
    if (result)
      passed++;
  }

  printf("\n============================================================\n");
  printf("Summary: %d/%d tests passed\n", passed, total);
  printf("============================================================\n");

  return 0;
}