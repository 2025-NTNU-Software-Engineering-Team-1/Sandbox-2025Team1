// AC Code - ZIP submission main.cpp
#include <cctype>
#include <iostream>
#include <string>

extern std::string toUpper(const std::string &s);
// AC Code - utils.cpp

std::string toUpper(const std::string &s) {
  std::string result;
  for (char c : s) {
    result += std::toupper(c);
  }
  return result;
}

int main() {
  std::string line;
  std::getline(std::cin, line);
  std::cout << toUpper(line) << std::endl;
  return 0;
}
