// Fail Code - 違反 SA (使用 for)
#include "student.h"

long long sum(int arr[], int n) {
  long long result = 0;
  for (int i = 0; i < n; i++) { // 違反: for
    result += arr[i];
  }
  return result;
}
