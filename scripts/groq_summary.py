import json
import requests
from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-8b-8192"

SYSTEM_PROMPT = """你是一位專業的財經新聞編輯，請用繁體中文撰寫詳細的新聞摘要，格式如下：
1. 摘要：至少 6 行，包含事件背景、關鍵細節、影響分析與後續展望，讓讀者不需閱讀原文就能完整掌握新聞內容
2. 情緒：只能回答「正面」「中性」「負面」其中一個

回覆格式（JSON）：
{"summary": "...", "sentiment": "中性"}"""

VALID_SENTIMENTS = {"正面", "中性", "負面"}
FALLBACK = {"summary": "", "sentiment": "中性"}


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


def _parse_response(text: str, fallback_title: str) -> dict:
    try:
        result = json.loads(text)
        sentiment = result.get("sentiment", "中性")
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "中性"
        return {"summary": result.get("summary", fallback_title), "sentiment": sentiment}
    except json.JSONDecodeError:
        return {"summary": fallback_title, "sentiment": "中性"}


def summarize(title: str, content: str = "") -> dict:
    """
    回傳 {"summary": str, "sentiment": str}
    失敗或未設定 API Key 時，回傳標題作為摘要。
    """
    if not GROQ_API_KEY:
        return {"summary": title, "sentiment": "中性"}

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"標題：{title}\n內文：{content[:800] or '（無）'}"},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=_build_headers(), json=payload, timeout=20)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return _parse_response(text, title)
    except Exception as e:
        print(f"[Groq] 摘要失敗：{e}")
        return {"summary": title, "sentiment": "中性"}
