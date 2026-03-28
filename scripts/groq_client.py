"""
統一 Groq API 呼叫模組。
提供帶 retry、rate limit 偵測、自適應節流的共用請求函式。
"""
import time

import requests

from config import (
    GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL,
    GROQ_MAX_RETRIES, GROQ_RETRY_BASE_WAIT,
)

# Adaptive throttle state — shared across all callers within one process
_throttle_extra_delay: float = 0.0  # extra seconds to add after a 429 hit
_THROTTLE_DECAY = 0.5               # decay factor per successful call


def get_throttle_delay() -> float:
    """Return the current extra delay (seconds) recommended after a 429 hit."""
    return _throttle_extra_delay


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


def chat_completion(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 800,
    timeout: int = 30,
) -> str | None:
    """
    呼叫 Groq Chat Completion API，回傳回應文字。
    自動處理 429 rate limit 重試（讀取 Retry-After header）。
    命中 429 時會提升 adaptive throttle delay，供呼叫端調整間隔。
    失敗時回傳 None。
    """
    global _throttle_extra_delay

    if not GROQ_API_KEY:
        print("[Groq] 未設定 GROQ_API_KEY，跳過")
        return None

    payload = {
        "model": model or GROQ_MODEL,
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

            # Success — decay the throttle delay
            _throttle_extra_delay = max(0, _throttle_extra_delay * _THROTTLE_DECAY)
            return resp.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                # Read Retry-After header if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = int(float(retry_after)) + 2
                    except (ValueError, TypeError):
                        wait = GROQ_RETRY_BASE_WAIT * (attempt + 1)
                else:
                    wait = GROQ_RETRY_BASE_WAIT * (attempt + 1)
                # Cap at 90 seconds (was 120 — shorter cap + adaptive avoids repeats)
                wait = min(wait, 90)

                # Bump adaptive throttle — subsequent calls should be slower
                _throttle_extra_delay = min(_throttle_extra_delay + 4.0, 20.0)

                print(f"[Groq] 速率限制，等待 {wait} 秒後重試 ({attempt+1}/{GROQ_MAX_RETRIES})"
                      f"（自適應延遲提升至 +{_throttle_extra_delay:.0f}s）")
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
