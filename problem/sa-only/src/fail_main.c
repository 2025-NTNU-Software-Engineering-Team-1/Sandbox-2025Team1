// Fail Code - 違反 SA (使用 while)
#include <stdio.h>

int main() {
  int n;
  scanf("%d", &n);
  int sum = 0;
  while (n > 0) { // while
    sum += n;
    n--;
  }
  printf("%d\n", sum);
  return 0;
}
