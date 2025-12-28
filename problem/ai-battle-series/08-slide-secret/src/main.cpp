#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string filename;
    if (!(cin >> filename)) {
        return 0;
    }

    ifstream fin(filename, ios::binary);
    if (!fin) {
        return 0;
    }

    unsigned char header[54];
    fin.read(reinterpret_cast<char *>(header), 54);
    if (!fin) {
        return 0;
    }

    int32_t width = *reinterpret_cast<int32_t *>(&header[18]);
    int32_t height = *reinterpret_cast<int32_t *>(&header[22]);
    if (height < 0) {
        height = -height;
    }

    int row_padded = (width * 3 + 3) & (~3);
    vector<unsigned char> row(row_padded);

    int bit_count = 0;
    unsigned char current = 0;
    bool done = false;

    for (int i = 0; i < height && !done; i++) {
        fin.read(reinterpret_cast<char *>(row.data()), row_padded);
        if (!fin) {
            break;
        }
        for (int j = 0; j < width; j++) {
            unsigned char r = row[j * 3 + 2];
            current = static_cast<unsigned char>((current << 1) | (r & 1));
            bit_count++;
            if (bit_count == 8) {
                if (current == 0) {
                    done = true;
                    break;
                }
                cout << static_cast<char>(current);
                bit_count = 0;
                current = 0;
            }
        }
    }

    cout << "
";
    return 0;
}
