#include <arpa/inet.h>
#include <netdb.h>
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

int is_ip_address(const char *str) {
  struct in_addr addr;
  return inet_pton(AF_INET, str, &addr) == 1;
}

int resolve_dns(const char *hostname, char *ip_out, int max_len) {
  struct hostent *he = gethostbyname(hostname);
  if (!he) {
    char buf[256];
    snprintf(buf, sizeof(buf), "DNS: %s -> FAILED", hostname);
    debug_log(buf);
    return 0;
  }

  char *ip = inet_ntoa(*((struct in_addr *)he->h_addr_list[0]));
  strncpy(ip_out, ip, max_len - 1);
  ip_out[max_len - 1] = '\0';

  int is_sinkhole = (strcmp(ip, "0.0.0.0") == 0);

  char buf[256];
  snprintf(buf, sizeof(buf), "DNS: %s -> %s%s", hostname, ip,
           is_sinkhole ? " (SINKHOLE)" : "");
  debug_log(buf);

  return is_sinkhole ? 0 : 1;
}

int check_connection(const char *host, int port) {
  struct sockaddr_in server;
  server.sin_family = AF_INET;
  server.sin_port = htons(port);

  if (!is_ip_address(host)) {
    char ip[64];
    if (!resolve_dns(host, ip, sizeof(ip)))
      return 0;
    if (strcmp(ip, "0.0.0.0") == 0)
      return 0;
    inet_pton(AF_INET, ip, &server.sin_addr);
  } else {
    inet_pton(AF_INET, host, &server.sin_addr);
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1)
    return 0;

  struct timeval tv;
  tv.tv_sec = 3;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

  char buf[128];
  snprintf(buf, sizeof(buf), "Connecting to %s:%d", host, port);
  debug_log(buf);

  int result = connect(sock, (struct sockaddr *)&server, sizeof(server)) >= 0;
  close(sock);

  debug_log(result ? "Connected successfully" : "Connection failed");
  return result;
}

int test_target(const char *type, const char *target, int port,
                int expect_connect) {
  char buf[256];
  snprintf(buf, sizeof(buf), "Testing: %s %s:%d, expect=%s", type, target, port,
           expect_connect ? "connect" : "block");
  debug_log(buf);

  int connected = check_connection(target, port);
  int passed = (connected == expect_connect);

  const char *status = connected ? "CONNECTED" : "BLOCKED";
  const char *result = passed ? "[PASS]" : "[FAIL]";

  if (passed) {
    printf("%s %s:%d -> %s\n", result, target, port, status);
  } else {
    printf("%s %s:%d -> %s (expected %s)\n", result, target, port, status,
           expect_connect ? "connect" : "block");
  }

  return passed;
}

int main() {
  printf("============================================================\n");
  printf("Network Test Client (C)\n");
  printf("============================================================\n");

  char line[512];
  int total = 0, passed = 0;

  while (fgets(line, sizeof(line), stdin)) {
    line[strcspn(line, "\r\n")] = 0;
    if (strlen(line) == 0 || line[0] == '#')
      continue;

    char type[32], target[128], expect_str[32];
    int port;

    if (sscanf(line, "%31s %127s %d %31s", type, target, &port, expect_str) < 4)
      continue;

    printf("\n----------------------------------------\n");

    int expect_connect = (strcmp(expect_str, "connect") == 0);
    int result = test_target(type, target, port, expect_connect);

    total++;
    if (result)
      passed++;
  }

  printf("\n============================================================\n");
  printf("Summary: %d/%d tests passed\n", passed, total);
  printf("============================================================\n");

  return 0;
}