#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main () {
    vector <string> vec;
    vec.push_back ("Hello");
    vec.push_back ("World");
    for (const auto &str : vec) {
        cout << str << endl;
    }
    while (true) {
        // Infinite loop
    }
    return 0;
}
