#!/usr/bin/env python3
import os
import re
import sys
from typing import List, Optional, Tuple

DEBUG = os.environ.get("CHECKER_DEBUG", "1").strip().lower() not in (
    "",
    "0",
    "false",
    "no",
    "off",
)

REASON_KEYWORDS = {
    "生病": ["生病", "就醫", "住院", "感冒", "發燒", "病"],
    "家庭": ["家庭", "家人", "親人", "家中", "家裡", "照顧", "家務"],
    "技術問題": ["技術", "系統", "程式", "電腦", "設備", "伺服", "環境", "版本", "除錯", "debug"],
}

GENERIC_REASON_MARKERS = ["因為", "由於", "原因", "導致", "所以"]

APOLOGY_KEYWORDS = ["抱歉", "不好意思", "對不起", "歉意"]
THANKS_KEYWORDS = ["感謝", "謝謝", "感激"]
CLOSING_KEYWORDS = ["敬上", "敬啟", "此致", "敬祝", "致敬"]


def debug_log(message: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def parse_input(text: str) -> Tuple[int, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip() != ""]
    days = 0
    reason = ""
    if lines:
        try:
            days = int(lines[0])
        except ValueError:
            days = 0
    if len(lines) > 1:
        reason = lines[1]
    return days, reason


def count_chars(text: str) -> int:
    return sum(1 for ch in text if not ch.isspace())


def contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def has_days(text: str, days: int) -> bool:
    if days <= 0:
        return False
    digits = str(days)
    chinese = "一二三四五六七"
    chinese_digit = chinese[days - 1] if 1 <= days <= 7 else ""
    patterns = [rf"{digits}\s*(天|日)"]
    if chinese_digit:
        patterns.append(rf"{chinese_digit}\s*(天|日)")
    return any(re.search(pattern, text) for pattern in patterns)


def has_greeting(text: str) -> bool:
    return ("您好" in text or "你好" in text) and ("教授" in text or "老師" in text)


def has_banned_reason(text: str) -> bool:
    if "狗" in text and "作業" in text and "吃" in text:
        return True
    if "電腦壞" in text and ("沒有備份" in text or "沒備份" in text):
        return True
    if "忘記" in text:
        return True
    return False


def reason_ok(text: str, reason_type: str) -> bool:
    reason_type = reason_type.strip()
    if not reason_type or reason_type == "其他":
        return contains_any(text, GENERIC_REASON_MARKERS)
    keywords = REASON_KEYWORDS.get(reason_type, [reason_type])
    return contains_any(text,
                        keywords + GENERIC_REASON_MARKERS + [reason_type])


def heuristic_check(text: str, days: int,
                    reason_type: str) -> Tuple[bool, str]:
    length = count_chars(text)
    debug_log(f"length={length}")
    if length < 100 or length > 300:
        return False, f"內容長度需為 100-300 字，目前為 {length} 字"

    if has_banned_reason(text):
        return False, "包含禁止使用的理由"

    if not has_days(text, days):
        return False, "未提及延後天數"

    if not reason_ok(text, reason_type):
        return False, "未清楚說明延期原因"

    feature_score = 0
    if has_greeting(text):
        feature_score += 1
    if contains_any(text, APOLOGY_KEYWORDS):
        feature_score += 1
    if contains_any(text, THANKS_KEYWORDS):
        feature_score += 1
    if contains_any(text, CLOSING_KEYWORDS):
        feature_score += 1

    if feature_score < 2:
        return False, "稱謂、歉意或結尾等要素不足"

    return True, "通過基本格式與內容檢查"


def evaluate_with_ai(api_key: str, model: str, days: int, reason_type: str,
                     text: str) -> Optional[Tuple[bool, str]]:
    try:
        import google.generativeai as genai
    except Exception as exc:
        debug_log(f"ai_import_failed={exc}")
        return None

    genai.configure(api_key=api_key)
    ai_model = genai.GenerativeModel(model)

    prompt = f"""你是一個延期申請信的評分系統。請根據題目規範判斷學生輸出是否合格。\n\n"""
    prompt += f"延期天數：{days}\n原因類型：{reason_type or '其他'}\n"
    prompt += "評估標準：\n"
    prompt += "1. 邏輯連貫性\n2. 理由合理性\n3. 態度誠懇度\n4. 語言表達\n"
    prompt += "必須包含：稱謂、延期原因、新期限（可用延後天數表達）、歉意與感謝、結尾。\n"
    prompt += "禁止理由：狗吃作業、電腦壞了但沒有備份、忘記了。\n"
    prompt += "長度限制：100-300 字。\n\n"
    prompt += "學生輸出：\n" + text.strip() + "\n\n"
    prompt += "請回覆以下格式：\nSCORE: [0-100]\nVERDICT: [PASS 或 FAIL]\nFEEDBACK: [一句話回饋]"

    debug_log(f"ai_prompt_len={len(prompt)}")
    response = ai_model.generate_content(prompt)
    result_text = (response.text or "").strip()
    debug_log(f"ai_response={result_text[:200]}")

    verdict = ""
    feedback = "AI 評估完成"
    score = None
    for line in result_text.splitlines():
        if line.startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip()
        elif line.startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip()
        elif line.startswith("SCORE:"):
            value = line.split(":", 1)[1].strip()
            try:
                score = int(re.findall(r"\d+", value)[0])
            except Exception:
                score = None

    if verdict.upper().startswith("PASS"):
        return True, feedback
    if verdict.upper().startswith("FAIL"):
        return False, feedback
    if score is not None:
        return score >= 60, feedback
    return None


def check(input_file: str, output_file: str) -> Tuple[str, str]:
    input_text = read_text(input_file)
    output_text = read_text(output_file)
    days, reason = parse_input(input_text)

    if not output_text.strip():
        return "WA", "輸出為空"

    if has_banned_reason(output_text):
        return "WA", "包含禁止使用的理由"

    length = count_chars(output_text)
    if length < 100 or length > 300:
        return "WA", f"內容長度需為 100-300 字，目前為 {length} 字"

    api_key = os.environ.get("AI_API_KEY")
    model = os.environ.get("AI_MODEL", "gemini-2.5-flash")

    if api_key:
        try:
            ai_result = evaluate_with_ai(api_key, model, days, reason,
                                         output_text)
            if ai_result is not None:
                passed, feedback = ai_result
                return ("AC" if passed else "WA", feedback)
        except Exception as exc:
            debug_log(f"ai_eval_failed={exc}")

    ok, message = heuristic_check(output_text, days, reason)
    return ("AC" if ok else "WA", message)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("STATUS: WA")
        print("MESSAGE: Invalid checker arguments (expected 3 file paths)")
        sys.exit(1)

    status, message = check(sys.argv[1], sys.argv[2])
    print(f"STATUS: {status}")
    print(f"MESSAGE: {message}")
