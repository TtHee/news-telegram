#!/usr/bin/env python3
"""
One-time backfill script: re-fetch RSS + Groq summaries without
the GROQ_MAX_NEW_PER_RUN=20 limit, then generate a daily digest
with the new deep-analysis structure.

Usage:
  GROQ_API_KEY=xxx python scripts/backfill_catchup.py

After running, this script can be deleted.
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    NEWS_JSON_PATH, GROQ_RPM_SLEEP,
    GROQ_BATCH_PAUSE_SEC, INDICATOR_THRESHOLDS, MAX_AGE_HOURS,
)
from rss_fetcher import fetch_all as rss_fetch_all
from newsdata_fetcher import fetch_all as newsdata_fetch_all
from groq_summary import summarize
from groq_client import get_throttle_delay
from daily_digest import generate_daily_digest, save_daily_digest
from market_data import get_all_market_data
from risk_score import calc_risk_score
from fetch_news import (
    _load_existing, _is_expired, _is_breaking,
    _deduplicate, categorize, build_output, write_json,
    _parse_published,
)

TZ_TW = timezone(timedelta(hours=8))

# Backfill config: process more articles than normal
BACKFILL_MAX = 80           # process up to 80 articles
BACKFILL_BATCH_SIZE = 8     # pause every 8 articles
BACKFILL_BATCH_PAUSE = 25   # 25 seconds between batches


def enrich_articles_backfill(articles: list, cache: dict) -> list:
    """Like enrich_articles but with higher limits for backfill."""
    new_count = 0
    cached_count = 0

    for a in articles:
        cached = cache.get(a["id"])
        if (cached
            and not _is_expired(cached)
            and cached.get("summary_zh", "") != cached.get("title", "")
            and cached.get("ai_classified")):
            a["title"]       = cached["title"]
            a["summary_zh"]  = cached["summary_zh"]
            a["sentiment"]   = cached["sentiment"]
            a["is_breaking"] = cached.get("is_breaking", False)
            a["category"]    = cached["category"]
            a["ai_classified"] = True
            a.pop("raw_content", None)
            cached_count += 1
        else:
            if new_count >= BACKFILL_MAX:
                a.pop("raw_content", None)
                continue

            # Batch pause
            if new_count > 0 and new_count % BACKFILL_BATCH_SIZE == 0:
                print(f"  [Backfill] 已處理 {new_count} 則，暫停 {BACKFILL_BATCH_PAUSE} 秒...")
                time.sleep(BACKFILL_BATCH_PAUSE)

            title_for_groq = cached["title"] if cached and cached.get("summary_zh") else a["title"]
            content_for_groq = a.get("raw_content", "") or (cached.get("summary_zh", "") if cached else "")
            source_cat = a.get("category", "global")
            print(f"  [Groq] 補債 {new_count+1}/{BACKFILL_MAX}: [{source_cat}] {title_for_groq[:45]}")
            result = summarize(title_for_groq, content_for_groq, source_category=source_cat)
            a["title"]       = result["title_zh"]
            a["summary_zh"]  = result["summary"]
            a["sentiment"]   = result["sentiment"]
            if result.get("category"):
                a["category"] = result["category"]
            if result["summary"] != result["title_zh"]:
                a["ai_classified"] = True
            a["is_breaking"] = _is_breaking(a)
            a.pop("raw_content", None)
            new_count += 1

            adaptive_delay = get_throttle_delay()
            total_sleep = GROQ_RPM_SLEEP + adaptive_delay
            if adaptive_delay > 0:
                print(f"  [Throttle] 自適應間隔 {total_sleep:.0f}s")
            time.sleep(total_sleep)

    # Filter: remove skip category
    skip_count = sum(1 for a in articles if a.get("category") == "skip")
    if skip_count:
        print(f"[Filter] AI 判定 {skip_count} 則為不相關雜聞，已移除")
    articles = [a for a in articles if a.get("category") != "skip"]

    # Filter: remove articles without summary
    no_summary = [a for a in articles
                  if not a.get("summary_zh")
                  or a.get("summary_zh", "") == a.get("title", "")]
    if no_summary:
        print(f"[Filter] {len(no_summary)} 則無摘要，已移除")
    articles = [a for a in articles
                if a.get("summary_zh")
                and a.get("summary_zh", "") != a.get("title", "")]

    print(f"[Backfill] 新摘要 {new_count} 則，快取命中 {cached_count} 則，最終 {len(articles)} 則")
    return articles


def main() -> None:
    print(f"[Backfill Start] {datetime.now(TZ_TW).isoformat()}")
    print(f"[Backfill] 上限 {BACKFILL_MAX} 則，每 {BACKFILL_BATCH_SIZE} 則暫停 {BACKFILL_BATCH_PAUSE}s")

    cache = _load_existing()
    rss_articles = rss_fetch_all()
    newsdata_articles = newsdata_fetch_all()
    articles = _deduplicate(rss_articles + newsdata_articles)
    print(f"[Fetch] RSS {len(rss_articles)} + NewsData {len(newsdata_articles)} → 去重後 {len(articles)}")

    articles = enrich_articles_backfill(articles, cache)

    # Filter expired
    expired = [a for a in articles if _is_expired(a)]
    articles = [a for a in articles if not _is_expired(a)]
    if expired:
        print(f"[Filter] 移除 {len(expired)} 則過期文章（>{MAX_AGE_HOURS}h）")

    categories = categorize(articles)
    market_info = get_all_market_data()
    risk = calc_risk_score(market_info["market"], articles)

    # Generate digest with market data
    digest = generate_daily_digest(articles, market=market_info.get("market"))
    output = build_output(categories, market_info, risk, digest)

    write_json(output)

    # Archive
    if digest:
        save_daily_digest(digest)

    total = sum(len(v) for v in categories.values())
    print(f"[Backfill Done] {total} 則有效新聞已寫入，脈絡{'已' if digest else '未'}歸檔")


if __name__ == "__main__":
    main()
