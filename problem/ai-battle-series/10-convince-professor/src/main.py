import sys


def reason_phrase(reason: str) -> str:
    if reason == "生病":
        return "生病就醫"
    if reason == "家庭":
        return "家庭因素"
    if reason == "技術問題":
        return "技術問題"
    return "其他個人因素"


def main() -> None:
    lines = [
        line.strip() for line in sys.stdin.read().splitlines()
        if line.strip() != ""
    ]
    if not lines:
        return
    try:
        days = int(lines[0])
    except ValueError:
        return
    reason = lines[1] if len(lines) > 1 else "其他"

    phrase = reason_phrase(reason)

    letter = ("教授您好：\n\n"
              f"我是修課學生，想誠懇地請求將專題報告截止日期延後{days}天。"
              f"因為{phrase}影響進度，目前已完成約70%內容，剩餘部分主要是測試與文件整理。"
              "若能獲得延期，我會在新期限前提交完整版本並願意補充相關證明。"
              "對於造成的不便深感抱歉，感謝您的理解與指導。\n\n"
              "學生 敬上\n")

    sys.stdout.write(letter)


if __name__ == "__main__":
    main()
