#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>


void log_msg(const char *msg) { printf("[LOG] %s\n", msg); }

void log_fmt(const char *fmt, const char *arg) {
  printf("[LOG] ");
  printf(fmt, arg);
  printf("\n");
}

void log_fmt_int(const char *fmt, int arg) {
  printf("[LOG] ");
  printf(fmt, arg);
  printf("\n");
}

int resolve_host(const char *host, struct sockaddr_in *server) {
  server->sin_family = AF_INET;

  if (inet_pton(AF_INET, host, &server->sin_addr) <= 0) {
    log_msg("Resolving hostname via DNS...");
    struct hostent *he = gethostbyname(host);
    if (he == NULL) {
      log_msg("DNS resolution failed!");
      return -1;
    }
    server->sin_addr = *((struct in_addr *)he->h_addr_list[0]);
  }

  char ip_str[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, &server->sin_addr, ip_str, sizeof(ip_str));
  log_fmt("Resolved IP: %s", ip_str);
  return 0;
}

void test_redis(const char *host, int port) {
  log_msg("Mode: Redis test");
  log_fmt("Target host: %s", host);
  log_fmt_int("Target port: %d", port);

  struct sockaddr_in server;
  if (resolve_host(host, &server) < 0) {
    printf("fail\n");
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    printf("fail\n");
    return;
  }

  log_msg("Connecting to Redis...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    printf("fail\n");
    close(sock);
    return;
  }
  log_msg("Connected!");

  const char *auth_cmd = "AUTH noj_secret_pass\r\n";
  log_msg("Sending AUTH command...");
  send(sock, auth_cmd, strlen(auth_cmd), 0);

  char buffer[1024];
  memset(buffer, 0, sizeof(buffer));
  int len = recv(sock, buffer, sizeof(buffer) - 1, 0);

  if (len > 0) {
    buffer[strcspn(buffer, "\r\n")] = 0;
    log_fmt("Raw response: [%s]", buffer);

    if (strncmp(buffer, "+OK", 3) == 0) {
      log_msg("Redis AUTH succeeded!");
      printf("good\n");
    } else {
      log_msg("Redis AUTH failed!");
      printf("fail\n");
    }
  } else {
    log_msg("No response received!");
    printf("fail\n");
  }

  close(sock);
}

void test_http_sidecar(const char *host, int port) {
  log_msg("Mode: HTTP sidecar test");
  log_fmt("Target host: %s", host);
  log_fmt_int("Target port: %d", port);

  struct sockaddr_in server;
  if (resolve_host(host, &server) < 0) {
    printf("fail\n");
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    printf("fail\n");
    return;
  }

  log_msg("Connecting...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    printf("fail\n");
    close(sock);
    return;
  }
  log_msg("Connected!");

  char msg[256];
  snprintf(msg, sizeof(msg), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n", host);
  log_msg("Sending HTTP GET request...");
  send(sock, msg, strlen(msg), 0);

  log_msg("Receiving response...");
  char buffer[4096];
  int total_len = 0;
  int len;

  while ((len = recv(sock, buffer + total_len, sizeof(buffer) - total_len - 1,
                     0)) > 0) {
    total_len += len;
    if (total_len >= sizeof(buffer) - 1)
      break;
  }
  buffer[total_len] = '\0';

  log_fmt_int("Response length: %d", total_len);

  if (strstr(buffer, "verify_env_args_success")) {
    log_msg("Found secret keyword!");
    printf("good\n");
  } else {
    log_msg("Secret keyword not found!");
    printf("fail\n");
  }

  close(sock);
}

void test_custom_python(const char *host, int port) {
  log_msg("Mode: Custom Python env test");
  log_fmt("Target host: %s", host);
  log_fmt_int("Target port: %d", port);

  struct sockaddr_in server;
  if (resolve_host(host, &server) < 0) {
    printf("fail\n");
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    printf("fail\n");
    return;
  }

  log_msg("Connecting...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    printf("fail\n");
    close(sock);
    return;
  }
  log_msg("Connected!");

  char msg[256];
  snprintf(msg, sizeof(msg), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n", host);
  log_msg("Sending HTTP GET request...");
  send(sock, msg, strlen(msg), 0);

  log_msg("Receiving response...");
  char buffer[4096];
  int total_len = 0;
  int len;

  while ((len = recv(sock, buffer + total_len, sizeof(buffer) - total_len - 1,
                     0)) > 0) {
    total_len += len;
    if (total_len >= sizeof(buffer) - 1)
      break;
  }
  buffer[total_len] = '\0';

  log_fmt_int("Response length: %d", total_len);

  if (strstr(buffer, "Hello from Server Container!")) {
    log_msg("Matched Python env signature!");
    printf("good\n");
  } else {
    log_msg("Python env signature not found!");
    printf("fail\n");
  }

  close(sock);
}

void test_custom_cpp(const char *host, int port) {
  log_msg("Mode: Custom C++ env test");
  log_fmt("Target host: %s", host);
  log_fmt_int("Target port: %d", port);

  struct sockaddr_in server;
  if (resolve_host(host, &server) < 0) {
    printf("fail\n");
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    printf("fail\n");
    return;
  }

  log_msg("Connecting...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    printf("fail\n");
    close(sock);
    return;
  }
  log_msg("Connected!");

  char msg[256];
  snprintf(msg, sizeof(msg), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n", host);
  log_msg("Sending HTTP GET request...");
  send(sock, msg, strlen(msg), 0);

  log_msg("Receiving response...");
  char buffer[4096];
  int total_len = 0;
  int len;

  while ((len = recv(sock, buffer + total_len, sizeof(buffer) - total_len - 1,
                     0)) > 0) {
    total_len += len;
    if (total_len >= sizeof(buffer) - 1)
      break;
  }
  buffer[total_len] = '\0';

  log_fmt_int("Response length: %d", total_len);

  if (strstr(buffer, "Hello from C++ File!")) {
    log_msg("Matched C++ env signature!");
    printf("good\n");
  } else {
    log_msg("C++ env signature not found!");
    printf("fail\n");
  }

  close(sock);
}

void test_external(const char *host, int port) {
  log_msg("Mode: External network test");
  log_fmt("Target host: %s", host);
  log_fmt_int("Target port: %d", port);

  struct sockaddr_in server;
  if (resolve_host(host, &server) < 0) {
    printf("fail\n");
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    printf("fail\n");
    return;
  }

  struct timeval timeout;
  timeout.tv_sec = 3;
  timeout.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (const char *)&timeout,
             sizeof(timeout));

  log_msg("Attempting connection...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    printf("fail\n");
  } else {
    log_msg("Connection succeeded!");
    printf("good\n");
  }

  close(sock);
}

int main() {
  char type[32];
  char host[128];
  int port;

  if (scanf("%31s %127s %d", type, host, &port) != 3) {
    log_msg("Invalid input format!");
    printf("fail\n");
    return 0;
  }

  log_fmt("Input type: %s", type);
  log_fmt("Input host: %s", host);
  log_fmt_int("Input port: %d", port);

  if (strcmp(type, "redis") == 0) {
    test_redis(host, port);
  } else if (strcmp(type, "http") == 0) {
    test_http_sidecar(host, port);
  } else if (strcmp(type, "custom_python") == 0) {
    test_custom_python(host, port);
  } else if (strcmp(type, "custom_cpp") == 0) {
    test_custom_cpp(host, port);
  } else if (strcmp(type, "external") == 0) {
    test_external(host, port);
  } else {
    log_fmt("Unknown test type: %s", type);
    printf("fail\n");
  }

  return 0;
}