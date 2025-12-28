import sys


def main():
    lines = sys.stdin.read().splitlines()
    if not lines:
        return
    days = int(lines[0].strip())
    reason = lines[1].strip() if len(lines) > 1 else "其他"

    sys.stdout.write("教授您好：\n\n")
    sys.stdout.write(f"我想誠懇地請求將專題報告截止日期延後{days}天，原因是{reason}，近期狀況影響了進度。")
    sys.stdout.write("我已完成大部分實作與測試，剩餘部分會在延期內補齊並提交完整版本。")
    sys.stdout.write("很抱歉造成不便，謝謝您的理解與考量。\n\n")
    sys.stdout.write("學生 敬上\n")


if __name__ == "__main__":
    main()
