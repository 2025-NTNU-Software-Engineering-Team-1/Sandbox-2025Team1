// AC Code - ZIP submission main.cpp
#include <iostream>
#include <string>

extern std::string toUpper(const std::string &s);

int main() {
  std::string line;
  std::getline(std::cin, line);
  std::cout << toUpper(line) << std::endl;
  return 0;
}
