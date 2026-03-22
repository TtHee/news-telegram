"""
統一 Groq API 呼叫模組。
提供帶 retry、rate limit 偵測的共用請求函式。
"""
import time

import requests

from config import (
    GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL,
    GROQ_MAX_RETRIES, GROQ_RETRY_BASE_WAIT,
)


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


def chat_completion(
    messages: list[dict],
    *,
    temperature: float = 0.3,
    max_tokens: int = 800,
    timeout: int = 30,
) -> str | None:
    """
    呼叫 Groq Chat Completion API，回傳回應文字。
    自動處理 429 rate limit 重試。失敗時回傳 None。
    """
    if not GROQ_API_KEY:
        print("[Groq] 未設定 GROQ_API_KEY，跳過")
        return None

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(GROQ_MAX_RETRIES):
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers=_build_headers(),
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = GROQ_RETRY_BASE_WAIT * (attempt + 1)
                print(f"[Groq] 速率限制，等待 {wait} 秒後重試 ({attempt+1}/{GROQ_MAX_RETRIES})")
                time.sleep(wait)
                continue
            print(f"[Groq] HTTP 錯誤：{e}")
            if e.response is not None:
                print(f"[Groq] 回應內容：{e.response.text[:300]}")
            return None

        except requests.exceptions.ConnectionError as e:
            print(f"[Groq] 連線錯誤：{e}")
            return None

        except requests.exceptions.Timeout:
            print(f"[Groq] 請求逾時（{timeout}s）")
            return None

    print(f"[Groq] 重試 {GROQ_MAX_RETRIES} 次仍失敗")
    return None
