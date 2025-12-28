/*
 * Combined Pull_image + URL_IP network test
 * Input format (from .in file):
 *   - sidecar <hostname> <port>      -> test sidecar container connection
 *   - external ip <ip> <port>        -> test external IP connection
 *   - external url <hostname> <port> -> test external URL connection
 * Output: debug logs showing connection attempts and results
 */

#include <arpa/inet.h>
#include <cstring>
#include <errno.h>
#include <fcntl.h>
#include <iostream>
#include <netdb.h>
#include <netinet/in.h>
#include <sstream>
#include <string>
#include <sys/socket.h>
#include <unistd.h>

using namespace std;

void debug(const string &msg) { cout << "[DEBUG] " << msg << endl; }

int connect_with_timeout(const char *host, int port, int timeout_sec) {
  struct addrinfo hints, *res, *p;
  int sockfd = -1;
  int status;

  memset(&hints, 0, sizeof(hints));
  hints.ai_family = AF_INET;
  hints.ai_socktype = SOCK_STREAM;

  char port_str[16];
  snprintf(port_str, sizeof(port_str), "%d", port);

  debug("Resolving " + string(host) + ":" + to_string(port) + "...");

  if ((status = getaddrinfo(host, port_str, &hints, &res)) != 0) {
    debug("DNS resolution failed: " + string(gai_strerror(status)));
    return -1;
  }

  for (p = res; p != NULL; p = p->ai_next) {
    // Get resolved IP
    char ip_str[INET_ADDRSTRLEN];
    struct sockaddr_in *ipv4 = (struct sockaddr_in *)p->ai_addr;
    inet_ntop(AF_INET, &(ipv4->sin_addr), ip_str, INET_ADDRSTRLEN);
    debug("Resolved to IP: " + string(ip_str));

    // Check for sinkhole
    if (strcmp(ip_str, "0.0.0.0") == 0) {
      debug("DNS sinkholed! This URL is not whitelisted.");
      freeaddrinfo(res);
      return -2; // Special code for sinkhole
    }

    sockfd = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
    if (sockfd == -1)
      continue;

    // Set timeout
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

    debug("Connect failed: " + string(strerror(errno)));
    close(sockfd);
    sockfd = -1;
  }

  freeaddrinfo(res);
  return sockfd;
}

void test_redis(const string &host, int port) {
  debug("Testing Redis sidecar at " + host + ":" + to_string(port));

  int sockfd = connect_with_timeout(host.c_str(), port, 5);
  if (sockfd < 0) {
    cout << "RESULT: FAIL" << endl;
    return;
  }

  // Send Redis AUTH command
  const char *password = "noj_secret_pass";
  char cmd[256];
  snprintf(cmd, sizeof(cmd), "AUTH %s\r\n", password);

  debug("Sending AUTH command...");
  send(sockfd, cmd, strlen(cmd), 0);

  char response[1024] = {0};
  recv(sockfd, response, sizeof(response) - 1, 0);
  debug("Raw response: " + string(response));

  if (strncmp(response, "+OK", 3) == 0) {
    debug("Redis AUTH successful!");
    cout << "RESULT: PASS" << endl;
  } else {
    debug("Redis AUTH failed");
    cout << "RESULT: FAIL" << endl;
  }

  close(sockfd);
}

void test_http(const string &host, int port) {
  debug("Testing HTTP sidecar at " + host + ":" + to_string(port));

  int sockfd = connect_with_timeout(host.c_str(), port, 5);
  if (sockfd < 0) {
    cout << "RESULT: FAIL" << endl;
    return;
  }

  // Send HTTP GET request
  char request[512];
  snprintf(request, sizeof(request), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n",
           host.c_str());

  debug("Sending HTTP GET request...");
  send(sockfd, request, strlen(request), 0);

  debug("Receiving response...");
  string response;
  char buffer[4096];
  ssize_t n;
  while ((n = recv(sockfd, buffer, sizeof(buffer) - 1, 0)) > 0) {
    buffer[n] = '\0';
    response += buffer;
  }

  debug("Response length: " + to_string(response.length()));
  if (response.length() > 200) {
    debug("Content snippet: " + response.substr(0, 200) + "...");
  } else {
    debug("Content: " + response);
  }

  if (response.find("verify_env_args_success") != string::npos) {
    debug("HTTP secret keyword found!");
    cout << "RESULT: PASS" << endl;
  } else {
    debug("HTTP secret keyword NOT found");
    cout << "RESULT: FAIL" << endl;
  }

  close(sockfd);
}

void test_external(const string &host, int port, bool is_url) {
  string conn_type = is_url ? "URL" : "IP";
  debug("Testing external " + conn_type + " connection to " + host + ":" +
        to_string(port));

  int sockfd = connect_with_timeout(host.c_str(), port, 5);

  if (sockfd == -2) {
    cout << "RESULT: BLOCKED (sinkhole)" << endl;
    return;
  }

  if (sockfd < 0) {
    debug("Connection blocked or failed");
    cout << "RESULT: BLOCKED" << endl;
    return;
  }

  debug("Connection successful!");

  if (port == 443) {
    debug("HTTPS port connected, TLS handshake not performed");
  } else if (port == 80) {
    char request[512];
    snprintf(request, sizeof(request), "GET / HTTP/1.0\r\nHost: %s\r\n\r\n",
             host.c_str());
    send(sockfd, request, strlen(request), 0);

    char response[1024] = {0};
    recv(sockfd, response, sizeof(response) - 1, 0);
    debug("HTTP response snippet: " + string(response).substr(0, 100));
  }

  cout << "RESULT: PASS" << endl;
  close(sockfd);
}

int main() {
  debug("============================================================");
  debug("Combined Pull_image + URL_IP Network Test (C++)");
  debug("============================================================");

  string line;
  getline(cin, line);
  debug("Input: " + line);

  if (line.empty()) {
    debug("No input provided");
    cout << "RESULT: FAIL (no input)" << endl;
    return 0;
  }

  istringstream iss(line);
  string cmd;
  iss >> cmd;

  if (cmd == "sidecar") {
    string host;
    int port;
    iss >> host >> port;

    debug("Sidecar test: " + host + ":" + to_string(port));

    if (port == 6379) {
      test_redis(host, port);
    } else if (port == 8080) {
      test_http(host, port);
    } else {
      debug("Unknown sidecar port, attempting generic TCP connect");
      test_external(host, port, false);
    }
  } else if (cmd == "external") {
    string ext_type, host;
    int port;
    iss >> ext_type >> host >> port;

    if (ext_type == "ip") {
      test_external(host, port, false);
    } else if (ext_type == "url") {
      test_external(host, port, true);
    } else {
      debug("Unknown external type: " + ext_type);
      cout << "RESULT: FAIL (bad input)" << endl;
    }
  } else {
    debug("Unknown command: " + cmd);
    cout << "RESULT: FAIL (unknown command)" << endl;
  }

  debug("============================================================");
  debug("Test complete");
  debug("============================================================");

  return 0;
}
