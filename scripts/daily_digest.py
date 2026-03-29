"""
Today's Context: cross-news AI analysis module with historical memory.
Collects article summaries + market data, loads recent digest history,
and generates a deep-analysis daily digest JSON via Groq.
"""
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config import (
    GROQ_DIGEST_TIMEOUT, GROQ_DIGEST_TEMPERATURE, GROQ_DIGEST_MAX_TOKENS,
    GROQ_DIGEST_MODEL, GROQ_RPM_SLEEP, REPO_ROOT, INDICATOR_THRESHOLDS,
)
from groq_client import chat_completion

TZ_TW = timezone(timedelta(hours=8))

# Digest archive directories
DIGEST_DIR = REPO_ROOT / "docs" / "data" / "digests"
DAILY_DIR = DIGEST_DIR / "daily"
WEEKLY_DIR = DIGEST_DIR / "weekly"
MONTHLY_DIR = DIGEST_DIR / "monthly"

DIGEST_SYSTEM_PROMPT = """你是一位資深國際新聞主編兼財經分析師。今天是 {today}。
{history_block}
{market_block}
## 任務
根據今日新聞，產出深度脈絡報告。

僅回覆 JSON，不要加任何其他文字，不要用 markdown code block：
{{"key_themes":[{{"title":"具體標題","background":"前因 2-3 句","development":"經過 2-3 句，引用數據","impact":"影響 2-3 句","conclusion":"結論 1-2 句，含預判","region":"asia|americas|europe|global"}}],"watch_next":[{{"topic":"方向","reason":"原因","timeframe":"本週|下週|本月"}}],"cross_links":[{{"themes":["A","B"],"chain":"A→B 的具體傳導路徑"}}],"market_snapshot":{{"mood":"避險|觀望|樂觀|分歧","key_moves":"關鍵指標變動摘要"}}}}

嚴格規則：
- key_themes 3-5 個，只選財經/地緣政治/科技/市場相關的重大主題
- 每個主題必須有 background(前因) → development(經過) → impact(影響) → conclusion(結論) 四層
- development 和 impact 必須引用具體數據（股價、漲跌幅、金額、人數）
- conclusion 必須包含未來 1-3 天的預判或趨勢方向
- cross_links 要說明具體傳導路徑（A→B→C），不要空泛的「互相影響」
- watch_next 加上 timeframe（本週/下週/本月）
- 禁止寫「需要關注」「值得重視」「需要加強合作」這類廢話，直接給結論
- 如果有歷史脈絡，要延續分析（例如「連續第N天...」「延續昨日...」），不要重複歷史內容
- 全部繁體中文"""


# ── History loading ──────────────────────────────────


def _load_json_safe(path: Path) -> dict | None:
    """Read a JSON file, return None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _load_recent_digests(days: int = 3) -> list[dict]:
    """Load the most recent N daily digest files."""
    if not DAILY_DIR.exists():
        return []
    today = date.today()
    results = []
    for i in range(1, days + 1):
        d = today - timedelta(days=i)
        data = _load_json_safe(DAILY_DIR / f"{d.isoformat()}.json")
        if data:
            results.append(data)
    return results


def _load_weekly_digests(weeks: int = 4) -> list[dict]:
    """Load the most recent N weekly rollup files."""
    if not WEEKLY_DIR.exists():
        return []
    today = date.today()
    results = []
    for i in range(1, weeks + 1):
        d = today - timedelta(weeks=i)
        year, week_num, _ = d.isocalendar()
        path = WEEKLY_DIR / f"{year}-W{week_num:02d}.json"
        data = _load_json_safe(path)
        if data:
            results.append(data)
    return results


def _load_monthly_digests(months: int = 3) -> list[dict]:
    """Load the most recent N monthly rollup files."""
    if not MONTHLY_DIR.exists():
        return []
    today = date.today()
    results = []
    for i in range(1, months + 1):
        # Go back i months
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        path = MONTHLY_DIR / f"{year}-{month:02d}.json"
        data = _load_json_safe(path)
        if data:
            results.append(data)
    return results


def _format_history_context() -> str:
    """Build historical context string for injection into the system prompt."""
    sections = []

    # Layer 1: recent daily digests
    daily = _load_recent_digests(3)
    for d in daily:
        day_label = d.get("date", "?")
        themes = d.get("key_themes", [])
        if not themes:
            continue
        theme_lines = []
        for t in themes[:5]:
            title = t.get("title", "")
            # Use conclusion for brevity; fall back to summary for old format
            brief = t.get("conclusion", "") or t.get("summary", "")
            if brief and len(brief) > 80:
                brief = brief[:80] + "…"
            theme_lines.append(f"  - {title}：{brief}")
        snapshot = d.get("market_snapshot", {})
        mood = snapshot.get("mood", "")
        mood_str = f"（市場：{mood}）" if mood else ""
        sections.append(f"【{day_label} 日報】{mood_str}\n" + "\n".join(theme_lines))

    # Layer 2: weekly rollups
    weekly = _load_weekly_digests(4)
    for w in weekly:
        week_label = w.get("week", "?")
        period = w.get("period", "")
        themes = w.get("top_themes", [])
        mood = w.get("market_mood", "")
        theme_str = "；".join(themes[:3]) if themes else ""
        line = f"【{week_label}（{period}）】{theme_str}"
        if mood:
            line += f"（{mood}）"
        sections.append(line)

    # Layer 3: monthly rollups
    monthly = _load_monthly_digests(3)
    for m in monthly:
        month_label = m.get("month", "?")
        events = m.get("top_events", [])
        trend = m.get("macro_trend", "")
        event_str = "；".join(events[:3]) if events else ""
        line = f"【{month_label} 月報】{event_str}"
        if trend:
            line += f"（{trend}）"
        sections.append(line)

    if not sections:
        return ""

    return "## 近期脈絡背景（延續分析，不要重複這些內容）\n\n" + "\n\n".join(sections)


# ── Market snapshot ──────────────────────────────────


def _format_market_block(market: dict | None) -> str:
    """Format market data into a concise snapshot for the prompt."""
    if not market:
        return ""

    lines = []
    key_indicators = [
        ("VIX", "VIX 恐慌指數"),
        ("OIL", "原油 WTI"),
        ("GOLD", "黃金"),
        ("SP500", "S&P500"),
        ("NASDAQ", "那斯達克"),
        ("TWII", "台股"),
        ("DXY", "美元指數"),
        ("TNX", "美債10Y殖利率"),
        ("USDTWD", "美元/台幣"),
    ]
    for key, name in key_indicators:
        data = market.get(key, {})
        price = data.get("price")
        chg = data.get("change_pct")
        if price is not None and chg is not None:
            lines.append(f"{name} {price}({chg:+.2f}%)")

    if not lines:
        return ""

    return "## 今日市場快照\n" + "、".join(lines)


# ── News context ─────────────────────────────────────


def _build_news_context(articles: list) -> str:
    """Organize articles into a prompt-ready text context, grouped by category."""
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


# ── Main generation ──────────────────────────────────


def generate_daily_digest(articles: list,
                          market: dict | None = None) -> dict | None:
    """
    Generate today's context analysis from articles + market data + history.
    Returns digest dict or None on failure.
    """
    digest_articles = [a for a in articles if a.get("summary_zh")]

    if len(digest_articles) < 3:
        print(f"[Digest] 文章數不足（{len(digest_articles)} < 3），跳過今日脈絡")
        return None

    # Cap at 25 articles to avoid overly long prompts
    if len(digest_articles) > 25:
        digest_articles = digest_articles[:25]

    context = _build_news_context(digest_articles)
    today = date.today().isoformat()

    # Build dynamic prompt blocks
    history_block = _format_history_context()
    market_block = _format_market_block(market)

    system_prompt = DIGEST_SYSTEM_PROMPT.format(
        today=today,
        history_block=history_block,
        market_block=market_block,
    )
    user_msg = f"今日（{today}）{len(digest_articles)} 則新聞：\n{context}"

    print(f"[Digest] 送出 {len(digest_articles)} 則新聞給 Groq 分析脈絡...")
    if history_block:
        print(f"[Digest] 已注入歷史脈絡（{len(history_block)} 字）")

    # Wait for RPM interval to avoid colliding with prior summary calls
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
        themes = result.get("key_themes", [])
        print(f"[Digest] 成功：{len(themes)} 主題, "
              f"{len(result.get('watch_next', []))} 觀察方向")
    return result


# ── Archive ──────────────────────────────────────────


def save_daily_digest(digest: dict, target_date: date | None = None) -> Path | None:
    """
    Save digest to docs/data/digests/daily/YYYY-MM-DD.json.
    Returns the file path on success, None on failure.
    """
    if not digest:
        return None

    target = target_date or date.today()
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # Count articles from key_themes for metadata
    archive = {
        "date": target.isoformat(),
        "generated_at": datetime.now(TZ_TW).isoformat(),
        **digest,
    }

    path = DAILY_DIR / f"{target.isoformat()}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        print(f"[Digest] 已歸檔至 {path}")
        return path
    except OSError as e:
        print(f"[Digest] 歸檔失敗：{e}")
        return None


# ── Parsing ──────────────────────────────────────────


def _parse_digest(raw: str) -> dict | None:
    """Parse Groq response JSON with multiple fallback strategies."""
    # 1. Direct parse
    try:
        data = json.loads(raw)
        if _validate_digest(data):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code block
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', raw)
    if match:
        try:
            data = json.loads(match.group(1))
            if _validate_digest(data):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Find outermost {...} via brace matching
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

    # 4. Attempt to fix truncated JSON
    match = re.search(r'\{[\s\S]*', raw)
    if match:
        fragment = match.group(0)
        for suffix in [']}]}', '"]}]}', '"}]}]}', '"]}}', '"}}']:
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
    """Validate digest JSON structure. Requires key_themes."""
    if not isinstance(data, dict):
        return False
    if "key_themes" not in data or not isinstance(data["key_themes"], list):
        return False
    # Remove legacy fields, fill missing ones
    data.pop("timeline", None)
    data.pop("summary", None)  # old single-summary field
    data.setdefault("watch_next", [])
    data.setdefault("cross_links", [])
    data.setdefault("market_snapshot", {})
    return True
