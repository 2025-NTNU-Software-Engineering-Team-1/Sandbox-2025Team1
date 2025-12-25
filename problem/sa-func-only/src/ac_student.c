// AC Code - 使用 while 而非 for
#include "student.h"

long long sum(int arr[], int n) {
  long long result = 0;
  int i = 0;
  while (i < n) {
    result += arr[i];
    i++;
  }
  return result;
}
