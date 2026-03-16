#!/usr/bin/env python3
"""
主程式：串接所有模組，執行完整新聞抓取流水線。

流水線：
  1. 讀取現有 news.json（快取）
  2. RSS 抓取與去重       (rss_fetcher)
  3. 過濾已摘要文章，只對新文章呼叫 Groq
  4. 合併新舊文章
  5. 市場數據             (market_data)
  6. 風險評分             (risk_score)
  7. 寫入 news.json       (本模組)
  8. Telegram 推播        (telegram_notify)
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    NEWS_JSON_PATH, SENT_IDS_PATH, TRENDS_CACHE_PATH,
    BREAKING_KEYWORDS, WATCH_STOCKS, BREAKING_COOLDOWN_HOURS,
    QUIET_HOUR_START, QUIET_HOUR_END,
)
from rss_fetcher import fetch_all
from groq_summary import summarize
from market_data import get_all_market_data
from risk_score import calc_risk_score
from telegram_notify import send_morning_report, send_breaking_news

TZ_TW = timezone(timedelta(hours=8))

# 新聞最多保留 24 小時
MAX_AGE_HOURS = 24


# ── 快取相關 ──────────────────────────────────────────

def _load_existing() -> dict:
    """讀取現有 news.json，回傳已摘要文章的 ID → 文章 dict 對照表。"""
    try:
        with open(NEWS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cache = {}
        for cat_articles in data.get("categories", {}).values():
            for a in cat_articles:
                cache[a["id"]] = a
        print(f"[Cache] 載入 {len(cache)} 則已摘要文章")
        return cache
    except Exception:
        print("[Cache] 無現有資料，全部重新摘要")
        return {}


def _is_expired(article: dict) -> bool:
    """檢查文章是否超過 MAX_AGE_HOURS。"""
    pub = article.get("published_at", "")
    if not pub:
        return False
    try:
        pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        age = (datetime.now(TZ_TW) - pub_dt).total_seconds() / 3600
        return age > MAX_AGE_HOURS
    except Exception:
        return False


# ── 輔助函式 ──────────────────────────────────────────

def _is_breaking(article: dict) -> bool:
    text = (article.get("title", "") + " " + article.get("summary_zh", "")).lower()
    keyword_hit = any(kw.lower() in text for kw in BREAKING_KEYWORDS)
    stock_hit   = any(s.lower() in text for s in WATCH_STOCKS)
    return keyword_hit or stock_hit or article.get("sentiment") == "負面"


def _cooldown_ok(article_id: str, sent: dict) -> bool:
    if article_id not in sent:
        return True
    sent_at = datetime.fromisoformat(sent[article_id])
    elapsed_hours = (datetime.now(TZ_TW) - sent_at).total_seconds() / 3600
    return elapsed_hours >= BREAKING_COOLDOWN_HOURS


def _load_sent_ids() -> dict:
    try:
        with open(SENT_IDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sent_ids(sent: dict) -> None:
    Path(SENT_IDS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(sent, f)


# ── 流水線各步驟 ──────────────────────────────────────

def enrich_articles(articles: list, cache: dict) -> list:
    """只對新文章呼叫 Groq 摘要，已有的直接用快取。"""
    new_count = 0
    cached_count = 0

    for i, a in enumerate(articles):
        cached = cache.get(a["id"])
        # 快取有效條件：存在、未過期、摘要不等於標題（等於代表上次失敗）
        if (cached
            and not _is_expired(cached)
            and cached.get("summary_zh", "") != cached.get("title", "")):
            a["title"]       = cached["title"]
            a["summary_zh"]  = cached["summary_zh"]
            a["sentiment"]   = cached["sentiment"]
            a["is_breaking"] = cached.get("is_breaking", False)
            a.pop("raw_content", None)
            cached_count += 1
        else:
            # Google Trends 不需要 AI 摘要
            if a.get("category") == "trends":
                a["summary_zh"]  = ""
                a["sentiment"]   = "中性"
                a["is_breaking"] = False
                a.pop("raw_content", None)
                cached_count += 1
                continue

            # 新文章，呼叫 Groq
            print(f"  [Groq] 新文章 {new_count+1}: {a['title'][:45]}")
            result = summarize(a["title"], a.get("raw_content", ""))
            a["title"]       = result["title_zh"]
            a["summary_zh"]  = result["summary"]
            a["sentiment"]   = result["sentiment"]
            a["is_breaking"] = _is_breaking(a)
            a.pop("raw_content", None)
            new_count += 1
            time.sleep(2.5)  # Groq 免費版限制 30 RPM

    print(f"[Groq] 新摘要 {new_count} 則，快取命中 {cached_count} 則")
    return articles


def categorize(articles: list) -> dict:
    """依 category 欄位分組文章。"""
    result = {}
    for a in articles:
        cat = a["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(a)
    return result


def build_output(categories: dict, market_info: dict, risk: dict) -> dict:
    """組合最終要寫入 news.json 的資料結構。"""
    return {
        "generated_at":  datetime.now(TZ_TW).isoformat(),
        "risk_signals":  risk["signals"],
        "ai_summary":    risk["ai_summary"],
        "market":        market_info["market"],
        "macro":         market_info.get("macro", {}),
        "categories":    categories,
    }


def build_trends_weekly(today_trends: list) -> dict:
    """累積 7 天的 Google Trends 資料，按國家分組。"""
    # 載入舊的週趨勢快取
    try:
        with open(TRENDS_CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        cache = {"entries": []}

    now = datetime.now(TZ_TW)
    seven_days_ago = now - timedelta(hours=168)

    # 加入今天的趨勢
    for t in today_trends:
        cache["entries"].append({
            "title": t["title"],
            "url": t.get("url", ""),
            "source": t["source"],
            "fetched_at": now.isoformat(),
        })

    # 過濾掉超過 7 天的
    valid = []
    for e in cache["entries"]:
        try:
            fetched = datetime.fromisoformat(e["fetched_at"])
            if fetched >= seven_days_ago:
                valid.append(e)
        except Exception:
            pass
    cache["entries"] = valid

    # 儲存快取
    Path(TRENDS_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(TRENDS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    # 按國家分組，統計出現次數排名
    country_counts = {}
    for e in valid:
        src = e["source"]
        title = e["title"]
        if src not in country_counts:
            country_counts[src] = {}
        country_counts[src][title] = country_counts[src].get(title, 0) + 1

    # 排序：出現次數多的排前面
    weekly = {}
    for src, counts in country_counts.items():
        sorted_items = sorted(counts.items(), key=lambda x: -x[1])
        weekly[src] = [{"title": t, "count": c} for t, c in sorted_items[:10]]

    print(f"[Trends] 週快取 {len(valid)} 筆，{len(country_counts)} 個國家")
    return weekly


def write_json(output: dict) -> None:
    Path(NEWS_JSON_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[JSON] 已寫入 {NEWS_JSON_PATH}")


def _is_quiet_hour() -> bool:
    """判斷目前是否在勿擾時段。"""
    hour = datetime.now(TZ_TW).hour
    if QUIET_HOUR_START <= QUIET_HOUR_END:
        return QUIET_HOUR_START <= hour < QUIET_HOUR_END
    else:
        return hour >= QUIET_HOUR_START or hour < QUIET_HOUR_END


def handle_telegram(output: dict, risk: dict) -> None:
    """發送早報及重大新聞即時推播（勿擾時段不發送）。"""
    if _is_quiet_hour():
        print(f"[Telegram] 勿擾時段（{QUIET_HOUR_START}:00～{QUIET_HOUR_END}:00），跳過推播")
        return

    sent = _load_sent_ids()
    now  = datetime.now(TZ_TW)

    if now.hour == 11 and 5 <= now.minute <= 25:
        print("[Telegram] 發送每日早報...")
        send_morning_report(output, risk)

    for cat_articles in output.get("categories", {}).values():
        for a in cat_articles:
            if a.get("is_breaking") and _cooldown_ok(a["id"], sent):
                print(f"[Telegram] 重大新聞推播：{a['title'][:50]}")
                if send_breaking_news(a):
                    sent[a["id"]] = now.isoformat()

    _save_sent_ids(sent)


# ── 主流程 ────────────────────────────────────────────

def main() -> None:
    print(f"[Start] {datetime.now(TZ_TW).isoformat()}")

    cache       = _load_existing()
    articles    = fetch_all()
    articles    = enrich_articles(articles, cache)
    categories  = categorize(articles)
    market_info = get_all_market_data()
    risk        = calc_risk_score(market_info["market"], articles)
    output      = build_output(categories, market_info, risk)

    # 累積 Google Trends 週資料
    today_trends = [a for a in articles if a.get("category") == "trends"]
    output["trends_weekly"] = build_trends_weekly(today_trends)

    write_json(output)
    handle_telegram(output, risk)

    print("[Done]")


if __name__ == "__main__":
    main()
