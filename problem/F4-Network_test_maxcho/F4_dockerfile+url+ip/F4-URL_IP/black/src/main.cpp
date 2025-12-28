#include <arpa/inet.h>
#include <cstring>
#include <iostream>
#include <netdb.h>
#include <sstream>
#include <string>
#include <sys/socket.h>
#include <unistd.h>


void debug_log(const std::string &msg) {
  std::cout << "[DEBUG] " << msg << std::endl;
}

bool is_ip_address(const std::string &str) {
  struct in_addr addr;
  return inet_pton(AF_INET, str.c_str(), &addr) == 1;
}

std::pair<std::string, bool> resolve_dns(const std::string &hostname) {
  struct hostent *he = gethostbyname(hostname.c_str());
  if (!he) {
    debug_log("DNS: " + hostname + " -> FAILED");
    return {"", false};
  }

  char *ip = inet_ntoa(*((struct in_addr *)he->h_addr_list[0]));
  bool is_sinkhole = (strcmp(ip, "0.0.0.0") == 0);

  std::string result = std::string("DNS: ") + hostname + " -> " + ip;
  if (is_sinkhole)
    result += " (SINKHOLE)";
  debug_log(result);

  return {ip, !is_sinkhole};
}

bool check_connection(const std::string &host, int port) {
  struct sockaddr_in server;
  server.sin_family = AF_INET;
  server.sin_port = htons(port);

  if (!is_ip_address(host)) {
    auto [ip, resolved] = resolve_dns(host);
    if (!resolved || ip == "0.0.0.0")
      return false;
    inet_pton(AF_INET, ip.c_str(), &server.sin_addr);
  } else {
    inet_pton(AF_INET, host.c_str(), &server.sin_addr);
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1)
    return false;

  struct timeval tv;
  tv.tv_sec = 3;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

  debug_log("Connecting to " + host + ":" + std::to_string(port));
  bool result =
      (connect(sock, (struct sockaddr *)&server, sizeof(server)) >= 0);
  close(sock);

  debug_log(result ? "Connected successfully" : "Connection failed");
  return result;
}

bool test_target(const std::string &type, const std::string &target, int port,
                 bool expect_connect) {
  debug_log("Testing: " + type + " " + target + ":" + std::to_string(port) +
            ", expect=" + (expect_connect ? "connect" : "block"));

  bool connected = check_connection(target, port);
  bool passed = (connected == expect_connect);

  std::string status = connected ? "CONNECTED" : "BLOCKED";
  std::string result = passed ? "[PASS]" : "[FAIL]";

  if (passed) {
    std::cout << result << " " << target << ":" << port << " -> " << status
              << std::endl;
  } else {
    std::cout << result << " " << target << ":" << port << " -> " << status
              << " (expected " << (expect_connect ? "connect" : "block") << ")"
              << std::endl;
  }

  return passed;
}

int main() {
  std::cout << std::string(60, '=') << std::endl;
  std::cout << "Network Test Client (C++)" << std::endl;
  std::cout << std::string(60, '=') << std::endl;

  std::string line;
  int total = 0, passed = 0;

  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#')
      continue;

    std::istringstream iss(line);
    std::string type, target, expect_str;
    int port;

    iss >> type >> target >> port >> expect_str;

    std::cout << "\n" << std::string(40, '-') << std::endl;

    bool expect_connect = (expect_str == "connect");
    bool result = test_target(type, target, port, expect_connect);

    total++;
    if (result)
      passed++;
  }

  std::cout << "\n" << std::string(60, '=') << std::endl;
  std::cout << "Summary: " << passed << "/" << total << " tests passed"
            << std::endl;
  std::cout << std::string(60, '=') << std::endl;

  return 0;
}