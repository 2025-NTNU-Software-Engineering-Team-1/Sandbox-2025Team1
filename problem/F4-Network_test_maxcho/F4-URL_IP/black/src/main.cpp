#include <arpa/inet.h>
#include <iostream>
#include <netdb.h>
#include <string>
#include <sys/socket.h>
#include <unistd.h>
#include <vector>


struct Target {
  std::string host;
  int port;
  bool expect_success;
  std::string label;
};

void check(const Target &t) {
  struct sockaddr_in server;
  server.sin_family = AF_INET;
  server.sin_port = htons(t.port);

  if (inet_pton(AF_INET, t.host.c_str(), &server.sin_addr) <= 0) {
    struct hostent *he = gethostbyname(t.host.c_str());
    if (he == NULL) {
      if (t.expect_success) {
        std::cout << "[FAIL] " << t.host << ":" << t.port << " -> DNS FAILED ("
                  << t.label << ")" << std::endl;
      } else {
        std::cout << "[PASS] " << t.host << ":" << t.port << " -> DNS FAILED ("
                  << t.label << ")" << std::endl;
      }
      return;
    }
    server.sin_addr = *((struct in_addr *)he->h_addr_list[0]);
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    std::cout << "[FAIL] " << t.host << ":" << t.port << " -> SOCKET ERROR"
              << std::endl;
    return;
  }

  struct timeval timeout;
  timeout.tv_sec = 3;
  timeout.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

  bool connected =
      (connect(sock, (struct sockaddr *)&server, sizeof(server)) >= 0);
  close(sock);

  if (connected == t.expect_success) {
    std::cout << "[PASS] " << t.host << ":" << t.port << " -> "
              << (connected ? "CONNECTED" : "BLOCKED") << " (" << t.label << ")"
              << std::endl;
  } else {
    std::cout << "[FAIL] " << t.host << ":" << t.port << " -> "
              << (connected ? "CONNECTED" : "BLOCKED") << " (expected "
              << (t.expect_success ? "connect" : "block") << ", " << t.label
              << ")" << std::endl;
  }
}

int main() {
  std::cout << "==========================================================="
            << std::endl;
  std::cout << "Network BLACKLIST Test (C++)" << std::endl;
  std::cout << "Config: Blacklist IP=[1.1.1.1], URL=[www.google.com]"
            << std::endl;
  std::cout << "==========================================================="
            << std::endl;

  std::vector<Target> targets = {
      // Blacklisted IP - should be blocked
      {"1.1.1.1", 443, false, "blacklisted IP"},
      {"1.1.1.1", 80, false, "blacklisted IP"},
      {"1.1.1.1", 53, true, "NAT redirect"}, // Port 53 always NAT redirect

      // Non-blacklisted IPs - should connect
      {"9.9.9.9", 443, true, "not blacklisted"},
      {"8.8.8.8", 443, true, "not blacklisted"},
      {"9.9.9.9", 53, true, "NAT redirect"},

      // Blacklisted URL - sinkholed
      {"www.google.com", 443, false, "sinkholed"},
      {"www.google.com", 80, false, "sinkholed"},

      // Non-blacklisted URLs - should connect
      {"github.com", 443, true, "not blacklisted"},
      {"facebook.com", 443, true, "not blacklisted"},
      {"amazon.com", 443, true, "not blacklisted"},
  };

  std::cout << "\n--- Running Tests ---" << std::endl;
  for (const auto &t : targets) {
    check(t);
  }

  std::cout << "\n==========================================================="
            << std::endl;
  std::cout << "Test complete" << std::endl;
  std::cout << "==========================================================="
            << std::endl;

  return 0;
}