#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

typedef struct {
    int score;
    int id;
} Entry;

typedef struct {
    Entry *items;
    int count;
    int capacity;
} Page;

typedef struct {
    int score;
    int id;
    int list_idx;
    int elem_idx;
} Node;

static void page_push(Page *page, Entry value) {
    if (page->count >= page->capacity) {
        int new_cap = page->capacity ? page->capacity * 2 : 8;
        Entry *next = realloc(page->items, (size_t)new_cap * sizeof(Entry));
        if (!next) {
            return;
        }
        page->items = next;
        page->capacity = new_cap;
    }
    page->items[page->count++] = value;
}

static void page_free(Page *page) {
    free(page->items);
    page->items = NULL;
    page->count = 0;
    page->capacity = 0;
}

static int connect_to_host(const char *host, int port) {
    struct addrinfo hints;
    struct addrinfo *res = NULL;
    struct addrinfo *p = NULL;
    char port_str[16];
    int sock = -1;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    snprintf(port_str, sizeof(port_str), "%d", port);

    if (getaddrinfo(host, port_str, &hints, &res) != 0) {
        return -1;
    }

    for (p = res; p != NULL; p = p->ai_next) {
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

static char *http_get(const char *host, int port, const char *path) {
    int sock = connect_to_host(host, port);
    if (sock < 0) {
        return NULL;
    }

    char request[256];
    snprintf(request, sizeof(request),
             "GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n",
             path, host);
    send(sock, request, strlen(request), 0);

    char buffer[4096];
    size_t capacity = 0;
    size_t length = 0;
    char *response = NULL;
    while (1) {
        ssize_t n = recv(sock, buffer, sizeof(buffer), 0);
        if (n <= 0) {
            break;
        }
        size_t needed = length + (size_t)n + 1;
        if (needed > capacity) {
            size_t new_cap = capacity ? capacity * 2 : 8192;
            while (new_cap < needed) {
                new_cap *= 2;
            }
            char *next = realloc(response, new_cap);
            if (!next) {
                free(response);
                close(sock);
                return NULL;
            }
            response = next;
            capacity = new_cap;
        }
        memcpy(response + length, buffer, (size_t)n);
        length += (size_t)n;
    }
    close(sock);

    if (!response) {
        return NULL;
    }
    response[length] = '\0';

    char *body = strstr(response, "\r\n\r\n");
    if (body) {
        body += 4;
    } else {
        body = response;
    }

    char *output = strdup(body);
    free(response);
    return output;
}

static int parse_int(const char *text, size_t *pos) {
    while (text[*pos] && (text[*pos] < '0' || text[*pos] > '9') && text[*pos] != '-') {
        (*pos)++;
    }
    int sign = 1;
    if (text[*pos] == '-') {
        sign = -1;
        (*pos)++;
    }
    int value = 0;
    while (text[*pos] >= '0' && text[*pos] <= '9') {
        value = value * 10 + (text[*pos] - '0');
        (*pos)++;
    }
    return sign * value;
}

static int extract_int_after(const char *text, const char *key) {
    const char *pos = strstr(text, key);
    if (!pos) {
        return 0;
    }
    const char *colon = strchr(pos, ':');
    if (!colon) {
        return 0;
    }
    size_t idx = (size_t)(colon - text + 1);
    return parse_int(text, &idx);
}

static Page parse_entries(const char *text) {
    Page page = {0};
    size_t pos = 0;

    while (1) {
        const char *id_ptr = strstr(text + pos, "\"id\"");
        if (!id_ptr) {
            break;
        }
        const char *id_colon = strchr(id_ptr, ':');
        if (!id_colon) {
            break;
        }
        size_t id_pos = (size_t)(id_colon - text + 1);
        int id = parse_int(text, &id_pos);

        const char *score_ptr = strstr(text + id_pos, "\"score\"");
        if (!score_ptr) {
            break;
        }
        const char *score_colon = strchr(score_ptr, ':');
        if (!score_colon) {
            break;
        }
        size_t score_pos = (size_t)(score_colon - text + 1);
        int score = parse_int(text, &score_pos);

        page_push(&page, (Entry){score, id});
        pos = score_pos;
    }

    return page;
}

static int node_less(Node a, Node b) {
    if (a.score != b.score) {
        return a.score < b.score;
    }
    return a.id < b.id;
}

static void heap_push(Node *heap, int *size, Node value) {
    int idx = (*size)++;
    heap[idx] = value;
    while (idx > 0) {
        int parent = (idx - 1) / 2;
        if (node_less(heap[idx], heap[parent])) {
            Node tmp = heap[idx];
            heap[idx] = heap[parent];
            heap[parent] = tmp;
            idx = parent;
        } else {
            break;
        }
    }
}

static Node heap_pop(Node *heap, int *size) {
    Node root = heap[0];
    (*size)--;
    if (*size > 0) {
        heap[0] = heap[*size];
        int idx = 0;
        while (1) {
            int left = idx * 2 + 1;
            int right = left + 1;
            int smallest = idx;
            if (left < *size && node_less(heap[left], heap[smallest])) {
                smallest = left;
            }
            if (right < *size && node_less(heap[right], heap[smallest])) {
                smallest = right;
            }
            if (smallest == idx) {
                break;
            }
            Node tmp = heap[idx];
            heap[idx] = heap[smallest];
            heap[smallest] = tmp;
            idx = smallest;
        }
    }
    return root;
}

int main(void) {
    const char *host = "local_service";
    int port = 8080;
    char *body = http_get(host, port, "/api/answers?page=1");
    if (!body) {
        return 0;
    }

    int total_pages = extract_int_after(body, "\"total_pages\"");
    if (total_pages <= 0) {
        free(body);
        return 0;
    }

    Page *pages = calloc((size_t)total_pages, sizeof(Page));
    pages[0] = parse_entries(body);
    free(body);

    for (int page = 2; page <= total_pages; ++page) {
        char path[64];
        snprintf(path, sizeof(path), "/api/answers?page=%d", page);
        body = http_get(host, port, path);
        if (!body) {
            continue;
        }
        pages[page - 1] = parse_entries(body);
        free(body);
    }

    int total_count = 0;
    for (int i = 0; i < total_pages; ++i) {
        total_count += pages[i].count;
    }

    Node *heap = malloc((size_t)total_pages * sizeof(Node));
    int heap_size = 0;
    for (int i = 0; i < total_pages; ++i) {
        if (pages[i].count > 0) {
            Entry e = pages[i].items[0];
            heap_push(heap, &heap_size, (Node){e.score, e.id, i, 0});
        }
    }

    printf("%d\n", total_count);
    while (heap_size > 0) {
        Node cur = heap_pop(heap, &heap_size);
        printf("%d\n", cur.id);
        int next_idx = cur.elem_idx + 1;
        if (next_idx < pages[cur.list_idx].count) {
            Entry next = pages[cur.list_idx].items[next_idx];
            heap_push(heap, &heap_size,
                      (Node){next.score, next.id, cur.list_idx, next_idx});
        }
    }

    free(heap);
    for (int i = 0; i < total_pages; ++i) {
        page_free(&pages[i]);
    }
    free(pages);
    return 0;
}
