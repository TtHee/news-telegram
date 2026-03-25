"""
今日脈絡：跨新聞 AI 分析模組。
收集所有非 Trends 新聞摘要，透過 Groq 產出每日脈絡 JSON。
"""
import json
import re
import time
from datetime import date

from config import (
    GROQ_DIGEST_TIMEOUT, GROQ_DIGEST_TEMPERATURE, GROQ_DIGEST_MAX_TOKENS,
    GROQ_DIGEST_MODEL, GROQ_RPM_SLEEP,
)
from groq_client import chat_completion

DIGEST_SYSTEM_PROMPT = """你是一位資深國際新聞主編。今天是 {today}。
根據今日新聞摘要，產出「今日脈絡」深度分析。

僅回覆 JSON，不要加任何其他文字，不要用 markdown code block：
{{"key_themes":[{{"title":"主題標題","summary":"背景脈絡 → 關鍵發展 → 潛在影響，4-6句深度分析"}}],"watch_next":[{{"topic":"關注方向","reason":"原因"}}],"cross_links":[{{"themes":["主題A","主題B"],"explanation":"如何互相影響"}}]}}

規則：
- key_themes：3-5 個今日最重要主題，每個 summary 必須包含「背景脈絡→關鍵發展→潛在影響」三層分析，4-6 句
- watch_next：2-4 個接下來要關注的方向
- cross_links：1-3 個跨主題關聯
- 全部繁體中文，深入但簡潔"""


def _build_news_context(articles: list) -> str:
    """將文章清單整理成 prompt 用的文字脈絡，按 category 分組。"""
    groups: dict[str, list[str]] = {}
    for i, a in enumerate(articles, 1):
        cat = a.get("category", "其他")
        title = a.get("title", "")
        summary = (a.get("summary_zh", "") or "")[:300]
        sentiment = a.get("sentiment", "中性")
        line = f"  [{i}] {sentiment}|{title}|{summary}"
        groups.setdefault(cat, []).append(line)

    sections = []
    for cat, lines in groups.items():
        sections.append(f"【{cat}】\n" + "\n".join(lines))
    return "\n\n".join(sections)


def generate_daily_digest(articles: list) -> dict | None:
    """
    從所有非 Trends 文章產出今日脈絡分析。
    回傳 digest dict，失敗回傳 None。
    """
    digest_articles = [
        a for a in articles
        if a.get("summary_zh")
    ]

    if len(digest_articles) < 3:
        print(f"[Digest] 文章數不足（{len(digest_articles)} < 3），跳過今日脈絡")
        return None

    # 限制最多 20 篇避免 prompt 太長
    if len(digest_articles) > 20:
        digest_articles = digest_articles[:20]

    context = _build_news_context(digest_articles)
    today = date.today().isoformat()
    system_prompt = DIGEST_SYSTEM_PROMPT.format(today=today)
    user_msg = f"今日（{today}）{len(digest_articles)} 則新聞：\n{context}"

    print(f"[Digest] 送出 {len(digest_articles)} 則新聞給 Groq 分析脈絡...")

    # 等待 RPM 間隔，避免跟前面的摘要呼叫撞到 rate limit
    time.sleep(GROQ_RPM_SLEEP)

    raw = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=GROQ_DIGEST_MODEL,
        temperature=GROQ_DIGEST_TEMPERATURE,
        max_tokens=GROQ_DIGEST_MAX_TOKENS,
        timeout=GROQ_DIGEST_TIMEOUT,
    )

    if not raw:
        print("[Digest] Groq 回傳空值")
        return None

    result = _parse_digest(raw)
    if result:
        print(f"[Digest] 成功：{len(result.get('key_themes',[]))} 主題, "
              f"{len(result.get('watch_next',[]))} 觀察方向")
    return result


def _parse_digest(raw: str) -> dict | None:
    """從 Groq 回應中解析 JSON，多層容錯。"""
    # 1. 直接解析
    try:
        data = json.loads(raw)
        if _validate_digest(data):
            return data
    except json.JSONDecodeError:
        pass

    # 2. 從 markdown code block 取出
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', raw)
    if match:
        try:
            data = json.loads(match.group(1))
            if _validate_digest(data):
                return data
        except json.JSONDecodeError:
            pass

    # 3. 找最外層 {...}
    depth = 0
    start = -1
    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    data = json.loads(raw[start:i+1])
                    if _validate_digest(data):
                        return data
                except json.JSONDecodeError:
                    pass
                start = -1

    # 4. 嘗試修復常見問題：截斷的 JSON
    match = re.search(r'\{[\s\S]*', raw)
    if match:
        fragment = match.group(0)
        # 嘗試補上缺少的結尾
        for suffix in [']}]}', '"]}]}', '"}]}]}', '"]}}']:
            try:
                data = json.loads(fragment + suffix)
                if _validate_digest(data):
                    print("[Digest] 修復截斷 JSON 成功")
                    return data
            except json.JSONDecodeError:
                continue

    print(f"[Digest] 解析失敗，原始回應前 500 字：{raw[:500]}")
    return None


def _validate_digest(data: dict) -> bool:
    """驗證 digest JSON 結構，只要求 key_themes 存在。"""
    if not isinstance(data, dict):
        return False
    if "key_themes" not in data or not isinstance(data["key_themes"], list):
        return False
    # 移除舊欄位、補上缺少的欄位
    data.pop("timeline", None)
    data.setdefault("watch_next", [])
    data.setdefault("cross_links", [])
    return True
