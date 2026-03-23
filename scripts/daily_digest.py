"""
今日脈絡：跨新聞 AI 分析模組。
收集所有非 Trends 新聞摘要，透過 Groq 產出每日脈絡 JSON。
"""
import json
import re

from config import GROQ_DIGEST_TIMEOUT, GROQ_DIGEST_TEMPERATURE, GROQ_DIGEST_MAX_TOKENS
from groq_client import chat_completion

DIGEST_SYSTEM_PROMPT = """你是一位資深國際新聞主編，擅長從大量新聞中萃取脈絡、發現跨領域關聯。

任務：根據以下今日新聞摘要，產出「今日脈絡」分析。

輸出格式（僅回覆 JSON，不要加任何其他文字）：
{
  "key_themes": [
    {"title": "主題標題", "summary": "2-3 句說明為什麼這是今天重要主題"}
  ],
  "timeline": [
    {"time": "事件時間點或順序描述", "event": "事件描述", "impact": "影響或意義", "category": "相關分類"}
  ],
  "watch_next": [
    {"topic": "關注方向", "reason": "為什麼要關注"}
  ],
  "cross_links": [
    {"themes": ["主題A", "主題B"], "explanation": "這些主題如何互相影響"}
  ]
}

規則：
1. key_themes：3-5 個今日最重要主題，按重要性排序
2. timeline：5-8 個事件，按時間或因果順序排列，呈現事件發展脈絡
3. watch_next：2-4 個接下來要關注的方向
4. cross_links：1-3 個跨主題關聯（不同 category 間的連動）
5. 全部使用繁體中文
6. 用簡潔有力的語言，讓不熟悉國際情勢的人也能理解"""


def _build_news_context(articles: list) -> str:
    """將文章清單整理成 prompt 用的文字脈絡。"""
    lines = []
    for i, a in enumerate(articles, 1):
        cat = a.get("category", "")
        title = a.get("title", "")
        summary = a.get("summary_zh", "")
        sentiment = a.get("sentiment", "中性")
        published = a.get("published_at", "")
        lines.append(
            f"[{i}] 分類:{cat} | 情緒:{sentiment} | 時間:{published}\n"
            f"    標題：{title}\n"
            f"    摘要：{summary}"
        )
    return "\n\n".join(lines)


def generate_daily_digest(articles: list) -> dict | None:
    """
    從所有非 Trends 文章產出今日脈絡分析。
    回傳 digest dict，失敗回傳 None。
    """
    # 過濾掉 Trends 類別
    digest_articles = [
        a for a in articles
        if a.get("category") not in ("trends", "trends_weekly")
        and a.get("summary_zh")  # 需要有摘要
    ]

    if len(digest_articles) < 3:
        print("[Digest] 文章數不足（< 3），跳過今日脈絡")
        return None

    context = _build_news_context(digest_articles)
    user_msg = f"以下是今日 {len(digest_articles)} 則新聞摘要：\n\n{context}"

    print(f"[Digest] 送出 {len(digest_articles)} 則新聞給 Groq 分析脈絡...")

    raw = chat_completion(
        messages=[
            {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=GROQ_DIGEST_TEMPERATURE,
        max_tokens=GROQ_DIGEST_MAX_TOKENS,
        timeout=GROQ_DIGEST_TIMEOUT,
    )

    if not raw:
        print("[Digest] Groq 回傳空值")
        return None

    return _parse_digest(raw)


def _parse_digest(raw: str) -> dict | None:
    """從 Groq 回應中解析 JSON。"""
    # 嘗試直接解析
    try:
        data = json.loads(raw)
        if _validate_digest(data):
            print("[Digest] 解析成功")
            return data
    except json.JSONDecodeError:
        pass

    # 嘗試從 markdown code block 中取出 JSON
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', raw)
    if match:
        try:
            data = json.loads(match.group(1))
            if _validate_digest(data):
                print("[Digest] 從 code block 解析成功")
                return data
        except json.JSONDecodeError:
            pass

    # 嘗試抓最大的 {...}
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            data = json.loads(match.group(0))
            if _validate_digest(data):
                print("[Digest] 從 raw text 解析成功")
                return data
        except json.JSONDecodeError:
            pass

    print(f"[Digest] 解析失敗，原始回應：{raw[:300]}")
    return None


def _validate_digest(data: dict) -> bool:
    """驗證 digest JSON 結構。"""
    required = ["key_themes", "timeline", "watch_next", "cross_links"]
    return all(key in data and isinstance(data[key], list) for key in required)
