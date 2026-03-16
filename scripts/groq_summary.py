import json
import re
import requests
from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """你是一位專業的財經新聞編輯。不論原文是什麼語言，你都必須用「繁體中文」撰寫摘要。

任務：
1. 將新聞翻譯並改寫為繁體中文摘要，至少 6 行（約 200～300 字）
2. 內容包含：事件背景、關鍵細節、影響分析、後續展望
3. 讓讀者不需閱讀原文就能完整掌握新聞內容
4. 判斷情緒：只能回答「正面」「中性」「負面」其中一個

回覆格式（僅回覆 JSON，不要加任何其他文字）：
{"summary": "繁體中文摘要內容", "sentiment": "中性"}"""

VALID_SENTIMENTS = {"正面", "中性", "負面"}


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


def _strip_html(text: str) -> str:
    """移除 HTML 標籤，只保留純文字。"""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _parse_response(text: str, fallback_title: str) -> dict:
    # 嘗試從回應中提取 JSON（有時模型會加上額外文字）
    json_match = re.search(r'\{[^{}]*"summary"[^{}]*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group()
    try:
        result = json.loads(text)
        summary = result.get("summary", "")
        sentiment = result.get("sentiment", "中性")
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "中性"
        if not summary or summary == fallback_title:
            return {"summary": fallback_title, "sentiment": sentiment}
        return {"summary": summary, "sentiment": sentiment}
    except json.JSONDecodeError:
        print(f"[Groq] JSON 解析失敗，原始回應：{text[:200]}")
        return {"summary": fallback_title, "sentiment": "中性"}


def summarize(title: str, content: str = "") -> dict:
    """
    回傳 {"summary": str, "sentiment": str}
    失敗或未設定 API Key 時，回傳標題作為摘要。
    """
    if not GROQ_API_KEY:
        print("[Groq] 未設定 GROQ_API_KEY，跳過摘要")
        return {"summary": title, "sentiment": "中性"}

    clean_content = _strip_html(content)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"標題：{title}\n內文：{clean_content[:1500] or '（無內文，請根據標題撰寫摘要）'}"},
        ],
        "temperature": 0.3,
        "max_tokens": 800,
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=_build_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return _parse_response(text, title)
    except Exception as e:
        print(f"[Groq] 摘要失敗：{e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[Groq] 回應內容：{e.response.text[:300]}")
        return {"summary": title, "sentiment": "中性"}
