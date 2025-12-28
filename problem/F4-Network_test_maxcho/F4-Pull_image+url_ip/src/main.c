/*
 * Combined Pull_image + URL_IP network test
 * Input format (from .in file):
 *   - sidecar <hostname> <port>      -> test sidecar container connection
 *   - external ip <ip> <port>        -> test external IP connection
 *   - external url <hostname> <port> -> test external URL connection
 * Output: debug logs showing connection attempts and results
 */

#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

void debug(const char *msg) { printf("[DEBUG] %s\n", msg); }

int connect_with_timeout(const char *host, int port, int timeout_sec,
                         int *is_sinkhole) {
  struct addrinfo hints, *res, *p;
  int sockfd = -1;
  int status;
  char port_str[16];
  char ip_str[INET_ADDRSTRLEN];
  char debug_msg[256];

  *is_sinkhole = 0;

  memset(&hints, 0, sizeof(hints));
  hints.ai_family = AF_INET;
  hints.ai_socktype = SOCK_STREAM;

  snprintf(port_str, sizeof(port_str), "%d", port);

  snprintf(debug_msg, sizeof(debug_msg), "Resolving %s:%d...", host, port);
  debug(debug_msg);

  if ((status = getaddrinfo(host, port_str, &hints, &res)) != 0) {
    snprintf(debug_msg, sizeof(debug_msg), "DNS resolution failed: %s",
             gai_strerror(status));
    debug(debug_msg);
    return -1;
  }

  for (p = res; p != NULL; p = p->ai_next) {
    struct sockaddr_in *ipv4 = (struct sockaddr_in *)p->ai_addr;
    inet_ntop(AF_INET, &(ipv4->sin_addr), ip_str, INET_ADDRSTRLEN);

    snprintf(debug_msg, sizeof(debug_msg), "Resolved to IP: %s", ip_str);
    debug(debug_msg);

    if (strcmp(ip_str, "0.0.0.0") == 0) {
      debug("DNS sinkholed! This URL is not whitelisted.");
      *is_sinkhole = 1;
      freeaddrinfo(res);
      return -1;
    }

    sockfd = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
    if (sockfd == -1)
      continue;

    struct timeval tv;
    tv.tv_sec = timeout_sec;
    tv.tv_usec = 0;
    setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    debug("Connecting...");
    if (connect(sockfd, p->ai_addr, p->ai_addrlen) == 0) {
      debug("Connected!");
      freeaddrinfo(res);
      return sockfd;
    }

    snprintf(debug_msg, sizeof(debug_msg), "Connect failed: %s",
             strerror(errno));
    debug(debug_msg);
    close(sockfd);
    sockfd = -1;
  }

  freeaddrinfo(res);
  return sockfd;
}

void test_redis(const char *host, int port) {
  char debug_msg[256];
  int is_sinkhole;

  snprintf(debug_msg, sizeof(debug_msg), "Testing Redis sidecar at %s:%d", host,
           port);
  debug(debug_msg);

  int sockfd = connect_with_timeout(host, port, 5, &is_sinkhole);
  if (sockfd < 0) {
    printf("RESULT: FAIL\n");
    return;
  }

  const char *password = "noj_secret_pass";
  char cmd[256];
  snprintf(cmd, sizeof(cmd), "AUTH %s\r\n", password);

  debug("Sending AUTH command...");
  send(sockfd, cmd, strlen(cmd), 0);

  char response[1024] = {0};
  recv(sockfd, response, sizeof(response) - 1, 0);

  snprintf(debug_msg, sizeof(debug_msg), "Raw response: %s", response);
  debug(debug_msg);

  if (strncmp(response, "+OK", 3) == 0) {
    debug("Redis AUTH successful!");
    printf("RESULT: PASS\n");
  } else {
    debug("Redis AUTH failed");
    printf("RESULT: FAIL\n");
  }

  close(sockfd);
}

void test_http(const char *host, int port) {
  char debug_msg[256];
  int is_sinkhole;

  snprintf(debug_msg, sizeof(debug_msg), "Testing HTTP sidecar at %s:%d", host,
           port);
  debug(debug_msg);

  int sockfd = connect_with_timeout(host, port, 5, &is_sinkhole);
  if (sockfd < 0) {
    printf("RESULT: FAIL\n");
    return;
  }

  char request[512];
  snprintf(request, sizeof(request), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n",
           host);

  debug("Sending HTTP GET request...");
  send(sockfd, request, strlen(request), 0);

  debug("Receiving response...");
  char response[8192] = {0};
  char buffer[4096];
  ssize_t n;
  size_t total = 0;

  while ((n = recv(sockfd, buffer, sizeof(buffer) - 1, 0)) > 0 &&
         total < sizeof(response) - 1) {
    buffer[n] = '\0';
    strncat(response, buffer, sizeof(response) - total - 1);
    total += n;
  }

  snprintf(debug_msg, sizeof(debug_msg), "Response length: %zu",
           strlen(response));
  debug(debug_msg);

  if (strlen(response) > 200) {
    char snippet[256];
    strncpy(snippet, response, 200);
    snippet[200] = '\0';
    snprintf(debug_msg, sizeof(debug_msg), "Content snippet: %s...", snippet);
    debug(debug_msg);
  } else {
    snprintf(debug_msg, sizeof(debug_msg), "Content: %s", response);
    debug(debug_msg);
  }

  if (strstr(response, "verify_env_args_success") != NULL) {
    debug("HTTP secret keyword found!");
    printf("RESULT: PASS\n");
  } else {
    debug("HTTP secret keyword NOT found");
    printf("RESULT: FAIL\n");
  }

  close(sockfd);
}

void test_external(const char *host, int port, int is_url) {
  char debug_msg[256];
  const char *conn_type = is_url ? "URL" : "IP";
  int is_sinkhole;

  snprintf(debug_msg, sizeof(debug_msg),
           "Testing external %s connection to %s:%d", conn_type, host, port);
  debug(debug_msg);

  int sockfd = connect_with_timeout(host, port, 5, &is_sinkhole);

  if (is_sinkhole) {
    printf("RESULT: BLOCKED (sinkhole)\n");
    return;
  }

  if (sockfd < 0) {
    debug("Connection blocked or failed");
    printf("RESULT: BLOCKED\n");
    return;
  }

  debug("Connection successful!");

  if (port == 443) {
    debug("HTTPS port connected, TLS handshake not performed");
  } else if (port == 80) {
    char request[512];
    snprintf(request, sizeof(request), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n",
             host);
    send(sockfd, request, strlen(request), 0);

    char response[1024] = {0};
    recv(sockfd, response, sizeof(response) - 1, 0);

    char snippet[128];
    strncpy(snippet, response, 100);
    snippet[100] = '\0';
    snprintf(debug_msg, sizeof(debug_msg), "HTTP response snippet: %s",
             snippet);
    debug(debug_msg);
  }

  printf("RESULT: PASS\n");
  close(sockfd);
}

int main() {
  char line[1024];
  char cmd[64], arg1[256], arg2[256];
  int port;

  debug("============================================================");
  debug("Combined Pull_image + URL_IP Network Test (C)");
  debug("============================================================");

  if (fgets(line, sizeof(line), stdin) == NULL) {
    debug("No input provided");
    printf("RESULT: FAIL (no input)\n");
    return 0;
  }

  // Remove trailing newline
  line[strcspn(line, "\r\n")] = '\0';

  char debug_msg[1280];
  snprintf(debug_msg, sizeof(debug_msg), "Input: %s", line);
  debug(debug_msg);

  if (strlen(line) == 0) {
    debug("Empty input");
    printf("RESULT: FAIL (no input)\n");
    return 0;
  }

  // Parse command
  if (sscanf(line, "sidecar %255s %d", arg1, &port) == 2) {
    snprintf(debug_msg, sizeof(debug_msg), "Sidecar test: %s:%d", arg1, port);
    debug(debug_msg);

    if (port == 6379) {
      test_redis(arg1, port);
    } else if (port == 8080) {
      test_http(arg1, port);
    } else {
      debug("Unknown sidecar port, attempting generic TCP connect");
      test_external(arg1, port, 0);
    }
  } else if (sscanf(line, "external ip %255s %d", arg1, &port) == 2) {
    test_external(arg1, port, 0);
  } else if (sscanf(line, "external url %255s %d", arg1, &port) == 2) {
    test_external(arg1, port, 1);
  } else {
    debug("Unknown command format");
    printf("RESULT: FAIL (unknown command)\n");
  }

  debug("============================================================");
  debug("Test complete");
  debug("============================================================");

  return 0;
}
