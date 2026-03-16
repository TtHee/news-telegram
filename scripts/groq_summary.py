import json
import re
import time
import requests
from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

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
        return {"title_zh": fallback_title, "summary": fallback_title, "sentiment": "中性"}


def summarize(title: str, content: str = "") -> dict:
    """
    回傳 {"summary": str, "sentiment": str}
    失敗或未設定 API Key 時，回傳標題作為摘要。
    """
    if not GROQ_API_KEY:
        print("[Groq] 未設定 GROQ_API_KEY，跳過摘要")
        return {"title_zh": title, "summary": title, "sentiment": "中性"}

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

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(GROQ_API_URL, headers=_build_headers(), json=payload, timeout=30)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return _parse_response(text, title)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = 3 * (attempt + 1)
                print(f"[Groq] 速率限制，等待 {wait} 秒後重試 ({attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            print(f"[Groq] 摘要失敗：{e}")
            if e.response is not None:
                print(f"[Groq] 回應內容：{e.response.text[:300]}")
            return {"title_zh": title, "summary": title, "sentiment": "中性"}
        except Exception as e:
            print(f"[Groq] 摘要失敗：{e}")
            return {"title_zh": title, "summary": title, "sentiment": "中性"}

    print(f"[Groq] 重試 {max_retries} 次仍失敗：{title[:50]}")
    return {"title_zh": title, "summary": title, "sentiment": "中性"}
