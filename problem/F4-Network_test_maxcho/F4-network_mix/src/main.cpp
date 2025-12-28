#include <arpa/inet.h>
#include <cstring>
#include <iostream>
#include <netdb.h>
#include <string>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>


void log_msg(const std::string &msg) {
  std::cout << "[LOG] " << msg << std::endl;
}

int resolve_host(const std::string &host, struct sockaddr_in &server) {
  server.sin_family = AF_INET;

  if (inet_pton(AF_INET, host.c_str(), &server.sin_addr) <= 0) {
    log_msg("Resolving hostname via DNS...");
    struct hostent *he = gethostbyname(host.c_str());
    if (he == nullptr) {
      log_msg("DNS resolution failed!");
      return -1;
    }
    server.sin_addr = *((struct in_addr *)he->h_addr_list[0]);
  }

  char ip_str[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, &server.sin_addr, ip_str, sizeof(ip_str));
  log_msg("Resolved IP: " + std::string(ip_str));
  return 0;
}

void test_redis(const std::string &host, int port) {
  log_msg("Mode: Redis test");
  log_msg("Target host: " + host);
  log_msg("Target port: " + std::to_string(port));

  struct sockaddr_in server;
  if (resolve_host(host, server) < 0) {
    std::cout << "fail" << std::endl;
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    std::cout << "fail" << std::endl;
    return;
  }

  log_msg("Connecting to Redis...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    std::cout << "fail" << std::endl;
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
    std::string resp(buffer);
    while (!resp.empty() && (resp.back() == '\n' || resp.back() == '\r')) {
      resp.pop_back();
    }
    log_msg("Raw response: [" + resp + "]");

    if (resp.find("+OK") == 0) {
      log_msg("Redis AUTH succeeded!");
      std::cout << "good" << std::endl;
    } else {
      log_msg("Redis AUTH failed!");
      std::cout << "fail" << std::endl;
    }
  } else {
    log_msg("No response received!");
    std::cout << "fail" << std::endl;
  }

  close(sock);
}

void test_http_sidecar(const std::string &host, int port) {
  log_msg("Mode: HTTP sidecar test");
  log_msg("Target host: " + host);
  log_msg("Target port: " + std::to_string(port));

  struct sockaddr_in server;
  if (resolve_host(host, server) < 0) {
    std::cout << "fail" << std::endl;
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    std::cout << "fail" << std::endl;
    return;
  }

  log_msg("Connecting...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    std::cout << "fail" << std::endl;
    close(sock);
    return;
  }
  log_msg("Connected!");

  std::string msg = "GET / HTTP/1.0\r\nHost: " + host + "\r\n\r\n";
  log_msg("Sending HTTP GET request...");
  send(sock, msg.c_str(), msg.length(), 0);

  log_msg("Receiving response...");
  char buffer[4096];
  std::string response = "";
  int len;

  while ((len = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
    buffer[len] = '\0';
    response += buffer;
  }

  log_msg("Response length: " + std::to_string(response.length()));

  if (response.find("verify_env_args_success") != std::string::npos) {
    log_msg("Found secret keyword!");
    std::cout << "good" << std::endl;
  } else {
    log_msg("Secret keyword not found!");
    std::cout << "fail" << std::endl;
  }

  close(sock);
}

void test_custom_python(const std::string &host, int port) {
  log_msg("Mode: Custom Python env test");
  log_msg("Target host: " + host);
  log_msg("Target port: " + std::to_string(port));

  struct sockaddr_in server;
  if (resolve_host(host, server) < 0) {
    std::cout << "fail" << std::endl;
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    std::cout << "fail" << std::endl;
    return;
  }

  log_msg("Connecting...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    std::cout << "fail" << std::endl;
    close(sock);
    return;
  }
  log_msg("Connected!");

  std::string msg = "GET / HTTP/1.0\r\nHost: " + host + "\r\n\r\n";
  log_msg("Sending HTTP GET request...");
  send(sock, msg.c_str(), msg.length(), 0);

  log_msg("Receiving response...");
  char buffer[4096];
  std::string response = "";
  int len;

  while ((len = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
    buffer[len] = '\0';
    response += buffer;
  }

  log_msg("Response length: " + std::to_string(response.length()));

  if (response.find("Hello from Server Container!") != std::string::npos) {
    log_msg("Matched Python env signature!");
    std::cout << "good" << std::endl;
  } else {
    log_msg("Python env signature not found!");
    std::cout << "fail" << std::endl;
  }

  close(sock);
}

void test_custom_cpp(const std::string &host, int port) {
  log_msg("Mode: Custom C++ env test");
  log_msg("Target host: " + host);
  log_msg("Target port: " + std::to_string(port));

  struct sockaddr_in server;
  if (resolve_host(host, server) < 0) {
    std::cout << "fail" << std::endl;
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    std::cout << "fail" << std::endl;
    return;
  }

  log_msg("Connecting...");
  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    log_msg("Connection failed!");
    std::cout << "fail" << std::endl;
    close(sock);
    return;
  }
  log_msg("Connected!");

  std::string msg = "GET / HTTP/1.0\r\nHost: " + host + "\r\n\r\n";
  log_msg("Sending HTTP GET request...");
  send(sock, msg.c_str(), msg.length(), 0);

  log_msg("Receiving response...");
  char buffer[4096];
  std::string response = "";
  int len;

  while ((len = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
    buffer[len] = '\0';
    response += buffer;
  }

  log_msg("Response length: " + std::to_string(response.length()));

  if (response.find("Hello from C++ File!") != std::string::npos) {
    log_msg("Matched C++ env signature!");
    std::cout << "good" << std::endl;
  } else {
    log_msg("C++ env signature not found!");
    std::cout << "fail" << std::endl;
  }

  close(sock);
}

void test_external(const std::string &host, int port) {
  log_msg("Mode: External network test");
  log_msg("Target host: " + host);
  log_msg("Target port: " + std::to_string(port));

  struct sockaddr_in server;
  if (resolve_host(host, server) < 0) {
    std::cout << "fail" << std::endl;
    return;
  }
  server.sin_port = htons(port);

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    log_msg("Socket creation failed!");
    std::cout << "fail" << std::endl;
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
    std::cout << "fail" << std::endl;
  } else {
    log_msg("Connection succeeded!");
    std::cout << "good" << std::endl;
  }

  close(sock);
}

int main() {
  std::string type;
  std::string host;
  int port;

  if (!(std::cin >> type >> host >> port)) {
    log_msg("Invalid input format!");
    std::cout << "fail" << std::endl;
    return 0;
  }

  log_msg("Input type: " + type);
  log_msg("Input host: " + host);
  log_msg("Input port: " + std::to_string(port));

  if (type == "redis") {
    test_redis(host, port);
  } else if (type == "http") {
    test_http_sidecar(host, port);
  } else if (type == "custom_python") {
    test_custom_python(host, port);
  } else if (type == "custom_cpp") {
    test_custom_cpp(host, port);
  } else if (type == "external") {
    test_external(host, port);
  } else {
    log_msg("Unknown test type: " + type);
    std::cout << "fail" << std::endl;
  }

  return 0;
}