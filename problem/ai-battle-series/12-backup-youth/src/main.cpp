#include <bits/stdc++.h>
using namespace std;

struct FileEntry {
    string name;
    long size;
    string md5;
};

struct MD5_CTX {
    uint32_t a, b, c, d;
    uint64_t len_bits;
    unsigned char buffer[64];
    size_t buffer_len;
};

static uint32_t left_rotate(uint32_t x, uint32_t c) {
    return (x << c) | (x >> (32 - c));
}

static void md5_init(MD5_CTX *ctx) {
    ctx->a = 0x67452301;
    ctx->b = 0xefcdab89;
    ctx->c = 0x98badcfe;
    ctx->d = 0x10325476;
    ctx->len_bits = 0;
    ctx->buffer_len = 0;
}

static void md5_process_block(MD5_CTX *ctx, const unsigned char block[64]) {
    static const uint32_t k[64] = {
        0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
        0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
        0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
        0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
        0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
        0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
        0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
        0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
        0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
        0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
        0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
        0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
        0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
        0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
        0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
        0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
    };
    static const uint32_t r[] = {
        7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
        5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
        4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
        6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
    };

    uint32_t w[16];
    for (int i = 0; i < 16; i++) {
        w[i] = (uint32_t)block[i * 4]
             | ((uint32_t)block[i * 4 + 1] << 8)
             | ((uint32_t)block[i * 4 + 2] << 16)
             | ((uint32_t)block[i * 4 + 3] << 24);
    }

    uint32_t a = ctx->a;
    uint32_t b = ctx->b;
    uint32_t c = ctx->c;
    uint32_t d = ctx->d;

    for (int i = 0; i < 64; i++) {
        uint32_t f;
        uint32_t g;
        if (i < 16) {
            f = (b & c) | (~b & d);
            g = (uint32_t)i;
        } else if (i < 32) {
            f = (d & b) | (~d & c);
            g = (uint32_t)((5 * i + 1) % 16);
        } else if (i < 48) {
            f = b ^ c ^ d;
            g = (uint32_t)((3 * i + 5) % 16);
        } else {
            f = c ^ (b | ~d);
            g = (uint32_t)((7 * i) % 16);
        }
        uint32_t temp = d;
        d = c;
        c = b;
        uint32_t sum = a + f + k[i] + w[g];
        b = b + left_rotate(sum, r[i]);
        a = temp;
    }

    ctx->a += a;
    ctx->b += b;
    ctx->c += c;
    ctx->d += d;
}

static void md5_update(MD5_CTX *ctx, const unsigned char *data, size_t len) {
    ctx->len_bits += (uint64_t)len * 8;
    size_t offset = 0;
    while (len > 0) {
        size_t space = 64 - ctx->buffer_len;
        size_t to_copy = len < space ? len : space;
        memcpy(ctx->buffer + ctx->buffer_len, data + offset, to_copy);
        ctx->buffer_len += to_copy;
        offset += to_copy;
        len -= to_copy;
        if (ctx->buffer_len == 64) {
            md5_process_block(ctx, ctx->buffer);
            ctx->buffer_len = 0;
        }
    }
}

static void md5_final(MD5_CTX *ctx, unsigned char digest[16]) {
    unsigned char pad = 0x80;
    md5_update(ctx, &pad, 1);
    unsigned char zero = 0x00;
    while (ctx->buffer_len != 56) {
        md5_update(ctx, &zero, 1);
    }
    unsigned char length_bytes[8];
    for (int i = 0; i < 8; i++) {
        length_bytes[i] = (unsigned char)((ctx->len_bits >> (8 * i)) & 0xff);
    }
    md5_update(ctx, length_bytes, 8);

    uint32_t parts[4] = {ctx->a, ctx->b, ctx->c, ctx->d};
    for (int i = 0; i < 4; i++) {
        digest[i * 4] = (unsigned char)(parts[i] & 0xff);
        digest[i * 4 + 1] = (unsigned char)((parts[i] >> 8) & 0xff);
        digest[i * 4 + 2] = (unsigned char)((parts[i] >> 16) & 0xff);
        digest[i * 4 + 3] = (unsigned char)((parts[i] >> 24) & 0xff);
    }
}

static string md5_hex(const string &input) {
    MD5_CTX ctx;
    unsigned char digest[16];
    md5_init(&ctx);
    md5_update(&ctx, reinterpret_cast<const unsigned char *>(input.data()), input.size());
    md5_final(&ctx, digest);
    static const char hex[] = "0123456789abcdef";
    string out(32, '0');
    for (int i = 0; i < 16; i++) {
        out[i * 2] = hex[(digest[i] >> 4) & 0xF];
        out[i * 2 + 1] = hex[digest[i] & 0xF];
    }
    return out;
}

static int find_entry(const vector<FileEntry> &entries, const string &name) {
    for (size_t i = 0; i < entries.size(); i++) {
        if (entries[i].name == name) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

static vector<FileEntry> load_manifest(const string &filename) {
    vector<FileEntry> entries;
    ifstream fin(filename);
    if (!fin) {
        return entries;
    }
    string line;
    getline(fin, line);
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        stringstream ss(line);
        string name, size_str, md5;
        getline(ss, name, ',');
        getline(ss, size_str, ',');
        getline(ss, md5, ',');
        if (name.empty() || size_str.empty() || md5.empty()) {
            continue;
        }
        FileEntry entry;
        entry.name = name;
        entry.size = stol(size_str);
        entry.md5 = md5;
        entries.push_back(entry);
    }
    return entries;
}

int main() {
    vector<FileEntry> old_entries = load_manifest("old_manifest.csv");
    vector<FileEntry> new_entries = load_manifest("new_manifest.csv");

    int added = 0;
    int deleted = 0;
    int modified = 0;
    int unchanged = 0;
    long old_size = 0;
    long new_size = 0;

    for (const auto &e : old_entries) old_size += e.size;
    for (const auto &e : new_entries) new_size += e.size;

    for (const auto &e : new_entries) {
        int idx = find_entry(old_entries, e.name);
        if (idx < 0) {
            added++;
        } else if (old_entries[idx].md5 != e.md5) {
            modified++;
        } else {
            unchanged++;
        }
    }
    for (const auto &e : old_entries) {
        int idx = find_entry(new_entries, e.name);
        if (idx < 0) {
            deleted++;
        }
    }

    string diff_summary =
        string("Differential Backup Report\n") +
        "Added: " + to_string(added) + "\n" +
        "Deleted: " + to_string(deleted) + "\n" +
        "Modified: " + to_string(modified) + "\n" +
        "Unchanged: " + to_string(unchanged) + "\n";

    ofstream summary_file("diff_summary.txt");
    summary_file << diff_summary;

    string md5 = md5_hex(diff_summary);

    ofstream report("diff_report.json");
    report << "{\n";
    report << "  \"changes\": {\n";
    report << "    \"added\": " << added << ",\n";
    report << "    \"deleted\": " << deleted << ",\n";
    report << "    \"modified\": " << modified << ",\n";
    report << "    \"unchanged\": " << unchanged << "\n";
    report << "  },\n";
    report << "  \"statistics\": {\n";
    report << "    \"old_total_size\": " << old_size << ",\n";
    report << "    \"new_total_size\": " << new_size << ",\n";
    report << "    \"size_diff\": " << (new_size - old_size) << "\n";
    report << "  }\n";
    report << "}\n";

    cout << "Differential backup completed!\n";
    cout << "Added: " << added << ", Deleted: " << deleted
         << ", Modified: " << modified << ", Unchanged: " << unchanged << "\n";
    cout << "Report MD5: " << md5 << "\n";
    return 0;
}
