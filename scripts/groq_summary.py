"""
新聞摘要模組：呼叫 Groq API 產生繁體中文摘要與情緒判斷。
"""
import json
import re

from config import (
    GROQ_API_KEY,
    GROQ_SUMMARY_TIMEOUT, GROQ_SUMMARY_TEMPERATURE, GROQ_SUMMARY_MAX_TOKENS,
    CONTENT_TRUNCATE_LEN,
)
from groq_client import chat_completion
from utils import strip_html

SYSTEM_PROMPT = """你是一位專業的財經新聞編輯。不論原文是什麼語言，你都必須用「繁體中文」回覆所有欄位。

任務：
1. 將標題翻譯為繁體中文（title_zh）
2. 將新聞翻譯並改寫為繁體中文摘要（summary），至少 6 行（約 200～300 字）
3. 摘要內容包含：事件背景、關鍵細節、影響分析、後續展望
4. 讓讀者不需閱讀原文就能完整掌握新聞內容
5. 判斷情緒：只能回答「正面」「中性」「負面」其中一個

回覆格式（僅回覆 JSON，不要加任何其他文字）：
{"title_zh": "繁體中文標題", "summary": "繁體中文摘要內容", "sentiment": "中性"}"""

VALID_SENTIMENTS = {"正面", "中性", "負面"}

_FALLBACK = lambda title: {"title_zh": title, "summary": title, "sentiment": "中性"}


def _parse_response(text: str, fallback_title: str) -> dict:
    """解析 Groq 回應 JSON。"""
    json_match = re.search(r'\{[^{}]*"summary"[^{}]*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group()
    try:
        result = json.loads(text)
        title_zh = result.get("title_zh", "")
        summary = result.get("summary", "")
        sentiment = result.get("sentiment", "中性")
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "中性"
        return {
            "title_zh": title_zh or fallback_title,
            "summary": summary or fallback_title,
            "sentiment": sentiment,
        }
    except json.JSONDecodeError:
        print(f"[Groq] JSON 解析失敗，原始回應：{text[:200]}")
        return _FALLBACK(fallback_title)


def summarize(title: str, content: str = "") -> dict:
    """
    回傳 {"title_zh": str, "summary": str, "sentiment": str}
    失敗或未設定 API Key 時，回傳標題作為摘要。
    """
    if not GROQ_API_KEY:
        print("[Groq] 未設定 GROQ_API_KEY，跳過摘要")
        return _FALLBACK(title)

    clean_content = strip_html(content)
    user_msg = f"標題：{title}\n內文：{clean_content[:CONTENT_TRUNCATE_LEN] or '（無內文，請根據標題撰寫摘要）'}"

    text = chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=GROQ_SUMMARY_TEMPERATURE,
        max_tokens=GROQ_SUMMARY_MAX_TOKENS,
        timeout=GROQ_SUMMARY_TIMEOUT,
    )

    if text is None:
        return _FALLBACK(title)

    return _parse_response(text, title)
