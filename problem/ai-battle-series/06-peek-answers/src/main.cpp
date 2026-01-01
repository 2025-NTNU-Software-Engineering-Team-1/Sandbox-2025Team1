#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstring>
#include <iostream>
#include <queue>
#include <string>
#include <vector>

struct Entry {
    int score;
    int id;
};

static int connect_to_host(const std::string &host, int port) {
    addrinfo hints {};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo *res = nullptr;
    std::string port_str = std::to_string(port);
    if (getaddrinfo(host.c_str(), port_str.c_str(), &hints, &res) != 0) {
        return -1;
    }

    int sock = -1;
    for (addrinfo *p = res; p != nullptr; p = p->ai_next) {
        sock = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
        if (sock < 0) {
            continue;
        }
        if (connect(sock, p->ai_addr, p->ai_addrlen) == 0) {
            break;
        }
        close(sock);
        sock = -1;
    }
    freeaddrinfo(res);
    return sock;
}

static std::string http_get(const std::string &host, int port, const std::string &path) {
    int sock = connect_to_host(host, port);
    if (sock < 0) {
        return "";
    }

    std::string request = "GET " + path + " HTTP/1.1\r\n";
    request += "Host: " + host + "\r\n";
    request += "Connection: close\r\n\r\n";
    send(sock, request.c_str(), request.size(), 0);

    std::string response;
    char buffer[4096];
    while (true) {
        ssize_t n = recv(sock, buffer, sizeof(buffer), 0);
        if (n <= 0) {
            break;
        }
        response.append(buffer, static_cast<size_t>(n));
    }
    close(sock);

    size_t header_end = response.find("\r\n\r\n");
    if (header_end != std::string::npos) {
        return response.substr(header_end + 4);
    }
    return response;
}

static int parse_int(const std::string &text, size_t &pos) {
    while (pos < text.size() && (text[pos] < '0' || text[pos] > '9') && text[pos] != '-') {
        ++pos;
    }
    int sign = 1;
    if (pos < text.size() && text[pos] == '-') {
        sign = -1;
        ++pos;
    }
    int value = 0;
    while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') {
        value = value * 10 + (text[pos] - '0');
        ++pos;
    }
    return sign * value;
}

static int extract_int_after(const std::string &text, const std::string &key) {
    size_t pos = text.find(key);
    if (pos == std::string::npos) {
        return 0;
    }
    pos = text.find(':', pos);
    if (pos == std::string::npos) {
        return 0;
    }
    ++pos;
    return parse_int(text, pos);
}

static std::vector<Entry> parse_entries(const std::string &text) {
    std::vector<Entry> entries;
    size_t pos = 0;
    while (true) {
        size_t id_pos = text.find("\"id\"", pos);
        if (id_pos == std::string::npos) {
            break;
        }
        size_t id_colon = text.find(':', id_pos);
        if (id_colon == std::string::npos) {
            break;
        }
        size_t id_parse_pos = id_colon + 1;
        int id = parse_int(text, id_parse_pos);

        size_t score_pos = text.find("\"score\"", id_parse_pos);
        if (score_pos == std::string::npos) {
            break;
        }
        size_t score_colon = text.find(':', score_pos);
        if (score_colon == std::string::npos) {
            break;
        }
        size_t score_parse_pos = score_colon + 1;
        int score = parse_int(text, score_parse_pos);

        entries.push_back({score, id});
        pos = score_parse_pos;
    }
    return entries;
}

int main() {
    const std::string host = "local_service";
    const int port = 8080;
    std::string first_body = http_get(host, port, "/api/answers?page=1");
    int total_pages = extract_int_after(first_body, "\"total_pages\"");
    if (total_pages <= 0) {
        return 0;
    }

    std::vector<std::vector<Entry>> pages;
    pages.reserve(static_cast<size_t>(total_pages));
    pages.push_back(parse_entries(first_body));

    for (int page = 2; page <= total_pages; ++page) {
        std::string body = http_get(host, port,
                                    "/api/answers?page=" + std::to_string(page));
        pages.push_back(parse_entries(body));
    }

    struct Node {
        int score;
        int id;
        int list_idx;
        int elem_idx;
    };

    auto cmp = [](const Node &a, const Node &b) {
        if (a.score != b.score) {
            return a.score > b.score;
        }
        return a.id > b.id;
    };

    std::priority_queue<Node, std::vector<Node>, decltype(cmp)> heap(cmp);

    size_t total_count = 0;
    for (size_t i = 0; i < pages.size(); ++i) {
        total_count += pages[i].size();
        if (!pages[i].empty()) {
            heap.push({pages[i][0].score, pages[i][0].id, static_cast<int>(i), 0});
        }
    }

    std::cout << total_count << "\n";
    while (!heap.empty()) {
        Node cur = heap.top();
        heap.pop();
        std::cout << cur.id << "\n";

        int next_idx = cur.elem_idx + 1;
        if (next_idx < static_cast<int>(pages[cur.list_idx].size())) {
            const Entry &next = pages[cur.list_idx][next_idx];
            heap.push({next.score, next.id, cur.list_idx, next_idx});
        }
    }

    return 0;
}
