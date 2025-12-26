// Fail Code - 使用 bits/stdc++.h
#include <bits/stdc++.h> // 違反: bits/stdc++.h

int main() {
  std::string line;
  std::getline(std::cin, line);
  for (char &c : line) {
    c = std::toupper(c);
  }
  std::cout << line << std::endl;
  return 0;
}
