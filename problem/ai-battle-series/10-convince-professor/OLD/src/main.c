#include <stdio.h>
#include <string.h>

int main(void) {
    int days = 0;
    if (scanf("%d", &days) != 1) {
        return 0;
    }
    char reason[128];
    int ch = getchar();
    if (ch == EOF) {
        return 0;
    }
    if (!fgets(reason, sizeof(reason), stdin)) {
        return 0;
    }
    if (reason[0] == '\n' || reason[0] == '\r') {
        if (!fgets(reason, sizeof(reason), stdin)) {
            return 0;
        }
    }
    reason[strcspn(reason, "\r\n")] = '\0';

    printf("教授您好：\n\n");
    printf("我想誠懇地請求將專題報告截止日期延後%d天，原因是%s，近期狀況影響了進度。\n", days, reason);
    printf("我已完成大部分實作與測試，剩餘部分會在延期內補齊並提交完整版本。\n");
    printf("很抱歉造成不便，謝謝您的理解與考量。\n\n");
    printf("學生 敬上\n");
    return 0;
}
