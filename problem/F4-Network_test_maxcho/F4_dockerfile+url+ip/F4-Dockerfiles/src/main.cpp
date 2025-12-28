#include <arpa/inet.h>
#include <cstring>
#include <errno.h>
#include <fcntl.h>
#include <iostream>
#include <netdb.h>
#include <sstream>
#include <string>
#include <sys/socket.h>
#include <unistd.h>


void debug_log(const std::string &msg) {
  std::cout << "[DEBUG] " << msg << std::endl;
}

bool check_connection(const std::string &host, int port, int timeout_sec = 5) {
  struct sockaddr_in server;
  server.sin_family = AF_INET;
  server.sin_port = htons(port);

  // Check if it's an IP or hostname
  if (inet_pton(AF_INET, host.c_str(), &server.sin_addr) <= 0) {
    debug_log("Resolving hostname: " + host);
    struct hostent *he = gethostbyname(host.c_str());
    if (!he) {
      debug_log("DNS resolution failed");
      return false;
    }
    server.sin_addr = *((struct in_addr *)he->h_addr_list[0]);
    std::string resolved_ip = inet_ntoa(server.sin_addr);
    debug_log("Resolved to: " + resolved_ip);
    if (resolved_ip == "0.0.0.0") {
      debug_log("DNS sinkholed");
      return false;
    }
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1) {
    debug_log("Socket creation failed");
    return false;
  }

  // Set timeout
  struct timeval tv;
  tv.tv_sec = timeout_sec;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
  setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  debug_log("Connecting to " + host + ":" + std::to_string(port));
  bool result =
      (connect(sock, (struct sockaddr *)&server, sizeof(server)) >= 0);
  close(sock);

  if (result) {
    debug_log("Connection successful");
  } else {
    debug_log("Connection failed: " + std::string(strerror(errno)));
  }
  return result;
}

std::string send_http_request(const std::string &host, int port,
                              const std::string &path = "/") {
  struct sockaddr_in server;
  server.sin_family = AF_INET;
  server.sin_port = htons(port);

  if (inet_pton(AF_INET, host.c_str(), &server.sin_addr) <= 0) {
    struct hostent *he = gethostbyname(host.c_str());
    if (!he) {
      debug_log("DNS resolution failed for HTTP request");
      return "";
    }
    server.sin_addr = *((struct in_addr *)he->h_addr_list[0]);
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == -1)
    return "";

  struct timeval tv;
  tv.tv_sec = 5;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
    close(sock);
    return "";
  }

  debug_log("Sending HTTP GET to " + path);
  std::string request =
      "GET " + path + " HTTP/1.0\r\nHost: " + host + "\r\n\r\n";
  send(sock, request.c_str(), request.length(), 0);

  debug_log("Receiving response...");
  char buffer[4096];
  std::string response;
  int len;
  while ((len = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
    buffer[len] = '\0';
    response += buffer;
  }
  close(sock);

  debug_log("Response length: " + std::to_string(response.length()) + " bytes");
  return response;
}

bool test_docker_env(const std::string &env_name, int port,
                     const std::string &signature) {
  debug_log("Testing Docker env: " + env_name + ":" + std::to_string(port));
  debug_log("Expected signature: " + signature);

  std::string response = send_http_request(env_name, port);

  if (response.find(signature) != std::string::npos) {
    debug_log("Signature matched!");
    return true;
  } else {
    debug_log("Signature NOT found");
    return false;
  }
}

bool test_connectivity(const std::string &target, int port,
                       bool expect_success) {
  debug_log("Testing: " + target + ":" + std::to_string(port));
  debug_log("Expecting: " + std::string(expect_success ? "connect" : "block"));

  bool result = check_connection(target, port);

  if (result == expect_success) {
    debug_log("Result as expected");
    return true;
  } else {
    debug_log("Unexpected result");
    return false;
  }
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

    iss >> type >> target >> port;

    std::cout << "\n" << std::string(60, '-') << std::endl;
    std::cout << "Test: " << type << " " << target << ":" << port << std::endl;
    std::cout << std::string(60, '-') << std::endl;

    bool result = false;

    if (type == "DOCKER") {
      // Read remaining as signature
      std::string signature;
      std::getline(iss, signature);
      while (!signature.empty() && signature[0] == ' ')
        signature.erase(0, 1);
      result = test_docker_env(target, port, signature);
    } else if (type == "IP" || type == "URL") {
      iss >> expect_str;
      bool expect_connect = (expect_str != "block");
      result = test_connectivity(target, port, expect_connect);
    } else {
      debug_log("Unknown test type: " + type);
    }

    std::cout << "Result: [" << (result ? "PASS" : "FAIL") << "]" << std::endl;
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