// AC Code - utils.cpp
#include <cctype>
#include <string>

std::string toUpper(const std::string &s) {
  std::string result;
  for (char c : s) {
    result += std::toupper(c);
  }
  return result;
}
