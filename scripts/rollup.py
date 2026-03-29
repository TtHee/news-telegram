"""
Rollup module: generates weekly and monthly summary digests
by compressing daily/weekly archives via Groq.
"""
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config import (
    GROQ_DIGEST_TIMEOUT, GROQ_DIGEST_TEMPERATURE,
    GROQ_DIGEST_MODEL, GROQ_RPM_SLEEP,
)
from groq_client import chat_completion
from daily_digest import DAILY_DIR, WEEKLY_DIR, MONTHLY_DIR, _load_json_safe

TZ_TW = timezone(timedelta(hours=8))


# ── Weekly rollup ────────────────────────────────────


WEEKLY_PROMPT = """你是一位資深國際新聞主編。
以下是本週（{period}）每天的脈絡分析摘要。請將它們壓縮為一份「週報」。

僅回覆 JSON，不要加任何其他文字：
{{"week":"{week_label}","period":"{period}","top_themes":["本週 3-5 個最重要主題，每個一句話"],"trend_shifts":["相較前期的 1-3 個趨勢變化"],"market_mood":"本週市場整體氛圍一句話"}}

規則：
- top_themes 是本週最重要的 3-5 個主題，每個用一句話概括
- trend_shifts 指出相較上週或近期的變化趨勢
- market_mood 用一句話描述本週市場整體氛圍
- 全部繁體中文，簡潔有力"""


def generate_weekly_rollup(target_date: date | None = None) -> dict | None:
    """
    Read this week's daily digests and compress into a weekly rollup.
    target_date: any date within the target week (defaults to today).
    """
    target = target_date or date.today()
    year, week_num, weekday = target.isocalendar()
    week_label = f"{year}-W{week_num:02d}"

    # Find Monday of this week
    monday = target - timedelta(days=weekday - 1)
    sunday = monday + timedelta(days=6)
    period = f"{monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')}"

    # Load daily digests for this week
    daily_summaries = []
    for i in range(7):
        d = monday + timedelta(days=i)
        data = _load_json_safe(DAILY_DIR / f"{d.isoformat()}.json")
        if not data:
            continue
        themes = data.get("key_themes", [])
        if not themes:
            continue
        theme_lines = []
        for t in themes[:5]:
            title = t.get("title", "")
            conclusion = t.get("conclusion", "") or t.get("summary", "")
            if conclusion and len(conclusion) > 60:
                conclusion = conclusion[:60] + "…"
            theme_lines.append(f"  - {title}：{conclusion}")
        snapshot = data.get("market_snapshot", {})
        mood = snapshot.get("mood", "")
        day_str = f"【{d.isoformat()}】" + (f"（{mood}）" if mood else "")
        daily_summaries.append(day_str + "\n" + "\n".join(theme_lines))

    if len(daily_summaries) < 2:
        print(f"[Rollup] 週報資料不足（{len(daily_summaries)} 天 < 2），跳過")
        return None

    user_msg = "\n\n".join(daily_summaries)
    system_prompt = WEEKLY_PROMPT.format(
        period=period, week_label=week_label,
    )

    print(f"[Rollup] 產生週報 {week_label}（{len(daily_summaries)} 天資料）...")
    time.sleep(GROQ_RPM_SLEEP)

    raw = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=GROQ_DIGEST_MODEL,
        temperature=GROQ_DIGEST_TEMPERATURE,
        max_tokens=1500,
        timeout=GROQ_DIGEST_TIMEOUT,
    )

    if not raw:
        print("[Rollup] 週報 Groq 回傳空值")
        return None

    result = _parse_rollup(raw)
    if result:
        # Ensure metadata
        result.setdefault("week", week_label)
        result.setdefault("period", period)
        _save_rollup(result, WEEKLY_DIR, f"{week_label}.json")
    return result


# ── Monthly rollup ───────────────────────────────────


MONTHLY_PROMPT = """你是一位資深國際新聞主編。
以下是本月（{month}）的每週摘要。請將它們壓縮為一份「月報」。

僅回覆 JSON，不要加任何其他文字：
{{"month":"{month}","top_events":["本月 3-5 件大事，每件一句話"],"macro_trend":"宏觀趨勢一句話"}}

規則：
- top_events 是本月最重要的 3-5 件事，每件用一句話概括
- macro_trend 用一句話描述本月宏觀趨勢方向
- 全部繁體中文，簡潔有力"""


def generate_monthly_rollup(target_date: date | None = None) -> dict | None:
    """
    Read this month's weekly rollups and compress into a monthly rollup.
    target_date: any date within the target month (defaults to previous month).
    """
    target = target_date or date.today()
    # Default: summarize the previous month
    if target_date is None:
        first = target.replace(day=1)
        target = first - timedelta(days=1)  # last day of previous month

    month_label = target.strftime("%Y-%m")

    # Collect weekly rollups that fall within this month
    weekly_summaries = []
    if WEEKLY_DIR.exists():
        for f in sorted(WEEKLY_DIR.glob("*.json")):
            data = _load_json_safe(f)
            if not data:
                continue
            period = data.get("period", "")
            week = data.get("week", "")
            # Check if week belongs to this month (simple: year matches)
            if not week.startswith(str(target.year)):
                continue
            themes = data.get("top_themes", [])
            mood = data.get("market_mood", "")
            theme_str = "；".join(themes[:3]) if themes else ""
            line = f"【{week}（{period}）】{theme_str}"
            if mood:
                line += f"（{mood}）"
            weekly_summaries.append(line)

    # Also load daily digests for this month as fallback
    if len(weekly_summaries) < 2 and DAILY_DIR.exists():
        print("[Rollup] 週報不足，改用日報產生月報")
        for f in sorted(DAILY_DIR.glob(f"{month_label}-*.json")):
            data = _load_json_safe(f)
            if not data:
                continue
            themes = data.get("key_themes", [])
            if not themes:
                continue
            day = data.get("date", f.stem)
            theme_titles = [t.get("title", "") for t in themes[:3]]
            weekly_summaries.append(f"【{day}】" + "；".join(theme_titles))

    if len(weekly_summaries) < 2:
        print(f"[Rollup] 月報資料不足（{len(weekly_summaries)} 筆 < 2），跳過")
        return None

    user_msg = "\n".join(weekly_summaries)
    system_prompt = MONTHLY_PROMPT.format(month=month_label)

    print(f"[Rollup] 產生月報 {month_label}（{len(weekly_summaries)} 筆資料）...")
    time.sleep(GROQ_RPM_SLEEP)

    raw = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=GROQ_DIGEST_MODEL,
        temperature=GROQ_DIGEST_TEMPERATURE,
        max_tokens=1000,
        timeout=GROQ_DIGEST_TIMEOUT,
    )

    if not raw:
        print("[Rollup] 月報 Groq 回傳空值")
        return None

    result = _parse_rollup(raw)
    if result:
        result.setdefault("month", month_label)
        _save_rollup(result, MONTHLY_DIR, f"{month_label}.json")
    return result


# ── Helpers ──────────────────────────────────────────


def _parse_rollup(raw: str) -> dict | None:
    """Parse rollup JSON from Groq response."""
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    import re
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', raw)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding outermost braces
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    print(f"[Rollup] JSON 解析失敗：{raw[:300]}")
    return None


def _save_rollup(data: dict, directory: Path, filename: str) -> Path | None:
    """Save rollup JSON to the specified directory."""
    directory.mkdir(parents=True, exist_ok=True)
    data["generated_at"] = datetime.now(TZ_TW).isoformat()
    path = directory / filename
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[Rollup] 已歸檔至 {path}")
        return path
    except OSError as e:
        print(f"[Rollup] 歸檔失敗：{e}")
        return None
